use gvpie_core::{
    gpu::OptimizedGpuExecutionScheduler,
    pixel_language::{ExecutionErrorCode, PixelInstruction},
    GpuCore,
};
use std::sync::Arc;
use tokio::sync::Mutex;
use crate::pixel_vm::PixelProgramResponse;

/// Bridge between AI runtime and GPU execution
#[derive(Debug)]
pub struct GpuExecutionBridge {
    scheduler: Arc<Mutex<Option<OptimizedGpuExecutionScheduler>>>,
    gpu_core: Option<Arc<GpuCore>>,
}

impl GpuExecutionBridge {
    pub fn new(gpu_core: Option<Arc<GpuCore>>) -> Self {
        Self {
            scheduler: Arc::new(Mutex::new(None)),
            gpu_core,
        }
    }

    pub async fn initialize(&self) -> anyhow::Result<()> {
        if let Some(gpu_core) = &self.gpu_core {
            let mut scheduler_guard = self.scheduler.lock().await;
            if scheduler_guard.is_none() {
                let scheduler = OptimizedGpuExecutionScheduler::new(
                    gpu_core.device().clone(),
                    gpu_core.queue().clone()
                ).await?;
                *scheduler_guard = Some(scheduler);
            }
        }
        Ok(())
    }

    pub async fn execute_pixel_program(
        &self,
        program: &[PixelInstruction],
        max_cycles: u64,
    ) -> anyhow::Result<PixelProgramResponse> {
        let scheduler_guard = self.scheduler.lock().await;
        
        if let Some(scheduler) = &*scheduler_guard {
            let start_time = std::time::Instant::now();
            
            let result = scheduler.execute_program(program, max_cycles).await?;
            if result.metadata.error_code != ExecutionErrorCode::Success {
                anyhow::bail!("GPU execution failed with code {:?}", result.metadata.error_code);
            }
            
            Ok(PixelProgramResponse {
                success: true,
                cycles_executed: result.metadata.steps_executed as u64,
                instruction_pointer: result.metadata.final_ip,
                canvas_data: self.canvas_to_rgba(&result.canvas),
                execution_time_ms: start_time.elapsed().as_millis() as u64,
                backend_used: "gpu".to_string(),
                error: None,
            })
        } else {
            anyhow::bail!("GPU scheduler not initialized")
        }
    }

    pub fn is_gpu_available(&self) -> bool {
        self.gpu_core.is_some()
    }

    fn canvas_to_rgba(&self, canvas: &[PixelInstruction]) -> Vec<u8> {
        let mut rgba = Vec::with_capacity(canvas.len() * 4);
        for pixel in canvas {
            rgba.push(pixel.r);
            rgba.push(pixel.g);
            rgba.push(pixel.b);
            rgba.push(pixel.a);
        }
        rgba
    }
}
