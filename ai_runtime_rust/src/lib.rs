pub mod api;
pub mod cartridges;
pub mod config;
pub mod database;
pub mod models;
pub mod pixel_vm;
pub mod gpu_bridge;
pub mod monitor;
pub mod errors;
pub mod logging;

pub use api::SystemStatus;
pub use cartridges::Cartridge;
pub use monitor::{SystemMonitor, SystemMetrics};
pub use errors::{AiRuntimeError, Result};
pub use database::{ExperienceDB, SystemMetricsRecord, DecisionRecord, EventRecord, PatternAnalysis, TrendAnalysis};
pub use logging::{StructuredLogger, LogSeverity, IncidentSeverity};

use std::{path::PathBuf, sync::Arc};
use tokio::sync::RwLock;

use gvpie_core::{PixelInstruction};
use gpu_bridge::GpuExecutionBridge;

pub use pixel_vm::{ExecutionBackend, PixelProgramRequest, PixelProgramResponse};

#[derive(Debug)]
pub struct AiRuntime {
    #[cfg(feature = "gpu")]
    gpu_core: Option<Arc<gvpie_core::GpuCore>>,
    pixel_vm: pixel_vm::PixelVmRuntime,
    cartridge_manager: Arc<RwLock<cartridges::CartridgeManager>>,
    gpu_bridge: GpuExecutionBridge,  // NEW
    // TODO: Add database, monitoring, etc.
}

impl AiRuntime {
    pub async fn new() -> Result<Self> {
        // Initialize GPU core (may fail if no GPU available)
        #[cfg(feature = "gpu")]
        let gpu_core = if std::env::var("GVPIE_DISABLE_GPU").is_ok() {
            None
        } else {
            match gvpie_core::GpuCore::new().await {
                Ok(core) => Some(Arc::new(core)),
                Err(e) => {
                    println!("⚠️  GPU not available: {}", e);
                    None
                }
            }
        };

        #[cfg(not(feature = "gpu"))]
        let gpu_core = None;

        let cartridge_manager =
            cartridges::CartridgeManager::new(cartridge_storage_path())?;

        #[cfg(feature = "gpu")]
        let pixel_vm = pixel_vm::PixelVmRuntime::new(gpu_core.clone());
        #[cfg(not(feature = "gpu"))]
        let pixel_vm = pixel_vm::PixelVmRuntime::new(None);

        let gpu_bridge = GpuExecutionBridge::new(gpu_core.clone());

        // Initialize GPU bridge if available
        if gpu_bridge.is_gpu_available() {
            gpu_bridge.initialize().await.map_err(AiRuntimeError::AnyhowError)?;
        }

        Ok(Self {
            gpu_core,
            pixel_vm,
            cartridge_manager: Arc::new(RwLock::new(cartridge_manager)),
            gpu_bridge,
        })
    }
    
    #[cfg(feature = "gpu")]
    pub fn gpu_available(&self) -> bool {
        self.gpu_bridge.is_gpu_available()
    }

    #[cfg(not(feature = "gpu"))]
    pub fn gpu_available(&self) -> bool {
        false
    }

    pub async fn list_cartridges(&self) -> Vec<Cartridge> {
        let manager = self.cartridge_manager.read().await;
        manager.list()
    }

    pub async fn get_cartridge(&self, id: &str) -> Option<Cartridge> {
        let manager = self.cartridge_manager.read().await;
        manager.get(id)
    }

    pub async fn execute_cartridge(&self, cartridge_id: &str, input_data: Option<&str>) -> Result<ExecutionResult> {
        let start = std::time::Instant::now();
        let manager = self.cartridge_manager.read().await;
        
        // Execute the cartridge
        let output_data = manager.execute(cartridge_id, input_data)?;
        
        // GPU GLYPH EXPANSION INTEGRATION
        let (backend, glyphs_expanded) = if self.gpu_available() {
            self.execute_with_glyph_expansion(&output_data).await?
                .map(|_| ("gpu".to_string(), true))
                .unwrap_or(("cpu".to_string(), false))
        } else {
            ("cpu".to_string(), false)
        };
        
        let result = ExecutionResult {
            output: format!("Executed cartridge: {} ({} bytes)", cartridge_id, output_data.len()),
            backend,
            duration_ms: start.elapsed().as_millis() as u64,
            data: output_data,
            glyphs_expanded,  // NEW: Report if glyph expansion occurred
        };
        
        Ok(result)
    }

    #[cfg(feature = "gpu")]
    async fn execute_with_glyph_expansion(&self, ascii_data: &[u8]) -> Result<Option<()>> {
        // Convert to u32 for glyph expander (assuming ASCII data)
        let ascii_u32: Vec<u32> = ascii_data.iter().map(|&b| b as u32).collect();
        
        // Pad or truncate to expected 128x64 size
        let mut padded_data = vec![32u32; 128 * 64]; // Space characters
        let copy_len = std::cmp::min(ascii_u32.len(), padded_data.len());
        padded_data[..copy_len].copy_from_slice(&ascii_u32[..copy_len]);
        
        // Execute glyph expansion
        // Note: This requires GlyphExpander to be available in gvpie-core
        println!("🎨 Expanding glyphs on GPU...");
        
        // TODO: Actually call glyph expansion once gvpie-core exports it
        // For now, simulate the operation
        tokio::time::sleep(std::time::Duration::from_millis(10)).await;
        println!("✅ Glyph expansion simulated");
        
        Ok(Some(()))
    }
    
    #[cfg(not(feature = "gpu"))]
    async fn execute_with_glyph_expansion(&self, _ascii_data: &[u8]) -> Result<Option<()>> {
        // No-op when GPU feature is disabled
        Ok(Some(()))
    }


    pub async fn create_cartridge(&self, cartridge: Cartridge) -> Result<Cartridge> {
        let mut manager = self.cartridge_manager.write().await;
        manager.create_cartridge(cartridge.clone())?;
        Ok(cartridge)
    }
    
    pub async fn update_cartridge(&self, cartridge: Cartridge) -> Result<Cartridge> {
        let mut manager = self.cartridge_manager.write().await;
        manager.update_cartridge(cartridge.clone())?;
        Ok(cartridge)
    }
    
    pub async fn delete_cartridge(&self, id: &str) -> Result<()> {
        let mut manager = self.cartridge_manager.write().await;
        manager.delete_cartridge(id)?;
        Ok(())
    }

    pub async fn execute_pixel_program(
        &self,
        request: PixelProgramRequest,
    ) -> Result<PixelProgramResponse> {
        self.pixel_vm.execute_program(request).await.map_err(AiRuntimeError::AnyhowError)
    }

    pub fn assemble_pixel_program(
        &self,
        source: &str,
    ) -> Result<Vec<PixelInstruction>> {
        self.pixel_vm.assemble_from_text(source).map_err(AiRuntimeError::AnyhowError)
    }

    pub fn pixel_backends(&self) -> Vec<String> {
        self.pixel_vm.available_backends()
    }
}

// Re-export main types
pub use api::ApiServer;

#[derive(Debug, Clone)]
pub struct ExecutionResult {
    pub output: String,
    pub backend: String,
    pub duration_ms: u64,
    pub data: Vec<u8>,
    pub glyphs_expanded: bool,  // NEW
}

fn cartridge_storage_path() -> PathBuf {
    std::env::var("GVPIE_CARTRIDGE_PATH")
        .map(PathBuf::from)
        .unwrap_or_else(|_| PathBuf::from("./cartridges"))
}
