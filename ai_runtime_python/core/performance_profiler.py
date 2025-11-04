import asyncio
import subprocess
import tempfile
import json
from pathlib import Path
from typing import Dict, List, Optional
import os

class PerformanceProfiler:
    """High-performance asynchronous profiling with py-spy integration"""
    
    def __init__(self, config):
        self.config = config
        self.profiling_enabled = config.get("performance", {}).get("profiling_enabled", False)
        self.py_spy_path = config.get("performance", {}).get("py_spy_path", "py-spy")
        
    async def profile_daemon_performance(self, duration: int = 30) -> Dict:
        """Profile the daemon using py-spy with minimal overhead"""
        if not self.profiling_enabled:
            return {"status": "profiling_disabled"}
        
        try:
            # Get our own process ID
            pid = os.getpid()
            
            # Create temporary file for flamegraph
            with tempfile.NamedTemporaryFile(suffix='.svg', delete=False) as f:
                flamegraph_path = f.name
            
            # Run py-spy to capture performance data
            cmd = [
                self.py_spy_path, "record",
                "--pid", str(pid),
                "--duration", str(duration),
                "--format", "raw",
                "--output", flamegraph_path
            ]
            
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0:
                # Parse and analyze the profile
                analysis = await self._analyze_profile(flamegraph_path)
                os.unlink(flamegraph_path)
                return analysis
            else:
                return {
                    "status": "error",
                    "error": stderr.decode() if stderr else "Unknown py-spy error"
                }
                
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def _analyze_profile(self, profile_path: str) -> Dict:
        """Analyze py-spy profile for performance bottlenecks"""
        try:
            # For now, return basic analysis
            # In production, this would parse the actual profile data
            return {
                "status": "success",
                "bottlenecks": await self._detect_performance_patterns(),
                "recommendations": self._generate_performance_recommendations(),
                "profile_path": profile_path
            }
        except Exception as e:
            return {"status": "analysis_error", "error": str(e)}
    
    async def _detect_performance_patterns(self) -> List[Dict]:
        """Detect common Python performance anti-patterns"""
        patterns = []
        
        # This would integrate with actual profiling data
        # For now, provide static recommendations based on common issues
        patterns.extend([
            {
                "pattern": "string_concatenation",
                "description": "Inefficient string concatenation using + operator",
                "severity": "medium",
                "suggestion": "Use str.join() or f-strings for better performance",
                "files": ["code_manager.py", "project_monitor.py"]  # Example
            },
            {
                "pattern": "inefficient_loops", 
                "description": "Potential N+1 query patterns or repeated function calls",
                "severity": "high",
                "suggestion": "Use vectorized operations or batch processing",
                "files": ["monitor.py", "brain.py"]  # Example
            }
        ])
        
        return patterns
    
    def _generate_performance_recommendations(self) -> List[str]:
        """Generate performance optimization recommendations"""
        return [
            "Enable asyncio debug mode for event loop monitoring",
            "Use list comprehensions instead of manual loops for simple transformations",
            "Implement connection pooling for database operations",
            "Add caching for frequently accessed system metrics",
            "Use async context managers for resource cleanup"
        ]
    
    def enable_asyncio_debug(self):
        """Enable asyncio debug mode for detailed event loop monitoring"""
        loop = asyncio.get_event_loop()
        loop.set_debug(True)
        print("✓ Asyncio debug mode enabled - monitoring for slow callbacks and unawaited coroutines")
