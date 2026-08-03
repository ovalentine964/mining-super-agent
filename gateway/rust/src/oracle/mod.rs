//! Oracle Service — Submits AI analysis to MiningOracle.sol on Polygon
//!
//! Takes mineral analysis results from the Python AI engine and submits them
//! to the blockchain oracle. Handles gas estimation, retry logic, and
//! transaction confirmation.

use ethers::prelude::*;
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tracing::{info, error, warn};

/// AI analysis result from the Python engine
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MineralAnalysis {
    pub lat: f64,
    pub lon: f64,
    pub mineral_type: String,
    pub estimated_value_kes: u64,
    pub confidence: f64,       // 0.0 - 1.0
    pub source: String,        // "vision", "satellite", "geological"
    pub data_hash: String,     // SHA-256 of full analysis data
}

/// Oracle submission result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SubmissionResult {
    pub success: bool,
    pub tx_hash: Option<String>,
    pub block_number: Option<u64>,
    pub gas_used: Option<u64>,
    pub error: Option<String>,
}

/// Configuration for the oracle service
#[derive(Debug, Clone)]
pub struct OracleConfig {
    pub rpc_url: String,
    pub oracle_private_key: String,
    pub mining_oracle_address: Address,
    pub chain_id: u64,
    pub gas_limit: u64,
    pub max_retries: u32,
    pub max_fee_multiplier: f64,
}

impl OracleConfig {
    pub fn from_env() -> Self {
        Self {
            rpc_url: std::env::var("POLYGON_RPC_URL")
                .unwrap_or_else(|_| "https://polygon-rpc.com".to_string()),
            oracle_private_key: std::env::var("ORACLE_PRIVATE_KEY")
                .unwrap_or_default(),
            mining_oracle_address: std::env::var("MINING_ORACLE_ADDRESS")
                .unwrap_or_default()
                .parse()
                .unwrap_or(Address::zero()),
            chain_id: std::env::var("CHAIN_ID")
                .unwrap_or_else(|_| "137".to_string())
                .parse()
                .unwrap_or(137),
            gas_limit: 300_000,
            max_retries: 3,
            max_fee_multiplier: 2.0,
        }
    }
}

/// The oracle service
pub struct OracleService {
    config: OracleConfig,
    provider: Arc<Provider<Http>>,
    wallet: LocalWallet,
}

impl OracleService {
    pub fn new(config: OracleConfig) -> Result<Self, Box<dyn std::error::Error + Send + Sync>> {
        let provider = Arc::new(Provider::<Http>::try_from(&config.rpc_url)?);
        let wallet = config.oracle_private_key.parse::<LocalWallet>()?
            .with_chain_id(config.chain_id);

        Ok(Self { config, provider, wallet })
    }

    /// Submit mineral analysis to the blockchain oracle
    pub async fn submit_analysis(
        &self,
        analysis: &MineralAnalysis,
    ) -> SubmissionResult {
        for attempt in 1..=self.config.max_retries {
            match self.try_submit(analysis).await {
                Ok(result) => return result,
                Err(e) => {
                    warn!(
                        "Oracle submission attempt {}/{} failed: {}",
                        attempt, self.config.max_retries, e
                    );
                    if attempt < self.config.max_retries {
                        tokio::time::sleep(tokio::time::Duration::from_secs(
                            2u64.pow(attempt)
                        )).await;
                    }
                }
            }
        }

        SubmissionResult {
            success: false,
            tx_hash: None,
            block_number: None,
            gas_used: None,
            error: Some(format!("Failed after {} attempts", self.config.max_retries)),
        }
    }

