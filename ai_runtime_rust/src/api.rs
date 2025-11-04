use axum::{
    extract::{Path, State},
    routing::{delete, get, post, put},
    Json, Router,
};
use gvpie_core::PixelInstruction;
use serde::{Deserialize, Serialize};
use std::sync::Arc;

use crate::{
    cartridges::Cartridge, AiRuntime, ExecutionBackend, PixelProgramRequest, PixelProgramResponse,
};

#[derive(Debug, Clone)]
pub struct ApiServer {
    runtime: Arc<AiRuntime>,
}

impl ApiServer {
    pub fn new(runtime: AiRuntime) -> Self {
        Self {
            runtime: Arc::new(runtime),
        }
    }

    pub fn router(runtime: Arc<AiRuntime>) -> Router {
        Router::new()
            .route("/health", get(Self::health))
            .route("/status", get(Self::system_status))
            .route("/api/execute", post(Self::execute_cartridge))
            .route(
                "/api/cartridges",
                get(Self::list_cartridges).post(Self::create_cartridge),
            )
            .route("/api/cartridges/:id", get(Self::get_cartridge))
            .route("/api/cartridges/:id", put(Self::update_cartridge))
            .route("/api/cartridges/:id", delete(Self::delete_cartridge))
            .route("/api/pixel/run", post(Self::execute_pixel_program))
            .route("/api/pixel/assemble", post(Self::assemble_pixel_program))
            .route("/api/pixel/backends", get(Self::list_pixel_backends))
            .with_state(runtime)
    }

    pub fn into_router(self) -> Router {
        Self::router(self.runtime.clone())
    }
    
    pub async fn run(&self, addr: &str) -> Result<(), Box<dyn std::error::Error>> {
        let app = Self::router(self.runtime.clone());
        let listener = tokio::net::TcpListener::bind(addr).await?;
        println!("🌐 Server running on {}", addr);
        axum::Server::bind(&listener.local_addr().unwrap())
            .serve(app.into_make_service())
            .await?;
        Ok(())
    }
    
    pub async fn health() -> &'static str {
        "✅ AI Runtime Healthy"
    }

    pub async fn list_cartridges(State(runtime): State<Arc<AiRuntime>>) -> Json<Vec<Cartridge>> {
        Json(runtime.list_cartridges().await)
    }

    pub async fn get_cartridge(State(runtime): State<Arc<AiRuntime>>, Path(id): Path<String>) -> Result<Json<Cartridge>, Json<ErrorResponse>> {
        match runtime.get_cartridge(&id).await {
            Some(c) => Ok(Json(c)),
            None => Err(Json(ErrorResponse { success: false, error: "Cartridge not found".to_string() })),
        }
    }
    
    pub async fn system_status(
        State(runtime): State<Arc<AiRuntime>>,
    ) -> Json<SystemStatus> {
        Json(SystemStatus {
            version: env!("CARGO_PKG_VERSION").to_string(),
            gpu_available: runtime.gpu_available(),
            uptime: 0,
        })
    }
    
    pub async fn execute_cartridge(
        State(runtime): State<Arc<AiRuntime>>,
        Json(request): Json<ExecuteRequest>,
    ) -> Json<ExecuteResponse> {
        match runtime.execute_cartridge(&request.code, None).await {
            Ok(result) => Json(ExecuteResponse {
                success: true,
                output: result.output,
            }),
            Err(e) => Json(ExecuteResponse {
                success: false,
                output: format!("Execution failed: {}", e),
            }),
        }
    }

    pub async fn execute_pixel_program(
        State(runtime): State<Arc<AiRuntime>>,
        Json(request): Json<PixelExecuteRequest>,
    ) -> Json<PixelProgramResponse> {
        let pixel_request = PixelProgramRequest {
            program: request.program,
            backend: request.backend,
            max_cycles: request.max_cycles,
            canvas_width: request.canvas_width,
            canvas_height: request.canvas_height,
        };

        match runtime.execute_pixel_program(pixel_request).await {
            Ok(response) => Json(response),
            Err(e) => Json(PixelProgramResponse::error(e.to_string())),
        }
    }

    pub async fn assemble_pixel_program(
        State(runtime): State<Arc<AiRuntime>>,
        Json(request): Json<PixelAssembleRequest>,
    ) -> Json<AssembleResponse> {
        match runtime.assemble_pixel_program(&request.source) {
            Ok(program) => {
                let instructions = program.len();
                Json(AssembleResponse {
                    success: true,
                    program,
                    instructions,
                    error: None,
                })
            }
            Err(e) => Json(AssembleResponse {
                success: false,
                program: Vec::new(),
                instructions: 0,
                error: Some(e.to_string()),
            }),
        }
    }

    pub async fn list_pixel_backends(
        State(runtime): State<Arc<AiRuntime>>,
    ) -> Json<BackendsResponse> {
        Json(BackendsResponse {
            backends: runtime.pixel_backends(),
        })
    }

    pub async fn create_cartridge(
        State(runtime): State<Arc<AiRuntime>>,
        Json(payload): Json<CreateCartridgeRequest>,
    ) -> Result<Json<CartridgeResponse>, Json<ErrorResponse>> {
        println!("📦 Creating cartridge: {}", payload.id);
        
        let cartridge = Cartridge {
            id: payload.id,
            name: payload.name,
            description: payload.description,
            code: payload.code,
            version: "1.0.0".to_string(),
            author: Some("API".to_string()),
            tags: vec![],
        };
        
        match runtime.create_cartridge(cartridge).await {
            Ok(created) => {
                let response = CartridgeResponse {
                    success: true,
                    message: "Cartridge created successfully".to_string(),
                    cartridge: Some(created),
                };
                Ok(Json(response))
            }
            Err(e) => {
                let error = ErrorResponse {
                    success: false,
                    error: format!("Failed to create cartridge: {}", e),
                };
                Err(Json(error))
            }
        }
    }

    pub async fn update_cartridge(
        State(runtime): State<Arc<AiRuntime>>,
        Path(id): Path<String>,
        Json(payload): Json<UpdateCartridgeRequest>,
    ) -> Result<Json<CartridgeResponse>, Json<ErrorResponse>> {
        println!("📦 Updating cartridge: {}", id);
        
        let cartridge = Cartridge {
            id,
            name: payload.name,
            description: payload.description,
            code: payload.code,
            version: payload.version.unwrap_or("1.0.0".to_string()),
            author: payload.author,
            tags: payload.tags.unwrap_or_default(),
        };
        
        match runtime.update_cartridge(cartridge).await {
            Ok(updated) => {
                let response = CartridgeResponse {
                    success: true,
                    message: "Cartridge updated successfully".to_string(),
                    cartridge: Some(updated),
                };
                Ok(Json(response))
            }
            Err(e) => {
                let error = ErrorResponse {
                    success: false,
                    error: format!("Failed to update cartridge: {}", e),
                };
                Err(Json(error))
            }
        }
    }

    pub async fn delete_cartridge(
        State(runtime): State<Arc<AiRuntime>>,
        Path(id): Path<String>,
    ) -> Result<Json<DeleteResponse>, Json<ErrorResponse>> {
        println!("🗑️ Deleting cartridge: {}", id);
        
        match runtime.delete_cartridge(&id).await {
            Ok(()) => {
                let response = DeleteResponse {
                    success: true,
                    message: format!("Cartridge {} deleted", id),
                };
                Ok(Json(response))
            }
            Err(e) => {
                let error = ErrorResponse {
                    success: false,
                    error: format!("Failed to delete cartridge: {}", e),
                };
                Err(Json(error))
            }
        }
    }
}

