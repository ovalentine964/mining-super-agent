//! Polygon client — ethers-rs wrapper for MiningOracle.sol interactions.
//!
//! Handles:
//! - Wallet / signer initialization from private key
//! - EIP-1559 gas estimation with dynamic pricing
//! - ABI encoding for MiningOracle.submitData()
//! - Transaction submission with retry
//! - Nonce management
//! - Transaction confirmation polling

use anyhow::{anyhow, Context, Result};
use ethers::{
    abi::{self, Token},
    middleware::SignerMiddleware,
    providers::{Http, Middleware, Provider},
    signers::{LocalWallet, Signer},
    types::{
        transaction::eip2718::TypedTransaction, Address, Bytes, Eip1559TransactionRequest,
        H256, U256,
    },
};
use sha2::{Digest, Sha256};
use std::sync::Arc;
use tracing::{debug, error, info, warn};

use super::config::OracleConfig;
use super::retry::{is_retryable_error, is_retryable_pending_error, RetryPolicy};
use super::types::*;

/// Minimal ABI for MiningOracle.submitData(bytes32,string,uint256,uint256,bytes32).
///
/// We build the call manually via ethers::abi to avoid a full ABI JSON dependency.
/// The function selector is the first 4 bytes of keccak256(
///   "submitData(bytes32,string,uint256,uint256,bytes32)"
/// ) = 0x2c940588 (computed below at compile time).
const SUBMIT_DATA_SIGNATURE: &str = "submitData(bytes32,string,uint256,uint256,bytes32)";

/// Core oracle service — wraps ethers-rs provider + signer + config.
pub struct OracleService {
    config: OracleConfig,
    /// The ethers middleware (provider + signer).
    client: Arc<SignerMiddleware<Provider<Http>, LocalWallet>>,
    /// Oracle wallet address (derived from private key).
    oracle_address: Address,
    /// MiningOracle contract address.
    contract_address: Address,
    /// Retry policy.
    retry: RetryPolicy,
}

impl OracleService {
    /// Create a new oracle service from config.
    ///
    /// Initializes the ethers provider, derives the wallet, and validates
    /// the RPC connection.
    pub async fn new(config: OracleConfig) -> Result<Self> {
        // Parse private key
        let key_hex = config.private_key.trim_start_matches("0x");
        let wallet: LocalWallet = key_hex
            .parse::<LocalWallet>()
            .map_err(|e| anyhow!("Invalid ORACLE_PRIVATE_KEY: {}", e))?
            .with_chain_id(config.chain_id);

        let oracle_address = wallet.address();
        info!(address = ?oracle_address, "Oracle wallet loaded");

        // Connect to Polygon RPC
        let provider = Provider::<Http>::try_from(&config.rpc_url)
            .context("Failed to connect to Polygon RPC")?;

        // Verify chain ID
        let network = provider
            .get_chainid()
            .await
            .context("Failed to fetch chain ID from RPC")?;
        if network.as_u64() != config.chain_id {
            warn!(
                expected = config.chain_id,
                actual = network.as_u64(),
                "Chain ID mismatch — transactions may fail"
            );
        }

        let client = Arc::new(SignerMiddleware::new(provider, wallet));

        let contract_address: Address = config
            .oracle_contract_address
            .parse()
            .map_err(|_| anyhow!("Invalid MINING_ORACLE_ADDRESS: {}", config.oracle_contract_address))?;

        let retry = RetryPolicy::new(config.max_retries, config.retry_base_ms);

        info!(
            rpc = %config.rpc_url,
            chain_id = config.chain_id,
            contract = ?contract_address,
            "Polygon oracle service initialized"
        );

        Ok(OracleService {
            config,
            client,
            oracle_address,
            contract_address,
            retry,
        })
    }

    // ──────────────────── Public API ────────────────────

