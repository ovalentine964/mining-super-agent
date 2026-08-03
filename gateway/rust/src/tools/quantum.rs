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
                Err(e) => {
                    tracing::error!("Quantum service invalid response: {}", e);
                    HttpResponse::BadGateway().json(serde_json::json!({
                        "error": "invalid_response",
                        "message": "Service returned an invalid response"
                    }))
                }
            }
        }
        Err(e) => {
            tracing::error!("Quantum service call failed: {}", e);
            HttpResponse::BadGateway().json(serde_json::json!({
                "error": "service_unavailable",
                "message": "Quantum optimization service is temporarily unavailable"
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
        .map_err(|e| {
            tracing::error!("Quantum service HTTP error ({}): {}", endpoint, e);
            "Service temporarily unavailable".to_string()
        })?;

    if !resp.status().is_success() {
        let status = resp.status();
        let text = resp.text().await.unwrap_or_default();
        tracing::error!("Quantum service returned {} at {}: {}", status, endpoint, text);
        return Err(format!("Service error (HTTP {})", status));
    }

    resp.json::<serde_json::Value>()
        .await
        .map_err(|e| {
            tracing::error!("Quantum service JSON parse error: {}", e);
            "Invalid response from quantum service".to_string()
        })
}