#[derive(Debug, Serialize)]
pub struct SystemStatus {
    version: String,
    gpu_available: bool,
    uptime: u64,
}

#[derive(Debug, Deserialize)]
pub struct ExecuteRequest {
    code: String,
}

#[derive(Debug, Serialize)] 
pub struct ExecuteResponse {
    success: bool,
    output: String,
}

#[derive(Debug, Deserialize)]
pub struct PixelExecuteRequest {
    pub program: Vec<PixelInstruction>,
    #[serde(default)]
    pub backend: ExecutionBackend,
    #[serde(default = "default_max_cycles")]
    pub max_cycles: u64,
    #[serde(default = "default_canvas_width")]
    pub canvas_width: u32,
    #[serde(default = "default_canvas_height")]
    pub canvas_height: u32,
}

#[derive(Debug, Deserialize)]
pub struct PixelAssembleRequest {
    pub source: String,
}

#[derive(Debug, Serialize)]
pub struct AssembleResponse {
    pub success: bool,
    pub program: Vec<PixelInstruction>,
    pub instructions: usize,
    pub error: Option<String>,
}

#[derive(Debug, Serialize)]
pub struct BackendsResponse {
    pub backends: Vec<String>,
}

#[derive(Debug, Deserialize)]
pub struct CreateCartridgeRequest {
    pub id: String,
    pub name: String,
    pub description: String,
    pub code: String,
}

#[derive(Debug, Serialize)]
pub struct CartridgeResponse {
    pub success: bool,
    pub message: String,
    pub cartridge: Option<Cartridge>,
}

#[derive(Debug, Serialize)]
pub struct DeleteResponse {
    pub success: bool,
    pub message: String,
}

#[derive(Debug, Serialize)]
pub struct ErrorResponse {
    pub success: bool,
    pub error: String,
}

fn default_max_cycles() -> u64 {
    1024
}

fn default_canvas_width() -> u32 {
    64
}

fn default_canvas_height() -> u32 {
    64
}

#[derive(Debug, Deserialize)]
pub struct UpdateCartridgeRequest {
    pub name: String,
    pub description: String,
    pub code: String,
    pub version: Option<String>,
    pub author: Option<String>,
    pub tags: Option<Vec<String>>,
}
