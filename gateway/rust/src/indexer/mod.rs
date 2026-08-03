//! Blockchain Indexer — Listens to Polygon PoS events
//!
//! Subscribes to smart contract events (ExtractionTracker, RoyaltyDistributor,
//! QuadraticVoting) and indexes them into PostgreSQL for fast querying.
//!
//! This is the "chain watcher" that makes on-chain data accessible to the
//! AI agents and community dashboard.

use ethers::prelude::*;
use serde::{Deserialize, Serialize};
use sqlx::PgPool;
use std::sync::Arc;
use tokio::sync::broadcast;
use tracing::{info, error, warn};

/// Event types we index from the blockchain
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ChainEvent {
    ExtractionRecorded {
        record_id: U256,
        submitter: Address,
        location_hash: H256,
        mineral_type: String,
        status: String,
        block_number: u64,
        tx_hash: H256,
    },
    RevenueDistributed {
        payer: Address,
        source: String,
        total_amount: U256,
        community_dev_share: U256,
        community_wallet_share: U256,
        reserve_share: U256,
        block_number: u64,
        tx_hash: H256,
    },
    VoteCast {
        proposal_id: U256,
        voter: Address,
        tokens_committed: U256,
        quadratic_power: U256,
        support: bool,
        block_number: u64,
        tx_hash: H256,
    },
    ProposalCreated {
        proposal_id: U256,
        proposer: Address,
        description: String,
        block_number: u64,
        tx_hash: H256,
    },
}

/// Configuration for the blockchain indexer
#[derive(Debug, Clone)]
pub struct IndexerConfig {
    pub rpc_url: String,
    pub chain_id: u64,
    pub extraction_tracker_address: Address,
    pub royalty_distributor_address: Address,
    pub quadratic_voting_address: Address,
    pub poll_interval_ms: u64,
    pub start_block: u64,
}

impl IndexerConfig {
    pub fn from_env() -> Self {
        Self {
            rpc_url: std::env::var("POLYGON_RPC_URL")
                .unwrap_or_else(|_| "https://polygon-rpc.com".to_string()),
            chain_id: std::env::var("CHAIN_ID")
                .unwrap_or_else(|_| "137".to_string())
                .parse()
                .unwrap_or(137),
            extraction_tracker_address: std::env::var("EXTRACTION_TRACKER_ADDRESS")
                .unwrap_or_default()
                .parse()
                .unwrap_or(Address::zero()),
            royalty_distributor_address: std::env::var("ROYALTY_DISTRIBUTOR_ADDRESS")
                .unwrap_or_default()
                .parse()
                .unwrap_or(Address::zero()),
            quadratic_voting_address: std::env::var("QUADRATIC_VOTING_ADDRESS")
                .unwrap_or_default()
                .parse()
                .unwrap_or(Address::zero()),
            poll_interval_ms: std::env::var("INDEXER_POLL_INTERVAL_MS")
                .unwrap_or_else(|_| "12000".to_string())  // 12s = Polygon block time
                .parse()
                .unwrap_or(12000),
            start_block: std::env::var("INDEXER_START_BLOCK")
                .unwrap_or_else(|_| "0".to_string())
                .parse()
                .unwrap_or(0),
        }
    }
}

/// The blockchain indexer
pub struct BlockchainIndexer {
    config: IndexerConfig,
    db: PgPool,
    event_sender: broadcast::Sender<ChainEvent>,
}

impl BlockchainIndexer {
    pub fn new(config: IndexerConfig, db: PgPool) -> Self {
        let (event_sender, _) = broadcast::channel(1024);
        Self { config, db, event_sender }
    }

    /// Subscribe to indexed events
    pub fn subscribe(&self) -> broadcast::Receiver<ChainEvent> {
        self.event_sender.subscribe()
    }

    /// Start indexing blockchain events
    pub async fn start(&self) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        info!("Starting blockchain indexer...");
        info!("Chain ID: {}", self.config.chain_id);
        info!("RPC: {}", self.config.rpc_url);

        let provider = Provider::<Http>::try_from(&self.config.rpc_url)?;
        let current_block = provider.get_block_number().await?;
        info!("Current block: {}", current_block);

