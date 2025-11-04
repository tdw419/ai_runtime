//! Example demonstrating the ExperienceDB module
//!
//! Run with: cargo run --example database_demo

use ai_runtime::database::{ExperienceDB, SystemMetricsRecord, DecisionRecord, EventRecord};
use chrono::Utc;
use serde_json::json;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("💾 GVPIE AI Runtime - Database Demo\n");
    println!("===================================\n");

    // Create database
    let db_path = "/tmp/gvpie_demo.db";
    let db = ExperienceDB::new(db_path).await?;
    println!("✅ Database created at: {}\n", db_path);

    // Log system metrics
    println!("📊 Logging system metrics...");
    for i in 1..=5 {
        let metrics = SystemMetricsRecord {
            recorded_at: Utc::now(),
            cpu: Some(50.0 + i as f32),
            memory: Some(70.0 + i as f32 * 0.5),
            disk: Some(60.0),
            state_json: json!({
                "cpu_cores": 8,
                "hostname": "demo-host",
                "sample": i
            }),
        };
        db.log_metrics(&metrics).await?;
        println!("  Sample {}: CPU={:.1}%, Memory={:.1}%", i, metrics.cpu.unwrap(), metrics.memory.unwrap());
    }

    // Log AI decisions
    println!("\n🤖 Logging AI decisions...");
    let decisions = vec![
        ("optimize_code", 0.95),
        ("run_tests", 0.88),
        ("update_dependencies", 0.72),
    ];

    for (action, confidence) in decisions {
        let decision = DecisionRecord {
            decided_at: Utc::now(),
            action: Some(action.to_string()),
            confidence: Some(confidence),
            decision_json: json!({
                "action": action,
                "confidence": confidence,
                "reasoning": "Automated decision"
            }),
            state_json: json!({
                "system_load": "normal"
            }),
        };
        db.log_decision(&decision).await?;
        println!("  Decision: {} (confidence: {:.0}%)", action, confidence * 100.0);
    }

    // Log events
    println!("\n📝 Logging events...");
    let events = vec![
        ("startup", json!({"version": "0.1.0"})),
        ("health_check", json!({"status": "healthy"})),
    ];

    for (kind, payload) in events {
        let event = EventRecord {
            kind: kind.to_string(),
            payload_json: payload.clone(),
            created_at: Utc::now(),
        };
        db.record_event(&event).await?;
        println!("  Event: {} - {:?}", kind, payload);
    }

    // Analyze patterns
    println!("\n📈 Analyzing patterns...");
    let patterns = db.analyze_patterns(5).await?;
    println!("  CPU Average: {:.2}%", patterns.resource_trends.cpu_avg);
    println!("  Memory Average: {:.2}%", patterns.resource_trends.memory_avg);
    println!("  Disk Average: {:.2}%", patterns.resource_trends.disk_avg);

    // Get recent context
    println!("\n🔍 Recent decision context:");
    let context = db.get_recent_context(3).await?;
    for (i, decision) in context.iter().enumerate() {
        println!("  {}. {}", i + 1, decision);
    }

    println!("\n✅ Database demo complete!");
    println!("Database file: {}", db.path().display());

    Ok(())
}
