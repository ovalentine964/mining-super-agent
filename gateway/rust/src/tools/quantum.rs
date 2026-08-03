use actix_web::{web, HttpResponse};
use serde::Deserialize;
use std::sync::Arc;
use crate::AppState;

#[derive(Debug, Deserialize)]
pub struct QuantumOptimizeRequest {
    pub problem_type: Option<String>,   // "portfolio", "scheduling", "routing"
    pub constraints: Option<serde_json::Value>,
    pub objective: Option<String>,
    pub parameters: Option<serde_json::Value>,
}

/// POST /api/v1/quantum/optimize — Send optimization problem to Python quantum service
pub async fn optimize(
    state: web::Data<Arc<AppState>>,
    body: web::Json<QuantumOptimizeRequest>,
) -> HttpResponse {
    let client = reqwest::Client::new();
    let url = format!("{}/optimize", state.config.quantum_service_url);

    match client
        .post(&url)
        .json(&body.into_inner())
        .timeout(std::time::Duration::from_secs(600))  // Quantum optimization can take a while
        .send()
        .await
    {
        Ok(resp) => {
            match resp.json::<serde_json::Value>().await {
                Ok(result) => HttpResponse::Ok().json(result),
                Err(e) => HttpResponse::BadGateway().json(serde_json::json!({
                    "error": "invalid_response",
                    "message": e.to_string()
                })),
            }
        }
        Err(e) => {
            tracing::error!("Quantum service call failed: {}", e);
            HttpResponse::BadGateway().json(serde_json::json!({
                "error": "service_unavailable",
                "message": format!("Quantum service unreachable: {}", e)
            }))
        }
    }
}

/// Call the Python quantum service (used by the generic tool executor)
pub async fn call_service(
    client: &reqwest::Client,
    base_url: &str,
    endpoint: &str,
    body: &serde_json::Value,
) -> Result<serde_json::Value, String> {
    let url = format!("{}{}", base_url, endpoint);
    let resp = client
        .post(&url)
        .json(body)
        .timeout(std::time::Duration::from_secs(600))
        .send()
        .await
        .map_err(|e| format!("HTTP error: {}", e))?;

    if !resp.status().is_success() {
        let status = resp.status();
        let text = resp.text().await.unwrap_or_default();
        return Err(format!("Service returned {}: {}", status, text));
    }

    resp.json::<serde_json::Value>()
        .await
        .map_err(|e| format!("JSON parse error: {}", e))
}
