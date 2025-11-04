#!/usr/bin/env python3

import asyncio
import sys
import os
import json
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def comprehensive_health_check():
    """Comprehensive health check for high-assurance AI daemon"""
    print("🔍 Comprehensive AI Daemon Health Check")
    print("=" * 50)
    
    checks = {
        "configuration": False,
        "dependencies": False,
        "logging": False,
        "security": False,
        "performance": False
    }
    
    # Check configuration
    try:
        from core.daemon import AIDaemon
        daemon = AIDaemon()
        checks["configuration"] = True
        print("✓ Configuration loaded successfully")
    except Exception as e:
        print(f"✗ Configuration error: {e}")
    
    # Check dependencies
    try:
        import aiohttp, yaml, psutil, aiosqlite
        checks["dependencies"] = True
        print("✓ Core dependencies available")
    except ImportError as e:
        print(f"✗ Missing dependency: {e}")
    
    # Check logging infrastructure
    try:
        log_dir = Path("logs")
        if log_dir.exists():
            checks["logging"] = True
            print("✓ Log directory exists")
        else:
            print("⚠️  Log directory missing - creating...")
            log_dir.mkdir(exist_ok=True)
            checks["logging"] = True
    except Exception as e:
        print(f"✗ Log setup error: {e}")
    
    # Check security configuration
    try:
        with open("config/system.yaml", "r") as f:
            import yaml
            config = yaml.safe_load(f)
            
        security_config = config.get("security", {})
        if security_config.get("blocked_commands"):
            checks["security"] = True
            print("✓ Security guardrails configured")
        else:
            print("⚠️  Security guardrails not fully configured")
    except Exception as e:
        print(f"✗ Security config error: {e}")
    
    # Check performance tools
    try:
        import subprocess
        result = subprocess.run(["which", "py-spy"], capture_output=True, text=True)
        if result.returncode == 0:
            checks["performance"] = True
            print("✓ Performance profiler (py-spy) available")
        else:
            print("⚠️  py-spy not installed - performance profiling limited")
    except Exception as e:
        print(f"✗ Performance tools check error: {e}")
    
    # Overall health assessment
    print("\n" + "=" * 50)
    passed_checks = sum(checks.values())
    total_checks = len(checks)
    
    if passed_checks == total_checks:
        print("🎉 ALL CHECKS PASSED - System is healthy!")
        return True
    elif passed_checks >= total_checks * 0.8:
        print(f"⚠️  {passed_checks}/{total_checks} checks passed - System operational with warnings")
        return True
    else:
        print(f"❌ {passed_checks}/{total_checks} checks passed - System needs attention")
        return False

async def check_daemon_process():
    """Check if daemon process is running"""
    print("\n🔎 Checking daemon process...")
    
    try:
        import subprocess
        result = subprocess.run(["pgrep", "-f", "python.*daemon"], capture_output=True, text=True)
        
        if result.returncode == 0:
            pids = result.stdout.strip().split('\n')
            print(f"✓ Daemon running with PIDs: {', '.join(pids)}")
            return True
        else:
            print("✗ Daemon process not found")
            return False
    except Exception as e:
        print(f"✗ Process check error: {e}")
        return False

async def check_recent_logs():
    """Check recent log activity"""
    print("\n📋 Checking recent logs...")
    
    log_files = [
        "logs/daemon.log",
        "logs/structured_daemon.log", 
        "logs/security_findings.jsonl"
    ]
    
    for log_file in log_files:
        path = Path(log_file)
        if path.exists():
            # Get last modified time
            mtime = path.stat().st_mtime
            from datetime import datetime
            age = datetime.now().timestamp() - mtime
            
            if age < 3600:  # Less than 1 hour
                print(f"✓ {log_file}: active (updated {int(age/60)} minutes ago)")
            else:
                print(f"⚠️  {log_file}: stale (updated {int(age/3600)} hours ago)")
        else:
            print(f"⚠️  {log_file}: not found")

if __name__ == "__main__":
    print("High-Assurance AI Daemon Health Check")
    print("=" * 50)
    
    async def main():
        health_ok = await comprehensive_health_check()
        process_ok = await check_daemon_process()
        await check_recent_logs()
        
        print("\n" + "=" * 50)
        if health_ok and process_ok:
            print("🎉 SYSTEM STATUS: HEALTHY")
            sys.exit(0)
        else:
            print("❌ SYSTEM STATUS: NEEDS ATTENTION")
            sys.exit(1)
    
    asyncio.run(main())
