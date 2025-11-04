//! System monitoring module for AI Runtime
//!
//! Provides real-time system metrics including CPU, memory, disk, and network usage.

use serde::{Deserialize, Serialize};
use sysinfo::{System, Networks, Disks};
use std::time::Duration;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SystemMetrics {
    pub cpu_usage: f32,
    pub memory_used_mb: u64,
    pub memory_total_mb: u64,
    pub memory_usage_percent: f32,
    pub disk_usage: Vec<DiskMetrics>,
    pub network_rx_bytes: u64,
    pub network_tx_bytes: u64,
    pub timestamp: chrono::DateTime<chrono::Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DiskMetrics {
    pub name: String,
    pub mount_point: String,
    pub total_space_gb: f64,
    pub available_space_gb: f64,
    pub usage_percent: f32,
}

pub struct SystemMonitor {
    system: System,
    networks: Networks,
    disks: Disks,
}

impl SystemMonitor {
    pub fn new() -> Self {
        Self {
            system: System::new_all(),
            networks: Networks::new_with_refreshed_list(),
            disks: Disks::new_with_refreshed_list(),
        }
    }

    pub fn capture_system_state(&mut self) -> SystemMetrics {
        // Refresh all system data
        self.system.refresh_all();
        self.networks.refresh();
        self.disks.refresh();

        // Calculate CPU usage (average across all cores)
        let cpu_usage = self.system.global_cpu_info().cpu_usage();

        // Memory metrics
        let memory_used = self.system.used_memory();
        let memory_total = self.system.total_memory();
        let memory_used_mb = memory_used / 1024 / 1024;
        let memory_total_mb = memory_total / 1024 / 1024;
        let memory_usage_percent = if memory_total > 0 {
            (memory_used as f64 / memory_total as f64 * 100.0) as f32
        } else {
            0.0
        };

        // Disk metrics
        let disk_usage: Vec<DiskMetrics> = self.disks
            .iter()
            .map(|disk| {
                let total_space = disk.total_space();
                let available_space = disk.available_space();
                let used_space = total_space.saturating_sub(available_space);

                DiskMetrics {
                    name: disk.name().to_string_lossy().to_string(),
                    mount_point: disk.mount_point().to_string_lossy().to_string(),
                    total_space_gb: total_space as f64 / 1024.0 / 1024.0 / 1024.0,
                    available_space_gb: available_space as f64 / 1024.0 / 1024.0 / 1024.0,
                    usage_percent: if total_space > 0 {
                        (used_space as f64 / total_space as f64 * 100.0) as f32
                    } else {
                        0.0
                    },
                }
            })
            .collect();

        // Network metrics (sum of all interfaces)
        let mut network_rx_bytes = 0u64;
        let mut network_tx_bytes = 0u64;

        for (_interface_name, data) in self.networks.iter() {
            network_rx_bytes += data.received();
            network_tx_bytes += data.transmitted();
        }

        SystemMetrics {
            cpu_usage,
            memory_used_mb,
            memory_total_mb,
            memory_usage_percent,
            disk_usage,
            network_rx_bytes,
            network_tx_bytes,
            timestamp: chrono::Utc::now(),
        }
    }

    /// Continuously monitor system and call callback with metrics
    pub async fn monitor_loop<F>(&mut self, interval: Duration, mut callback: F)
    where
        F: FnMut(SystemMetrics),
    {
        let mut interval_timer = tokio::time::interval(interval);

        loop {
            interval_timer.tick().await;
            let metrics = self.capture_system_state();
            callback(metrics);
        }
    }
}

impl Default for SystemMonitor {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_system_monitor_creation() {
        let monitor = SystemMonitor::new();
        assert!(monitor.system.cpus().len() > 0);
    }

    #[test]
    fn test_capture_system_state() {
        let mut monitor = SystemMonitor::new();
        let metrics = monitor.capture_system_state();

        assert!(metrics.cpu_usage >= 0.0);
        assert!(metrics.memory_total_mb > 0);
        assert!(metrics.memory_usage_percent >= 0.0 && metrics.memory_usage_percent <= 100.0);
    }
}
