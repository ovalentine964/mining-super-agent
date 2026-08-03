//! Blockchain event type definitions for the Sovereign Resource DAO.
//!
//! Each struct corresponds to a Solidity event emitted by the on-chain contracts.
//! Event signatures are computed as keccak256 of the canonical Solidity event string.

use ethers::types::{Address, H256, U256};
use serde::{Deserialize, Serialize};

// ═══════════════════════════════════════════════════════════════════════════════
// Event Signatures (keccak256 hashes)
// ═══════════════════════════════════════════════════════════════════════════════

/// ExtractionRecorded(uint256,address,bytes32,string,uint8)
pub const EXTRACTION_RECORDED_SIG: H256 = H256(ethers::types::H256([
    0xd3, 0x3c, 0xae, 0x16, 0x5b, 0x4b, 0xc5, 0x59,
    0x1e, 0x85, 0x0b, 0xb2, 0xd0, 0x1b, 0x56, 0x32,
    0x82, 0xba, 0xab, 0x9b, 0xa1, 0x7f, 0x2a, 0x8c,
    0x1c, 0x4b, 0x20, 0x6f, 0x40, 0xf3, 0xd2, 0x0b,
]));

/// ExtractionVerified(uint256,address,uint8,uint256)
pub const EXTRACTION_VERIFIED_SIG: H256 = H256(ethers::types::H256([
    0x6a, 0x01, 0xd8, 0xc5, 0x39, 0xf3, 0xb0, 0x40,
    0x0b, 0x74, 0x1c, 0x88, 0x10, 0xf9, 0xc2, 0x2e,
    0x71, 0x57, 0xa3, 0xd1, 0xd8, 0xb3, 0x26, 0x34,
    0x0b, 0x9e, 0x6b, 0xd5, 0xc1, 0xd0, 0x93, 0x67,
]));

/// ExtractionDisputed(uint256,address,string)
pub const EXTRACTION_DISPUTED_SIG: H256 = H256(ethers::types::H256([
    0x29, 0x4b, 0xc3, 0x36, 0xf8, 0x1a, 0x7e, 0x29,
    0xc2, 0xa0, 0xf0, 0xb6, 0x11, 0x74, 0xd4, 0x17,
    0xe5, 0xa6, 0x77, 0x14, 0x41, 0x50, 0x32, 0x54,
    0xd2, 0x1a, 0x58, 0x3c, 0xd5, 0x46, 0xf7, 0xab,
]));

/// RevenueDistributed(address,uint8,uint256,uint256,uint256,uint256,uint256)
pub const REVENUE_DISTRIBUTED_SIG: H256 = H256(ethers::types::H256([
    0x5e, 0xf7, 0xb2, 0xdf, 0x4c, 0x19, 0xc3, 0xd7,
    0x99, 0x8d, 0xa8, 0x09, 0xc5, 0xa5, 0xd5, 0xf2,
    0x51, 0x1b, 0xf8, 0x3e, 0xa7, 0xab, 0x92, 0x3c,
    0x1c, 0x02, 0x31, 0x76, 0x0e, 0xb5, 0xf7, 0x21,
]));

/// SplitPercentagesUpdated(uint256,uint256,uint256,uint256)
pub const SPLIT_UPDATED_SIG: H256 = H256(ethers::types::H256([
    0x72, 0x34, 0x26, 0xf8, 0xd1, 0x05, 0xf2, 0x42,
    0x12, 0x65, 0xc4, 0xb0, 0x9b, 0xb3, 0x15, 0x0f,
    0x57, 0xfe, 0xd9, 0xb7, 0x35, 0x40, 0x46, 0x8d,
    0x05, 0xa4, 0xb5, 0x14, 0x83, 0x89, 0xc8, 0xf7,
]));

/// DestinationUpdated(address,string,uint256)
pub const DESTINATION_UPDATED_SIG: H256 = H256(ethers::types::H256([
    0xb3, 0x02, 0x82, 0x6d, 0xa4, 0xf4, 0x80, 0x3c,
    0x11, 0x15, 0x88, 0xd6, 0xf5, 0x52, 0x42, 0x17,
    0x23, 0xe9, 0x49, 0x68, 0xd0, 0xb6, 0xca, 0xa0,
    0x71, 0xd3, 0xcd, 0xab, 0x29, 0x1a, 0x5f, 0x41,
]));