    /// Submit an AI observation to MiningOracle.submitData().
    ///
    /// This is the main entry point called by the REST handler.
    /// Handles gas estimation, signing, submission, and confirmation.
    pub async fn submit_observation(
        &self,
        obs: ObservationRequest,
    ) -> Result<SubmissionResult> {
        // 1. Derive on-chain parameters
        let location_hash = self.compute_location_hash(obs.lat, obs.lon);
        let data_hash = self.compute_data_hash(&obs.raw_data);
        let confidence_bps = (obs.confidence * 10000.0).round() as u64;

        info!(
            location_hash = format!("0x{}", hex::encode(location_hash)),
            mineral_type = %obs.mineral_type,
            confidence_bps = confidence_bps,
            estimated_value_kes = obs.estimated_value_kes,
            "Preparing oracle submission"
        );

        // 2. Build calldata for submitData(bytes32,string,uint256,uint256,bytes32)
        let calldata = self.encode_submit_data(
            location_hash,
            &obs.mineral_type,
            obs.estimated_value_kes,
            confidence_bps,
            data_hash,
        );

        // 3. Submit with retry
        let client = self.client.clone();
        let contract_addr = self.contract_address;
        let gas_limit = U256::from(self.config.gas_limit);
        let max_fee_mult = self.config.max_fee_multiplier;
        let priority_fee_gwei = self.config.priority_fee_gwei;
        let oracle_addr = self.oracle_address;

        let result = self
            .retry
            .execute(
                || {
                    let client = client.clone();
                    let calldata = calldata.clone();
                    async move {
                        Self::send_transaction(
                            &client,
                            contract_addr,
                            calldata,
                            gas_limit,
                            max_fee_mult,
                            priority_fee_gwei,
                        )
                        .await
                    }
                },
                |e| {
                    // Retry on provider errors that are transient
                    if let Some(provider_err) = e.downcast_ref::<ethers::providers::ProviderError>()
                    {
                        is_retryable_error(provider_err)
                    } else {
                        false
                    }
                },
                "submit_observation",
            )
            .await?;

        Ok(SubmissionResult {
            success: true,
            tx_hash: format!("0x{}", hex::encode(result.tx_hash.as_bytes())),
            block_number: result.block_number,
            gas_used: result.gas_used,
            effective_gas_price: result.effective_gas_price,
            location_hash: format!("0x{}", hex::encode(location_hash)),
            mineral_type: obs.mineral_type,
            confidence_bps,
            nonce: result.nonce,
            attempt: result.attempt,
        })
    }

    /// Get oracle wallet status (balance, nonce, chain info).
    pub async fn get_status(&self) -> Result<OracleStatus> {
        let block = self
            .client
            .provider()
            .get_block_number()
            .await
            .context("Failed to get block number")?;

        let balance = self
            .client
            .provider()
            .get_balance(self.oracle_address, None)
            .await
            .context("Failed to get balance")?;

        let nonce = self
            .client
            .provider()
            .get_transaction_count(self.oracle_address, None)
            .await
            .context("Failed to get nonce")?;

        let min_balance: U256 = self.config.min_balance_warning_wei.parse().unwrap_or_default();
        let balance_warning = balance < min_balance;

        if balance_warning {
            warn!(
                balance_matic = format!("{}", balance.as_u64() as f64 / 1e18),
                "Oracle balance below minimum threshold!"
            );
        }

        Ok(OracleStatus {
            connected: true,
            chain_id: self.config.chain_id,
            latest_block: block.as_u64(),
            oracle_address: format!("{:?}", self.oracle_address),
            balance_matic: format!("{}", balance.as_u64() as f64 / 1e18),
            balance_warning,
            pending_nonce: nonce.as_u64(),
            contract_address: format!("{:?}", self.contract_address),
        })
    }

    /// Look up a transaction receipt by hash.
    pub async fn get_transaction_receipt(
        &self,
        tx_hash_hex: &str,
    ) -> Result<Option<TxReceiptInfo>> {
        let hash: H256 = tx_hash_hex
            .trim_start_matches("0x")
            .parse()
            .map_err(|_| anyhow!("Invalid transaction hash: {}", tx_hash_hex))?;

        let receipt = self
            .client
            .provider()
            .get_transaction_receipt(hash)
            .await
            .context("Failed to fetch transaction receipt")?;

        Ok(receipt.map(|r| TxReceiptInfo {
            tx_hash: format!("0x{}", hex::encode(r.transaction_hash.as_bytes())),
            block_number: r.block_number.map(|b| b.as_u64()).unwrap_or(0),
            gas_used: r.gas_used.map(|g| g.as_u64()).unwrap_or(0),
            effective_gas_price: r
                .effective_gas_price
                .map(|p| format!("{}", p.as_u64()))
                .unwrap_or_default(),
            status: match r.status.map(|s| s.as_u64()) {
                Some(1) => "success".to_string(),
                Some(0) => "reverted".to_string(),
                _ => "unknown".to_string(),
            },
            from: format!("{:?}", r.from),
            to: r
                .to
                .map(|t| format!("{:?}", t))
                .unwrap_or_else(|| "contract_creation".to_string()),
        }))
    }

