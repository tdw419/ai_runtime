use std::{fmt, sync::Arc};
use std::time::Instant;

use anyhow::{anyhow, Result};
use gvpie_core::{
    PixelAssembler, PixelBackend, PixelExecutionOutcome, PixelExecutor, PixelInstruction,
    GpuMachineExecutor,
};
use serde::{Deserialize, Serialize};

pub struct PixelVmRuntime {
    assembler: PixelAssembler,
    #[cfg(feature = "gpu")]
    gpu_core: Option<Arc<gvpie_core::GpuCore>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PixelProgramRequest {
    pub program: Vec<PixelInstruction>,
    pub backend: ExecutionBackend,
    pub max_cycles: u64,
    pub canvas_width: u32,
    pub canvas_height: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PixelProgramResponse {
    pub success: bool,
    pub cycles_executed: u64,
    pub instruction_pointer: u32,
    pub canvas_data: Vec<u8>,
    pub execution_time_ms: u64,
    pub backend_used: String,
    pub error: Option<String>,
}

impl PixelProgramResponse {
    pub fn error(message: impl Into<String>) -> Self {
        Self {
            success: false,
            cycles_executed: 0,
            instruction_pointer: 0,
            canvas_data: Vec::new(),
            execution_time_ms: 0,
            backend_used: "error".to_string(),
            error: Some(message.into()),
        }
    }
}

impl fmt::Debug for PixelVmRuntime {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        #[cfg(feature = "gpu")]
        let gpu_available = self.gpu_core.is_some();
        #[cfg(not(feature = "gpu"))]
        let gpu_available = false;

        f.debug_struct("PixelVmRuntime")
            .field("gpu_available", &gpu_available)
            .finish()
    }
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, Default)]
#[serde(rename_all = "lowercase")]
pub enum ExecutionBackend {
    #[default]
    Cpu,
    Gpu,
}

impl PixelVmRuntime {
    #[cfg(feature = "gpu")]
    pub fn new(gpu_core: Option<Arc<gvpie_core::GpuCore>>) -> Self {
        Self {
            assembler: PixelAssembler::new(64, 64),
            gpu_core,
        }
    }

    #[cfg(not(feature = "gpu"))]
    pub fn new(_gpu_core: Option<Arc<gvpie_core::GpuCore>>) -> Self {
        Self {
            assembler: PixelAssembler::new(64, 64),
        }
    }

    pub async fn execute_program(
        &self,
        request: PixelProgramRequest,
    ) -> Result<PixelProgramResponse> {
        let start = Instant::now();
        let mut executor = PixelExecutor::new(request.canvas_width, request.canvas_height);
        let preferred_backend = match request.backend {
            ExecutionBackend::Cpu => PixelBackend::Cpu,
            ExecutionBackend::Gpu => PixelBackend::Gpu,
        };

        #[cfg(feature = "gpu")]
        if preferred_backend != PixelBackend::Cpu {
            let gpu_core = self
                .gpu_core
                .as_ref()
                .ok_or_else(|| anyhow!("GPU backend requested but no GPU core available"))?;
            let gpu_executor = GpuMachineExecutor::new(
                gpu_core.device().clone(),
                gpu_core.queue().clone(),
            )?;
            executor.enable_gpu(gpu_executor);
        }

        #[cfg(not(feature = "gpu"))]
        if preferred_backend == PixelBackend::Gpu {
            return Err(anyhow!("GPU backend not supported in this build"));
        }

        executor.set_backend(preferred_backend);
        let PixelExecutionOutcome {
            state,
            metadata,
            backend_used,
        } = executor
            .execute_program(&request.program, request.max_cycles)
            .map_err(|err| anyhow!(err))?;

        let elapsed = start.elapsed();
        let canvas_data = Self::canvas_to_rgba(&state.canvas);

        Ok(PixelProgramResponse {
            success: true,
            cycles_executed: metadata.steps_executed as u64,
            instruction_pointer: metadata.final_ip,
            canvas_data,
            execution_time_ms: elapsed.as_millis() as u64,
            backend_used: backend_used.as_str().to_string(),
            error: None,
        })
    }

    pub fn assemble_from_text(&self, source: &str) -> Result<Vec<PixelInstruction>> {
        Ok(self.assembler.assemble_from_text(source))
    }

    pub fn assemble_from_pixels(&self, pixels: &[[u8; 4]]) -> Result<Vec<PixelInstruction>> {
        Ok(self.assembler.assemble_from_pixels(pixels))
    }

    pub fn available_backends(&self) -> Vec<String> {
        let mut backends = vec!["cpu".to_string()];
        #[cfg(feature = "gpu")]
        if self.gpu_core.is_some() {
            backends.push("gpu".to_string());
        }
        backends
    }

    fn canvas_to_rgba(canvas: &[PixelInstruction]) -> Vec<u8> {
        let mut data = Vec::with_capacity(canvas.len() * 4);
        for pixel in canvas {
            data.push(pixel.r);
            data.push(pixel.g);
            data.push(pixel.b);
            data.push(pixel.a);
        }
        data
    }
}
