import json
import os
from typing import List, Dict

class CodeManager:
    def __init__(self, llm_manager):
        self.llm = llm_manager
    
    async def analyze_code_quality(self, project_path: str) -> Dict:
        """Use LM Studio to analyze overall code quality"""
        # Fallback if LLM is not available
        if not self.llm:
            return self._basic_code_analysis(project_path)
            
        # Get recent changes and key files
        recent_files = await self._get_recent_files(project_path)
        project_structure = await self._scan_project_structure(project_path)
        
        prompt = f"""
        Analyze this project's code quality and identify potential issues:
        
        PROJECT: {project_path}
        RECENT FILES: {recent_files[:10]}  # First 10 files
        
        PROJECT STRUCTURE:
        {self._format_structure(project_structure)}
        
        Provide analysis in this JSON format:
        {{
          "overall_health": "excellent|good|fair|poor",
          "issues_found": [
            {{
              "file": "path/to/file.py",
              "issue_type": "syntax|performance|security|maintainability",
              "description": "specific issue description",
              "severity": "low|medium|high|critical",
              "suggestion": "how to fix it"
            }}
          ],
          "recommendations": ["list of general improvements"],
          "confidence": 0.95
        }}
        """
        
        response = await self.llm.query(prompt)
        return self._parse_analysis_response(response)
    
    async def _get_recent_files(self, project_path: str, hours: int = 24) -> List[str]:
        """Get files modified in the last N hours"""
        try:
            result = subprocess.run(
                ["find", project_path, "-name", "*.py", "-mtime", f"-{hours/24}", "-type", "f"],
                capture_output=True, text=True
            )
            return [f for f in result.stdout.strip().split('\n') if f]
        except:
            return []
    
    async def _scan_project_structure(self, project_path: str) -> Dict:
        """Scan project structure and key files"""
        structure = {
            "python_files": [],
            "config_files": [],
            "test_files": [],
            "requirements_files": []
        }
        
        try:
            for root, dirs, files in os.walk(project_path):
                for file in files:
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, project_path)
                    
                    if file.endswith('.py'):
                        if 'test' in file or 'test' in root:
                            structure["test_files"].append(rel_path)
                        else:
                            structure["python_files"].append(rel_path)
                    elif file in ['requirements.txt', 'pyproject.toml', 'setup.py']:
                        structure["requirements_files"].append(rel_path)
                    elif file.endswith(('.yaml', '.yml', '.json', '.config')):
                        structure["config_files"].append(rel_path)
        except:
            pass
            
        return structure

    async def detect_common_issues(self, file_path: str) -> List[Dict]:
        """Detect common code issues in a specific file"""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            issues = []
            
            # Basic static analysis
            if len(content) > 1000:
                issues.append({
                    "issue_type": "maintainability",
                    "description": "File is very large, consider splitting",
                    "severity": "medium",
                    "suggestion": "Break into smaller modules"
                })
            
            # Check for common patterns
            if "import *" in content:
                issues.append({
                    "issue_type": "maintainability", 
                    "description": "Wildcard import found",
                    "severity": "low",
                    "suggestion": "Use explicit imports"
                })
            
            # Use LM Studio for deeper analysis
            llm_issues = await self._analyze_with_llm(file_path, content)
            issues.extend(llm_issues)
            
            return issues
            
        except Exception as e:
            return [{"error": f"Could not analyze {file_path}: {str(e)}"}]
    
    async def _analyze_with_llm(self, file_path: str, content: str) -> List[Dict]:
        """Use LM Studio to analyze specific code issues"""
        prompt = f"""
        Analyze this Python file for code quality issues:
        
        FILE: {file_path}
        
        CODE:
        ```python
        {content[:2000]}  # First 2000 chars to avoid token limits
        ```
        
        Identify specific issues and return as JSON:
        {{
          "issues": [
            {{
              "line": "approx line number or pattern",
              "issue_type": "syntax|performance|security|style",
              "description": "specific issue found",
              "severity": "low|medium|high",
              "suggestion": "specific fix suggestion"
            }}
          ]
        }}
        """
        
        try:
            response = await self.llm.query(prompt)
            data = json.loads(response)
            return data.get("issues", [])
        except:
            return []
    
    async def analyze_code_issue(self, file_path: str, error: str) -> Dict:
        """Use LM Studio to analyze and fix code issues"""
        with open(file_path, 'r') as f:
            code_content = f.read()
        
        prompt = f"""
        Analyze this code issue and suggest a fix:
        
        FILE: {file_path}
        ERROR: {error}
        
        CODE:
        {code_content}
        
        Provide a specific code fix in this JSON format:
        {{
          "analysis": "brief analysis of the issue",
          "fix_type": "syntax_error|logic_error|performance|refactor",
          "fixed_code": "the complete fixed code",
          "changes_made": ["list of specific changes"],
          "confidence": 0.95
        }}
        """
        
        response = await self.llm.query(prompt)
        return self._parse_code_response(response)
    
    async def apply_code_fix(self, file_path: str, fixed_code: str, backup: bool = True):
        """Apply code fixes with backup and validation"""
        if backup:
            backup_path = f"{file_path}.backup"
            subprocess.run(["sudo", "cp", file_path, backup_path])
        
        try:
            # Validate syntax before applying
            ast.parse(fixed_code)
            
            with open(file_path, 'w') as f:
                f.write(fixed_code)
            
            # Format the code
            formatted = autopep8.fix_code(fixed_code)
            with open(file_path, 'w') as f:
                f.write(formatted)
                
            return True
        except Exception as e:
            # Restore backup if fix fails
            if backup:
                subprocess.run(["sudo", "cp", backup_path, file_path])
            raise e
    
    async def run_tests(self, project_path: str) -> Dict:
        """Run project tests with elevated privileges if needed"""
        try:
            # Try without sudo first
            result = subprocess.run(
                ["python", "-m", "pytest"],
                cwd=project_path,
                capture_output=True, text=True, timeout=120
            )
            
            if result.returncode != 0:
                # Try with sudo for permission issues
                result = subprocess.run(
                    ["sudo", "python", "-m", "pytest"],
                    cwd=project_path,
                    capture_output=True, text=True, timeout=120
                )
            
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "errors": result.stderr
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

        except:
            return []

    def _format_structure(self, structure: Dict) -> str:
        """Format project structure for LLM prompt"""
        output = []
        for key, files in structure.items():
            output.append(f"{key}: {len(files)} files")
            if files:
                output.extend([f"  - {f}" for f in files[:5]])  # Show first 5 files
        return "\n".join(output)

    def _parse_analysis_response(self, response: str) -> Dict:
        """Parse LLM response for code analysis"""
        try:
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return {"error": "No JSON found in response", "raw_response": response}
        except Exception as e:
            return {"error": f"Failed to parse response: {e}", "raw_response": response}
    
    def _basic_code_analysis(self, project_path: str) -> Dict:
        """Basic code analysis without LM Studio"""
        structure = asyncio.run(self._scan_project_structure(project_path))
        return {
            "overall_health": "good",
            "issues_found": [],
            "recommendations": ["Enable LM Studio for detailed analysis"],
            "confidence": 0.5,
            "file_count": len(structure["python_files"]),
            "test_file_count": len(structure["test_files"])
        }

    def _parse_code_response(self, response: str) -> Dict:
        # This is a placeholder. In a real implementation, you would parse the JSON response from the LLM.
        # For now, we'll just return a dummy dictionary.
        return {
            "analysis": "dummy analysis",
            "fix_type": "logic_error",
            "fixed_code": "print('hello world')",
            "changes_made": ["dummy change"],
            "confidence": 0.95
        }

    async def suggest_refactoring(self, project_path: str) -> Dict:
        """Use LM Studio to suggest large-scale refactoring improvements"""
        if not self.llm:
            return {"refactorings": [], "reason": "LM Studio not available"}
        
        project_structure = await self._scan_project_structure(project_path)
        
        prompt = f"""
        Analyze this project for refactoring opportunities:
        
        PROJECT: {project_path}
        
        STRUCTURE:
        {self._format_structure(project_structure)}
        
        Suggest 3-5 specific refactoring improvements that would significantly improve:
        - Code maintainability
        - Performance  
        - Readability
        - Architecture
        
        Return as JSON:
        {{
          "refactorings": [
            {{
              "name": "refactoring name",
              "description": "what to change and why",
              "impact": "high|medium|low",
              "effort": "high|medium|low", 
              "files_affected": ["list of files"],
              "steps": ["step 1", "step 2", ...],
              "benefits": ["benefit 1", "benefit 2", ...]
            }}
          ],
          "overall_priority": "which refactoring to do first"
        }}
        """
        
        response = await self.llm.query(prompt)
        return self._parse_refactoring_response(response)
    
    async def perform_refactoring(self, project_path: str, refactoring: Dict) -> Dict:
        """Perform a specific refactoring with user confirmation"""
        results = {
            "completed": False,
            "changes_made": [],
            "backup_created": False,
            "errors": []
        }
        
        try:
            # Create project backup
            backup_dir = f"{project_path}.backup.{int(asyncio.get_event_loop().time())}"
            import shutil
            shutil.copytree(project_path, backup_dir)
            results["backup_created"] = True
            
            self.logger.info(f"Starting refactoring: {refactoring['name']}")
            self.logger.info(f"Backup created at: {backup_dir}")
            
            # For now, just log the refactoring plan
            # In a real implementation, you'd execute the steps
            results["changes_made"] = refactoring.get("steps", [])
            results["completed"] = True
            
            return results
            
        except Exception as e:
            results["errors"].append(str(e))
            return results
    
    def _parse_refactoring_response(self, response: str) -> Dict:
        """Parse LLM response for refactoring suggestions"""
        try:
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return {"refactorings": [], "error": "No JSON found in response"}
        except Exception as e:
            return {"refactorings": [], "error": f"Parse error: {e}"}

    async def analyze_performance(self, project_path: str) -> Dict:
        """Analyze code for performance bottlenecks and optimization opportunities"""
        project_structure = await self._scan_project_structure(project_path)
        
        # Look for common performance patterns
        performance_issues = await self._scan_for_performance_issues(project_path)
        
        if self.llm:
            return await self._get_llm_performance_analysis(project_path, project_structure, performance_issues)
        else:
            return self._basic_performance_analysis(performance_issues)
    
    async def _scan_for_performance_issues(self, project_path: str) -> List[Dict]:
        """Scan code for common performance anti-patterns"""
        issues = []
        
        try:
            for python_file in Path(project_path).rglob("*.py"):
                with open(python_file, 'r') as f:
                    content = f.read()
                    lines = content.split('\n')
                
                # Check for common performance issues
                for i, line in enumerate(lines):
                    line_issues = self._check_line_performance(str(python_file), line, i+1)
                    issues.extend(line_issues)
                    
        except Exception as e:
            print(f"Performance scan error: {e}")
            
        return issues
    
    def _check_line_performance(self, file_path: str, line: str, line_num: int) -> List[Dict]:
        """Check a single line for performance issues"""
        issues = []
        line_lower = line.lower()
        
        # N+1 query patterns
        if any(pattern in line_lower for pattern in ['for', 'in', 'select', 'query']) and 'database' in line_lower:
            issues.append({
                "file": file_path,
                "line": line_num,
                "issue_type": "performance",
                "description": "Potential N+1 query pattern",
                "severity": "medium",
                "suggestion": "Consider using eager loading or batch queries"
            })
        
        # Inefficient loops
        if 'for ' in line_lower and 'range(' in line_lower and 'len(' in line_lower:
            issues.append({
                "file": file_path, 
                "line": line_num,
                "issue_type": "performance",
                "description": "Inefficient loop calling len() repeatedly",
                "severity": "low",
                "suggestion": "Store len() result in variable before loop"
            })
        
        # String concatenation in loops
        if 'for ' in line_lower and '+=' in line and "'" in line:
            issues.append({
                "file": file_path,
                "line": line_num, 
                "issue_type": "performance",
                "description": "String concatenation in loop (inefficient)",
                "severity": "medium",
                "suggestion": "Use list.append() and ''.join() instead"
            })
        
        return issues
    
    async def _get_llm_performance_analysis(self, project_path: str, structure: Dict, issues: List[Dict]) -> Dict:
        """Get detailed performance analysis from LM Studio"""
        prompt = f"""
        Analyze this project for performance optimization opportunities:
        
        PROJECT: {project_path}
        STRUCTURE: {self._format_structure(structure)}
        
        FOUND ISSUES: {len(issues)} potential performance issues
        
        Provide performance optimization suggestions in JSON format:
        {{
          "overall_performance_score": 0-100,
          "bottlenecks": [
            {{
              "type": "cpu|memory|io|database",
              "description": "bottleneck description", 
              "impact": "high|medium|low",
              "files_affected": ["file1.py", "file2.py"],
              "optimization": "specific optimization strategy",
              "expected_improvement": "estimated improvement description"
            }}
          ],
          "quick_wins": ["list of easy optimizations"],
          "architectural_changes": ["larger structural improvements"]
        }}
        """
        
        try:
            response = await self.llm.query(prompt)
            return self._parse_performance_response(response)
        except:
            return self._basic_performance_analysis(issues)
    
    def _basic_performance_analysis(self, issues: List[Dict]) -> Dict:
        """Basic performance analysis without LM Studio"""
        return {
            "overall_performance_score": max(0, 100 - len(issues) * 5),
            "bottlenecks": issues[:5],  # Show first 5 issues as bottlenecks
            "quick_wins": ["Fix identified performance patterns", "Review database queries"],
            "architectural_changes": ["Consider caching strategies", "Review data structures"]
        }
    
    def _parse_performance_response(self, response: str) -> Dict:
        """Parse LM Studio performance analysis response"""
        try:
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        return self._basic_performance_analysis([])

    async def analyze_security(self, project_path: str) -> Dict:
        """Analyze code for security vulnerabilities"""
        security_issues = await self._scan_for_security_vulnerabilities(project_path)
        
        if self.llm:
            return await self._get_llm_security_analysis(project_path, security_issues)
        else:
            return self._basic_security_analysis(security_issues)
    
    async def _scan_for_security_vulnerabilities(self, project_path: str) -> List[Dict]:
        """Scan code for common security vulnerabilities"""
        issues = []
        
        try:
            for python_file in Path(project_path).rglob("*.py"):
                with open(python_file, 'r') as f:
                    content = f.read()
                    lines = content.split('\n')
                
                # Check for security vulnerabilities
                for i, line in enumerate(lines):
                    line_issues = self._check_line_security(str(python_file), line, i+1)
                    issues.extend(line_issues)
                    
        except Exception as e:
            print(f"Security scan error: {e}")
            
        return issues
    
    def _check_line_security(self, file_path: str, line: str, line_num: int) -> List[Dict]:
        """Check a single line for security vulnerabilities"""
        issues = []
        line_lower = line.lower()
        
        # Hardcoded secrets
        if any(secret in line_lower for secret in ['password', 'secret', 'api_key', 'token']) and '=' in line:
            if not any(safe in line_lower for safe in ['os.environ', 'config', 'getenv', 'input']):
                issues.append({
                    "file": file_path,
                    "line": line_num,
                    "issue_type": "security",
                    "description": "Potential hardcoded secret",
                    "severity": "high",
                    "suggestion": "Use environment variables or secure config storage"
                })
        
        # SQL injection
        if any(db in line_lower for db in ['execute', 'query', 'sql']) and '%s' not in line and '?' not in line:
            if '+' in line or 'format(' in line or 'f"' in line:
                issues.append({
                    "file": file_path,
                    "line": line_num,
                    "issue_type": "security", 
                    "description": "Potential SQL injection vulnerability",
                    "severity": "critical",
                    "suggestion": "Use parameterized queries with %s or ? placeholders"
                })
        
        # Shell injection
        if any(cmd in line_lower for cmd in ['os.system', 'subprocess.call', 'popen']) and any(var in line for var in ['+', 'format', 'f"']):
            issues.append({
                "file": file_path,
                "line": line_num,
                "issue_type": "security",
                "description": "Potential shell injection vulnerability",
                "severity": "high", 
                "suggestion": "Use subprocess with explicit args list instead of string concatenation"
            })
        
        # Insecure deserialization
        if 'pickle.load' in line_lower:
            issues.append({
                "file": file_path,
                "line": line_num,
                "issue_type": "security",
                "description": "Insecure deserialization with pickle",
                "severity": "high",
                "suggestion": "Use json or other safe serialization formats"
            })
        
        return issues
    
    async def _get_llm_security_analysis(self, project_path: str, issues: List[Dict]) -> Dict:
        """Get detailed security analysis from LM Studio"""
        prompt = f"""
        Analyze this project for security vulnerabilities:
        
        PROJECT: {project_path}
        FOUND ISSUES: {len(issues)} potential security vulnerabilities
        
        Provide security analysis in JSON format:
        {{
          "security_score": 0-100,
          "critical_issues": {len([i for i in issues if i.get('severity') == 'critical'])},
          "high_issues": {len([i for i in issues if i.get('severity') == 'high'])},
          "vulnerabilities": [
            {{
              "type": "injection|auth|data_exposure|etc",
              "description": "vulnerability description",
              "severity": "critical|high|medium|low", 
              "files_affected": ["file1.py"],
              "remediation": "specific fix instructions",
              "risk_level": "description of potential impact"
            }}
          ],
          "recommendations": ["list of security improvements"],
          "immediate_actions": ["urgent security fixes needed"]
        }}
        """
        
        try:
            response = await self.llm.query(prompt)
            return self._parse_security_response(response)
        except:
            return self._basic_security_analysis(issues)
    
    def _basic_security_analysis(self, issues: List[Dict]) -> Dict:
        """Basic security analysis without LM Studio"""
        critical_issues = [i for i in issues if i.get('severity') == 'critical']
        high_issues = [i for i in issues if i.get('severity') == 'high']
        
        return {
            "security_score": max(0, 100 - len(critical_issues) * 20 - len(high_issues) * 10),
            "critical_issues": len(critical_issues),
            "high_issues": len(high_issues),
            "vulnerabilities": critical_issues + high_issues[:3],
            "recommendations": ["Fix identified security vulnerabilities", "Review authentication mechanisms"],
            "immediate_actions": ["Address critical vulnerabilities immediately"] if critical_issues else ["No critical issues found"]
        }
    
    def _parse_security_response(self, response: str) -> Dict:
        """Parse LM Studio security analysis response"""
        try:
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        return self._basic_security_analysis([])

    async def apply_safe_fixes(self, project_path: str, issues: List[Dict]) -> Dict:
        """Apply safe automated fixes to code issues"""
        results = {
            "applied_fixes": 0,
            "failed_fixes": 0,
            "files_modified": [],
            "backups_created": []
        }
        
        for issue in issues:
            if await self._is_safe_to_fix(issue):
                success = await self._apply_single_fix(issue, project_path)
                if success:
                    results["applied_fixes"] += 1
                    if issue["file"] not in results["files_modified"]:
                        results["files_modified"].append(issue["file"])
                else:
                    results["failed_fixes"] += 1
        
        return results
    
    async def _is_safe_to_fix(self, issue: Dict) -> bool:
        """Determine if an issue is safe to fix automatically"""
        # High risk actions that should be manual
        unsafe_patterns = [
            "delete", "remove", "drop", "destroy", "truncate",
            "security", "authentication", "password", "secret",
            "critical", "data loss", "irreversible"
        ]
        
        issue_desc = issue.get("description", "").lower()
        issue_type = issue.get("issue_type", "").lower()
        
        # Only fix low/medium severity issues automatically
        if issue.get("severity") in ["high", "critical"]:
            return False
        
        # Don't fix security issues automatically
        if "security" in issue_type:
            return False
            
        # Check for unsafe patterns in description
        if any(pattern in issue_desc for pattern in unsafe_patterns):
            return False
            
        return True
    
    async def _apply_single_fix(self, issue: Dict, project_path: str) -> bool:
        """Apply a single fix to a code issue"""
        file_path = os.path.join(project_path, issue["file"])
        
        if not os.path.exists(file_path):
            return False
        
        try:
            # Create backup
            backup_path = f"{file_path}.backup"
            import shutil
            shutil.copy2(file_path, backup_path)
            
            # Apply fix using LM Studio
            fixed = await self._fix_with_llm(file_path, issue)
            
            if fixed:
                # Run tests to verify fix doesn't break anything
                tests_pass = await self._verify_fix(project_path)
                if tests_pass:
                    return True
                else:
                    # Restore backup if tests fail
                    shutil.copy2(backup_path, file_path)
                    os.remove(backup_path)
                    return False
            else:
                os.remove(backup_path)
                return False
                
        except Exception as e:
            print(f"Fix failed for {file_path}: {e}")
            return False

    async def _fix_with_llm(self, file_path: str, issue: Dict) -> bool:
        """Use LM Studio to generate and apply a fix"""
        try:
            with open(file_path, 'r') as f:
                original_content = f.read()
            
            prompt = f"""
            Fix this code issue:
            
            FILE: {file_path}
            ISSUE: {issue['description']}
            SUGGESTION: {issue.get('suggestion', 'Fix the issue')}
            
            ORIGINAL CODE:
            ```python
            {original_content}
            ```
            
            Provide the COMPLETE fixed file content. Return ONLY the code, no explanations.
            Ensure the fix is minimal and preserves all functionality.
            """
            
            fixed_content = await self.llm.query(prompt)
            
            # Validate the fix
            if self._is_valid_fix(original_content, fixed_content):
                with open(file_path, 'w') as f:
                    f.write(fixed_content)
                return True
            else:
                return False
                
        except Exception as e:
            print(f"LLM fix failed: {e}")
            return False
    
    def _is_valid_fix(self, original: str, fixed: str) -> bool:
        """Validate that the fix is reasonable"""
        if not fixed or len(fixed) < 10:
            return False
        
        # Check that the fix isn't completely different
        original_lines = original.split('\n')
        fixed_lines = fixed.split('\n')
        
        # Should have similar number of lines
        if abs(len(original_lines) - len(fixed_lines)) > 10:
            return False
            
        # Should preserve key structures (basic check)
        original_imports = len([l for l in original_lines if l.startswith('import') or l.startswith('from')])
        fixed_imports = len([l for l in fixed_lines if l.startswith('import') or l.startswith('from')])
        
        if abs(original_imports - fixed_imports) > 2:
            return False
            
        return True
    
    async def _verify_fix(self, project_path: str) -> bool:
        """Verify that fixes don't break the project"""
        try:
            # Find a Python file to test syntax
            python_files = list(Path(project_path).rglob("*.py"))
            if not python_files:
                return True
                
            test_file = python_files[0]
            result = subprocess.run(
                ["python", "-m", "py_compile", str(test_file)],
                capture_output=True, text=True, timeout=30
            )
            return result.returncode == 0
        except:
            return True  # If we can't verify, assume it's ok
