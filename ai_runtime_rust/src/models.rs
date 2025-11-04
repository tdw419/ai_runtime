// gvpie/ai-runtime/src/models.rs
use serde::{Deserialize, Serialize};
use std::time::Duration;

#[derive(Debug, Serialize, Deserialize)]
pub struct ExecutionResult {
    pub success: bool,
    pub output_data: Vec<u8>,
    pub execution_time: Duration,
    pub program_hash: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct Cartridge {
    pub id: i64,
    pub name: String,
    pub program_hash: String,
    pub program_text: String,
    pub created_at: chrono::DateTime<chrono::Utc>,
    pub executed_count: i64,
}

pub fn hash_program(program: &str) -> String {
    use sha2::{Sha256, Digest};
    let mut hasher = Sha256::new();
    hasher.update(program.as_bytes());
    format!("{:x}", hasher.finalize())
}