/// VoteCast(uint256,address,uint256,uint256,bool)
pub const VOTE_CAST_SIG: H256 = H256(ethers::types::H256([
    0xc0, 0xd6, 0xc3, 0xc2, 0xa0, 0xd6, 0xca, 0xf6,
    0xa3, 0x89, 0x01, 0xb8, 0x8a, 0x75, 0x6b, 0x82,
    0x1a, 0xf0, 0xb3, 0xe5, 0xf5, 0x70, 0x07, 0x1b,
    0x79, 0x76, 0xc9, 0x2c, 0x64, 0xf7, 0xe1, 0x4a,
]));

/// VoteWithdrawn(uint256,address,uint256)
pub const VOTE_WITHDRAWN_SIG: H256 = H256(ethers::types::H256([
    0x7f, 0x5a, 0x58, 0x9b, 0x34, 0xe1, 0xf3, 0x25,
    0x81, 0x5c, 0x80, 0x9b, 0xb8, 0x0f, 0x32, 0x0a,
    0xb6, 0xd8, 0x96, 0x11, 0x4d, 0x8a, 0x81, 0xd2,
    0x53, 0xa3, 0xf0, 0x8f, 0x25, 0xb3, 0xf4, 0xa8,
]));

/// OracleSubmitted(bytes32,address,string,uint256)
pub const ORACLE_SUBMITTED_SIG: H256 = H256(ethers::types::H256([
    0x3e, 0x7b, 0x8c, 0xd5, 0x57, 0xa1, 0x41, 0x6f,
    0xd4, 0xf6, 0x1f, 0xb9, 0x29, 0xc5, 0x2e, 0xb7,
    0x42, 0x9d, 0x3b, 0x58, 0x4a, 0x38, 0x9c, 0x6f,
    0x1e, 0x41, 0x52, 0xb5, 0xd7, 0x8a, 0x39, 0x44,
]));

/// LocationVerified(bytes32,uint256,uint256)
pub const LOCATION_VERIFIED_SIG: H256 = H256(ethers::types::H256([
    0xc5, 0x93, 0x42, 0x76, 0xa0, 0x71, 0x28, 0x21,
    0xf0, 0x5b, 0x2e, 0xd8, 0x67, 0x1a, 0x3d, 0x4e,
    0xf7, 0x88, 0x79, 0x3a, 0x69, 0x11, 0x47, 0x85,
    0xab, 0x95, 0x5e, 0xd5, 0x83, 0xf0, 0xa7, 0x3c,
]));

// ═══════════════════════════════════════════════════════════════════════════════
// Parsed Event Structs
// ═══════════════════════════════════════════════════════════════════════════════

/// Verification status enum matching the Solidity enum
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[repr(u8)]
pub enum VerificationStatus {
    Unverified = 0,
    OracleVerified = 1,
    CommunityConfirmed = 2,
    Disputed = 3,
}

impl From<u8> for VerificationStatus {
    fn from(v: u8) -> Self {
        match v {
            0 => Self::Unverified,
            1 => Self::OracleVerified,
            2 => Self::CommunityConfirmed,
            3 => Self::Disputed,
            _ => Self::Unverified,
        }
    }
}

impl std::fmt::Display for VerificationStatus {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Unverified => write!(f, "unverified"),
            Self::OracleVerified => write!(f, "oracle_verified"),
            Self::CommunityConfirmed => write!(f, "community_confirmed"),
            Self::Disputed => write!(f, "disputed"),
        }
    }
}

/// Royalty source enum matching the Solidity enum
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[repr(u8)]
pub enum RoyaltySource {
    DataLicensing = 0,
    Extraction = 1,
    PlatformFee = 2,
    Donation = 3,
    Recovery = 4,
}

impl From<u8> for RoyaltySource {
    fn from(v: u8) -> Self {
        match v {
            0 => Self::DataLicensing,
            1 => Self::Extraction,
            2 => Self::PlatformFee,
            3 => Self::Donation,
            4 => Self::Recovery,
            _ => Self::DataLicensing,
        }
    }
}

impl std::fmt::Display for RoyaltySource {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::DataLicensing => write!(f, "data_licensing"),
            Self::Extraction => write!(f, "extraction"),
            Self::PlatformFee => write!(f, "platform_fee"),
            Self::Donation => write!(f, "donation"),
            Self::Recovery => write!(f, "recovery"),
        }
    }
}

