import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import asyncio
import subprocess
import psutil

# Add the core module to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class AIDaemonGUI:
    """Tkinter GUI for AI System Daemon Dashboard"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("AI System Daemon Dashboard")
        self.root.geometry("1200x800")
        self.root.configure(bg='#2b2b2b')
        
        # Style configuration
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self._configure_styles()
        
        # State variables
        self.daemon_running = False
        self.update_thread = None
        self.stats_data = {}
        
        self.setup_gui()
        self.start_updates()
        
    def _configure_styles(self):
        """Configure modern dark theme styles"""
        self.style.configure('Title.TLabel', 
                           background='#2b2b2b', 
                           foreground='#ffffff',
                           font=('Arial', 16, 'bold'))
        
        self.style.configure('Card.TFrame',
                           background='#3c3c3c',
                           relief='raised',
                           borderwidth=1)
        
        self.style.configure('Card.TLabel',
                           background='#3c3c3c',
                           foreground='#ffffff',
                           font=('Arial', 10))
        
        self.style.configure('Metric.TLabel',
                           background='#3c3c3c',
                           foreground='#00ff00',
                           font=('Arial', 12, 'bold'))
        
        self.style.configure('Warning.TLabel',
                           background='#3c3c3c', 
                           foreground='#ff9900',
                           font=('Arial', 10, 'bold'))
        
        self.style.configure('Error.TLabel',
                           background='#3c3c3c',
                           foreground='#ff4444',
                           font=('Arial', 10, 'bold'))
        
        self.style.configure('Action.TButton',
                           background='#007acc',
                           foreground='#ffffff',
                           font=('Arial', 10, 'bold'))
    
    def setup_gui(self):
        """Setup the main GUI layout"""
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Header
        header_frame = ttk.Frame(main_frame, style='Card.TFrame')
        header_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(header_frame, text="🤖 AI System Daemon Dashboard", 
                 style='Title.TLabel').grid(row=0, column=0, padx=10, pady=10)
        
        # Status indicator
        self.status_label = ttk.Label(header_frame, text="● UNKNOWN", 
                                    style='Warning.TLabel')
        self.status_label.grid(row=0, column=1, padx=10, pady=10, sticky=tk.E)
        
        # Control buttons
        control_frame = ttk.Frame(header_frame)
        control_frame.grid(row=0, column=2, padx=10, pady=10, sticky=tk.E)
        
        ttk.Button(control_frame, text="Start Daemon", 
                  command=self.start_daemon, style='Action.TButton').grid(row=0, column=0, padx=5)
        ttk.Button(control_frame, text="Stop Daemon", 
                  command=self.stop_daemon, style='Action.TButton').grid(row=0, column=1, padx=5)
        ttk.Button(control_frame, text="Refresh", 
                  command=self.force_refresh, style='Action.TButton').grid(row=0, column=2, padx=5)
        
        # Left panel - Metrics
        metrics_frame = ttk.LabelFrame(main_frame, text="System Metrics", padding="10")
        metrics_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        
        self.setup_metrics_panel(metrics_frame)
        
        # Right panel - Logs and Controls
        logs_frame = ttk.LabelFrame(main_frame, text="Real-time Monitoring", padding="10")
        logs_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.setup_logs_panel(logs_frame)
        
        # Configure row weights for proper resizing
        main_frame.rowconfigure(1, weight=1)
        metrics_frame.columnconfigure(0, weight=1)
        logs_frame.columnconfigure(0, weight=1)
        logs_frame.rowconfigure(1, weight=1)
    
    def setup_metrics_panel(self, parent):
        """Setup the metrics display panel"""
        # System Health
        health_frame = ttk.Frame(parent, style='Card.TFrame')
        health_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(health_frame, text="System Health", style='Card.TLabel').grid(
            row=0, column=0, sticky=tk.W, padx=10, pady=5)
        
        self.health_status = ttk.Label(health_frame, text="Checking...", style='Metric.TLabel')
        self.health_status.grid(row=0, column=1, sticky=tk.E, padx=10, pady=5)
        
        # CPU Usage
        cpu_frame = ttk.Frame(parent, style='Card.TFrame')
        cpu_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(cpu_frame, text="CPU Usage", style='Card.TLabel').grid(
            row=0, column=0, sticky=tk.W, padx=10, pady=2)
        
        self.cpu_usage = ttk.Label(cpu_frame, text="0%", style='Metric.TLabel')
        self.cpu_usage.grid(row=0, column=1, sticky=tk.E, padx=10, pady=2)
        
        # Memory Usage
        memory_frame = ttk.Frame(parent, style='Card.TFrame')
        memory_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(memory_frame, text="Memory Usage", style='Card.TLabel').grid(
            row=0, column=0, sticky=tk.W, padx=10, pady=2)
        
        self.memory_usage = ttk.Label(memory_frame, text="0%", style='Metric.TLabel')
        self.memory_usage.grid(row=0, column=1, sticky=tk.E, padx=10, pady=2)
        
        # Active Projects
        projects_frame = ttk.Frame(parent, style='Card.TFrame')
        projects_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(projects_frame, text="Active Projects", style='Card.TLabel').grid(
            row=0, column=0, sticky=tk.W, padx=10, pady=2)
        
        self.projects_count = ttk.Label(projects_frame, text="0", style='Metric.TLabel')
        self.projects_count.grid(row=0, column=1, sticky=tk.E, padx=10, pady=2)
        
        # Security Events
        security_frame = ttk.Frame(parent, style='Card.TFrame')
        security_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(security_frame, text="Security Events", style='Card.TLabel').grid(
            row=0, column=0, sticky=tk.W, padx=10, pady=2)
        
        self.security_count = ttk.Label(security_frame, text="0", style='Metric.TLabel')
        self.security_count.grid(row=0, column=1, sticky=tk.E, padx=10, pady=2)
        
        # Performance Issues
        perf_frame = ttk.Frame(parent, style='Card.TFrame')
        perf_frame.grid(row=5, column=0, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(perf_frame, text="Performance Issues", style='Card.TLabel').grid(
            row=0, column=0, sticky=tk.W, padx=10, pady=2)
        
        self.perf_issues = ttk.Label(perf_frame, text="0", style='Metric.TLabel')
        self.perf_issues.grid(row=0, column=1, sticky=tk.E, padx=10, pady=2)
        
        # Auto-fixes Applied
        fixes_frame = ttk.Frame(parent, style='Card.TFrame')
        fixes_frame.grid(row=6, column=0, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(fixes_frame, text="Auto-fixes Applied", style='Card.TLabel').grid(
            row=0, column=0, sticky=tk.W, padx=10, pady=2)
        
        self.fixes_applied = ttk.Label(fixes_frame, text="0", style='Metric.TLabel')
        self.fixes_applied.grid(row=0, column=1, sticky=tk.E, padx=10, pady=2)
    
    def setup_logs_panel(self, parent):
        """Setup the logs and monitoring panel"""
        # Log level filter
        filter_frame = ttk.Frame(parent)
        filter_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        ttk.Label(filter_frame, text="Log Level:").grid(row=0, column=0, padx=(0, 5))
        self.log_level = ttk.Combobox(filter_frame, values=["ALL", "INFO", "WARNING", "ERROR"], width=10)
        self.log_level.set("INFO")
        self.log_level.grid(row=0, column=1, padx=5)
        self.log_level.bind('<<ComboboxSelected>>', self.on_log_level_change)
        
        ttk.Button(filter_frame, text="Clear Logs", 
                  command=self.clear_logs).grid(row=0, column=2, padx=5)
        
        # Log display
        self.log_text = scrolledtext.ScrolledText(parent, width=80, height=20, 
                                                bg='#1e1e1e', fg='#ffffff',
                                                insertbackground='white',
                                                font=('Consolas', 9))
        self.log_text.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        # Configure tag colors for different log levels
        self.log_text.tag_config('INFO', foreground='#00ff00')
        self.log_text.tag_config('WARNING', foreground='#ff9900')
        self.log_text.tag_config('ERROR', foreground='#ff4444')
        self.log_text.tag_config('CRITICAL', foreground='#ff0000', background='#440000')
    
    def start_updates(self):
        """Start the background update thread"""
        self.update_thread = threading.Thread(target=self.update_loop, daemon=True)
        self.update_thread.start()
    
    def update_loop(self):
        """Background update loop"""
        while True:
            try:
                self.update_stats()
                self.update_logs()
                threading.Event().wait(2)  # Update every 2 seconds
            except Exception as e:
                print(f"Update error: {e}")
    
    def update_stats(self):
        """Update all statistics displays"""
        try:
            # Check daemon status
            self.daemon_running = self.check_daemon_process()
            
            # Update status indicator
            status_text = "● RUNNING" if self.daemon_running else "● STOPPED"
            status_style = 'Metric.TLabel' if self.daemon_running else 'Error.TLabel'
            
            self.root.after(0, lambda: self.status_label.configure(
                text=status_text, style=status_style))
            
            # System metrics
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            
            # Read log statistics
            log_stats = self.get_log_statistics()
            security_stats = self.get_security_statistics()
            
            # Update all metrics in thread-safe way
            self.root.after(0, lambda: self.update_displayed_metrics(
                cpu_percent, memory.percent, log_stats, security_stats))
                
        except Exception as e:
            print(f"Stats update error: {e}")
    
    def update_displayed_metrics(self, cpu, memory, log_stats, security_stats):
        """Thread-safe update of displayed metrics"""
        self.cpu_usage.config(text=f"{cpu:.1f}%")
        self.memory_usage.config(text=f"{memory:.1f}%")
        self.projects_count.config(text=str(log_stats.get('projects', 0)))
        self.security_count.config(text=str(security_stats.get('total', 0)))
        self.perf_issues.config(text=str(log_stats.get('performance_issues', 0)))
        self.fixes_applied.config(text=str(log_stats.get('fixes_applied', 0)))
        
        # Update health status
        health_score = self.calculate_health_score(cpu, memory, security_stats)
        if health_score >= 80:
            self.health_status.config(text="EXCELLENT", style='Metric.TLabel')
        elif health_score >= 60:
            self.health_status.config(text="GOOD", style='Metric.TLabel') 
        elif health_score >= 40:
            self.health_status.config(text="FAIR", style='Warning.TLabel')
        else:
            self.health_status.config(text="POOR", style='Error.TLabel')
    
    def update_logs(self):
        """Update the log display"""
        try:
            recent_logs = self.get_recent_logs()
            if recent_logs:
                self.root.after(0, lambda: self.display_logs(recent_logs))
        except Exception as e:
            print(f"Log update error: {e}")
    
    def display_logs(self, logs):
        """Display logs in the text widget"""
        current_level = self.log_level.get()
        
        # Clear if too many lines
        if int(self.log_text.index('end-1c').split('.')[0]) > 1000:
            self.log_text.delete(1.0, tk.END)
        
        for log in logs[-20:]:
            log_level = log.get('log', {}).get('level', 'INFO')
            
            # Filter by log level
            if current_level != "ALL" and log_level != current_level:
                continue
            
            timestamp = log.get('@timestamp', '')
            message = log.get('message', '')
            
            log_line = f"[{timestamp}] [{log_level}] {message}\n"
            
            self.log_text.insert(tk.END, log_line, log_level)
        
        self.log_text.see(tk.END)
    
    def check_daemon_process(self):
        """Check if daemon process is running"""
        try:
            result = subprocess.run(['pgrep', '-f', 'python.*daemon'], 
                                  capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False
    
    def get_log_statistics(self):
        """Read and analyze log statistics"""
        stats = {
            'projects': 0,
            'performance_issues': 0,
            'fixes_applied': 0
        }
        
        try:
            log_file = Path("logs/structured_daemon.log")
            if log_file.exists():
                with open(log_file, 'r') as f:
                    for line in f.readlines()[-1000:]:
                        try:
                            log = json.loads(line.strip())
                            # Count projects
                            if 'project' in log.get('message', '').lower():
                                stats['projects'] += 1
                            # Count performance issues
                            if 'performance' in log.get('message', '').lower():
                                stats['performance_issues'] += 1
                            # Count fixes
                            if 'fix' in log.get('message', '').lower() and 'applied' in log.get('message', '').lower():
                                stats['fixes_applied'] += 1
                        except:
                            continue
        except:
            pass
        
        return stats
    
    def get_security_statistics(self):
        """Read security event statistics"""
        stats = {'total': 0}
        
        try:
            security_file = Path("logs/security_findings.jsonl")
            if security_file.exists():
                with open(security_file, 'r') as f:
                    stats['total'] = len(f.readlines())
        except:
            pass
        
        return stats
    
    def get_recent_logs(self):
        """Get recent structured logs"""
        logs = []
        try:
            log_file = Path("logs/structured_daemon.log")
            if log_file.exists():
                with open(log_file, 'r') as f:
                    for line in f.readlines()[-50:]:
                        try:
                            logs.append(json.loads(line.strip()))
                        except:
                            continue
        except:
            pass
        
        return logs
    
    def calculate_health_score(self, cpu, memory, security_stats):
        """Calculate overall system health score"""
        score = 100
        
        # Penalize high resource usage
        if cpu > 80:
            score -= 20
        elif cpu > 60:
            score -= 10
            
        if memory > 80:
            score -= 20
        elif memory > 60:
            score -= 10
            
        # Penalize security events
        score -= min(security_stats.get('total', 0) * 5, 30)
        
        return max(score, 0)
    
    def start_daemon(self):
        """Start the AI daemon"""
        try:
            subprocess.Popen(['./scripts/start.sh'], 
                           cwd=os.path.dirname(os.path.abspath(__file__)))
            messagebox.showinfo("Success", "AI Daemon started successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start daemon: {e}")
    
    def stop_daemon(self):
        """Stop the AI daemon"""
        try:
            subprocess.run(['pkill', '-f', 'python.*daemon'])
            messagebox.showinfo("Success", "AI Daemon stopped successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to stop daemon: {e}")
    
    def force_refresh(self):
        """Force refresh all data"""
        self.update_stats()
        self.update_logs()
    
    def clear_logs(self):
        """Clear the log display"""
        self.log_text.delete(1.0, tk.END)
    
    def on_log_level_change(self, event):
        """Handle log level filter change"""
        self.update_logs()

def main():
    """Main entry point for the GUI"""
    root = tk.Tk()
    app = AIDaemonGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
