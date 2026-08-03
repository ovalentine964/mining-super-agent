use sqlx::postgres::{PgPool, PgPoolOptions};
use sqlx::Row;
use anyhow::{Context, Result};
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

/// Database connection pool wrapper
#[derive(Clone)]
pub struct Database {
    pool: PgPool,
}

#[derive(Debug, Serialize, Deserialize, sqlx::FromRow)]
pub struct MineSite {
    pub id: Uuid,
    pub name: String,
    pub location: Option<String>, // PostGIS WKT
    pub mine_type: Option<String>,
    pub status: Option<String>,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

#[derive(Debug, Serialize, Deserialize, sqlx::FromRow)]
pub struct AnalysisResult {
    pub id: Uuid,
    pub analysis_type: String,
    pub input_data: serde_json::Value,
    pub output_data: serde_json::Value,
    pub model_version: Option<String>,
    pub confidence: Option<f64>,
    pub created_at: DateTime<Utc>,
}

#[derive(Debug, Serialize, Deserialize, sqlx::FromRow)]
pub struct ToolExecutionLog {
    pub id: Uuid,
    pub tool_name: String,
    pub input_params: serde_json::Value,
    pub output_data: serde_json::Value,
    pub status: String,
    pub duration_ms: i32,
    pub created_at: DateTime<Utc>,
}

impl Database {
    /// Create a new database connection pool
    pub async fn new(database_url: &str) -> Result<Self> {
        let pool = PgPoolOptions::new()
            .max_connections(20)
            .min_connections(2)
            .acquire_timeout(std::time::Duration::from_secs(10))
            .idle_timeout(std::time::Duration::from_secs(300))
            .connect(database_url)
            .await
            .context("Failed to connect to PostgreSQL")?;

        Ok(Database { pool })
    }

    /// Simple connectivity check
    pub async fn ping(&self) -> Result<()> {
        sqlx::query("SELECT 1")
            .execute(&self.pool)
            .await
            .context("Database ping failed")?;
        Ok(())
    }

    /// Run pending migrations
    pub async fn migrate(&self) -> Result<()> {
        sqlx::migrate!("./migrations")
            .run(&self.pool)
            .await
            .context("Database migration failed")?;
        Ok(())
    }

    // ─── Mine Site Queries ────────────────────────────────────────

    /// Find mine sites within a radius (PostGIS) — returns sites in JSON
    pub async fn find_sites_within_radius(
        &self,
        lat: f64,
        lon: f64,
        radius_meters: f64,
    ) -> Result<Vec<MineSite>> {
        let sites = sqlx::query_as::<_, MineSite>(
            r#"
            SELECT id, name, ST_AsText(location) as location, mine_type, status, created_at, updated_at
            FROM mine_sites
            WHERE ST_DWithin(
                location::geography,
                ST_SetSRID(ST_MakePoint($1, $2), 4326)::geography,
                $3
            )
            ORDER BY ST_Distance(
                location::geography,
                ST_SetSRID(ST_MakePoint($1, $2), 4326)::geography
            )
            "#,
        )
        .bind(lon)
        .bind(lat)
        .bind(radius_meters)
        .fetch_all(&self.pool)
        .await
        .context("PostGIS radius query failed")?;

        Ok(sites)
    }

    /// Get all mine sites with pagination
    pub async fn list_sites(&self, offset: i64, limit: i64) -> Result<Vec<MineSite>> {
        let sites = sqlx::query_as::<_, MineSite>(
            "SELECT id, name, ST_AsText(location) as location, mine_type, status, created_at, updated_at
             FROM mine_sites ORDER BY created_at DESC OFFSET $1 LIMIT $2"
        )
        .bind(offset)
        .bind(limit)
        .fetch_all(&self.pool)
        .await
        .context("Failed to list mine sites")?;

        Ok(sites)
    }

    /// Get a single mine site by ID
    pub async fn get_site(&self, id: Uuid) -> Result<Option<MineSite>> {
        let site = sqlx::query_as::<_, MineSite>(
            "SELECT id, name, ST_AsText(location) as location, mine_type, status, created_at, updated_at
             FROM mine_sites WHERE id = $1"
        )
        .bind(id)
        .fetch_optional(&self.pool)
        .await
        .context("Failed to fetch mine site")?;

        Ok(site)
    }

    // ─── Analysis Results ─────────────────────────────────────────

    /// Store an analysis result
    pub async fn store_analysis(&self, result: &AnalysisResult) -> Result<()> {
        sqlx::query(
            r#"
            INSERT INTO analysis_results (id, analysis_type, input_data, output_data, model_version, confidence, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            "#,
        )
        .bind(result.id)
        .bind(&result.analysis_type)
        .bind(&result.input_data)
        .bind(&result.output_data)
        .bind(&result.model_version)
        .bind(result.confidence)
        .bind(result.created_at)
        .execute(&self.pool)
        .await
        .context("Failed to store analysis result")?;

        Ok(())
    }

    /// Get recent analysis results by type
    pub async fn get_analyses(
        &self,
        analysis_type: &str,
        limit: i64,
    ) -> Result<Vec<AnalysisResult>> {
        let results = sqlx::query_as::<_, AnalysisResult>(
            "SELECT * FROM analysis_results WHERE analysis_type = $1 ORDER BY created_at DESC LIMIT $2"
        )
        .bind(analysis_type)
        .bind(limit)
        .fetch_all(&self.pool)
        .await
        .context("Failed to fetch analysis results")?;

        Ok(results)
    }

    // ─── Tool Execution Logs ──────────────────────────────────────

    /// Log a tool execution
    pub async fn log_tool_execution(&self, log: &ToolExecutionLog) -> Result<()> {
        sqlx::query(
            r#"
            INSERT INTO tool_execution_logs (id, tool_name, input_params, output_data, status, duration_ms, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            "#,
        )
        .bind(log.id)
        .bind(&log.tool_name)
        .bind(&log.input_params)
        .bind(&log.output_data)
        .bind(&log.status)
        .bind(log.duration_ms)
        .bind(log.created_at)
        .execute(&self.pool)
        .await
        .context("Failed to log tool execution")?;

        Ok(())
    }

    /// Get tool execution stats
    pub async fn get_tool_stats(&self, tool_name: &str) -> Result<ToolStats> {
        let row = sqlx::query(
            r#"
            SELECT
                COUNT(*) as total_executions,
                COUNT(*) FILTER (WHERE status = 'success') as successful,
                COUNT(*) FILTER (WHERE status = 'error') as failed,
                AVG(duration_ms)::float as avg_duration_ms,
                MAX(created_at) as last_execution
            FROM tool_execution_logs
            WHERE tool_name = $1
            "#,
        )
        .bind(tool_name)
        .fetch_one(&self.pool)
        .await
        .context("Failed to get tool stats")?;

        Ok(ToolStats {
            tool_name: tool_name.to_string(),
            total_executions: row.get::<i64, _>("total_executions"),
            successful: row.get::<i64, _>("successful"),
            failed: row.get::<i64, _>("failed"),
            avg_duration_ms: row.get::<Option<f64>, _>("avg_duration_ms"),
            last_execution: row.get::<Option<DateTime<Utc>>, _>("last_execution"),
        })
    }
}

#[derive(Debug, Serialize)]
pub struct ToolStats {
    pub tool_name: String,
    pub total_executions: i64,
    pub successful: i64,
    pub failed: i64,
    pub avg_duration_ms: Option<f64>,
    pub last_execution: Option<DateTime<Utc>>,
}