// ── ExtractionTracker events ──────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExtractionRecorded {
    pub record_id: U256,
    pub submitter: Address,
    pub location_hash: H256,
    pub mineral_type: String,
    pub status: VerificationStatus,
    pub block_number: u64,
    pub tx_hash: H256,
    pub log_index: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExtractionVerified {
    pub record_id: U256,
    pub oracle: Address,
    pub new_status: VerificationStatus,
    pub confidence_score: U256,
    pub block_number: u64,
    pub tx_hash: H256,
    pub log_index: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExtractionDisputed {
    pub record_id: U256,
    pub disputer: Address,
    pub reason: String,
    pub block_number: u64,
    pub tx_hash: H256,
    pub log_index: u64,
}

// ── RoyaltyDistributor events ─────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RevenueDistributed {
    pub payer: Address,
    pub source: RoyaltySource,
    pub total_amount: U256,
    pub community_dev_share: U256,
    pub community_wallet_share: U256,
    pub reserve_share: U256,
    pub timestamp: U256,
    pub block_number: u64,
    pub tx_hash: H256,
    pub log_index: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SplitPercentagesUpdated {
    pub new_dev_bps: U256,
    pub new_wallet_bps: U256,
    pub new_reserve_bps: U256,
    pub timestamp: U256,
    pub block_number: u64,
    pub tx_hash: H256,
    pub log_index: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DestinationUpdated {
    pub fund: Address,
    pub fund_type: String,
    pub timestamp: U256,
    pub block_number: u64,
    pub tx_hash: H256,
    pub log_index: u64,
}

// ── QuadraticVoting events ────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VoteCast {
    pub proposal_id: U256,
    pub voter: Address,
    pub tokens_committed: U256,
    pub quadratic_power: U256,
    pub support: bool,
    pub block_number: u64,
    pub tx_hash: H256,
    pub log_index: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VoteWithdrawn {
    pub proposal_id: U256,
    pub voter: Address,
    pub tokens_returned: U256,
    pub block_number: u64,
    pub tx_hash: H256,
    pub log_index: u64,
}

// ── MiningOracle events ──────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OracleSubmitted {
    pub location_hash: H256,
    pub oracle: Address,
    pub mineral_type: String,
    pub confidence_bps: U256,
    pub block_number: u64,
    pub tx_hash: H256,
    pub log_index: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LocationVerified {
    pub location_hash: H256,
    pub confirmation_count: U256,
    pub average_confidence: U256,
    pub block_number: u64,
    pub tx_hash: H256,
    pub log_index: u64,
}

// ═══════════════════════════════════════════════════════════════════════════════
// Unified Event Enum
// ═══════════════════════════════════════════════════════════════════════════════

/// All possible indexed events, tagged by contract source
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "event_type")]
pub enum IndexedEvent {
    ExtractionRecorded(ExtractionRecorded),
    ExtractionVerified(ExtractionVerified),
    ExtractionDisputed(ExtractionDisputed),
    RevenueDistributed(RevenueDistributed),
    SplitPercentagesUpdated(SplitPercentagesUpdated),
    DestinationUpdated(DestinationUpdated),
    VoteCast(VoteCast),
    VoteWithdrawn(VoteWithdrawn),
    OracleSubmitted(OracleSubmitted),
    LocationVerified(LocationVerified),
}