    /// Lightweight health check — just verifies RPC connectivity.
    pub async fn health_check(&self) -> Result<bool> {
        match self.client.provider().get_block_number().await {
            Ok(_) => Ok(true),
            Err(e) => {
                warn!(error = %e, "Oracle health check failed");
                Ok(false)
            }
        }
    }

    // ──────────────────── Internals ────────────────────

    /// Compute the on-chain location hash: keccak256(uint256(lat*1e6), uint256(lon*1e6)).
    ///
    /// Matches the Python oracle bridge's `Web3.solidity_keccak` call.
    fn compute_location_hash(&self, lat: f64, lon: f64) -> [u8; 32] {
        let lat_scaled = (lat * 1e6).round() as i64;
        let lon_scaled = (lon * 1e6).round() as i64;

        // Encode as ABI uint256 (signed integers cast to U256)
        let mut encoded = Vec::with_capacity(64);
        encoded.extend_from_slice(&abi::encode(&[
            Token::Int(U256::from(lat_scaled)),
            Token::Int(U256::from(lon_scaled)),
        ]));

        let hash = ethers::utils::keccak256(&encoded);
        hash
    }

    /// Compute the data integrity hash: SHA-256 of canonical JSON.
    ///
    /// Matches the Python oracle bridge's `_hash_data` method.
    fn compute_data_hash(&self, data: &serde_json::Value) -> [u8; 32] {
        // Canonical JSON: sorted keys, no whitespace
        let canonical = serde_json::to_string(data).unwrap_or_default();
        let mut hasher = Sha256::new();
        hasher.update(canonical.as_bytes());
        let result = hasher.finalize();
        let mut hash = [0u8; 32];
        hash.copy_from_slice(&result);
        hash
    }

    /// Encode calldata for MiningOracle.submitData(bytes32,string,uint256,uint256,bytes32).
    fn encode_submit_data(
        &self,
        location_hash: [u8; 32],
        mineral_type: &str,
        estimated_value_kes: u64,
        confidence_bps: u64,
        data_hash: [u8; 32],
    ) -> Bytes {
        // Function selector: first 4 bytes of keccak256(signature)
        let selector = &ethers::utils::id(SUBMIT_DATA_SIGNATURE)[..4];

        // ABI encode the parameters
        let encoded = abi::encode(&[
            Token::FixedBytes(location_hash.to_vec()),
            Token::String(mineral_type.to_string()),
            Token::Uint(U256::from(estimated_value_kes)),
            Token::Uint(U256::from(confidence_bps)),
            Token::FixedBytes(data_hash.to_vec()),
        ]);

        // Combine selector + encoded params
        let mut calldata = Vec::with_capacity(4 + encoded.len());
        calldata.extend_from_slice(selector);
        calldata.extend_from_slice(&encoded);

        Bytes::from(calldata)
    }

