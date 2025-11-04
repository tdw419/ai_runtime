#!/usr/bin/env python3

import asyncio
import sys
import os
import tempfile
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def test_high_assurance_features():
    """Test all high-assurance features integration"""
    print("🧪 Testing High-Assurance Features Integration")
    print("=" * 60)
    
    tests = {}
    
    try:
        # Test security guardrails
        from core.security_guardrails import SecurityGuardrails
        
        guardrails = SecurityGuardrails({
            "security": {
                "blocked_commands": ["rm -rf", "format"]
            },
            "direct_actions": {
                "allowed_services": ["nginx", "redis"]
            }
        })
        
        # Test safe command validation
        safe_commands = ["systemctl restart nginx", "ls -la"]
        unsafe_commands = ["rm -rf /", "systemctl restart unknown"]
        
        for cmd in safe_commands:
            result = guardrails._is_command_safe(cmd)
            tests[f"safe_command_{cmd}"] = result
        
        for cmd in unsafe_commands:
            result = guardrails._is_command_safe(cmd)
            tests[f"unsafe_command_{cmd}"] = not result
        
        print("✓ Security guardrails functioning")
        
    except Exception as e:
        print(f"✗ Security guardrails test failed: {e}")
        tests["security_guardrails"] = False
    
    try:
        # Test structured logging
        from core.structured_logger import StructuredLogger, LogSeverity
        
        logger = StructuredLogger({})
        logger.log_system_operation(
            LogSeverity.INFO,
            "Integration test operation",
            operation="test",
            resource="integration",
            outcome="success"
        )
        tests["structured_logging"] = True
        print("✓ Structured logging functioning")
        
    except Exception as e:
        print(f"✗ Structured logging test failed: {e}")
        tests["structured_logging"] = False
    
    try:
        # Test vulnerability prioritization
        from core.vulnerability_prioritizer import VulnerabilityPrioritizer
        
        prioritizer = VulnerabilityPrioritizer({})
        test_vulns = [{
            "cve_id": "CVE-2021-44228",  # Log4Shell example
            "description": "Remote code execution vulnerability",
            "affected_files": ["pom.xml"]
        }]
        
        prioritized = await prioritizer.prioritize_vulnerabilities(test_vulns)
        tests["vulnerability_prioritization"] = len(prioritized) > 0
        print("✓ Vulnerability prioritization functioning")
        
    except Exception as e:
        print(f"✗ Vulnerability prioritization test failed: {e}")
        tests["vulnerability_prioritization"] = False
    
    # Summary
    print("\n" + "=" * 60)
    passed = sum(tests.values())
    total = len(tests)
    
    print(f"Integration Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 ALL HIGH-ASSURANCE FEATURES INTEGRATED SUCCESSFULLY!")
        return True
    else:
        print("⚠️  Some features need attention")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_high_assurance_features())
    sys.exit(0 if success else 1)