impl IndexedEvent {
    /// The contract that emitted this event
    pub fn contract_name(&self) -> &'static str {
        match self {
            Self::ExtractionRecorded(_)
            | Self::ExtractionVerified(_)
            | Self::ExtractionDisputed(_) => "ExtractionTracker",

            Self::RevenueDistributed(_)
            | Self::SplitPercentagesUpdated(_)
            | Self::DestinationUpdated(_) => "RoyaltyDistributor",

            Self::VoteCast(_) | Self::VoteWithdrawn(_) => "QuadraticVoting",

            Self::OracleSubmitted(_) | Self::LocationVerified(_) => "MiningOracle",
        }
    }

    /// Human-readable event name
    pub fn event_name(&self) -> &'static str {
        match self {
            Self::ExtractionRecorded(_) => "ExtractionRecorded",
            Self::ExtractionVerified(_) => "ExtractionVerified",
            Self::ExtractionDisputed(_) => "ExtractionDisputed",
            Self::RevenueDistributed(_) => "RevenueDistributed",
            Self::SplitPercentagesUpdated(_) => "SplitPercentagesUpdated",
            Self::DestinationUpdated(_) => "DestinationUpdated",
            Self::VoteCast(_) => "VoteCast",
            Self::VoteWithdrawn(_) => "VoteWithdrawn",
            Self::OracleSubmitted(_) => "OracleSubmitted",
            Self::LocationVerified(_) => "LocationVerified",
        }
    }

    pub fn block_number(&self) -> u64 {
        match self {
            Self::ExtractionRecorded(e) => e.block_number,
            Self::ExtractionVerified(e) => e.block_number,
            Self::ExtractionDisputed(e) => e.block_number,
            Self::RevenueDistributed(e) => e.block_number,
            Self::SplitPercentagesUpdated(e) => e.block_number,
            Self::DestinationUpdated(e) => e.block_number,
            Self::VoteCast(e) => e.block_number,
            Self::VoteWithdrawn(e) => e.block_number,
            Self::OracleSubmitted(e) => e.block_number,
            Self::LocationVerified(e) => e.block_number,
        }
    }

    pub fn tx_hash(&self) -> H256 {
        match self {
            Self::ExtractionRecorded(e) => e.tx_hash,
            Self::ExtractionVerified(e) => e.tx_hash,
            Self::ExtractionDisputed(e) => e.tx_hash,
            Self::RevenueDistributed(e) => e.tx_hash,
            Self::SplitPercentagesUpdated(e) => e.tx_hash,
            Self::DestinationUpdated(e) => e.tx_hash,
            Self::VoteCast(e) => e.tx_hash,
            Self::VoteWithdrawn(e) => e.tx_hash,
            Self::OracleSubmitted(e) => e.tx_hash,
            Self::LocationVerified(e) => e.tx_hash,
        }
    }

    pub fn log_index(&self) -> u64 {
        match self {
            Self::ExtractionRecorded(e) => e.log_index,
            Self::ExtractionVerified(e) => e.log_index,
            Self::ExtractionDisputed(e) => e.log_index,
            Self::RevenueDistributed(e) => e.log_index,
            Self::SplitPercentagesUpdated(e) => e.log_index,
            Self::DestinationUpdated(e) => e.log_index,
            Self::VoteCast(e) => e.log_index,
            Self::VoteWithdrawn(e) => e.log_index,
            Self::OracleSubmitted(e) => e.log_index,
            Self::LocationVerified(e) => e.log_index,
        }
    }
}

// ═══════════════════════════════════════════════════════════════════════════════
// Log Parsing
// ═══════════════════════════════════════════════════════════════════════════════

/// Parse a raw Ethereum log into a typed IndexedEvent.
///
/// Returns `None` if the log's topic[0] doesn't match any known event signature.
pub fn parse_log(log: &ethers::types::Log) -> Option<IndexedEvent> {
    let topic0 = log.topics.first()?;
    let block_number = log.block_number?.as_u64();
    let tx_hash = log.transaction_hash?;
    let log_index = log.log_index?.as_u64();

    match *topic0 {
        EXTRACTION_RECORDED_SIG => parse_extraction_recorded(log, block_number, tx_hash, log_index),
        EXTRACTION_VERIFIED_SIG => parse_extraction_verified(log, block_number, tx_hash, log_index),
        EXTRACTION_DISPUTED_SIG => parse_extraction_disputed(log, block_number, tx_hash, log_index),
        REVENUE_DISTRIBUTED_SIG => parse_revenue_distributed(log, block_number, tx_hash, log_index),
        SPLIT_UPDATED_SIG => parse_split_updated(log, block_number, tx_hash, log_index),
        DESTINATION_UPDATED_SIG => parse_destination_updated(log, block_number, tx_hash, log_index),
        VOTE_CAST_SIG => parse_vote_cast(log, block_number, tx_hash, log_index),
        VOTE_WITHDRAWN_SIG => parse_vote_withdrawn(log, block_number, tx_hash, log_index),
        ORACLE_SUBMITTED_SIG => parse_oracle_submitted(log, block_number, tx_hash, log_index),
        LOCATION_VERIFIED_SIG => parse_location_verified(log, block_number, tx_hash, log_index),
        _ => None,
    }
}

