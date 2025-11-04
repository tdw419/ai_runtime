//! Example demonstrating the Structured Logger module
//!
//! Run with: cargo run --example logging_demo

use ai_runtime::logging::{
    StructuredLogger, LogSeverity, PerformanceMetrics, SystemOperation,
};
use std::collections::HashMap;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("📝 GVPIE AI Runtime - Structured Logging Demo\n");
    println!("==============================================\n");

    // Initialize logger
    let log_dir = "/tmp/gvpie_logs";
    let logger = StructuredLogger::new(log_dir)?;
    println!("✅ Logger initialized at: {}\n", log_dir);

    // Log security events
    println!("🛡️ Logging security events...");
    logger.log_security_event(
        LogSeverity::Critical,
        "Suspicious command detected: rm -rf /".to_string(),
        "SEC-2024-001".to_string(),
        9.2,
        Some({
            let mut context = HashMap::new();
            context.insert("command".to_string(), serde_json::json!("rm -rf /"));
            context.insert("user".to_string(), serde_json::json!("suspicious_user"));
            context
        }),
    )?;
    println!("  ✓ Critical security event logged (Risk: 9.2/10)");

    logger.log_security_event(
        LogSeverity::Warning,
        "Failed authentication attempt".to_string(),
        "SEC-2024-002".to_string(),
        4.5,
        None,
    )?;
    println!("  ✓ Warning security event logged (Risk: 4.5/10)\n");

    // Log performance events
    println!("📊 Logging performance metrics...");
    let perf_metrics = PerformanceMetrics {
        duration_ms: 250,
        cpu_percent: Some(65.3),
        memory_mb: Some(1024),
        custom: {
            let mut custom = HashMap::new();
            custom.insert("operation".to_string(), serde_json::json!("llm_query"));
            custom.insert("tokens".to_string(), serde_json::json!(150));
            custom
        },
    };
    logger.log_performance_event(
        LogSeverity::Info,
        "LLM query completed".to_string(),
        perf_metrics,
    )?;
    println!("  ✓ Performance event logged (250ms, 65.3% CPU)\n");

    // Log system operations
    println!("⚙️ Logging system operations...");
    let operation = SystemOperation {
        operation: "code_analysis".to_string(),
        resource: "/home/user/project".to_string(),
        outcome: "success".to_string(),
        user: Some("ai_daemon".to_string()),
    };
    logger.log_system_operation(
        LogSeverity::Notice,
        "Code analysis completed successfully".to_string(),
        operation,
    )?;
    println!("  ✓ System operation logged (success)\n");

    // Demonstrate severity mapping
    println!("🎯 Incident severity mapping:");
    let severities = vec![
        LogSeverity::Emergency,
        LogSeverity::Critical,
        LogSeverity::Error,
        LogSeverity::Warning,
        LogSeverity::Info,
    ];

    for severity in severities {
        let incident_sev = logger.get_incident_severity(severity);
        println!(
            "  {} → {} ({:?})",
            severity.as_str(),
            incident_sev.as_str(),
            incident_sev
        );
    }

    // Show log files created
    println!("\n📁 Log files created:");
    let log_files = vec![
        "structured_daemon.log",
        "security_findings.jsonl",
        "performance.log",
        "audit.log",
    ];

    for file in log_files {
        let path = std::path::Path::new(log_dir).join(file);
        if path.exists() {
            let size = std::fs::metadata(&path)?.len();
            println!("  ✓ {} ({} bytes)", file, size);
        }
    }

    println!("\n✅ Logging demo complete!");
    println!("📂 Check logs at: {}", log_dir);
    println!("\nECS and ASFF compliant logs are ready for ingestion by:");
    println!("  - Elasticsearch/Kibana (ECS format)");
    println!("  - AWS Security Hub (ASFF format)");
    println!("  - SIEM systems (structured JSON)");

    Ok(())
}
