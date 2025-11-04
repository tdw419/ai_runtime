//! Structured logging implementation with ECS and ASFF compliance
//!
//! Based on Python's ai_runtime/core/structured_logger.py

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value as JsonValue};
use std::collections::HashMap;
use std::fs::OpenOptions;
use std::io::Write;
use std::path::{Path, PathBuf};
use crate::errors::Result;

/// Log severity levels (syslog compatible, 0-7)
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "UPPERCASE")]
pub enum LogSeverity {
    Emergency = 0,  // System is unusable
    Alert = 1,      // Action must be taken immediately
    Critical = 2,   // Critical conditions
    Error = 3,      // Error conditions
    Warning = 4,    // Warning conditions
    Notice = 5,     // Normal but significant condition
    Info = 6,       // Informational messages
    Debug = 7,      // Debug-level messages
}

impl LogSeverity {
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::Emergency => "emergency",
            Self::Alert => "alert",
            Self::Critical => "critical",
            Self::Error => "error",
            Self::Warning => "warning",
            Self::Notice => "notice",
            Self::Info => "info",
            Self::Debug => "debug",
        }
    }
}

/// Incident severity tiers for incident response
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum IncidentSeverity {
    #[serde(rename = "critical")]
    Sev1,  // Critical - immediate response
    #[serde(rename = "high")]
    Sev2,  // High - urgent response
    #[serde(rename = "medium")]
    Sev3,  // Medium - planned response
    #[serde(rename = "low")]
    Sev4,  // Low - routine handling
    #[serde(rename = "info")]
    Sev5,  // Informational - no action needed
}

impl IncidentSeverity {
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::Sev1 => "critical",
            Self::Sev2 => "high",
            Self::Sev3 => "medium",
            Self::Sev4 => "low",
            Self::Sev5 => "info",
        }
    }
}

