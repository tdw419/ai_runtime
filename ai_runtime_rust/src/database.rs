// gvpie/ai-runtime/src/database.rs
//! Experience Database module for AI Runtime
//!
//! Provides an asynchronous SQLite persistence layer for system metrics, decisions, and events.
//! Based on Python's ai_runtime/core/memory.py

use rusqlite::{Connection, params};
use tokio::sync::Mutex;
use std::path::{Path, PathBuf};
use chrono::{DateTime, Utc, Duration};
use serde::{Deserialize, Serialize};
use serde_json::Value as JsonValue;
use crate::errors::{AiRuntimeError, Result};

/// System metrics record for database storage
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SystemMetricsRecord {
    pub recorded_at: DateTime<Utc>,
    pub cpu: Option<f32>,
    pub memory: Option<f32>,
    pub disk: Option<f32>,
    pub state_json: JsonValue,
}

/// AI decision record for database storage
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DecisionRecord {
    pub decided_at: DateTime<Utc>,
    pub action: Option<String>,
    pub confidence: Option<f32>,
    pub decision_json: JsonValue,
    pub state_json: JsonValue,
}

/// System event record for database storage
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EventRecord {
    pub kind: String,
    pub payload_json: JsonValue,
    pub created_at: DateTime<Utc>,
}

/// Pattern analysis result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PatternAnalysis {
    pub resource_trends: ResourceTrends,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResourceTrends {
    pub cpu_avg: f32,
    pub memory_avg: f32,
    pub disk_avg: f32,
}

/// Trend analysis result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TrendAnalysis {
    pub metric: String,
    pub current: f32,
    pub trend_percent: Option<f32>,
    pub direction: String,
    pub samples: usize,
}

/// Asynchronous interface around a SQLite datastore
pub struct ExperienceDB {
    connection: Mutex<Connection>,
    db_path: PathBuf,
}

impl ExperienceDB {
    /// Create a new database connection and initialize schema
    pub async fn new(db_path: impl AsRef<Path>) -> Result<Self> {
        let db_path = db_path.as_ref().to_path_buf();

        // Create parent directory if it doesn't exist
        if let Some(parent) = db_path.parent() {
            tokio::fs::create_dir_all(parent).await?;
        }

        let conn = Connection::open(&db_path)?;

        // Initialize database with WAL mode and foreign keys
        conn.execute_batch(
            "PRAGMA journal_mode = WAL;
             PRAGMA foreign_keys = ON;

             CREATE TABLE IF NOT EXISTS metrics (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 recorded_at TEXT NOT NULL,
                 cpu REAL,
                 memory REAL,
                 disk REAL,
                 state_json TEXT NOT NULL
             );

             CREATE TABLE IF NOT EXISTS decisions (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 decided_at TEXT NOT NULL,
                 action TEXT,
                 confidence REAL,
                 decision_json TEXT NOT NULL,
                 state_json TEXT NOT NULL
             );

             CREATE TABLE IF NOT EXISTS events (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 kind TEXT NOT NULL,
                 payload_json TEXT NOT NULL,
                 created_at TEXT NOT NULL
             );"
        )?;

        Ok(Self {
            connection: Mutex::new(conn),
            db_path,
        })
    }

    /// Log system metrics to the database
    pub async fn log_metrics(&self, metrics: &SystemMetricsRecord) -> Result<()> {
        let conn = self.connection.lock().await;
        let state_json = serde_json::to_string(&metrics.state_json)?;

        conn.execute(
            "INSERT INTO metrics (recorded_at, cpu, memory, disk, state_json)
             VALUES (?1, ?2, ?3, ?4, ?5)",
            params![
                metrics.recorded_at.to_rfc3339(),
                metrics.cpu,
                metrics.memory,
                metrics.disk,
                state_json
            ],
        )?;
        Ok(())
    }

    /// Log an AI decision to the database
    pub async fn log_decision(&self, decision: &DecisionRecord) -> Result<()> {
        let conn = self.connection.lock().await;
        let decision_json = serde_json::to_string(&decision.decision_json)?;
        let state_json = serde_json::to_string(&decision.state_json)?;

        conn.execute(
            "INSERT INTO decisions (decided_at, action, confidence, decision_json, state_json)
             VALUES (?1, ?2, ?3, ?4, ?5)",
            params![
                decision.decided_at.to_rfc3339(),
                decision.action,
                decision.confidence,
                decision_json,
                state_json
            ],
        )?;
        Ok(())
    }

    /// Get recent decision context for AI prompting
    pub async fn get_recent_context(&self, limit: usize) -> Result<Vec<JsonValue>> {
        let conn = self.connection.lock().await;
        let mut stmt = conn.prepare(
            "SELECT decision_json FROM decisions ORDER BY id DESC LIMIT ?1"
        )?;

        let decisions = stmt.query_map(params![limit], |row| {
            let json_str: String = row.get(0)?;
            Ok(json_str)
        })?
        .collect::<std::result::Result<Vec<String>, _>>()?;

        let mut result = Vec::new();
        for json_str in decisions {
            result.push(serde_json::from_str(&json_str)?);
        }
        Ok(result)
    }

