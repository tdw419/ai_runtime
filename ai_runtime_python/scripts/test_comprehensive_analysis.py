import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.code_manager import CodeManager

async def test_comprehensive_analysis():
    """Test performance and security analysis"""
    code_manager = CodeManager(None)  # Test without LM Studio first
    
    project_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    print("Testing Performance Analysis...")
    performance = await code_manager.analyze_performance(project_path)
    print(f"Performance Score: {performance.get('overall_performance_score')}")
    print(f"Bottlenecks Found: {len(performance.get('bottlenecks', []))}")
    
    for bottleneck in performance.get('bottlenecks', [])[:2]:
        print(f"  - {bottleneck['description']}")
    
    print("\nTesting Security Analysis...")
    security = await code_manager.analyze_security(project_path)
    print(f"Security Score: {security.get('security_score')}")
    print(f"Critical Issues: {security.get('critical_issues')}")
    print(f"High Issues: {security.get('high_issues')}")
    
    for vuln in security.get('vulnerabilities', [])[:2]:
        print(f"  - {vuln['description']} ({vuln.get('severity')})")
    
    print("\n✓ Comprehensive analysis working!")

if __name__ == "__main__":
    asyncio.run(test_comprehensive_analysis())