/// Elastic Common Schema (ECS) base event
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EcsEvent {
    #[serde(rename = "@timestamp")]
    pub timestamp: DateTime<Utc>,
    pub log: LogInfo,
    pub message: String,
    pub service: ServiceInfo,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub event: Option<EventInfo>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub process: Option<ProcessInfo>,
    #[serde(flatten)]
    pub extra: HashMap<String, JsonValue>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LogInfo {
    pub level: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ServiceInfo {
    pub name: String,
    pub version: String,
    #[serde(rename = "type")]
    pub service_type: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EventInfo {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub category: Option<Vec<String>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub r#type: Option<Vec<String>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub action: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub outcome: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub dataset: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProcessInfo {
    pub pid: u32,
}

/// AWS Security Finding Format (ASFF) compatible security event
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SecurityFinding {
    #[serde(rename = "SchemaVersion")]
    pub schema_version: String,
    #[serde(rename = "Id")]
    pub id: String,
    #[serde(rename = "ProductArn")]
    pub product_arn: String,
    #[serde(rename = "GeneratorId")]
    pub generator_id: String,
    #[serde(rename = "AwsAccountId")]
    pub aws_account_id: String,
    #[serde(rename = "Types")]
    pub types: Vec<String>,
    #[serde(rename = "CreatedAt")]
    pub created_at: DateTime<Utc>,
    #[serde(rename = "UpdatedAt")]
    pub updated_at: DateTime<Utc>,
    #[serde(rename = "Severity")]
    pub severity: SeverityInfo,
    #[serde(rename = "Title")]
    pub title: String,
    #[serde(rename = "Description")]
    pub description: String,
    #[serde(rename = "Resources")]
    pub resources: Vec<ResourceInfo>,
    #[serde(rename = "Workflow")]
    pub workflow: WorkflowInfo,
    #[serde(rename = "RecordState")]
    pub record_state: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SeverityInfo {
    #[serde(rename = "Label")]
    pub label: String,
    #[serde(rename = "Original")]
    pub original: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResourceInfo {
    #[serde(rename = "Type")]
    pub resource_type: String,
    #[serde(rename = "Id")]
    pub id: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkflowInfo {
    #[serde(rename = "Status")]
    pub status: String,
}

/// Performance metrics for structured logging
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PerformanceMetrics {
    pub duration_ms: u64,
    pub cpu_percent: Option<f32>,
    pub memory_mb: Option<u64>,
    #[serde(flatten)]
    pub custom: HashMap<String, JsonValue>,
}

/// System operation for audit trail
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SystemOperation {
    pub operation: String,
    pub resource: String,
    pub outcome: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub user: Option<String>,
}

/// High-assurance structured logger with ECS/ASFF compliance
pub struct StructuredLogger {
    log_dir: PathBuf,
    service_name: String,
    service_version: String,
}

impl StructuredLogger {
    pub fn new(log_dir: impl AsRef<Path>) -> Result<Self> {
        let log_dir = log_dir.as_ref().to_path_buf();
        std::fs::create_dir_all(&log_dir)?;

        Ok(Self {
            log_dir,
            service_name: "ai_runtime".to_string(),
            service_version: "0.1.0".to_string(),
        })
    }

    /// Map log severity to incident severity tier
    pub fn get_incident_severity(&self, severity: LogSeverity) -> IncidentSeverity {
        match severity {
            LogSeverity::Emergency | LogSeverity::Alert => IncidentSeverity::Sev1,
            LogSeverity::Critical => IncidentSeverity::Sev2,
            LogSeverity::Error => IncidentSeverity::Sev3,
            LogSeverity::Warning => IncidentSeverity::Sev4,
            _ => IncidentSeverity::Sev5,
        }
    }

    /// Log a security event with ASFF compliance
    pub fn log_security_event(
        &self,
        severity: LogSeverity,
        message: String,
        finding_id: String,
        risk_score: f32,
        context: Option<HashMap<String, JsonValue>>,
    ) -> Result<()> {
        let now = Utc::now();
        let incident_sev = self.get_incident_severity(severity);

        // Create ECS event
        let mut ecs_event = self.create_base_event(severity, message.clone(), now);
        if let Some(ctx) = &context {
            ecs_event.extra.extend(ctx.clone());
        }

        // Create ASFF finding
        let asff_finding = SecurityFinding {
            schema_version: "2018-10-08".to_string(),
            id: finding_id.clone(),
            product_arn: format!(
                "arn:aws:securityhub:us-east-1:123456789012:product/gvpie/ai-runtime"
            ),
            generator_id: "ai-runtime-security-scanner".to_string(),
            aws_account_id: "123456789012".to_string(),
            types: vec!["Software and Configuration Checks/Security Best Practices".to_string()],
            created_at: now,
            updated_at: now,
            severity: SeverityInfo {
                label: incident_sev.as_str().to_uppercase(),
                original: risk_score.to_string(),
            },
            title: message.clone(),
            description: message,
            resources: vec![ResourceInfo {
                resource_type: "Process".to_string(),
                id: "ai-runtime".to_string(),
            }],
            workflow: WorkflowInfo {
                status: "NEW".to_string(),
            },
            record_state: "ACTIVE".to_string(),
        };

        // Write ECS log
        self.write_log("structured_daemon.log", &ecs_event)?;

        // Write ASFF security finding
        self.write_security_finding(&asff_finding)?;

        // Also write to console via tracing
        match severity {
            LogSeverity::Emergency | LogSeverity::Alert | LogSeverity::Critical => {
                tracing::error!(target: "security", "{}", serde_json::to_string(&ecs_event)?);
            }
            LogSeverity::Error => {
                tracing::error!("{}", serde_json::to_string(&ecs_event)?);
            }
            LogSeverity::Warning => {
                tracing::warn!("{}", serde_json::to_string(&ecs_event)?);
            }
            _ => {
                tracing::info!("{}", serde_json::to_string(&ecs_event)?);
            }
        }

        Ok(())
    }

    /// Log a performance event with structured metrics
    pub fn log_performance_event(
        &self,
        severity: LogSeverity,
        message: String,
        metrics: PerformanceMetrics,
    ) -> Result<()> {
        let now = Utc::now();
        let mut event = self.create_base_event(severity, message, now);

        event.event = Some(EventInfo {
            category: Some(vec!["performance".to_string()]),
            r#type: Some(vec!["metrics".to_string()]),
            action: None,
            outcome: None,
            dataset: Some("ai_runtime.performance".to_string()),
        });

        event.extra.insert("metrics".to_string(), serde_json::to_value(&metrics)?);

        self.write_log("performance.log", &event)?;

        Ok(())
    }

    /// Log a system operation for audit trail
    pub fn log_system_operation(
        &self,
        severity: LogSeverity,
        message: String,
        operation: SystemOperation,
    ) -> Result<()> {
        let now = Utc::now();
        let mut event = self.create_base_event(severity, message, now);

        event.event = Some(EventInfo {
            category: Some(vec!["system".to_string()]),
            r#type: Some(vec!["operation".to_string()]),
            action: Some(operation.operation.clone()),
            outcome: Some(operation.outcome.clone()),
            dataset: None,
        });

        event.extra.insert("resource".to_string(), json!({"name": operation.resource}));
        if let Some(user) = &operation.user {
            event.extra.insert("user".to_string(), json!({"name": user}));
        }

        self.write_log("audit.log", &event)?;

        Ok(())
    }

    /// Create base ECS event
    fn create_base_event(
        &self,
        severity: LogSeverity,
        message: String,
        timestamp: DateTime<Utc>,
    ) -> EcsEvent {
        EcsEvent {
            timestamp,
            log: LogInfo {
                level: severity.as_str().to_string(),
            },
            message,
            service: ServiceInfo {
                name: self.service_name.clone(),
                version: self.service_version.clone(),
                service_type: "ai_runtime".to_string(),
            },
            event: None,
            process: Some(ProcessInfo {
                pid: std::process::id(),
            }),
            extra: HashMap::new(),
        }
    }

    /// Write log entry to file
    fn write_log(&self, filename: &str, event: &EcsEvent) -> Result<()> {
        let log_path = self.log_dir.join(filename);
        let mut file = OpenOptions::new()
            .create(true)
            .append(true)
            .open(log_path)?;

        let json_line = serde_json::to_string(event)?;
        writeln!(file, "{}", json_line)?;

        Ok(())
    }

    /// Write security finding to dedicated security log
    fn write_security_finding(&self, finding: &SecurityFinding) -> Result<()> {
        let security_path = self.log_dir.join("security_findings.jsonl");
        let mut file = OpenOptions::new()
            .create(true)
            .append(true)
            .open(security_path)?;

        let json_line = serde_json::to_string(finding)?;
        writeln!(file, "{}", json_line)?;

        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    #[test]
    fn test_logger_creation() {
        let dir = tempdir().unwrap();
        let logger = StructuredLogger::new(dir.path()).unwrap();
        assert_eq!(logger.service_name, "ai_runtime");
    }

    #[test]
    fn test_severity_mapping() {
        let dir = tempdir().unwrap();
        let logger = StructuredLogger::new(dir.path()).unwrap();

        assert_eq!(
            logger.get_incident_severity(LogSeverity::Emergency),
            IncidentSeverity::Sev1
        );
        assert_eq!(
            logger.get_incident_severity(LogSeverity::Error),
            IncidentSeverity::Sev3
        );
        assert_eq!(
            logger.get_incident_severity(LogSeverity::Info),
            IncidentSeverity::Sev5
        );
    }

    #[test]
    fn test_security_logging() {
        let dir = tempdir().unwrap();
        let logger = StructuredLogger::new(dir.path()).unwrap();

        logger
            .log_security_event(
                LogSeverity::Critical,
                "Test security event".to_string(),
                "SEC-001".to_string(),
                8.5,
                None,
            )
            .unwrap();

        let security_log = dir.path().join("security_findings.jsonl");
        assert!(security_log.exists());
    }

    #[test]
    fn test_performance_logging() {
        let dir = tempdir().unwrap();
        let logger = StructuredLogger::new(dir.path()).unwrap();

        let metrics = PerformanceMetrics {
            duration_ms: 150,
            cpu_percent: Some(45.2),
            memory_mb: Some(512),
            custom: HashMap::new(),
        };

        logger
            .log_performance_event(
                LogSeverity::Info,
                "Test performance event".to_string(),
                metrics,
            )
            .unwrap();

        let perf_log = dir.path().join("performance.log");
        assert!(perf_log.exists());
    }
}
