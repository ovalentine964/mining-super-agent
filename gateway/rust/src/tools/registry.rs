use serde::Deserialize;
use std::collections::HashMap;
use dashmap::DashMap;
use chrono::{DateTime, Utc};

/// Tool configuration loaded from YAML
#[derive(Debug, Clone, Deserialize)]
pub struct ToolConfig {
    pub name: String,
    pub description: String,
    pub service_type: String,  // geological, satellite, market, vision, quantum
    pub endpoint: String,
    pub method: String,        // GET, POST
    pub rate_limit: Option<u64>,
    pub cache_ttl_secs: Option<u64>,
    pub timeout_secs: Option<u64>,
    pub enabled: bool,
    /// JSON Schema for validating tool input parameters
    pub params_schema: Option<serde_json::Value>,
    /// Required parameter names (enforced even without full schema)
    pub required_params: Option<Vec<String>>,
}

/// YAML file structure
#[derive(Debug, Deserialize)]
struct ToolsYaml {
    tools: Vec<ToolConfig>,
}

/// In-memory tool registry with caching support
pub struct ToolRegistry {
    tools: HashMap<String, ToolConfig>,
    /// Per-tool rate limit counters (key: "tool_name:minute_timestamp")
    rate_counters: DashMap<String, (u64, DateTime<Utc>)>,
}

impl ToolRegistry {
    /// Load tools from a YAML config file
    pub fn from_config(path: &str) -> Self {
        let tools = match std::fs::read_to_string(path) {
            Ok(content) => {
                match serde_yaml::from_str::<ToolsYaml>(&content) {
                    Ok(yaml) => {
                        yaml.tools.into_iter()
                            .filter(|t| t.enabled)
                            .map(|t| (t.name.clone(), t))
                            .collect()
                    }
                    Err(e) => {
                        tracing::error!("Failed to parse tools YAML: {}", e);
                        HashMap::new()
                    }
                }
            }
            Err(e) => {
                tracing::warn!("Tools config file not found at '{}': {}. Using empty registry.", path, e);
                HashMap::new()
            }
        };

        tracing::info!("Loaded {} tools from {}", tools.len(), path);

        ToolRegistry {
            tools,
            rate_counters: DashMap::new(),
        }
    }

    /// Get a tool by name
    pub fn get(&self, name: &str) -> Option<ToolConfig> {
        self.tools.get(name).cloned()
    }

    /// List all registered tools (summary)
    pub fn list(&self) -> Vec<ToolSummary> {
        self.tools.values().map(|t| ToolSummary {
            name: t.name.clone(),
            description: t.description.clone(),
            service_type: t.service_type.clone(),
            endpoint: t.endpoint.clone(),
            rate_limit: t.rate_limit,
            cache_ttl_secs: t.cache_ttl_secs,
            enabled: t.enabled,
        }).collect()
    }

    /// Number of registered tools
    pub fn len(&self) -> usize {
        self.tools.len()
    }

    /// Check if a tool exists
    pub fn contains(&self, name: &str) -> bool {
        self.tools.contains_key(name)
    }

    /// Validate input parameters against the tool's schema.
    /// Returns Ok(()) if valid, Err(message) if validation fails.
    pub fn validate_params(&self, name: &str, params: &serde_json::Value) -> Result<(), String> {
        let tool = match self.tools.get(name) {
            Some(t) => t,
            None => return Err(format!("Tool '{}' not found", name)),
        };

        // 1. Check required params
        if let Some(ref required) = tool.required_params {
            let obj = params.as_object().ok_or("Parameters must be a JSON object")?;
            for param_name in required {
                if !obj.contains_key(param_name) {
                    return Err(format!(
                        "Missing required parameter '{}' for tool '{}'",
                        param_name, name
                    ));
                }
                // Reject null values for required params
                if obj[param_name].is_null() {
                    return Err(format!(
                        "Required parameter '{}' for tool '{}' must not be null",
                        param_name, name
                    ));
                }
            }
        }

        // 2. Validate against JSON Schema if provided
        if let Some(ref schema) = tool.params_schema {
            // Use jsonschema crate for validation
            match jsonschema::validate(schema, params) {
                Ok(()) => {}
                Err(errors) => {
                    let msgs: Vec<String> = errors.map(|e| e.to_string()).collect();
                    return Err(format!(
                        "Parameter validation failed for tool '{}': {}",
                        name, msgs.join("; ")
                    ));
                }
            }
        }

        // 3. Type safety: reject unexpected top-level types
        if !params.is_object() && !params.is_null() {
            return Err("Parameters must be a JSON object".to_string());
        }

        Ok(())
    }

    /// Check per-tool rate limit (token bucket in-memory, fallback to Redis)
    pub fn check_rate_limit(&self, name: &str) -> bool {
        if let Some(tool) = self.tools.get(name) {
            if let Some(limit) = tool.rate_limit {
                let now = Utc::now();
                let minute_key = format!("{}:{}", name, now.timestamp() / 60);
                let mut entry = self.rate_counters.entry(minute_key).or_insert((0, now));
                let (count, ref mut ts) = *entry;
                if (now - *ts).num_seconds() >= 60 {
                    *entry = (1, now);
                    return true;
                }
                if count >= limit {
                    return false;
                }
                *entry = (count + 1, *ts);
            }
        }
        true
    }
}

/// Serializable tool summary for API responses
#[derive(Debug, serde::Serialize)]
pub struct ToolSummary {
    pub name: String,
    pub description: String,
    pub service_type: String,
    pub endpoint: String,
    pub rate_limit: Option<u64>,
    pub cache_ttl_secs: Option<u64>,
    pub enabled: bool,
}
