use actix_web::{web, HttpResponse};
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use crate::AppState;

#[derive(Debug, Deserialize)]
pub struct GeoAnalyzeRequest {
    pub site_id: Option<uuid::Uuid>,
    pub coordinates: Option<Coordinates>,
    pub analysis_type: Option<String>,
}

#[derive(Debug, Deserialize, Serialize)]
pub struct Coordinates {
    pub lat: f64,
    pub lon: f64,
}

#[derive(Debug, Deserialize)]
pub struct NearbyQuery {
    pub lat: f64,
    pub lon: f64,
    #[serde(default = "default_radius")]
    pub radius_meters: f64,
}

fn default_radius() -> f64 { 50_000.0 }

/// POST /api/v1/geo/analyze — Send geological data to Python service for analysis
pub async fn analyze(
    state: web::Data<Arc<AppState>>,
    body: web::Json<GeoAnalyzeRequest>,
) -> HttpResponse {
    let client = reqwest::Client::new();
    let url = format!("{}/analyze", state.config.geological_service_url);

    match client
        .post(&url)
        .json(&body.into_inner())
        .timeout(std::time::Duration::from_secs(120))
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
            tracing::error!("Geological service call failed: {}", e);
            HttpResponse::BadGateway().json(serde_json::json!({
                "error": "service_unavailable",
                "message": format!("Geological service unreachable: {}", e)
            }))
        }
    }
}

/// GET /api/v1/geo/sites/nearby — Find mine sites near coordinates (PostGIS)
pub async fn nearby_sites(
    state: web::Data<Arc<AppState>>,
    query: web::Query<NearbyQuery>,
) -> HttpResponse {
    match state.db.find_sites_within_radius(query.lat, query.lon, query.radius_meters).await {
        Ok(sites) => HttpResponse::Ok().json(serde_json::json!({
            "sites": sites,
            "count": sites.len(),
            "query": {
                "lat": query.lat,
                "lon": query.lon,
                "radius_meters": query.radius_meters
            }
        })),
        Err(e) => HttpResponse::InternalServerError().json(serde_json::json!({
            "error": "query_failed",
            "message": e.to_string()
        })),
    }
}

/// Call the Python geological service (used by the generic tool executor)
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
        .timeout(std::time::Duration::from_secs(120))
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
