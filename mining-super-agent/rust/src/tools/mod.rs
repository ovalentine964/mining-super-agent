pub mod registry;
pub mod geo;
pub mod satellite;
pub mod market;
pub mod vision;
pub mod quantum;

use actix_web::{web, HttpResponse};
use registry::ToolRegistry;
use std::sync::Arc;
use crate::AppState;

/// Configure all tool API routes under /api/v1
pub fn configure_routes(cfg: &mut web::ServiceConfig) {
    cfg.service(
        web::scope("/tools")
            // List all registered tools
            .route("", web::get().to(list_tools))
            // Execute a tool by name
            .route("/{tool_name}/execute", web::post().to(execute_tool))
            // Tool stats
            .route("/{tool_name}/stats", web::get().to(tool_stats))
    )
    .service(
        web::scope("/geo")
            .route("/analyze", web::post().to(geo::analyze))
            .route("/sites/nearby", web::get().to(geo::nearby_sites))
    )
    .service(
        web::scope("/satellite")
            .route("/process", web::post().to(satellite::process))
            .route("/imagery", web::get().to(satellite::get_imagery))
    )
    .service(
        web::scope("/market")
            .route("/price", web::get().to(market::get_price))
            .route("/history", web::get().to(market::get_history))
            .route("/forecast", web::post().to(market::forecast))
    )
    .service(
        web::scope("/vision")
            .route("/analyze", web::post().to(vision::analyze))
    )
    .service(
        web::scope("/quantum")
            .route("/optimize", web::post().to(quantum::optimize))
    );
}

/// GET /api/v1/tools — List all registered tools
async fn list_tools(state: web::Data<Arc<AppState>>) -> HttpResponse {
    let tools = state.tools.list();
    HttpResponse::Ok().json(serde_json::json!({
        "tools": tools,
        "count": tools.len()
    }))
}

/// POST /api/v1/tools/{tool_name}/execute — Execute a tool
async fn execute_tool(
    state: web::Data<Arc<AppState>>,
    path: web::Path<String>,
    body: web::Json<serde_json::Value>,
) -> HttpResponse {
    let tool_name = path.into_inner();

    // Check rate limit via Redis
    let rate_key = format!("rate:tool:{}", tool_name);
    let mut conn = state.redis.clone();
    let current: Result<i64, _> = redis::cmd("INCR")
        .arg(&rate_key)
        .query_async(&mut conn)
        .await;
    match current {
        Ok(count) => {
            if count == 1 {
                // First request in window — set expiry
                let _: () = redis::cmd("EXPIRE")
                    .arg(&rate_key)
                    .arg(state.config.rate_window_secs)
                    .query_async(&mut conn)
                    .await
                    .unwrap_or(());
            }
            if count as u64 > state.config.default_rate_limit {
                return HttpResponse::TooManyRequests().json(serde_json::json!({
                    "error": "rate_limit_exceeded",
                    "tool": tool_name,
                    "limit": state.config.default_rate_limit,
                    "window_secs": state.config.rate_window_secs
                }));
            }
        }
        Err(e) => {
            tracing::error!("Redis INCR failed: {}", e);
            // Fail open — allow the request
        }
    }

    // Look up the tool
    let tool_config = match state.tools.get(&tool_name) {
        Some(t) => t,
        None => {
            return HttpResponse::NotFound().json(serde_json::json!({
                "error": "tool_not_found",
                "tool": tool_name
            }));
        }
    };

    // Compute deterministic cache key (used for both read and write)
    let cache_key = format!("cache:tool:{}:{}", tool_name, {
        use std::collections::hash_map::DefaultHasher;
        use std::hash::{Hash, Hasher};
        let mut h = DefaultHasher::new();
        body.to_string().hash(&mut h);
        h.finish()
    });

    // Check cache first
    if let Some(_ttl) = tool_config.cache_ttl_secs {
        let cached: Result<Option<String>, _> = redis::cmd("GET")
            .arg(&cache_key)
            .query_async(&mut conn)
            .await;
        if let Ok(Some(cached_str)) = cached {
            if let Ok(cached_val) = serde_json::from_str::<serde_json::Value>(&cached_str) {
                return HttpResponse::Ok().json(serde_json::json!({
                    "tool": tool_name,
                    "cached": true,
                    "result": cached_val
                }));
            }
        }
    }

    // Forward to the appropriate service
    let http_client = reqwest::Client::new();
    let start = std::time::Instant::now();
    let result = match tool_config.service_type.as_str() {
        "geological" => geo::call_service(&http_client, &state.config.geological_service_url, &tool_config.endpoint, &body).await,
        "satellite" => satellite::call_service(&http_client, &state.config.satellite_service_url, &tool_config.endpoint, &body).await,
        "market" => market::call_service(&http_client, &tool_config.endpoint, &body, &state.config).await,
        "vision" => vision::call_service(&http_client, &state.config.vision_service_url, &tool_config.endpoint, &body).await,
        "quantum" => quantum::call_service(&http_client, &state.config.quantum_service_url, &tool_config.endpoint, &body).await,
        _ => {
            return HttpResponse::BadRequest().json(serde_json::json!({
                "error": "unknown_service_type",
                "service_type": tool_config.service_type
            }));
        }
    };
    let duration = start.elapsed();

    // Log execution
    let log = crate::db::ToolExecutionLog {
        id: uuid::Uuid::new_v4(),
        tool_name: tool_name.clone(),
        input_params: body.into_inner(),
        output_data: match &result {
            Ok(v) => v.clone(),
            Err(_) => serde_json::json!(null),
        },
        status: if result.is_ok() { "success" } else { "error" }.to_string(),
        duration_ms: duration.as_millis() as i32,
        created_at: chrono::Utc::now(),
    };
    let _ = state.db.log_tool_execution(&log).await;

    match result {
        Ok(value) => {
            // Cache the result if TTL is configured
            if let Some(ttl) = tool_config.cache_ttl_secs {
                // Reuse the same deterministic cache_key computed above
                let _: () = redis::cmd("SETEX")
                    .arg(&cache_key)
                    .arg(ttl)
                    .arg(value.to_string())
                    .query_async(&mut conn)
                    .await
                    .unwrap_or(());
            }
            HttpResponse::Ok().json(serde_json::json!({
                "tool": tool_name,
                "cached": false,
                "duration_ms": duration.as_millis(),
                "result": value
            }))
        }
        Err(e) => {
            tracing::error!("Tool '{}' execution failed: {}", tool_name, e);
            HttpResponse::BadGateway().json(serde_json::json!({
                "error": "tool_execution_failed",
                "tool": tool_name,
                "message": e
            }))
        }
    }
}

/// GET /api/v1/tools/{tool_name}/stats — Get tool execution statistics
async fn tool_stats(
    state: web::Data<Arc<AppState>>,
    path: web::Path<String>,
) -> HttpResponse {
    let tool_name = path.into_inner();
    match state.db.get_tool_stats(&tool_name).await {
        Ok(stats) => HttpResponse::Ok().json(stats),
        Err(e) => HttpResponse::InternalServerError().json(serde_json::json!({
            "error": "failed_to_get_stats",
            "message": e.to_string()
        })),
    }
}
