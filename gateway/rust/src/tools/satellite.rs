use actix_web::{web, HttpResponse};
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use crate::AppState;

#[derive(Debug, Deserialize)]
pub struct SatelliteProcessRequest {
    pub site_id: Option<uuid::Uuid>,
    pub coordinates: Option<GeoPoint>,
    pub date_range: Option<DateRange>,
    pub bands: Option<Vec<String>>,
    pub analysis_type: Option<String>,  // ndvi, change_detection, mineral_mapping
}

#[derive(Debug, Deserialize, Serialize)]
pub struct GeoPoint {
    pub lat: f64,
    pub lon: f64,
}

#[derive(Debug, Deserialize)]
pub struct DateRange {
    pub start: String,
    pub end: String,
}

#[derive(Debug, Deserialize)]
pub struct ImageryQuery {
    pub lat: f64,
    pub lon: f64,
    #[serde(default = "default_buffer")]
    pub buffer_km: f64,
    pub date_from: Option<String>,
    pub date_to: Option<String>,
}

fn default_buffer() -> f64 { 10.0 }

/// POST /api/v1/satellite/process — Send satellite imagery for processing
pub async fn process(
    state: web::Data<Arc<AppState>>,
    body: web::Json<SatelliteProcessRequest>,
) -> HttpResponse {
    let client = reqwest::Client::new();
    let url = format!("{}/process", state.config.satellite_service_url);

    match client
        .post(&url)
        .json(&body.into_inner())
        .timeout(std::time::Duration::from_secs(300))  // Satellite processing can take longer
        .send()
        .await
    {
        Ok(resp) => {
            match resp.json::<serde_json::Value>().await {
                Ok(result) => HttpResponse::Ok().json(result),
                Err(e) => {
                    tracing::error!("Satellite service invalid response: {}", e);
                    HttpResponse::BadGateway().json(serde_json::json!({
                        "error": "invalid_response",
                        "message": "Service returned an invalid response"
                    }))
                }
            }
        }
        Err(e) => {
            tracing::error!("Satellite service call failed: {}", e);
            HttpResponse::BadGateway().json(serde_json::json!({
                "error": "service_unavailable",
                "message": "Satellite processing service is temporarily unavailable"
            }))
        }
    }
}

/// GET /api/v1/satellite/imagery — Query available satellite imagery
pub async fn get_imagery(
    state: web::Data<Arc<AppState>>,
    query: web::Query<ImageryQuery>,
) -> HttpResponse {
    let client = reqwest::Client::new();
    let url = format!("{}/imagery", state.config.satellite_service_url);

    let mut req = client.get(&url)
        .query(&[
            ("lat", query.lat.to_string()),
            ("lon", query.lon.to_string()),
            ("buffer_km", query.buffer_km.to_string()),
        ]);

    if let Some(ref from) = query.date_from {
        req = req.query(&[("date_from", from.as_str())]);
    }
    if let Some(ref to) = query.date_to {
        req = req.query(&[("date_to", to.as_str())]);
    }

    match req.send().await {
        Ok(resp) => {
            match resp.json::<serde_json::Value>().await {
                Ok(result) => HttpResponse::Ok().json(result),
                Err(e) => {
                    tracing::error!("Satellite imagery invalid response: {}", e);
                    HttpResponse::BadGateway().json(serde_json::json!({
                        "error": "invalid_response",
                        "message": "Service returned an invalid response"
                    }))
                }
            }
        }
        Err(e) => {
            tracing::error!("Satellite imagery query failed: {}", e);
            HttpResponse::BadGateway().json(serde_json::json!({
                "error": "service_unavailable",
                "message": "Satellite imagery service is temporarily unavailable"
            }))
        }
    }
}

/// Call the Python satellite service (used by the generic tool executor)
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
        .timeout(std::time::Duration::from_secs(300))
        .send()
        .await
        .map_err(|e| {
            tracing::error!("Satellite service HTTP error ({}): {}", endpoint, e);
            "Service temporarily unavailable".to_string()
        })?;

    if !resp.status().is_success() {
        let status = resp.status();
        let text = resp.text().await.unwrap_or_default();
        tracing::error!("Satellite service returned {} at {}: {}", status, endpoint, text);
        return Err(format!("Service error (HTTP {})", status));
    }

    resp.json::<serde_json::Value>()
        .await
        .map_err(|e| {
            tracing::error!("Satellite service JSON parse error: {}", e);
            "Invalid response from satellite service".to_string()
        })
}