    /// Estimate gas and build an EIP-1559 transaction, then send it.
    ///
    /// Returns the tx hash, nonce, and waits for confirmation.
    async fn send_transaction(
        client: &Arc<SignerMiddleware<Provider<Http>, LocalWallet>>,
        to: Address,
        data: Bytes,
        gas_limit: U256,
        max_fee_multiplier: f64,
        priority_fee_gwei: u64,
    ) -> Result<TransactionReceipt> {
        let provider = client.provider();

        // Get current nonce
        let nonce = provider
            .get_transaction_count(client.address(), None)
            .await
            .context("Failed to get nonce")?;

        // EIP-1559 gas estimation
        let (max_fee_per_gas, max_priority_fee_per_gas) =
            Self::estimate_gas_prices(provider, max_fee_multiplier, priority_fee_gwei).await?;

        // Try to estimate actual gas usage, fall back to configured limit
        let estimated_gas = {
            let tx = Eip1559TransactionRequest::new()
                .to(to)
                .data(data.clone())
                .from(client.address());

            match provider
                .estimate_gas(&TypedTransaction::Eip1559(tx), None)
                .await
            {
                Ok(gas) => {
                    // Add 20% buffer
                    let buffered = gas * 120 / 100;
                    debug!(estimated = %gas, buffered = %buffered, "Gas estimated");
                    buffered.min(gas_limit) // Never exceed configured limit
                }
                Err(e) => {
                    warn!(error = %e, "Gas estimation failed — using configured limit");
                    gas_limit
                }
            }
        };

        // Build EIP-1559 transaction
        let tx = Eip1559TransactionRequest::new()
            .to(to)
            .data(data)
            .value(U256::zero())
            .nonce(nonce)
            .gas(estimated_gas)
            .max_fee_per_gas(max_fee_per_gas)
            .max_priority_fee_per_gas(max_priority_fee_per_gas)
            .chain_id(client.signer().chain_id());

        let typed_tx = TypedTransaction::Eip1559(tx);

        debug!(
            nonce = %nonce,
            max_fee = %max_fee_per_gas,
            priority_fee = %max_priority_fee_per_gas,
            gas_limit = %estimated_gas,
            "Sending transaction"
        );

        // Sign and send
        let pending_tx = client
            .send_transaction(typed_tx, None)
            .await
            .context("Failed to send transaction")?;

        let tx_hash = *pending_tx;
        info!(tx_hash = format!("0x{}", hex::encode(tx_hash.as_bytes())), "Transaction submitted");

        // Wait for confirmation
        let receipt = pending_tx
            .await
            .context("Transaction confirmation failed (timeout or dropped)")?;

        match receipt {
            Some(r) => {
                let block = r.block_number.map(|b| b.as_u64()).unwrap_or(0);
                let gas = r.gas_used.map(|g| g.as_u64()).unwrap_or(0);
                let status = r.status.map(|s| s.as_u64()).unwrap_or(0);

                if status == 0 {
                    return Err(anyhow!(
                        "Transaction reverted: tx=0x{}",
                        hex::encode(r.transaction_hash.as_bytes())
                    ));
                }

                info!(
                    tx_hash = format!("0x{}", hex::encode(r.transaction_hash.as_bytes())),
                    block = block,
                    gas_used = gas,
                    "Transaction confirmed"
                );

                Ok(TransactionReceipt {
                    tx_hash: r.transaction_hash,
                    block_number: block,
                    gas_used: gas,
                    effective_gas_price: r
                        .effective_gas_price
                        .map(|p| format!("{}", p.as_u64()))
                        .unwrap_or_default(),
                    nonce: nonce.as_u64(),
                    attempt: 1, // Caller tracks retries
                })
            }
            None => Err(anyhow!("Transaction dropped from mempool")),
        }
    }

    /// Estimate EIP-1559 gas prices from the current network state.
    ///
    /// Uses `eth_feeHistory` for base fee + configured priority fee.
    async fn estimate_gas_prices(
        provider: &Provider<Http>,
        max_fee_multiplier: f64,
        priority_fee_gwei: u64,
    ) -> Result<(U256, U256)> {
        // Try fee history for accurate base fee
        let base_fee = match provider
            .request::<_, ethers::types::FeeHistory>(
                "eth_feeHistory",
                (4u64, "latest", &[25.0, 75.0]),
            )
            .await
        {
            Ok(history) => {
                // Use the latest base fee per gas
                history
                    .base_fee_per_gas
                    .last()
                    .copied()
                    .unwrap_or_else(|| U256::from(30_000_000_000u64)) // 30 gwei fallback
            }
            Err(e) => {
                warn!(error = %e, "eth_feeHistory failed — using fallback base fee");
                // Fallback: get current gas price and estimate base fee
                let gas_price = provider
                    .get_gas_price()
                    .await
                    .unwrap_or_else(|_| U256::from(50_000_000_000u64)); // 50 gwei
                gas_price
            }
        };

        let max_priority_fee = U256::from(priority_fee_gwei) * U256::from(1_000_000_000u64);
        let max_fee = base_fee * U256::from((max_fee_multiplier * 100.0) as u64) / U256::from(100)
            + max_priority_fee;

        debug!(
            base_fee_gwei = %base_fee.as_u64() / 1_000_000_000,
            max_fee_gwei = %max_fee.as_u64() / 1_000_000_000,
            priority_fee_gwei = priority_fee_gwei,
            "Gas prices estimated"
        );

        Ok((max_fee, max_priority_fee))
    }
}

/// Internal transaction receipt used between retry attempts.
struct TransactionReceipt {
    tx_hash: H256,
    block_number: u64,
    gas_used: u64,
    effective_gas_price: String,
    nonce: u64,
    attempt: u32,
}
