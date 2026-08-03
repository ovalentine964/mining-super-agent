use actix_web::{web, HttpResponse};
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use crate::AppState;
use crate::config::AppConfig;

#[derive(Debug, Deserialize)]
pub struct PriceQuery {
    pub symbol: String,   // e.g. "GC=F" for gold, "CL=F" for crude oil
    pub source: Option<String>,  // "finnhub", "yfinance"
}

#[derive(Debug, Deserialize)]
pub struct HistoryQuery {
    pub symbol: String,
    pub period: Option<String>,   // "1d", "5d", "1mo", "3mo", "1y"
    pub interval: Option<String>, // "1m", "5m", "1h", "1d"
}

#[derive(Debug, Deserialize)]
pub struct ForecastRequest {
    pub symbol: String,
    pub horizon_days: Option<u32>,
    pub model: Option<String>,    // "arima", "lstm", "prophet"
}

/// GET /api/v1/market/price — Get current commodity price
pub async fn get_price(
    state: web::Data<Arc<AppState>>,
    query: web::Query<PriceQuery>,
) -> HttpResponse {
    let client = reqwest::Client::new();
    let source = query.source.as_deref().unwrap_or("finnhub");

    match source {
        "finnhub" => {
            let api_key = match &state.config.finnhub_api_key {
                Some(k) => k.clone(),
                None => {
                    return HttpResponse::InternalServerError().json(serde_json::json!({
                        "error": "api_key_missing",
                        "message": "FINNHUB_API_KEY not configured"
                    }));
                }
            };
            let url = format!(
                "https://finnhub.io/api/v1/quote?symbol={}&token={}",
                query.symbol, api_key
            );
            match client.get(&url).send().await {
                Ok(resp) => match resp.json::<serde_json::Value>().await {
                    Ok(data) => HttpResponse::Ok().json(serde_json::json!({
                        "symbol": query.symbol,
                        "source": "finnhub",
                        "data": data
                    })),
                    Err(e) => {
                        tracing::error!("Finnhub response parse error: {}", e);
                        HttpResponse::BadGateway().json(serde_json::json!({
                            "error": "parse_error",
                            "message": "Invalid response from market data provider"
                        }))
                    }
                },
                Err(e) => {
                    tracing::error!("Finnhub API error: {}", e);
                    HttpResponse::BadGateway().json(serde_json::json!({
                        "error": "api_error",
                        "message": "Market data service is temporarily unavailable"
                    }))
                }
            }
        }
        _ => {
            // For yfinance, delegate to Python service
            let url = format!("{}/market/price", state.config.deerflow_url);
            match client.get(&url).query(&[("symbol", query.symbol.as_str())]).send().await {
                Ok(resp) => match resp.json::<serde_json::Value>().await {
                    Ok(data) => HttpResponse::Ok().json(data),
                    Err(e) => {
                        tracing::error!("Market data service parse error: {}", e);
                        HttpResponse::BadGateway().json(serde_json::json!({
                            "error": "parse_error",
                            "message": "Invalid response from market data service"
                        }))
                    }
                },
                Err(e) => {
                    tracing::error!("Market data service unreachable: {}", e);
                    HttpResponse::BadGateway().json(serde_json::json!({
                        "error": "service_unavailable",
                        "message": "Market data service is temporarily unavailable"
                    }))
                }
            }
        }
    }
}

/// GET /api/v1/market/history — Get historical price data
pub async fn get_history(
    state: web::Data<Arc<AppState>>,
    query: web::Query<HistoryQuery>,
) -> HttpResponse {
    let client = reqwest::Client::new();
    let url = format!("{}/market/history", state.config.deerflow_url);

    let period = query.period.as_deref().unwrap_or("1mo");
    let interval = query.interval.as_deref().unwrap_or("1d");

    match client
        .get(&url)
        .query(&[
            ("symbol", query.symbol.as_str()),
            ("period", period),
            ("interval", interval),
        ])
        .send()
        .await
    {
        Ok(resp) => match resp.json::<serde_json::Value>().await {
            Ok(data) => HttpResponse::Ok().json(data),
            Err(e) => {
                tracing::error!("Market history parse error: {}", e);
                HttpResponse::BadGateway().json(serde_json::json!({
                    "error": "parse_error",
                    "message": "Invalid response from market data service"
                }))
            }
        },
        Err(e) => {
            tracing::error!("Market history service unreachable: {}", e);
            HttpResponse::BadGateway().json(serde_json::json!({
                "error": "service_unavailable",
                "message": "Market data service is temporarily unavailable"
            }))
        }
    }
}

/// POST /api/v1/market/forecast — Generate price forecast via Python ML service
pub async fn forecast(
    state: web::Data<Arc<AppState>>,
    body: web::Json<ForecastRequest>,
) -> HttpResponse {
    let client = reqwest::Client::new();
    let url = format!("{}/market/forecast", state.config.deerflow_url);

    match client
        .post(&url)
        .json(&body.into_inner())
        .timeout(std::time::Duration::from_secs(120))
        .send()
        .await
    {
        Ok(resp) => match resp.json::<serde_json::Value>().await {
            Ok(result) => HttpResponse::Ok().json(result),
            Err(e) => {
                tracing::error!("Forecast service invalid response: {}", e);
                HttpResponse::BadGateway().json(serde_json::json!({
                    "error": "invalid_response",
                    "message": "Invalid response from forecast service"
                }))
            }
        },
        Err(e) => {
            tracing::error!("Forecast service unreachable: {}", e);
            HttpResponse::BadGateway().json(serde_json::json!({
                "error": "service_unavailable",
                "message": "Forecast service is temporarily unavailable"
            }))
        }
    }
}

/// Call market service directly (used by generic tool executor)
pub async fn call_service(
    client: &reqwest::Client,
    endpoint: &str,
    body: &serde_json::Value,
    config: &AppConfig,
) -> Result<serde_json::Value, String> {
    // Market endpoints can be Finnhub direct or Python service
    if endpoint.starts_with("/finnhub") {
        let api_key = config.finnhub_api_key.as_ref()
            .ok_or("FINNHUB_API_KEY not configured")?;
        let symbol = body.get("symbol")
            .and_then(|v| v.as_str())
            .unwrap_or("GC=F");
        let url = format!(
            "https://finnhub.io/api/v1/quote?symbol={}&token={}",
            symbol, api_key
        );
        let resp = client.get(&url).send().await
            .map_err(|e| {
                tracing::error!("Finnhub HTTP error ({}): {}", endpoint, e);
                "Service temporarily unavailable".to_string()
            })?;
        resp.json::<serde_json::Value>().await
            .map_err(|e| {
                tracing::error!("Finnhub JSON parse error: {}", e);
                "Invalid response from market data provider".to_string()
            })
    } else {
        let url = format!("{}{}", config.deerflow_url, endpoint);
        let resp = client.post(&url).json(body)
            .timeout(std::time::Duration::from_secs(120))
            .send().await
            .map_err(|e| {
                tracing::error!("Market service HTTP error ({}): {}", endpoint, e);
                "Service temporarily unavailable".to_string()
            })?;
        if !resp.status().is_success() {
            let status = resp.status();
            let text = resp.text().await.unwrap_or_default();
            tracing::error!("Market service returned {} at {}: {}", status, endpoint, text);
            return Err(format!("Service error (HTTP {})", status));
        }
        resp.json::<serde_json::Value>().await
            .map_err(|e| {
                tracing::error!("Market service JSON parse error: {}", e);
                "Invalid response from market data service".to_string()
            })
    }
}