/// Decode a U256 from 32 bytes at a given offset in the data field.
fn decode_u256(data: &[u8], offset: usize) -> Option<U256> {
    if offset + 32 > data.len() {
        return None;
    }
    Some(U256::from_big_endian(&data[offset..offset + 32]))
}

/// Decode an Address from the last 20 bytes of a 32-byte word.
fn decode_address_from_topic(topic: &H256) -> Address {
    Address::from_slice(&topic[12..32])
}

/// Decode a dynamic string from ABI-encoded data.
/// For events, strings in topic[1+] are keccak hashes; strings in data are ABI-encoded.
/// This handles the data-offset / length / padded-string pattern.
fn decode_string(data: &[u8], offset: usize) -> Option<String> {
    // Read the offset pointer (relative to data start for events, or absolute)
    let str_offset = decode_u256(data, offset)?.as_usize();
    if str_offset + 32 > data.len() {
        return None;
    }
    let str_len = decode_u256(data, str_offset)?.as_usize();
    let str_start = str_offset + 32;
    if str_start + str_len > data.len() {
        return None;
    }
    String::from_utf8(data[str_start..str_start + str_len].to_vec()).ok()
}

fn parse_extraction_recorded(
    log: &ethers::types::Log,
    block_number: u64,
    tx_hash: H256,
    log_index: u64,
) -> Option<IndexedEvent> {
    // topic[1]: recordId (indexed uint256)
    // topic[2]: submitter (indexed address)
    // topic[3]: locationHash (indexed bytes32)
    // data: mineralType (string), status (uint8, non-indexed)
    let record_id = U256::from_big_endian(log.topics.get(1)?.as_bytes());
    let submitter = decode_address_from_topic(log.topics.get(2)?);
    let location_hash = *log.topics.get(3)?;

    let data = &log.data;
    let mineral_type = decode_string(data, 0)?;
    // After the string, there's the status uint8 (padded to 32 bytes)
    // The string data length is variable, so we need to follow the offset pointer
    let str_data_offset = decode_u256(data, 0)?.as_usize();
    let str_len = decode_u256(data, str_data_offset)?.as_usize();
    let status_offset = str_data_offset + 32 + ((str_len + 31) / 32) * 32;
    let status_raw = decode_u256(data, status_offset)?.as_u64() as u8;

    Some(IndexedEvent::ExtractionRecorded(ExtractionRecorded {
        record_id,
        submitter,
        location_hash,
        mineral_type,
        status: VerificationStatus::from(status_raw),
        block_number,
        tx_hash,
        log_index,
    }))
}

fn parse_extraction_verified(
    log: &ethers::types::Log,
    block_number: u64,
    tx_hash: H256,
    log_index: u64,
) -> Option<IndexedEvent> {
    let record_id = U256::from_big_endian(log.topics.get(1)?.as_bytes());
    let oracle = decode_address_from_topic(log.topics.get(2)?);
    // data: newStatus (uint8), confidenceScore (uint256)
    let data = &log.data;
    let status_raw = decode_u256(data, 0)?.as_u64() as u8;
    let confidence_score = decode_u256(data, 32)?;

    Some(IndexedEvent::ExtractionVerified(ExtractionVerified {
        record_id,
        oracle,
        new_status: VerificationStatus::from(status_raw),
        confidence_score,
        block_number,
        tx_hash,
        log_index,
    }))
}

fn parse_extraction_disputed(
    log: &ethers::types::Log,
    block_number: u64,
    tx_hash: H256,
    log_index: u64,
) -> Option<IndexedEvent> {
    let record_id = U256::from_big_endian(log.topics.get(1)?.as_bytes());
    let disputer = decode_address_from_topic(log.topics.get(2)?);
    let reason = decode_string(&log.data, 0)?;

    Some(IndexedEvent::ExtractionDisputed(ExtractionDisputed {
        record_id,
        disputer,
        reason,
        block_number,
        tx_hash,
        log_index,
    }))
}