    /// Analyze patterns in system metrics
    pub async fn analyze_patterns(&self, window: usize) -> Result<PatternAnalysis> {
        let conn = self.connection.lock().await;
        let mut stmt = conn.prepare(
            "SELECT cpu, memory, disk FROM metrics ORDER BY id DESC LIMIT ?1"
        )?;

        let rows: Vec<(Option<f32>, Option<f32>, Option<f32>)> = stmt
            .query_map(params![window], |row| {
                Ok((row.get(0)?, row.get(1)?, row.get(2)?))
            })?
            .collect::<std::result::Result<Vec<_>, _>>()?;

        if rows.is_empty() {
            return Ok(PatternAnalysis {
                resource_trends: ResourceTrends {
                    cpu_avg: 0.0,
                    memory_avg: 0.0,
                    disk_avg: 0.0,
                },
            });
        }

        let cpu_sum: f32 = rows.iter().map(|(cpu, _, _)| cpu.unwrap_or(0.0)).sum();
        let mem_sum: f32 = rows.iter().map(|(_, mem, _)| mem.unwrap_or(0.0)).sum();
        let disk_sum: f32 = rows.iter().map(|(_, _, disk)| disk.unwrap_or(0.0)).sum();
        let count = rows.len() as f32;

        Ok(PatternAnalysis {
            resource_trends: ResourceTrends {
                cpu_avg: cpu_sum / count,
                memory_avg: mem_sum / count,
                disk_avg: disk_sum / count,
            },
        })
    }

    /// Analyze trends for a specific metric over time
    pub async fn analyze_trends(&self, key: &str, window_hours: i64) -> Result<TrendAnalysis> {
        let conn = self.connection.lock().await;
        let mut stmt = conn.prepare(
            "SELECT recorded_at, state_json FROM metrics ORDER BY id DESC"
        )?;

        let cutoff = Utc::now() - Duration::hours(window_hours);
        let mut series: Vec<(DateTime<Utc>, f32)> = Vec::new();

        let rows = stmt.query_map([], |row| {
            let recorded_at: String = row.get(0)?;
            let state_json: String = row.get(1)?;
            Ok((recorded_at, state_json))
        })?;

        for row_result in rows {
            let (recorded_at_str, state_json_str) = row_result?;

            let timestamp = DateTime::parse_from_rfc3339(&recorded_at_str)
                .map(|dt| dt.with_timezone(&Utc))
                .unwrap_or_else(|_| Utc::now());

            if timestamp < cutoff {
                break;
            }

            let state: JsonValue = serde_json::from_str(&state_json_str)?;
            if let Some(value) = Self::extract_metric(&state, key) {
                series.push((timestamp, value));
            }
        }

        if series.len() < 2 {
            return Err(AiRuntimeError::internal("Not enough data for trend analysis"));
        }

        series.sort_by_key(|(timestamp, _)| *timestamp);
        let first_value = series.first().unwrap().1;
        let last_value = series.last().unwrap().1;

        let trend_percent = if first_value != 0.0 {
            Some(((last_value - first_value) / first_value) * 100.0)
        } else {
            None
        };

        let direction = match trend_percent {
            Some(pct) if pct > 0.0 => "up",
            Some(pct) if pct < 0.0 => "down",
            _ => "flat",
        };

        Ok(TrendAnalysis {
            metric: key.to_string(),
            current: last_value,
            trend_percent,
            direction: direction.to_string(),
            samples: series.len(),
        })
    }

    /// Record a system event
    pub async fn record_event(&self, event: &EventRecord) -> Result<()> {
        let conn = self.connection.lock().await;
        let payload_json = serde_json::to_string(&event.payload_json)?;

        conn.execute(
            "INSERT INTO events (kind, payload_json, created_at) VALUES (?1, ?2, ?3)",
            params![event.kind, payload_json, event.created_at.to_rfc3339()],
        )?;
        Ok(())
    }

    /// Extract a metric value from nested JSON using dot notation
    fn extract_metric(state: &JsonValue, key: &str) -> Option<f32> {
        let parts: Vec<&str> = key.split('.').collect();
        let mut current = state;

        for part in parts {
            current = current.get(part)?;
        }

        match current {
            JsonValue::Number(n) => n.as_f64().map(|f| f as f32),
            _ => None,
        }
    }

    /// Get database path
    pub fn path(&self) -> &Path {
        &self.db_path
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    #[tokio::test]
    async fn test_database_creation() {
        let dir = tempdir().unwrap();
        let db_path = dir.path().join("test.db");
        let db = ExperienceDB::new(&db_path).await.unwrap();
        assert!(db_path.exists());
    }

    #[tokio::test]
    async fn test_log_metrics() {
        let dir = tempdir().unwrap();
        let db = ExperienceDB::new(dir.path().join("test.db")).await.unwrap();

        let metrics = SystemMetricsRecord {
            recorded_at: Utc::now(),
            cpu: Some(50.0),
            memory: Some(75.0),
            disk: Some(60.0),
            state_json: serde_json::json!({"test": "data"}),
        };

        db.log_metrics(&metrics).await.unwrap();
    }

    #[tokio::test]
    async fn test_analyze_patterns() {
        let dir = tempdir().unwrap();
        let db = ExperienceDB::new(dir.path().join("test.db")).await.unwrap();

        // Log some metrics
        for i in 0..10 {
            let metrics = SystemMetricsRecord {
                recorded_at: Utc::now(),
                cpu: Some(50.0 + i as f32),
                memory: Some(75.0),
                disk: Some(60.0),
                state_json: serde_json::json!({}),
            };
            db.log_metrics(&metrics).await.unwrap();
        }

        let patterns = db.analyze_patterns(10).await.unwrap();
        assert!(patterns.resource_trends.cpu_avg > 0.0);
    }
}
