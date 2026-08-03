mod config;
mod db;
mod oracle;
mod tools;

use actix_cors::Cors;
use actix_web::{web, App, HttpServer, HttpRequest, HttpResponse, middleware};
use actix_web_lab::middleware::from_fn;
use config::AppConfig;
use db::Database;
use std::sync::Arc;
use tracing::{info, error};
use tracing_subscriber::EnvFilter;

/// Shared application state
pub struct AppState {
    pub config: AppConfig,
    pub db: Database,
    pub redis: redis::aio::ConnectionManager,
    pub tools: tools::ToolRegistry,
    pub oracle: Option<Arc<oracle::OracleState>>,
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    // Initialize tracing
    tracing_subscriber::fmt()
        .with_env_filter(EnvFilter::try_from_default_env().unwrap_or_else(|_| EnvFilter::new("info")))
        .init();

    info!("Starting Sovereign Resource DAO (Rust/Actix-web)");

    // Load config
    let config = AppConfig::from_env().expect("Failed to load configuration");
    let bind_addr = format!("{}:{}", config.host, config.port);
    info!("Binding to {}", bind_addr);

    // Connect to PostgreSQL
    let db = Database::new(&config.database_url)
        .await
        .expect("Failed to connect to PostgreSQL");
    info!("PostgreSQL connected");

    // Connect to Redis
    let redis_client = redis::Client::open(config.redis_url.clone())
        .expect("Failed to create Redis client");
    let redis = redis::aio::ConnectionManager::new(redis_client)
        .await
        .expect("Failed to connect to Redis");
    info!("Redis connected");

    // Load tool registry
    let tools = tools::ToolRegistry::from_config(&config.tools_config_path);
    info!("Loaded {} tools", tools.len());

    // Initialize oracle service (optional — requires ORACLE_PRIVATE_KEY)
    let oracle_state = match oracle::OracleConfig::from_env() {
        Ok(oracle_config) => {
            match oracle::client::OracleService::new(oracle_config).await {
                Ok(service) => {
                    info!("Polygon oracle service initialized");
                    Some(Arc::new(oracle::OracleState { service }))
                }
                Err(e) => {
                    error!(error = %e, "Failed to initialize oracle service");
                    None
                }
            }
        }
        Err(e) => {
            info!(reason = %e, "Oracle service not configured — skipping");
            None
        }
    };

    let state = Arc::new(AppState {
        config: config.clone(),
        db,
        redis,
        tools,
        oracle: oracle_state,
    });

    HttpServer::new(move || {
        let cors = if state.config.cors_origins.is_empty() {
            // No CORS origins configured — reject all cross-origin requests
            Cors::default()
        } else if state.config.cors_origins.contains(&"*".to_string()) {
            // Wildcard — allowed only in non-production (validated in config)
            tracing::warn!("CORS is set to wildcard '*' — this should NOT be used in production");
            Cors::default()
                .allow_any_origin()
                .allow_any_method()
                .allow_any_header()
                .max_age(3600)
        } else {
            let mut cors = Cors::default()
                .allow_any_method()
                .allow_any_header()
                .max_age(3600);
            for origin in &state.config.cors_origins {
                cors = cors.allowed_origin(origin);
            }
            cors
        };

        App::new()
            .app_data(web::Data::from(state.clone()))
            .wrap(cors)
            .wrap(tracing_actix_web::TracingLogger::default())
            .wrap(middleware::NormalizePath::trim())
            // Health check endpoints
            .route("/health", web::get().to(health_check))
            .route("/ready", web::get().to(readiness_check))
            // API v1 routes
            .service(
                web::scope("/api/v1")
                    .wrap(from_fn(auth::jwt_middleware))
                    .configure(tools::configure_routes)
                    .configure(oracle::configure_routes)
            )
    })
    .bind(&bind_addr)?
    .run()
    .await
}

/// Health check — always returns 200
async fn health_check() -> HttpResponse {
    HttpResponse::Ok().json(serde_json::json!({
        "status": "healthy",
        "service": "sovereign-resource-dao",
        "version": "1.0.0"
    }))
}

/// Readiness check — verifies DB and Redis connectivity
async fn readiness_check(state: web::Data<Arc<AppState>>) -> HttpResponse {
    let db_ok = state.db.ping().await.is_ok();
    let redis_ok = {
        let mut conn = state.redis.clone();
        redis::cmd("PING").query_async::<_, String>(&mut conn).await.is_ok()
    };

    if db_ok && redis_ok {
        HttpResponse::Ok().json(serde_json::json!({
            "status": "ready",
            "postgres": "connected",
            "redis": "connected"
        }))
    } else {
        HttpResponse::ServiceUnavailable().json(serde_json::json!({
            "status": "not_ready",
            "postgres": if db_ok { "connected" } else { "disconnected" },
            "redis": if redis_ok { "connected" } else { "disconnected" }
        }))
    }
}

/// JWT authentication middleware module
mod auth {
    use actix_web::{HttpRequest, HttpResponse, dev::ServiceRequest, Error};
    use actix_web_lab::middleware::Next;
    use jsonwebtoken::{decode, DecodingKey, Validation, Algorithm};
    use serde::{Deserialize, Serialize};

    #[derive(Debug, Serialize, Deserialize)]
    pub struct Claims {
        pub sub: String,
        pub exp: usize,
        pub iat: usize,
        pub role: Option<String>,
    }

    pub async fn jwt_middleware(
        req: ServiceRequest,
        next: Next<impl actix_web::body::MessageBody>,
    ) -> Result<HttpResponse, Error> {
        // Skip auth for public endpoints if needed
        let path = req.path().to_string();
        if path.ends_with("/health") || path.ends_with("/ready") {
            return next.call(req).await.map(|res| res.map_into_boxed_body());
        }

        let token = req
            .headers()
            .get("Authorization")
            .and_then(|h| h.to_str().ok())
            .and_then(|h| h.strip_prefix("Bearer "));

        match token {
            Some(token) => {
                let jwt_secret = req
                    .app_data::<actix_web::web::Data<std::sync::Arc<crate::AppState>>>()
                    .map(|s| s.config.jwt_secret.clone())
                    .unwrap_or_default();

                let mut validation = Validation::new(Algorithm::HS256);
                validation.validate_exp = true;

                match decode::<Claims>(
                    token,
                    &DecodingKey::from_secret(jwt_secret.as_bytes()),
                    &validation,
                ) {
                    Ok(_token_data) => {
                        // Token is valid; proceed
                        next.call(req).await.map(|res| res.map_into_boxed_body())
                    }
                    Err(e) => {
                        tracing::warn!("JWT validation failed: {}", e);
                        Ok(req.into_response(
                            HttpResponse::Unauthorized().json(serde_json::json!({
                                "error": "invalid_token",
                                "message": "JWT validation failed"
                            }))
                        ))
                    }
                }
            }
            None => {
                Ok(req.into_response(
                    HttpResponse::Unauthorized().json(serde_json::json!({
                        "error": "missing_token",
                        "message": "Authorization header with Bearer token required"
                    }))
                ))
            }
        }
    }
}