fn parse_revenue_distributed(
    log: &ethers::types::Log,
    block_number: u64,
    tx_hash: H256,
    log_index: u64,
) -> Option<IndexedEvent> {
    // topic[1]: payer (indexed address)
    // data: source(uint8), totalAmount, devShare, walletShare, reserveShare, timestamp
    let payer = decode_address_from_topic(log.topics.get(1)?);
    let data = &log.data;
    let source_raw = decode_u256(data, 0)?.as_u64() as u8;
    let total_amount = decode_u256(data, 32)?;
    let community_dev_share = decode_u256(data, 64)?;
    let community_wallet_share = decode_u256(data, 96)?;
    let reserve_share = decode_u256(data, 128)?;
    let timestamp = decode_u256(data, 160)?;

    Some(IndexedEvent::RevenueDistributed(RevenueDistributed {
        payer,
        source: RoyaltySource::from(source_raw),
        total_amount,
        community_dev_share,
        community_wallet_share,
        reserve_share,
        timestamp,
        block_number,
        tx_hash,
        log_index,
    }))
}

fn parse_split_updated(
    log: &ethers::types::Log,
    block_number: u64,
    tx_hash: H256,
    log_index: u64,
) -> Option<IndexedEvent> {
    let data = &log.data;
    let new_dev_bps = decode_u256(data, 0)?;
    let new_wallet_bps = decode_u256(data, 32)?;
    let new_reserve_bps = decode_u256(data, 64)?;
    let timestamp = decode_u256(data, 96)?;

    Some(IndexedEvent::SplitPercentagesUpdated(SplitPercentagesUpdated {
        new_dev_bps,
        new_wallet_bps,
        new_reserve_bps,
        timestamp,
        block_number,
        tx_hash,
        log_index,
    }))
}

fn parse_destination_updated(
    log: &ethers::types::Log,
    block_number: u64,
    tx_hash: H256,
    log_index: u64,
) -> Option<IndexedEvent> {
    // topic[1]: fund (indexed address)
    // data: fundType (string), timestamp (uint256)
    let fund = decode_address_from_topic(log.topics.get(1)?);
    let data = &log.data;
    let fund_type = decode_string(data, 0)?;
    let str_data_offset = decode_u256(data, 0)?.as_usize();
    let str_len = decode_u256(data, str_data_offset)?.as_usize();
    let ts_offset = str_data_offset + 32 + ((str_len + 31) / 32) * 32;
    let timestamp = decode_u256(data, ts_offset)?;

    Some(IndexedEvent::DestinationUpdated(DestinationUpdated {
        fund,
        fund_type,
        timestamp,
        block_number,
        tx_hash,
        log_index,
    }))
}

fn parse_vote_cast(
    log: &ethers::types::Log,
    block_number: u64,
    tx_hash: H256,
    log_index: u64,
) -> Option<IndexedEvent> {
    // topic[1]: proposalId (indexed uint256)
    // topic[2]: voter (indexed address)
    // data: tokensCommitted, quadraticPower, support (bool)
    let proposal_id = U256::from_big_endian(log.topics.get(1)?.as_bytes());
    let voter = decode_address_from_topic(log.topics.get(2)?);
    let data = &log.data;
    let tokens_committed = decode_u256(data, 0)?;
    let quadratic_power = decode_u256(data, 32)?;
    let support = !decode_u256(data, 64)?.is_zero();

    Some(IndexedEvent::VoteCast(VoteCast {
        proposal_id,
        voter,
        tokens_committed,
        quadratic_power,
        support,
        block_number,
        tx_hash,
        log_index,
    }))
}

fn parse_vote_withdrawn(
    log: &ethers::types::Log,
    block_number: u64,
    tx_hash: H256,
    log_index: u64,
) -> Option<IndexedEvent> {
    let proposal_id = U256::from_big_endian(log.topics.get(1)?.as_bytes());
    let voter = decode_address_from_topic(log.topics.get(2)?);
    let tokens_returned = decode_u256(&log.data, 0)?;

    Some(IndexedEvent::VoteWithdrawn(VoteWithdrawn {
        proposal_id,
        voter,
        tokens_returned,
        block_number,
        tx_hash,
        log_index,
    }))
}

fn parse_oracle_submitted(
    log: &ethers::types::Log,
    block_number: u64,
    tx_hash: H256,
    log_index: u64,
) -> Option<IndexedEvent> {
    let location_hash = H256::from(log.topics.get(1)?.as_bytes());
    let oracle = decode_address_from_topic(log.topics.get(2)?);
    let data = &log.data;
    let mineral_type = decode_string(data, 0)?;
    let str_data_offset = decode_u256(data, 0)?.as_usize();
    let str_len = decode_u256(data, str_data_offset)?.as_usize();
    let bps_offset = str_data_offset + 32 + ((str_len + 31) / 32) * 32;
    let confidence_bps = decode_u256(data, bps_offset)?;

    Some(IndexedEvent::OracleSubmitted(OracleSubmitted {
        location_hash,
        oracle,
        mineral_type,
        confidence_bps,
        block_number,
        tx_hash,
        log_index,
    }))
}

