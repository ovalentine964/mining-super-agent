//! WebSocket Server — Real-time updates for the Sovereign Resource DAO
//!
//! Broadcasts extraction records, royalty distributions, and governance votes
//! to connected clients in real-time.

use actix_web::{web, HttpRequest, HttpResponse, Error};
use actix_web_actors::actix::{Actor, ActorContext, AsyncContext, StreamHandler};
use actix_ws::Message;
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tokio::sync::broadcast;
use tracing::{info, error};

/// Real-time event broadcast to WebSocket clients
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WsEvent {
    pub event_type: String,
    pub data: serde_json::Value,
    pub timestamp: u64,
}

/// WebSocket session actor
pub struct WsSession {
    event_receiver: broadcast::Receiver<WsEvent>,
}

impl WsSession {
    pub fn new(event_receiver: broadcast::Receiver<WsEvent>) -> Self {
        Self { event_receiver }
    }
}

impl Actor for WsSession {
    type Context = actix_ws::WebsocketContext<Self>;

    fn started(&mut self, ctx: &mut Self::Context) {
        info!("WebSocket client connected");

        // Spawn task to forward events from broadcast channel to WebSocket
        let addr = ctx.address();
        let mut rx = self.event_receiver.resubscribe();

        actix::spawn(async move {
            loop {
                match rx.recv().await {
                    Ok(event) => {
                        if let Ok(json) = serde_json::to_string(&event) {
                            addr.do_send(WsText(json));
                        }
                    }
                    Err(broadcast::error::RecvError::Lagged(n)) => {
                        info!("WebSocket client lagged by {} messages", n);
                    }
                    Err(broadcast::error::RecvError::Closed) => {
                        break;
                    }
                }
            }
        });
    }

    fn stopped(&mut self, _: &mut Self::Context) {
        info!("WebSocket client disconnected");
    }
}

/// Message to send text to WebSocket
#[derive(actix::Message)]
#[rtype(result = "()")]
struct WsText(String);

impl Handler<WsText> for WsSession {
    type Result = ();

    fn handle(&mut self, msg: WsText, ctx: &mut Self::Context) {
        ctx.text(msg.0);
    }
}

/// Handle incoming WebSocket messages (ping/pong, close)
impl StreamHandler<Result<Message, actix_ws::ProtocolError>> for WsSession {
    fn handle(&mut self, msg: Result<Message, actix_ws::ProtocolError>, ctx: &mut Self::Context) {
        match msg {
            Ok(Message::Ping(msg)) => ctx.pong(&msg),
            Ok(Message::Text(text)) => {
                // Client messages are ignored (read-only stream)
                info!("Received from client: {}", text);
            }
            Ok(Message::Close(reason)) => {
                ctx.close(reason);
                ctx.stop();
            }
            _ => {}
        }
    }
}

/// WebSocket event broadcaster
pub struct WsBroadcaster {
    sender: broadcast::Sender<WsEvent>,
}

impl WsBroadcaster {
    pub fn new() -> Self {
        let (sender, _) = broadcast::channel(1024);
        Self { sender }
    }

    /// Broadcast an event to all connected WebSocket clients
    pub fn broadcast(&self, event: WsEvent) {
        let _ = self.sender.send(event);
    }

    /// Get a receiver for the broadcast channel
    pub fn subscribe(&self) -> broadcast::Receiver<WsEvent> {
        self.sender.subscribe()
    }

    /// Broadcast extraction recorded event
    pub fn extraction_recorded(&self, record_id: u64, mineral: &str, location: &str) {
        self.broadcast(WsEvent {
            event_type: "extraction_recorded".to_string(),
            data: serde_json::json!({
                "record_id": record_id,
                "mineral": mineral,
                "location": location,
            }),
            timestamp: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap_or_default()
                .as_secs(),
        });
    }

    /// Broadcast royalty distribution event
    pub fn royalty_distributed(&self, total: &str, dev_share: &str, community_share: &str) {
        self.broadcast(WsEvent {
            event_type: "royalty_distributed".to_string(),
            data: serde_json::json!({
                "total": total,
                "dev_share": dev_share,
                "community_share": community_share,
            }),
            timestamp: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap_or_default()
                .as_secs(),
        });
    }

    /// Broadcast governance vote event
    pub fn vote_cast(&self, proposal_id: u64, voter: &str, support: bool) {
        self.broadcast(WsEvent {
            event_type: "vote_cast".to_string(),
            data: serde_json::json!({
                "proposal_id": proposal_id,
                "voter": voter,
                "support": support,
            }),
            timestamp: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap_or_default()
                .as_secs(),
        });
    }
}

/// WebSocket upgrade handler
pub async fn ws_handler(
    req: HttpRequest,
    stream: web::Payload,
    broadcaster: web::Data<WsBroadcaster>,
) -> Result<HttpResponse, Error> {
    let receiver = broadcaster.subscribe();
    let session = WsSession::new(receiver);
    actix_ws::handle(&req, stream, session)
}