        let mut last_block = if self.config.start_block > 0 {
            self.config.start_block
        } else {
            current_block.as_u64().saturating_sub(1000) // Start from 1000 blocks ago
        };

        info!("Starting from block: {}", last_block);

        loop {
            match provider.get_block_number().await {
                Ok(latest) => {
                    let latest_num = latest.as_u64();
                    if latest_num > last_block {
                        info!("Indexing blocks {} to {}", last_block + 1, latest_num);

                        // Index ExtractionTracker events
                        if self.config.extraction_tracker_address != Address::zero() {
                            if let Err(e) = self.index_extraction_events(
                                &provider, last_block + 1, latest_num
                            ).await {
                                error!("Failed to index extraction events: {}", e);
                            }
                        }

                        // Index RoyaltyDistributor events
                        if self.config.royalty_distributor_address != Address::zero() {
                            if let Err(e) = self.index_royalty_events(
                                &provider, last_block + 1, latest_num
                            ).await {
                                error!("Failed to index royalty events: {}", e);
                            }
                        }

                        // Index QuadraticVoting events
                        if self.config.quadratic_voting_address != Address::zero() {
                            if let Err(e) = self.index_voting_events(
                                &provider, last_block + 1, latest_num
                            ).await {
                                error!("Failed to index voting events: {}", e);
                            }
                        }

                        last_block = latest_num;
                    }
                }
                Err(e) => {
                    error!("Failed to get latest block: {}", e);
                }
            }

            tokio::time::sleep(tokio::time::Duration::from_millis(
                self.config.poll_interval_ms
            )).await;
        }
    }

    /// Index ExtractionTracker events
    async fn index_extraction_events(
        &self,
        provider: &Provider<Http>,
        from_block: u64,
        to_block: u64,
    ) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        // ExtractionRecorded event signature
        let event_signature = keccak256(
            "ExtractionRecorded(uint256,address,bytes32,string,uint8)"
        );

        let filter = Filter::new()
            .address(self.config.extraction_tracker_address)
            .topic0(H256::from(event_signature))
            .from_block(BlockNumber::Number(from_block.into()))
            .to_block(BlockNumber::Number(to_block.into()));

        let logs = provider.get_logs(&filter).await?;

        for log in logs {
            let event = ChainEvent::ExtractionRecorded {
                record_id: U256::from(log.topics.get(1).unwrap_or(&H256::zero()).as_bytes()),
                submitter: Address::from(log.topics.get(2).unwrap_or(&H256::zero()).as_bytes()),
                location_hash: *log.topics.get(3).unwrap_or(&H256::zero()),
                mineral_type: String::from_utf8_lossy(&log.data).to_string(),
                status: "recorded".to_string(),
                block_number: log.block_number.unwrap_or_default().as_u64(),
                tx_hash: log.transaction_hash.unwrap_or_default(),
            };

            // Store in database
            if let Err(e) = self.store_event(&event).await {
                error!("Failed to store extraction event: {}", e);
            }

            // Broadcast to subscribers
            let _ = self.event_sender.send(event);
        }

        Ok(())
    }

    /// Index RoyaltyDistributor events
    async fn index_royalty_events(
        &self,
        provider: &Provider<Http>,
        from_block: u64,
        to_block: u64,
    ) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        let event_signature = keccak256(
            "RevenueDistributed(address,uint8,uint256,uint256,uint256,uint256,uint256)"
        );

        let filter = Filter::new()
            .address(self.config.royalty_distributor_address)
            .topic0(H256::from(event_signature))
            .from_block(BlockNumber::Number(from_block.into()))
            .to_block(BlockNumber::Number(to_block.into()));

        let logs = provider.get_logs(&filter).await?;

        for log in logs {
            let event = ChainEvent::RevenueDistributed {
                payer: Address::from(log.topics.get(1).unwrap_or(&H256::zero()).as_bytes()),
                source: "extraction".to_string(),
                total_amount: U256::from_big_endian(&log.data[..32].min(&log.data)),
                community_dev_share: U256::from_big_endian(
                    &log.data[32..64].min(&log.data[32..])
                ),
                community_wallet_share: U256::from_big_endian(
                    &log.data[64..96].min(&log.data[64..])
                ),
                reserve_share: U256::from_big_endian(
                    &log.data[96..128].min(&log.data[96..])
                ),
                block_number: log.block_number.unwrap_or_default().as_u64(),
                tx_hash: log.transaction_hash.unwrap_or_default(),
            };

            if let Err(e) = self.store_event(&event).await {
                error!("Failed to store royalty event: {}", e);
            }

            let _ = self.event_sender.send(event);
        }

        Ok(())
    }

    /// Index QuadraticVoting events
    async fn index_voting_events(
        &self,
        provider: &Provider<Http>,
        from_block: u64,
        to_block: u64,
    ) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        let event_signature = keccak256(
            "VoteCast(uint256,address,uint256,uint256,bool)"
        );

        let filter = Filter::new()
            .address(self.config.quadratic_voting_address)
            .topic0(H256::from(event_signature))
            .from_block(BlockNumber::Number(from_block.into()))
            .to_block(BlockNumber::Number(to_block.into()));

        let logs = provider.get_logs(&filter).await?;

        for log in logs {
            let event = ChainEvent::VoteCast {
                proposal_id: U256::from(log.topics.get(1).unwrap_or(&H256::zero()).as_bytes()),
                voter: Address::from(log.topics.get(2).unwrap_or(&H256::zero()).as_bytes()),
                tokens_committed: U256::from_big_endian(&log.data[..32].min(&log.data)),
                quadratic_power: U256::from_big_endian(
                    &log.data[32..64].min(&log.data[32..])
                ),
                support: log.data.get(96).map(|&b| b != 0).unwrap_or(true),
                block_number: log.block_number.unwrap_or_default().as_u64(),
                tx_hash: log.transaction_hash.unwrap_or_default(),
            };

            if let Err(e) = self.store_event(&event).await {
                error!("Failed to store vote event: {}", e);
            }

            let _ = self.event_sender.send(event);
        }

        Ok(())
    }

    /// Store event in PostgreSQL
    async fn store_event(
        &self,
        event: &ChainEvent,
    ) -> Result<(), sqlx::Error> {
        let (event_type, block_number, tx_hash, data) = match event {
            ChainEvent::ExtractionRecorded { block_number, tx_hash, .. } =>
                ("extraction", *block_number, *tx_hash, serde_json::to_string(event).unwrap_or_default()),
            ChainEvent::RevenueDistributed { block_number, tx_hash, .. } =>
                ("royalty", *block_number, *tx_hash, serde_json::to_string(event).unwrap_or_default()),
            ChainEvent::VoteCast { block_number, tx_hash, .. } =>
                ("vote", *block_number, *tx_hash, serde_json::to_string(event).unwrap_or_default()),
            ChainEvent::ProposalCreated { block_number, tx_hash, .. } =>
                ("proposal", *block_number, *tx_hash, serde_json::to_string(event).unwrap_or_default()),
        };

        sqlx::query(
            "INSERT INTO chain_events (event_type, block_number, tx_hash, data, indexed_at)
             VALUES ($1, $2, $3, $4, NOW())
             ON CONFLICT (tx_hash, event_type) DO NOTHING"
        )
        .bind(event_type)
        .bind(block_number as i64)
        .bind(format!("{:?}", tx_hash))
        .bind(data)
        .execute(&self.db)
        .await?;

        Ok(())
    }
}

/// Database migration for chain_events table
pub async fn run_migration(db: &PgPool) -> Result<(), sqlx::Error> {
    sqlx::query(
        "CREATE TABLE IF NOT EXISTS chain_events (
            id BIGSERIAL PRIMARY KEY,
            event_type VARCHAR(32) NOT NULL,
            block_number BIGINT NOT NULL,
            tx_hash VARCHAR(66) NOT NULL,
            data JSONB NOT NULL,
            indexed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(tx_hash, event_type)
        );
        CREATE INDEX IF NOT EXISTS idx_chain_events_type ON chain_events(event_type);
        CREATE INDEX IF NOT EXISTS idx_chain_events_block ON chain_events(block_number);
        CREATE INDEX IF NOT EXISTS idx_chain_events_time ON chain_events(indexed_at);"
    )
    .execute(db)
    .await?;

    info!("Chain events table created/verified");
    Ok(())
}
