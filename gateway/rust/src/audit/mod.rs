//! Audit Logger — Immutable audit trail with cryptographic integrity
//!
//! Provides tamper-proof logging for all system actions using SHA-256 hash chains.
//! Each log entry includes the hash of the previous entry, creating an immutable
//! chain that can be verified for integrity.

use serde::{Deserialize, Serialize};
use sha2::{Sha256, Digest};
use sqlx::PgPool;
use tracing::{info, error};

/// Audit log entry with cryptographic integrity
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuditEntry {
    pub id: i64,
    pub timestamp: String,
    pub action: String,
    pub actor: String,
    pub details: serde_json::Value,
    pub previous_hash: String,
    pub entry_hash: String,
}

/// The immutable audit logger
pub struct AuditLogger {
    db: PgPool,
}

impl AuditLogger {
    pub fn new(db: PgPool) -> Self {
        Self { db }
    }

    /// Log an action with cryptographic integrity
    pub async fn log(
        &self,
        action: &str,
        actor: &str,
        details: serde_json::Value,
    ) -> Result<AuditEntry, sqlx::Error> {
        // Get the hash of the previous entry
        let previous_hash = self.get_latest_hash().await?;

        // Create the entry
        let timestamp = chrono::Utc::now().to_rfc3339();
        let entry_data = serde_json::json!({
            "timestamp": timestamp,
            "action": action,
            "actor": actor,
            "details": details,
            "previous_hash": previous_hash,
        });

        // Calculate hash (SHA-256 of the entry data)
        let entry_hash = self.calculate_hash(&entry_data);

        // Store in database
        let row = sqlx::query_as::<_, (i64,)>(
            "INSERT INTO audit_log (timestamp, action, actor, details, previous_hash, entry_hash)
             VALUES ($1, $2, $3, $4, $5, $6)
             RETURNING id"
        )
        .bind(&timestamp)
        .bind(action)
        .bind(actor)
        .bind(&details)
        .bind(&previous_hash)
        .bind(&entry_hash)
        .fetch_one(&self.db)
        .await?;

        let entry = AuditEntry {
            id: row.0,
            timestamp,
            action: action.to_string(),
            actor: actor.to_string(),
            details,
            previous_hash,
            entry_hash,
        };

        info!(
            "Audit log: action={}, actor={}, hash={}",
            action, actor, &entry.entry_hash[..16]
        );

        Ok(entry)
    }

    /// Get the hash of the latest audit entry
    async fn get_latest_hash(&self) -> Result<String, sqlx::Error> {
        let result = sqlx::query_as::<_, (String,)>(
            "SELECT entry_hash FROM audit_log ORDER BY id DESC LIMIT 1"
        )
        .fetch_optional(&self.db)
        .await?;

        Ok(result.map(|r| r.0).unwrap_or_else(|| "genesis".to_string()))
    }

    /// Calculate SHA-256 hash of entry data
    fn calculate_hash(&self, data: &serde_json::Value) -> String {
        let mut hasher = Sha256::new();
        hasher.update(data.to_string().as_bytes());
        let result = hasher.finalize();
        hex::encode(result)
    }

    /// Verify the integrity of the audit chain
    pub async fn verify_chain(&self) -> Result<ChainVerification, sqlx::Error> {
        let entries = sqlx::query_as::<_, (i64, String, String, String, String, String)>(
            "SELECT id, timestamp, action, actor, previous_hash, entry_hash
             FROM audit_log ORDER BY id ASC"
        )
        .fetch_all(&self.db)
        .await?;

        let mut verified = 0;
        let mut broken_at: Option<i64> = None;
        let mut previous_hash = "genesis".to_string();

        for (id, timestamp, action, actor, stored_prev_hash, stored_entry_hash) in &entries {
            // Verify previous hash chain
            if stored_prev_hash != &previous_hash {
                broken_at = Some(*id);
                break;
            }

            // Verify entry hash
            let details: serde_json::Value = sqlx::query_as::<_, (serde_json::Value,)>(
                "SELECT details FROM audit_log WHERE id = $1"
            )
            .bind(id)
            .fetch_one(&self.db)
            .await
            .map(|r| r.0)
            .unwrap_or(serde_json::Value::Null);

            let entry_data = serde_json::json!({
                "timestamp": timestamp,
                "action": action,
                "actor": actor,
                "details": details,
                "previous_hash": stored_prev_hash,
            });

            let calculated_hash = self.calculate_hash(&entry_data);
            if calculated_hash != *stored_entry_hash {
                broken_at = Some(*id);
                break;
            }

            verified += 1;
            previous_hash = stored_entry_hash.clone();
        }

        Ok(ChainVerification {
            total_entries: entries.len() as i64,
            verified_entries: verified,
            chain_valid: broken_at.is_none(),
            broken_at,
        })
    }

    /// Get recent audit entries
    pub async fn get_recent(&self, limit: i64) -> Result<Vec<AuditEntry>, sqlx::Error> {
        let rows = sqlx::query_as::<_, (i64, String, String, String, serde_json::Value, String, String)>(
            "SELECT id, timestamp, action, actor, details, previous_hash, entry_hash
             FROM audit_log ORDER BY id DESC LIMIT $1"
        )
        .bind(limit)
        .fetch_all(&self.db)
        .await?;

        Ok(rows.into_iter().map(|(id, timestamp, action, actor, details, previous_hash, entry_hash)| {
            AuditEntry { id, timestamp, action, actor, details, previous_hash, entry_hash }
        }).collect())
    }
}

/// Chain verification result
#[derive(Debug, Serialize)]
pub struct ChainVerification {
    pub total_entries: i64,
    pub verified_entries: i64,
    pub chain_valid: bool,
    pub broken_at: Option<i64>,
}

/// Database migration for audit_log table
pub async fn run_migration(db: &PgPool) -> Result<(), sqlx::Error> {
    sqlx::query(
        "CREATE TABLE IF NOT EXISTS audit_log (
            id BIGSERIAL PRIMARY KEY,
            timestamp TIMESTAMPTZ NOT NULL,
            action VARCHAR(128) NOT NULL,
            actor VARCHAR(128) NOT NULL,
            details JSONB NOT NULL DEFAULT '{}',
            previous_hash VARCHAR(64) NOT NULL,
            entry_hash VARCHAR(64) NOT NULL UNIQUE
        );
        CREATE INDEX IF NOT EXISTS idx_audit_log_action ON audit_log(action);
        CREATE INDEX IF NOT EXISTS idx_audit_log_actor ON audit_log(actor);
        CREATE INDEX IF NOT EXISTS idx_audit_log_time ON audit_log(timestamp);"
    )
    .execute(db)
    .await?;

    info!("Audit log table created/verified");
    Ok(())
}
