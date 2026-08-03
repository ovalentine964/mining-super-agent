//! Request/response types for the oracle service.

use serde::{Deserialize, Serialize};

// ──────────────────────── Request Types ────────────────────────

/// Observation submitted by the Python AI engine.
#[derive(Debug, Clone, Deserialize)]
pub struct ObservationRequest {
    /// GPS latitude (-90 to 90)
    pub lat: f64,
    /// GPS longitude (-180 to 180)
    pub lon: f64,
    /// Mineral type: "gold", "copper", "titanium", etc.
    pub mineral_type: String,
    /// Estimated value in Kenyan Shillings
    pub estimated_value_kes: u64,
    /// AI confidence score (0.0 - 1.0)
    pub confidence: f64,
    /// Data source: "vision", "satellite", "geological", "market"
    #[serde(default)]
    pub source: String,
    /// Raw analysis data for on-chain integrity hash
    #[serde(default)]
    pub raw_data: serde_json::Value,
}

// ──────────────────────── Response Types ────────────────────────

/// Result of a successful on-chain oracle submission.
#[derive(Debug, Clone, Serialize)]
pub struct SubmissionResult {
    pub success: bool,
    pub tx_hash: String,
    pub block_number: u64,
    pub gas_used: u64,
    pub effective_gas_price: String,
    pub location_hash: String,
    pub mineral_type: String,
    pub confidence_bps: u64,
    pub nonce: u64,
    pub attempt: u32,
}

/// Oracle wallet status.
#[derive(Debug, Clone, Serialize)]
pub struct OracleStatus {
    pub connected: bool,
    pub chain_id: u64,
    pub latest_block: u64,
    pub oracle_address: String,
    pub balance_matic: String,
    pub balance_warning: bool,
    pub pending_nonce: u64,
    pub contract_address: String,
}

/// Transaction receipt info.
#[derive(Debug, Clone, Serialize)]
pub struct TxReceiptInfo {
    pub tx_hash: String,
    pub block_number: u64,
    pub gas_used: u64,
    pub effective_gas_price: String,
    pub status: String, // "success" or "reverted"
    pub from: String,
    pub to: String,
}

// ──────────────────────── Internal Types ────────────────────────

/// Result of a gas estimation.
#[derive(Debug, Clone)]
pub struct GasEstimate {
    pub max_fee_per_gas: ethers::types::U256,
    pub max_priority_fee_per_gas: ethers::types::U256,
    pub gas_limit: ethers::types::U256,
}

impl GasEstimate {
    /// Return a human-readable summary for logging.
    pub fn summary(&self) -> String {
        format!(
            "gas_limit={} max_fee={} gwei priority={} gwei",
            self.gas_limit,
            self.max_fee_per_gas / ethers::types::U256::from(1_000_000_000u64),
            self.max_priority_fee_per_gas / ethers::types::U256::from(1_000_000_000u64),
        )
    }
}
