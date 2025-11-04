//! Structured logging module for AI Runtime
//!
//! Provides ECS (Elastic Common Schema) and ASFF (AWS Security Finding Format) compliant logging.
//! Based on Python's ai_runtime/core/structured_logger.py

mod structured;

pub use structured::{
    StructuredLogger, LogSeverity, IncidentSeverity, EcsEvent, SecurityFinding,
    PerformanceMetrics, SystemOperation,
};