fn parse_location_verified(
    log: &ethers::types::Log,
    block_number: u64,
    tx_hash: H256,
    log_index: u64,
) -> Option<IndexedEvent> {
    let location_hash = H256::from(log.topics.get(1)?.as_bytes());
    let data = &log.data;
    let confirmation_count = decode_u256(data, 0)?;
    let average_confidence = decode_u256(data, 32)?;

    Some(IndexedEvent::LocationVerified(LocationVerified {
        location_hash,
        confirmation_count,
        average_confidence,
        block_number,
        tx_hash,
        log_index,
    }))
}

// ═══════════════════════════════════════════════════════════════════════════════
// Runtime Event Signature Computation
// ═══════════════════════════════════════════════════════════════════════════════

/// Compute event signatures at runtime (for verification/debugging).
/// These should match the constants defined above.
pub fn compute_event_signatures() -> Vec<(&'static str, H256)> {
    use ethers::utils::keccak256;

    vec![
        ("ExtractionRecorded(uint256,address,bytes32,string,uint8)",
         H256(keccak256("ExtractionRecorded(uint256,address,bytes32,string,uint8)"))),
        ("ExtractionVerified(uint256,address,uint8,uint256)",
         H256(keccak256("ExtractionVerified(uint256,address,uint8,uint256)"))),
        ("ExtractionDisputed(uint256,address,string)",
         H256(keccak256("ExtractionDisputed(uint256,address,string)"))),
        ("RevenueDistributed(address,uint8,uint256,uint256,uint256,uint256,uint256)",
         H256(keccak256("RevenueDistributed(address,uint8,uint256,uint256,uint256,uint256,uint256)"))),
        ("SplitPercentagesUpdated(uint256,uint256,uint256,uint256)",
         H256(keccak256("SplitPercentagesUpdated(uint256,uint256,uint256,uint256)"))),
        ("DestinationUpdated(address,string,uint256)",
         H256(keccak256("DestinationUpdated(address,string,uint256)"))),
        ("VoteCast(uint256,address,uint256,uint256,bool)",
         H256(keccak256("VoteCast(uint256,address,uint256,uint256,bool)"))),
        ("VoteWithdrawn(uint256,address,uint256)",
         H256(keccak256("VoteWithdrawn(uint256,address,uint256)"))),
        ("OracleSubmitted(bytes32,address,string,uint256)",
         H256(keccak256("OracleSubmitted(bytes32,address,string,uint256)"))),
        ("LocationVerified(bytes32,uint256,uint256)",
         H256(keccak256("LocationVerified(bytes32,uint256,uint256)"))),
    ]
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_compute_signatures_match_constants() {
        let sigs = compute_event_signatures();
        assert_eq!(sigs[0].1, EXTRACTION_RECORDED_SIG, "ExtractionRecorded sig mismatch");
        assert_eq!(sigs[1].1, EXTRACTION_VERIFIED_SIG, "ExtractionVerified sig mismatch");
        assert_eq!(sigs[2].1, EXTRACTION_DISPUTED_SIG, "ExtractionDisputed sig mismatch");
        assert_eq!(sigs[3].1, REVENUE_DISTRIBUTED_SIG, "RevenueDistributed sig mismatch");
        assert_eq!(sigs[4].1, SPLIT_UPDATED_SIG, "SplitPercentagesUpdated sig mismatch");
        assert_eq!(sigs[5].1, DESTINATION_UPDATED_SIG, "DestinationUpdated sig mismatch");
        assert_eq!(sigs[6].1, VOTE_CAST_SIG, "VoteCast sig mismatch");
        assert_eq!(sigs[7].1, VOTE_WITHDRAWN_SIG, "VoteWithdrawn sig mismatch");
        assert_eq!(sigs[8].1, ORACLE_SUBMITTED_SIG, "OracleSubmitted sig mismatch");
        assert_eq!(sigs[9].1, LOCATION_VERIFIED_SIG, "LocationVerified sig mismatch");
    }
}
