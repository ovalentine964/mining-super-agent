use serde::Deserialize;
use std::env;
use anyhow::{Context, Result};

/// Application configuration loaded from environment variables and YAML
#[derive(Debug, Clone, Deserialize)]
pub struct AppConfig {
    #[serde(default = "default_host")]
    pub host: String,
    #[serde(default = "default_port")]
    pub port: u16,

    pub database_url: String,
    pub redis_url: String,
    pub jwt_secret: String,

    #[serde(default)]
    pub cors_origins: Vec<String>,

    #[serde(default = "default_tools_config")]
    pub tools_config_path: String,

    /// Python AI/ML service base URLs
    #[serde(default = "default_deerflow_url")]
    pub deerflow_url: String,
    #[serde(default = "default_geological_url")]
    pub geological_service_url: String,
    #[serde(default = "default_satellite_url")]
    pub satellite_service_url: String,
    #[serde(default = "default_vision_url")]
    pub vision_service_url: String,
    #[serde(default = "default_quantum_url")]
    pub quantum_service_url: String,

    // External API keys
    pub finnhub_api_key: Option<String>,
    pub eia_api_key: Option<String>,

    /// Rate limiting defaults
    #[serde(default = "default_rate_limit")]
    pub default_rate_limit: u64,
    #[serde(default = "default_rate_window_secs")]
    pub rate_window_secs: u64,
}

fn default_host() -> String { "0.0.0.0".to_string() }
fn default_port() -> u16 { 8080 }
fn default_tools_config() -> String { "config/tools.yaml".to_string() }
fn default_deerflow_url() -> String { "http://deerflow:8000".to_string() }
fn default_geological_url() -> String { "http://geological:8001".to_string() }
fn default_satellite_url() -> String { "http://satellite:8002".to_string() }
fn default_vision_url() -> String { "http://vision:8003".to_string() }
fn default_quantum_url() -> String { "http://quantum:8004".to_string() }
fn default_rate_limit() -> u64 { 100 }
fn default_rate_window_secs() -> u64 { 60 }

impl AppConfig {
    /// Load configuration from environment variables.
    /// Required env vars: DATABASE_URL, REDIS_URL, JWT_SECRET
    pub fn from_env() -> Result<Self> {
        let database_url = env::var("DATABASE_URL")
            .context("DATABASE_URL must be set")?;
        let redis_url = env::var("REDIS_URL")
            .context("REDIS_URL must be set")?;
        let jwt_secret = env::var("JWT_SECRET")
            .context("JWT_SECRET must be set")?;

        // Validate JWT secret strength
        if jwt_secret.len() < 32 {
            anyhow::bail!("JWT_SECRET must be at least 32 characters");
        }

        let cors_raw = env::var("CORS_ORIGINS").unwrap_or_default();

        // Validate: refuse to start in production with wildcard "*"
        let app_env = env::var("APP_ENV").unwrap_or_else(|_| "development".to_string());
        if cors_raw.trim() == "*" && app_env == "production" {
            anyhow::bail!(
                "CORS_ORIGINS must not be '*' in production. \
                 Set explicit allowed origins (e.g. CORS_ORIGINS=https://yourdomain.com)"
            );
        }

        let cors_origins: Vec<String> = cors_raw
            .split(',')
            .map(|s| s.trim().to_string())
            .filter(|s| !s.is_empty())
            .collect();

        Ok(AppConfig {
            host: env::var("HOST").unwrap_or_else(|_| default_host()),
            port: env::var("PORT")
                .ok()
                .and_then(|p| p.parse().ok())
                .unwrap_or_else(default_port),
            database_url,
            redis_url,
            jwt_secret,
            cors_origins,
            tools_config_path: env::var("TOOLS_CONFIG_PATH")
                .unwrap_or_else(|_| default_tools_config()),
            deerflow_url: env::var("DEERFLOW_URL")
                .unwrap_or_else(|_| default_deerflow_url()),
            geological_service_url: env::var("GEOLOGICAL_SERVICE_URL")
                .unwrap_or_else(|_| default_geological_url()),
            satellite_service_url: env::var("SATELLITE_SERVICE_URL")
                .unwrap_or_else(|_| default_satellite_url()),
            vision_service_url: env::var("VISION_SERVICE_URL")
                .unwrap_or_else(|_| default_vision_url()),
            quantum_service_url: env::var("QUANTUM_SERVICE_URL")
                .unwrap_or_else(|_| default_quantum_url()),
            finnhub_api_key: env::var("FINNHUB_API_KEY").ok(),
            eia_api_key: env::var("EIA_API_KEY").ok(),
            default_rate_limit: env::var("DEFAULT_RATE_LIMIT")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or_else(default_rate_limit),
            rate_window_secs: env::var("RATE_WINDOW_SECS")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or_else(default_rate_window_secs),
        })
    }

    /// Load additional YAML config overlay (optional)
    pub fn with_yaml_overlay(mut self, path: &str) -> Result<Self> {
        let content = std::fs::read_to_string(path)
            .with_context(|| format!("Failed to read YAML config: {}", path))?;
        let yaml_config: serde_yaml::Value = serde_yaml::from_str(&content)
            .context("Failed to parse YAML config")?;

        // Overlay YAML values onto env-based config
        if let Some(host) = yaml_config.get("host").and_then(|v| v.as_str()) {
            self.host = host.to_string();
        }
        if let Some(port) = yaml_config.get("port").and_then(|v| v.as_u64()) {
            self.port = port as u16;
        }
        if let Some(origins) = yaml_config.get("cors_origins").and_then(|v| v.as_sequence()) {
            let app_env = std::env::var("APP_ENV").unwrap_or_else(|_| "development".to_string());
            let origins_vec: Vec<String> = origins
                .iter()
                .filter_map(|v| v.as_str().map(|s| s.to_string()))
                .collect();
            if origins_vec.contains(&"*".to_string()) && app_env == "production" {
                anyhow::bail!(
                    "cors_origins must not contain '*' in production"
                );
            }
            self.cors_origins = origins_vec;
        }
        Ok(self)
    }
}