    /// Try to submit analysis to the oracle (single attempt)
    async fn try_submit(
        &self,
        analysis: &MineralAnalysis,
    ) -> Result<SubmissionResult, Box<dyn std::error::Error + Send + Sync>> {
        // Calculate location hash (keccak256 of lat, lon)
        let lat_scaled = (analysis.lat * 1e6) as u64;
        let lon_scaled = (analysis.lon * 1e6) as u64;
        let location_hash = H256::from(ethers::utils::keccak256(
            &ethers::abi::encode(&[
                Token::Uint(U256::from(lat_scaled)),
                Token::Uint(U256::from(lon_scaled)),
            ])
        ));

        let confidence_bps = (analysis.confidence * 10000.0) as u64;
        let data_hash = H256::from_slice(
            &hex::decode(&analysis.data_hash).unwrap_or([0u8; 32])
        );

        // Build the function call
        let function = ethers::abi::Function {
            name: "submitData".to_string(),
            inputs: vec![
                ethers::abi::Param { name: "locationHash".to_string(), kind: ethers::abi::ParamType::FixedBytes(32), internal_type: None },
                ethers::abi::Param { name: "mineralType".to_string(), kind: ethers::abi::ParamType::String, internal_type: None },
                ethers::abi::Param { name: "estimatedValueKES".to_string(), kind: ethers::abi::ParamType::Uint(256), internal_type: None },
                ethers::abi::Param { name: "confidenceBps".to_string(), kind: ethers::abi::ParamType::Uint(256), internal_type: None },
                ethers::abi::Param { name: "dataHash".to_string(), kind: ethers::abi::ParamType::FixedBytes(32), internal_type: None },
            ],
            outputs: vec![],
            constant: None,
            state_mutability: ethers::abi::StateMutability::NonPayable,
        };

        let data = function.encode_input(&[
            Token::FixedBytes(location_hash.as_bytes().to_vec()),
            Token::String(analysis.mineral_type.clone()),
            Token::Uint(U256::from(analysis.estimated_value_kes)),
            Token::Uint(U256::from(confidence_bps)),
            Token::FixedBytes(data_hash.as_bytes().to_vec()),
        ])?;

        // Get gas price
        let gas_price = self.provider.get_gas_price().await?;
        let max_fee = gas_price * 2;

        // Build transaction
        let tx = TransactionRequest::new()
            .to(self.config.mining_oracle_address)
            .data(data)
            .gas(self.config.gas_limit)
            .gas_price(max_fee)
            .chain_id(self.config.chain_id);

        // Sign and send
        let signed = self.wallet.sign_transaction(&tx).await?;
        let pending_tx = self.provider.send_raw_transaction(signed).await?;

        info!("Oracle submission sent: {:?}", pending_tx.tx_hash());

        // Wait for confirmation
        let receipt = pending_tx.await?
            .ok_or("Transaction receipt not found")?;

        let result = SubmissionResult {
            success: receipt.status == Some(U64::from(1)),
            tx_hash: Some(format!("{:?}", receipt.transaction_hash)),
            block_number: receipt.block_number.map(|b| b.as_u64()),
            gas_used: receipt.gas_used.map(|g| g.as_u64()),
            error: if receipt.status == Some(U64::from(1)) {
                None
            } else {
                Some("Transaction reverted".to_string())
            },
        };

        info!(
            "Oracle submission confirmed: tx={}, block={}, gas={}",
            result.tx_hash.as_deref().unwrap_or("?"),
            result.block_number.unwrap_or(0),
            result.gas_used.unwrap_or(0)
        );

        Ok(result)
    }

    /// Check oracle service health
    pub async fn health_check(&self) -> serde_json::Value {
        let connected = self.provider.get_block_number().await.is_ok();
        let balance = self.provider.get_balance(self.wallet.address(), None).await;
        let balance_matic = balance
            .map(|b| ethers::utils::format_ether(b).to_string())
            .unwrap_or_else(|_| "unknown".to_string());

        serde_json::json!({
            "connected": connected,
            "oracle_address": format!("{:?}", self.wallet.address()),
            "balance_matic": balance_matic,
            "contract_address": format!("{:?}", self.config.mining_oracle_address),
            "chain_id": self.config.chain_id,
        })
    }
}
