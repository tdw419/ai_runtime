//! Example demonstrating the SystemMonitor module
//!
//! Run with: cargo run --example monitor_demo

use ai_runtime::SystemMonitor;
use std::time::Duration;

#[tokio::main]
async fn main() {
    println!("🔍 GVPIE AI Runtime - System Monitor Demo\n");
    println!("==========================================\n");

    let mut monitor = SystemMonitor::new();

    // Capture a single snapshot
    println!("📊 Single Snapshot:");
    let metrics = monitor.capture_system_state();
    print_metrics(&metrics);

    println!("\n\n🔄 Continuous Monitoring (5 samples, 2s interval):");
    println!("Press Ctrl+C to stop\n");

    let mut count = 0;
    let max_samples = 5;

    monitor
        .monitor_loop(Duration::from_secs(2), move |metrics| {
            count += 1;
            println!("Sample #{}", count);
            print_metrics(&metrics);
            println!();

            if count >= max_samples {
                std::process::exit(0);
            }
        })
        .await;
}

fn print_metrics(metrics: &ai_runtime::SystemMetrics) {
    println!("  ⏰ Timestamp: {}", metrics.timestamp.format("%Y-%m-%d %H:%M:%S"));
    println!("  🖥️  CPU Usage: {:.2}%", metrics.cpu_usage);
    println!(
        "  💾 Memory: {} MB / {} MB ({:.2}%)",
        metrics.memory_used_mb, metrics.memory_total_mb, metrics.memory_usage_percent
    );

    if !metrics.disk_usage.is_empty() {
        println!("  💿 Disks:");
        for disk in &metrics.disk_usage {
            println!(
                "     {} - {:.2} GB / {:.2} GB ({:.1}%)",
                disk.mount_point,
                disk.total_space_gb - disk.available_space_gb,
                disk.total_space_gb,
                disk.usage_percent
            );
        }
    }

    println!(
        "  🌐 Network: ⬇️  {} MB | ⬆️  {} MB",
        metrics.network_rx_bytes / 1024 / 1024,
        metrics.network_tx_bytes / 1024 / 1024
    );
}
