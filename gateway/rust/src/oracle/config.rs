//! Oracle configuration — loaded from environment variables.

use serde::Deserialize;
use std::env;

/// Configuration for the Polygon oracle service.
#[derive(Debug, Clone, Deserialize)]
pub struct OracleConfig {
    /// Polygon RPC endpoint (Alchemy, Infura, QuickNode, or public).
    /// Env: `POLYGON_RPC_URL` (default: `https://polygon-rpc.com`)
    pub rpc_url: String,

    /// Oracle wallet private key (hex, with or without 0x prefix).
    /// Env: `ORACLE_PRIVATE_KEY` (required)
    pub private_key: String,

    /// MiningOracle.sol contract address.
    /// Env: `MINING_ORACLE_ADDRESS` (required)
    pub oracle_contract_address: String,

    /// Chain ID: 137 (Polygon mainnet) or 80001 (Mumbai testnet).
    /// Env: `CHAIN_ID` (default: 137)
    pub chain_id: u64,

    /// Default gas limit for contract calls.
    /// Env: `ORACLE_GAS_LIMIT` (default: 300_000)
    pub gas_limit: u64,

    /// Maximum fee multiplier for EIP-1559 (multiplied by base fee).
    /// Env: `ORACLE_MAX_FEE_MULTIPLIER` (default: 2.0)
    pub max_fee_multiplier: f64,

    /// Priority fee in gwei for EIP-1559.
    /// Env: `ORACLE_PRIORITY_FEE_GWEI` (default: 30)
    pub priority_fee_gwei: u64,

    /// Maximum number of retry attempts for failed transactions.
    /// Env: `ORACLE_MAX_RETRIES` (default: 3)
    pub max_retries: u32,

    /// Base delay in milliseconds between retries (exponential backoff).
    /// Env: `ORACLE_RETRY_BASE_MS` (default: 2000)
    pub retry_base_ms: u64,

    /// Timeout in seconds to wait for transaction confirmation.
    /// Env: `ORACLE_TX_TIMEOUT_SECS` (default: 120)
    pub tx_timeout_secs: u64,

    /// Minimum MATIC balance before warning (in wei).
    /// Env: `ORACLE_MIN_BALANCE_WEI` (default: 0.1 MATIC)
    pub min_balance_warning_wei: String,
}

impl OracleConfig {
    /// Load from environment variables. Returns `Err` if required vars are missing.
    pub fn from_env() -> Result<Self, String> {
        let rpc_url = env::var("POLYGON_RPC_URL")
            .unwrap_or_else(|_| "https://polygon-rpc.com".to_string());

        let private_key = env::var("ORACLE_PRIVATE_KEY")
            .map_err(|_| "ORACLE_PRIVATE_KEY must be set".to_string())?;

        let oracle_contract_address = env::var("MINING_ORACLE_ADDRESS")
            .map_err(|_| "MINING_ORACLE_ADDRESS must be set".to_string())?;

        let chain_id: u64 = env::var("CHAIN_ID")
            .unwrap_or_else(|_| "137".to_string())
            .parse()
            .map_err(|_| "CHAIN_ID must be a valid u64".to_string())?;

        let gas_limit: u64 = env::var("ORACLE_GAS_LIMIT")
            .unwrap_or_else(|_| "300000".to_string())
            .parse()
            .unwrap_or(300_000);

        let max_fee_multiplier: f64 = env::var("ORACLE_MAX_FEE_MULTIPLIER")
            .unwrap_or_else(|_| "2.0".to_string())
            .parse()
            .unwrap_or(2.0);

        let priority_fee_gwei: u64 = env::var("ORACLE_PRIORITY_FEE_GWEI")
            .unwrap_or_else(|_| "30".to_string())
            .parse()
            .unwrap_or(30);

        let max_retries: u32 = env::var("ORACLE_MAX_RETRIES")
            .unwrap_or_else(|_| "3".to_string())
            .parse()
            .unwrap_or(3);

        let retry_base_ms: u64 = env::var("ORACLE_RETRY_BASE_MS")
            .unwrap_or_else(|_| "2000".to_string())
            .parse()
            .unwrap_or(2000);

        let tx_timeout_secs: u64 = env::var("ORACLE_TX_TIMEOUT_SECS")
            .unwrap_or_else(|_| "120".to_string())
            .parse()
            .unwrap_or(120);

        // 0.1 MATIC minimum balance warning
        let min_balance_warning_wei = env::var("ORACLE_MIN_BALANCE_WEI")
            .unwrap_or_else(|_| "100000000000000000".to_string()); // 0.1 MATIC

        Ok(OracleConfig {
            rpc_url,
            private_key,
            oracle_contract_address,
            chain_id,
            gas_limit,
            max_fee_multiplier,
            priority_fee_gwei,
            max_retries,
            retry_base_ms,
            tx_timeout_secs,
            min_balance_warning_wei,
        })
    }
}
