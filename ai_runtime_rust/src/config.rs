use serde::{Deserialize, Serialize};
use std::path::Path;
use crate::errors::{AiRuntimeError, Result};

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct LmStudioConfig {
    pub base_url: String,
    pub model: String,
    pub temperature: f32,
    pub max_tokens: u32,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct LoggingConfig {
    pub structured_enabled: bool,
    pub retention_days: u32,
    pub max_file_size_mb: u32,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct Config {
    #[serde(default = "default_database_url")]
    pub database_url: String,
    #[serde(default = "default_http_port")]
    pub http_port: u16,
    pub gpu_device_id: Option<u32>,
    #[serde(default)]
    pub lm_studio: LmStudioConfig,
    #[serde(default)]
    pub logging: LoggingConfig,
}

fn default_database_url() -> String {
    "sqlite:gvpie.db".to_string()
}

fn default_http_port() -> u16 {
    8080
}

impl Default for LmStudioConfig {
    fn default() -> Self {
        Self {
            base_url: "http://localhost:1234/v1".to_string(),
            model: "local-model".to_string(),
            temperature: 0.1,
            max_tokens: 500,
        }
    }
}

impl Default for LoggingConfig {
    fn default() -> Self {
        Self {
            structured_enabled: true,
            retention_days: 7,
            max_file_size_mb: 100,
        }
    }
}

impl Default for Config {
    fn default() -> Self {
        Self {
            database_url: default_database_url(),
            http_port: default_http_port(),
            gpu_device_id: None,
            lm_studio: LmStudioConfig::default(),
            logging: LoggingConfig::default(),
        }
    }
}

impl Config {
    pub fn load() -> Result<Self> {
        let mut config = Config::default();

        let config_files = vec![
            "config/system.yaml",
            "config/services.yaml",
            "config.yaml", // Fallback for single config
        ];

        for path_str in config_files {
            let path = Path::new(path_str);
            if path.exists() {
                let config_file = std::fs::File::open(path).map_err(|e| AiRuntimeError::IoError(e))?;
                let loaded_config: serde_yaml::Value = serde_yaml::from_reader(config_file).map_err(|e| AiRuntimeError::YamlSerializationError(e))?;
                
                // Merge loaded_config into the current config
                // This is a simplified merge, a more robust solution might be needed for complex nested structures
                if let Ok(merged) = serde_yaml::from_value::<Config>(loaded_config) {
                    config.database_url = merged.database_url;
                    config.http_port = merged.http_port;
                    config.gpu_device_id = merged.gpu_device_id;
                    config.lm_studio = merged.lm_studio;
                    config.logging = merged.logging;
                }
            }
        }

        Ok(config)
    }
}