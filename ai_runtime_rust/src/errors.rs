use thiserror::Error;
use crate::cartridges::CartridgeError;

pub type Result<T> = std::result::Result<T, AiRuntimeError>;

#[derive(Error, Debug)]
pub enum AiRuntimeError {
    #[error("Configuration error: {0}")]
    ConfigError(String),
    #[error("Database error: {0}")]
    DatabaseError(#[from] rusqlite::Error),
    #[error("Monitor error: {0}")]
    MonitorError(String),
    #[error("I/O error: {0}")]
    IoError(#[from] std::io::Error),
    #[error("Serialization error: {0}")]
    SerializationError(#[from] serde_json::Error),
    #[error("YAML serialization error: {0}")]
    YamlSerializationError(#[from] serde_yaml::Error),
    #[error("Anyhow error: {0}")]
    AnyhowError(#[from] anyhow::Error),
    #[error("Cartridge error: {0}")]
    CartridgeError(#[from] CartridgeError),
    #[error("Internal error: {0}")]
    InternalError(String),
    #[error("Not found: {0}")]
    NotFound(String),
    #[error("Validation error: {0}")]
    ValidationError(String),
    #[error("LLM error: {0}")]
    LlmError(String),
    #[error("Unknown error")]
    Unknown,
}

impl AiRuntimeError {
    pub fn config(msg: impl Into<String>) -> Self {
        Self::ConfigError(msg.into())
    }

    pub fn monitor(msg: impl Into<String>) -> Self {
        Self::MonitorError(msg.into())
    }

    pub fn internal(msg: impl Into<String>) -> Self {
        Self::InternalError(msg.into())
    }

    pub fn not_found(msg: impl Into<String>) -> Self {
        Self::NotFound(msg.into())
    }

    pub fn validation(msg: impl Into<String>) -> Self {
        Self::ValidationError(msg.into())
    }

    pub fn llm(msg: impl Into<String>) -> Self {
        Self::LlmError(msg.into())
    }
}
