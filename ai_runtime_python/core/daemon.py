#!/usr/bin/env python3
"""
AI System Daemon - Your 24/7 AI Co-pilot
"""
import asyncio
import json
from datetime import datetime
import logging
import signal
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from .brain import AIBrain
from .memory import ExperienceDB
from .monitor import SystemMonitor
from .project_monitor import ProjectMonitor, ProjectState
from .code_manager import CodeManager
from .performance_profiler import PerformanceProfiler
from .vulnerability_prioritizer import VulnerabilityPrioritizer
from .security_guardrails import SecurityGuardrails
from .structured_logger import StructuredLogger, LogSeverity, IncidentSeverity
from .alert_manager import AlertManager


class AIDaemon:
    """Coordinates monitoring, decision-making, and learning loops."""

    def __init__(self, config_dir: str = "config"):
        self.running = False
        self.config_dir = Path(config_dir)
        self.config: Dict[str, Any] = {}
        self.load_config()
        self.current_state: Dict[str, Any] = {}
        self.cycle_count = 0
        self.logger = setup_logging(Path("logs"))
        self.monitor = SystemMonitor(self.config)
        self.brain = AIBrain(self.config)
        self.code_manager = CodeManager(self.brain.llm_manager)
        print("CodeManager initialized")
        self.memory = ExperienceDB("knowledge/experience.db")
        
        try:
            self.project_monitor = ProjectMonitor(self.config)
            self.logger.info("Project monitor initialized successfully")
        except Exception as e:
            self.logger.warning(f"Project monitor initialization failed: {e}")
            self.project_monitor = None

        # Initialize high-assurance components
        self.performance_profiler = PerformanceProfiler(self.config)
        self.vulnerability_prioritizer = VulnerabilityPrioritizer(self.config) 
        self.security_guardrails = SecurityGuardrails(self.config)
        self.structured_logger = StructuredLogger(self.config)
        self.alert_manager = AlertManager(self.config)
        
        # Enable asyncio debug mode for performance monitoring
        self.performance_profiler.enable_asyncio_debug()

    def load_config(self) -> None:
        """Load YAML configuration files into memory."""
        system_config = self._normalize_system_config(self._load_yaml("system.yaml"))
        services_config = self._normalize_services_config(self._load_yaml("services.yaml"))

        if "n8n" in system_config and "webhooks" in system_config.get("n8n", {}):
            services_config.setdefault("n8n", {}).setdefault("webhooks", {}).update(system_config["n8n"]["webhooks"])

        self.config = {
            "system": system_config,
            "services": services_config,
            "habits": self._load_yaml("habits.yaml"),
        }

    def _load_yaml(self, filename: str) -> Dict[str, Any]:
        try:
            with open(self.config_dir / filename, "r", encoding="utf-8") as handle:
                data = yaml.safe_load(handle) or {}
            return data
        except FileNotFoundError:
            self.logger.warning("Config file missing: %s", filename)
            return {}
        except yaml.YAMLError as exc:
            self.logger.warning("Failed to parse %s: %s", filename, exc)
            return {}

    def _normalize_system_config(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if not data:
            return {}
        if "system" in data and isinstance(data["system"], dict):
            return data["system"]
        return data

    def _normalize_services_config(self, data: Dict[str, Any]) -> Dict[str, Any]:
        services = data or {}
        notifications = services.get("notifications") or {}
        notifications.setdefault("slack", {})
        notifications.setdefault("email", {})
        notifications.setdefault("webhook", {})
        services["notifications"] = notifications
        return services

    async def start(self) -> None:
        """Start all daemon subsystems and serve indefinitely until interrupted."""
        self.logger.info("Starting AI System Daemon...")
        self.running = True

        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(self.signal_handler(s)))

        try:
            await asyncio.gather(
                self.monitoring_loop(),
                self.decision_loop(),
                self.learning_loop(),
            )
        except asyncio.CancelledError:
            pass
        finally:
            await self.shutdown()

    async def monitoring_loop(self) -> None:
        """Continuously collect system state and react to critical alerts."""
        interval = self.config.get("system", {}).get("intervals", {}).get("system_metrics", 10)
        while self.running:
            try:
                self.current_state = await self.monitor.capture_system_state()
                await self.memory.log_metrics(self.current_state)
                if self.monitor.is_critical(self.current_state):
                    await self.handle_critical_condition()
            except Exception as exc:
                self.logger.exception("Monitoring error: %s", exc)
            await asyncio.sleep(interval)

    async def decision_loop(self) -> None:
        """Invoke the decision engine to plan actions based on live state."""
        while self.running:
            if self.current_state:
                try:
                    # CONSULT LLM FOR PROACTIVE INSIGHTS (NEW!)
                    if self.cycle_count % 5 == 0:  # Every 5 cycles (50 seconds)
                        await self._consult_llm_for_insights()
                    
                    # Monitor projects
                    project_states = await self.monitor_projects()

                    # Add project health to decision context
                    project_health = {
                        "total_projects": len(project_states),
                        "projects_with_errors": sum(1 for s in project_states.values() if s.error_count > 0),
                        "total_recent_changes": sum(len(s.recent_changes or []) for s in project_states.values())
                    }

                    # Check for critical conditions that require alerts
                    await self._check_critical_conditions()

                    # Analyze refactoring opportunities for stable projects
                    if project_health["total_recent_changes"] == 0:
                        # No recent changes, good time to suggest refactoring
                        await self._analyze_refactoring_opportunities(project_states)

                    self.current_state['projects'] = project_health
                    recent_context = await self.memory.get_recent_context()
                    decision = await self.brain.make_decision(self.current_state, recent_context)
                    if decision and decision.get("confidence", 0) > 0.8:
                        await self.execute_decision(decision)

                    # Analyze performance and security (less frequently)
                    if self.cycle_count % 10 == 0:  # Every 10 cycles
                        await self._analyze_performance_and_security(project_states)

                    # Performance profiling (hourly)
                    await self._run_performance_profiling()

                    self.cycle_count += 1
                except Exception as exc:
                    self.logger.exception("Decision error: %s", exc)
            await asyncio.sleep(10)

    async def monitor_projects(self):
        """Monitor all configured projects with code analysis"""
        if not self.project_monitor:
            return {}
            
        project_states = await self.project_monitor.scan_all_projects()
        await self._log_project_health(project_states)
        
        # Run deep code analysis on projects with recent changes
        if self.code_manager:
            await self._analyze_projects_with_changes(project_states)
        
        return project_states
    
    async def _analyze_projects_with_changes(self, project_states: Dict[str, ProjectState]):
        """Run deep code analysis on projects with recent changes"""
        for path, state in project_states.items():
            if (state.exists and state.recent_changes and len(state.recent_changes) > 0 and 
                hasattr(self, 'code_manager') and self.code_manager):
                self.logger.info(f"Analyzing code quality for {path} ({len(state.recent_changes)} recent changes)")
                
                try:
                    # USE LLM FOR CODE ANALYSIS (ENHANCED!)
                    if hasattr(self.brain, 'llm_manager') and self.brain.llm_manager:
                        llm_analysis = await self._analyze_with_llm(path, state)
                        if llm_analysis:
                            self.logger.info(f"LLM Code Analysis for {path}: {llm_analysis.get('code_quality', 'unknown')}")
                    
                    # Analyze overall code quality
                    analysis = await self.code_manager.analyze_code_quality(path)
                    
                    if analysis and "issues_found" in analysis:
                        issue_count = len(analysis["issues_found"])
                        if issue_count > 0:
                            self.logger.warning(f"Found {issue_count} code issues in {path}")
                            
                            # Apply safe fixes automatically
                            safe_issues = [issue for issue in analysis["issues_found"] 
                                         if issue.get("severity") in ["low", "medium"]]
                            
                            if safe_issues and self.config.get("projects", [{}])[0].get("auto_fix", False):
                                self.logger.info(f"Attempting to fix {len(safe_issues)} safe issues in {path}")
                                fix_results = await self.code_manager.apply_safe_fixes(path, safe_issues)
                                
                                self.logger.info(f"Fix results: {fix_results['applied_fixes']} applied, "
                                               f"{fix_results['failed_fixes']} failed, "
                                               f"{len(fix_results['files_modified'])} files modified")
                                
                                # Log critical issues that need manual attention
                                critical_issues = [i for i in analysis["issues_found"] 
                                                 if i.get("severity") in ["high", "critical"]]
                                for issue in critical_issues[:3]:
                                    self.logger.warning(f"  MANUAL NEEDED: {issue.get('description')} in {issue.get('file')}")
                except Exception as e:
                    self.logger.debug(f"Code analysis failed for {path}: {e}")

    async def _log_project_health(self, project_states: Dict[str, ProjectState]):
        """Log project health status"""
        for path, state in project_states.items():
            project_name = path.split('/')[-1]  # Get just the project folder name
            
            if state.error_count > 0:
                self.logger.warning(f"Project {project_name} has {state.error_count} scan errors")
            elif not state.exists:
                self.logger.error(f"Project {project_name} path not found: {path}")
            else:
                change_count = len(state.recent_changes or [])
                status_msg = f"Project {project_name}: {change_count} recent changes, git: {state.git_status}, deps: {state.dependency_count}"
                
                if change_count > 0:
                    self.logger.info(status_msg)
                    # Log the actual changed files (first 3)
                    for changed_file in state.recent_changes[:3]:
                        self.logger.debug(f"  - Changed: {changed_file}")
                    if change_count > 3:
                        self.logger.debug(f"  - ... and {change_count - 3} more changes")
                else:
                    self.logger.debug(status_msg)

    async def _analyze_refactoring_opportunities(self, project_states: Dict[str, ProjectState]):
        """Analyze refactoring opportunities for stable projects"""
        if not hasattr(self, 'code_manager') or not self.code_manager:
            return
            
        for path, state in project_states.items():
            # Only suggest refactoring for stable projects (no recent changes, good test status)
            if (state.exists and 
                (not state.recent_changes or len(state.recent_changes) == 0) and
                state.test_status == "has_tests"):
                
                self.logger.info(f"Analyzing refactoring opportunities for {path}")
                
                try:
                    refactoring_suggestions = await self.code_manager.suggest_refactoring(path)
                    
                    if refactoring_suggestions and "refactorings" in refactoring_suggestions:
                        refactorings = refactoring_suggestions["refactorings"]
                        if refactorings:
                            self.logger.info(f"Found {len(refactorings)} refactoring opportunities for {path}")
                            
                            # Log the highest impact refactoring
                            high_impact = [r for r in refactorings if r.get("impact") == "high"]
                            if high_impact:
                                best_refactor = high_impact[0]
                                self.logger.info(f"HIGH IMPACT: {best_refactor['name']} - {best_refactor['description']}")
                            
                except Exception as e:
                    self.logger.debug(f"Refactoring analysis failed for {path}: {e}")

    async def _analyze_performance_and_security(self, project_states: Dict[str, ProjectState]):
        """Analyze performance and security for all projects"""
        if not hasattr(self, 'code_manager') or not self.code_manager:
            return
            
        for path, state in project_states.items():
            if state.exists:
                # Analyze performance monthly or when issues are suspected
                if self._should_analyze_performance(path):
                    await self._analyze_project_performance(path)
                
                # Analyze security weekly or when new dependencies are added
                if self._should_analyze_security(path):
                    await self._analyze_project_security(path)

    async def _check_critical_conditions(self):
        """Check for conditions that require immediate alerts"""
        if not self.current_state:
            return
            
        # Check system resource emergencies
        cpu_usage = self.current_state.get("cpu_percent", 0)
        memory_usage = self.current_state.get("memory_percent", 0)
        
        if cpu_usage > 95:
            await self._trigger_resource_alert(
                "CRITICAL: CPU usage exceeding 95%",
                f"CPU usage is at {cpu_usage}% which may cause system instability",
                IncidentSeverity.SEV2,
                {"cpu_usage": cpu_usage, "threshold": 95}
            )
            
        if memory_usage > 90:
            await self._trigger_resource_alert(
                "CRITICAL: Memory usage exceeding 90%",
                f"Memory usage is at {memory_usage}% which may cause OOM kills",
                IncidentSeverity.SEV2,
                {"memory_usage": memory_usage, "threshold": 90}
            )
    
    async def _trigger_resource_alert(self, title: str, description: str, 
                                    severity: IncidentSeverity, context: Dict):
        """Trigger resource utilization alert"""
        alert = self.alert_manager.create_alert_from_log(
            LogSeverity.ERROR,
            severity,
            title,
            description,
            "system_monitor",
            context
        )
        
        success = await self.alert_manager.send_alert(alert)
        
        # Also log with structured logger
        self.structured_logger.log_system_operation(
            LogSeverity.ERROR,
            description,
            operation="resource_alert",
            resource="system",
            outcome="warning",
            context=context
        )
    
    async def _run_performance_profiling(self):
        """Run periodic performance profiling"""
        if self.cycle_count % 360 == 0:  # Every hour (360 cycles * 10 seconds)
            profile_result = await self.performance_profiler.profile_daemon_performance(30)
            
            if profile_result.get("status") == "success":
                self.structured_logger.log_performance_event(
                    LogSeverity.INFO,
                    "Periodic performance profile completed",
                    profile_result.get("bottlenecks", []),
                    {"profile_duration": 30}
                )

    async def _consult_llm_for_insights(self):
        """Regularly consult LLM for proactive system insights"""
        if not hasattr(self.brain, 'llm_manager') or not self.brain.llm_manager:
            return
            
        try:
            # Prepare context for LLM
            context = {
                "system_metrics": self.current_state,
                "timestamp": datetime.now().isoformat(),
                "cycle_count": self.cycle_count
            }
            
            # Ask LLM for general system insights
            prompt = f"""
            Analyze this system state and provide proactive recommendations:
            
            SYSTEM STATE:
            - CPU: {self.current_state.get('cpu_percent', 0)}%
            - Memory: {self.current_state.get('memory_percent', 0)}%
            - Disk: {self.current_state.get('disk_percent', 0)}%
            - Processes: {len(self.current_state.get('processes', []))}
            - Load Average: {self.current_state.get('load_avg', [0,0,0])}
            
            What proactive optimizations or checks would you recommend?
            Consider: performance tuning, security checks, maintenance tasks.
            
            Respond in JSON format:
            {{
              "analysis": "brief system analysis",
              "recommendations": ["list of specific actions"],
              "priority": "high|medium|low", 
              "confidence": 0.0-1.0
            }}
            """
            
            response = await self.brain.llm_manager.query(
                prompt, 
                system_prompt="You are an expert system administrator. Provide concise, actionable advice. Respond with valid JSON only. Do not include any thinking tags or explanations outside the JSON."
            )
            
            # Parse the JSON response
            try:
                insights = json.loads(response)
                self.logger.info(f"LLM System Insights: {insights.get('analysis', 'No analysis')}")
                
                # Log recommendations
                recommendations = insights.get('recommendations', [])
                if recommendations:
                    for rec in recommendations[:3]:  # Log first 3 recommendations
                        self.logger.info(f"LLM Recommendation: {rec}")
                
                # If high priority recommendation, consider immediate action
                if insights.get('priority') == 'high' and insights.get('confidence', 0) > 0.8:
                    self.logger.warning(f"LLM HIGH PRIORITY: {insights.get('analysis')}")
                    # Could trigger immediate actions here
                    
            except json.JSONDecodeError:
                self.logger.info(f"LLM Raw Response: {response}")
                
        except Exception as e:
            self.logger.debug(f"LLM consultation failed: {e}")

    async def _analyze_with_llm(self, project_path: str, state: ProjectState) -> Dict:
        """Use LLM to analyze project changes"""
        try:
            # Get recent file contents for context (first few files)
            recent_content_samples = []
            for file_path in state.recent_changes[:3]:  # Sample first 3 files
                try:
                    with open(file_path, 'r') as f:
                        content = f.read()[:500]  # First 500 chars
                        recent_content_samples.append(f"{file_path}:\n{content}")
                except:
                    continue
            
            prompt = f"""
            Analyze these recent code changes and suggest improvements:
            
            PROJECT: {project_path}
            RECENT CHANGES: {len(state.recent_changes)} files
            GIT STATUS: {state.git_status}
            DEPENDENCIES: {state.dependency_count}
            
            Sample of recent changes:
            {chr(10).join(recent_content_samples)}
            
            Provide code quality assessment and suggestions in JSON format:
            {{
              "code_quality": "excellent|good|needs_improvement|poor",
              "potential_issues": ["list of potential problems"],
              "refactoring_suggestions": ["specific improvement ideas"],
              "security_checks": ["security considerations"],
              "confidence": 0.0-1.0
            }}
            """
            
            response = await self.brain.llm_manager.query(
                prompt,
                system_prompt="You are an expert software engineer. Analyze code changes and provide specific, actionable feedback. Respond with valid JSON only."
            )
            
            # Parse and return the response
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                self.logger.debug(f"LLM returned non-JSON response: {response}")
                return {"raw_response": response, "code_quality": "unknown"}
                
        except Exception as e:
            self.logger.debug(f"LLM project analysis failed: {e}")
            return {}

    async def _get_llm_security_advice(self, project_path: str, security_analysis: Dict) -> str:
        """Get security advice from LLM"""
        try:
            prompt = f"""
            Provide security recommendations for this project:
            
            PROJECT: {project_path}
            SECURITY SCORE: {security_analysis.get('security_score', 0)}/100
            CRITICAL ISSUES: {security_analysis.get('critical_issues', 0)}
            HIGH ISSUES: {security_analysis.get('high_issues', 0)}
            
            VULNERABILITIES FOUND:
            {security_analysis.get('vulnerabilities', [])[:5]}  # First 5 vulnerabilities
            
            Provide 2-3 most important security recommendations.
            Respond with a concise list of actionable items.
            """
            
            response = await self.brain.llm_manager.query(
                prompt,
                system_prompt="You are a security expert. Provide clear, actionable security recommendations. Be concise and specific."
            )
            
            return response.strip()
            
        except Exception as e:
            self.logger.debug(f"LLM security advice failed: {e}")
            return ""
    
    async def _analyze_project_performance(self, project_path: str):
        """Analyze and log performance issues"""
        try:
            performance_analysis = await self.code_manager.analyze_performance(project_path)
            
            score = performance_analysis.get("overall_performance_score", 0)
            bottlenecks = performance_analysis.get("bottlenecks", [])
            
            if score < 80 or len(bottlenecks) > 0:
                self.logger.warning(f"Performance issues in {project_path}: score={score}, bottlenecks={len(bottlenecks)}")
                
                for bottleneck in bottlenecks[:2]:  # Log top 2 bottlenecks
                    self.logger.warning(f"  PERFORMANCE: {bottleneck['description']} (impact: {bottleneck.get('impact', 'unknown')})")
                    
        except Exception as e:
            self.logger.debug(f"Performance analysis failed for {project_path}: {e}")
    
    async def _analyze_project_security(self, project_path: str):
        """Analyze and log security vulnerabilities with LLM enhancement"""
        try:
            security_analysis = await self.code_manager.analyze_security(project_path)
            
            score = security_analysis.get("security_score", 0)
            critical_issues = security_analysis.get("critical_issues", 0)
            high_issues = security_analysis.get("high_issues", 0)
            
            # CONSULT LLM FOR SECURITY ASSESSMENT
            if (hasattr(self.brain, 'llm_manager') and self.brain.llm_manager and 
                (critical_issues > 0 or high_issues > 0 or score < 80)):
                llm_security_advice = await self._get_llm_security_advice(project_path, security_analysis)
                if llm_security_advice:
                    self.logger.warning(f"LLM Security Advice for {project_path}: {llm_security_advice}")
            
            if critical_issues > 0:
                self.logger.error(f"CRITICAL SECURITY: {project_path} has {critical_issues} critical vulnerabilities!")
            elif high_issues > 0 or score < 90:
                self.logger.warning(f"Security issues in {project_path}: score={score}, critical={critical_issues}, high={high_issues}")
                
        except Exception as e:
            self.logger.debug(f"Security analysis failed for {project_path}: {e}")
    
    def _should_analyze_performance(self, project_path: str) -> bool:
        """Determine if performance analysis should run"""
        # For now, run performance analysis randomly ~10% of the time
        import random
        return random.random() < 0.1
    
    def _should_analyze_security(self, project_path: str) -> bool:
        """Determine if security analysis should run"""
        # For now, run security analysis randomly ~5% of the time  
        import random
        return random.random() < 0.05

    async def learning_loop(self) -> None:
        """Periodically mine historical data for patterns and update models."""
        while self.running:
            try:
                patterns = await self.memory.analyze_patterns()
                if patterns:
                    await self.brain.update_models(patterns)
            except Exception as exc:
                self.logger.exception("Learning error: %s", exc)
            await asyncio.sleep(300)

    async def handle_critical_condition(self) -> None:
        """Escalate urgent issues immediately via workflows and alerts."""
        loop = asyncio.get_running_loop()
        critical_alert = {
            "type": "critical_system_condition",
            "state": self.current_state,
            "timestamp": loop.time(),
            "immediate_action": True,
            "level": "critical",
            "message": "Critical system condition detected",
        }
        await self.trigger_n8n_workflow("system_optimization", critical_alert)
        await self.send_alert(critical_alert)

    async def execute_decision(self, decision: Dict[str, Any]) -> None:
        """Execute a decision plan produced by the decision engine."""
        try:
            action = decision.get("action") or decision.get("recommended_action")
            if action == "trigger_workflow":
                await self.trigger_n8n_workflow(decision["workflow_type"], decision.get("payload", {}))
            elif action == "send_notification":
                await self.send_alert(decision.get("payload", {}))
            elif action in ["restart_service", "cleanup_files", "kill_process", "adjust_limits", "notify_admin"]:
                # This branch handles LLM-recommended actions
                await self.perform_system_optimization({
                    "type": action,
                    **decision.get("action_parameters", {})
                })
            elif action == "system_optimization":
                # This handles the old format
                await self.perform_system_optimization(decision.get("parameters", {}))
            
            await self.memory.log_decision(decision, self.current_state)
        except Exception as exc:
            self.logger.exception("Decision execution error: %s", exc)

    async def trigger_n8n_workflow(self, workflow_type: str, payload: Dict[str, Any]) -> None:
        """Deliver payloads to configured n8n workflows."""
        self.logger.warning(f"Workflow triggering disabled (n8n removed): {workflow_type}")
        return False

    async def send_alert(self, alert_data: Dict[str, Any]) -> None:
        """Send alerts over the configured communication channels."""
        notifications = self.config.get("services", {}).get("notifications", {})
        level = str(alert_data.get("level", "warning")).lower()
        message = alert_data.get("message") or alert_data.get("issue") or alert_data.get("type") or "AI daemon alert"
        context = alert_data.get("context") or alert_data

        log_fn = {
            "critical": self.logger.critical,
            "error": self.logger.error,
            "warning": self.logger.warning,
            "info": self.logger.info,
            "debug": self.logger.debug,
        }.get(level, self.logger.warning)
        log_fn("Alert dispatched: %s | context=%s", message, context)

        tasks = []
        if notifications.get("email", {}).get("enabled"):
            tasks.append(self._send_email_alert(level, message, context, notifications["email"]))
        if notifications.get("slack", {}).get("enabled"):
            tasks.append(self._send_slack_alert(level, message, context, notifications["slack"]))
        if notifications.get("webhook", {}).get("enabled"):
            tasks.append(self._send_webhook_alert(level, message, context, notifications["webhook"]))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _send_email_alert(
        self,
        level: str,
        message: str,
        context: Dict[str, Any],
        email_cfg: Dict[str, Any],
    ) -> None:
        import smtplib
        from email.message import EmailMessage

        smtp_server = email_cfg.get("smtp_server")
        smtp_port = email_cfg.get("smtp_port", 587)
        username = email_cfg.get("username") or email_cfg.get("from_addr")
        password = email_cfg.get("password")
        from_addr = email_cfg.get("from_addr")
        to_addr = email_cfg.get("to_addr")

        if not all([smtp_server, from_addr, to_addr]):
            self.logger.debug("Email alert skipped due to incomplete SMTP configuration")
            return

        async def _send() -> None:
            msg = EmailMessage()
            msg["Subject"] = f"[AI Daemon][{level.upper()}] {message}"
            msg["From"] = from_addr
            msg["To"] = to_addr
            msg.set_content(f"{message}\n\nContext:\n{context}")

            try:
                with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as server:
                    if email_cfg.get("use_tls", True):
                        server.starttls()
                    if username and password:
                        server.login(username, password)
                    server.send_message(msg)
                self.logger.info("Email alert delivered to %s", to_addr)
            except Exception as exc:
                self.logger.exception("Email alert failed: %s", exc)

        await asyncio.to_thread(_send)

    async def _send_slack_alert(
        self,
        level: str,
        message: str,
        context: Dict[str, Any],
        slack_cfg: Dict[str, Any],
    ) -> None:
        webhook = slack_cfg.get("webhook_url")
        if not webhook:
            self.logger.debug("Slack alert skipped: webhook_url missing")
            return

        payload = {
            "text": f"🚨 {level.upper()}: {message}",
            "blocks": [
                {"type": "section", "text": {"type": "mrkdwn", "text": f"*{level.upper()} Alert*"}},
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": message},
                },
            ],
        }
        if context:
            payload["blocks"].append(
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"```\n{context}\n```"},
                }
            )

        import aiohttp

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(webhook, json=payload) as resp:
                    if 200 <= resp.status < 300:
                        self.logger.info("Slack alert delivered (status=%s)", resp.status)
                    else:
                        text = await resp.text()
                        self.logger.error("Slack alert failed: %s %s", resp.status, text)
            except Exception as exc:
                self.logger.exception("Slack alert error: %s", exc)

    async def _send_webhook_alert(
        self,
        level: str,
        message: str,
        context: Dict[str, Any],
        hook_cfg: Dict[str, Any],
    ) -> None:
        url = hook_cfg.get("url")
        if not url:
            self.logger.debug("Webhook alert skipped: url missing")
            return

        payload = {
            "level": level,
            "message": message,
            "context": context,
            "source": "ai_daemon",
        }

        headers = {}
        token = hook_cfg.get("auth_token")
        if token:
            headers["Authorization"] = f"Bearer {token}"

        import aiohttp

        async with aiohttp.ClientSession(headers=headers) as session:
            try:
                async with session.post(url, json=payload) as resp:
                    if 200 <= resp.status < 300:
                        self.logger.info("Webhook alert delivered (status=%s)", resp.status)
                    else:
                        text = await resp.text()
                        self.logger.error("Webhook alert failed: %s %s", resp.status, text)
            except Exception as exc:
                self.logger.exception("Webhook alert error: %s", exc)

    async def perform_system_optimization(self, parameters: Dict[str, Any]) -> None:
        """Dispatch system optimization routines based on decision parameters."""
        optimization_type = parameters.get("type")
        routines = {
            "memory_cleanup": self.cleanup_memory,
            "process_optimization": self.optimize_processes,
            "disk_cleanup": self.cleanup_disk,
            "cleanup_temp": self.cleanup_temp_files,
            "restart_service": self.restart_service,
            "scale_workload": self.scale_workload,
            "cache_clear": self.clear_application_cache,
            "optimize_memory": self._optimize_memory,
            "manage_swap": self._manage_swap,
            "kill_process": self._kill_process,
            "adjust_limits": self._adjust_limits,
            "notify_admin": self._notify_admin_direct,
        }
        routine = routines.get(optimization_type)
        if routine is None:
            self.logger.warning(f"Unknown optimization action: {optimization_type}")
            return
        await routine(parameters)

    async def _optimize_memory(self, context):
        """Optimize system memory usage."""
        import subprocess
        try:
            # Clear page cache, dentries, and inodes
            subprocess.run(['sync'], capture_output=True)
            subprocess.run(['echo', '3', '>', '/proc/sys/vm/drop_caches'], 
                         shell=True, capture_output=True)
            self.logger.info("Memory caches cleared")
        except Exception as e:
            self.logger.warning(f"Memory optimization failed: {e}")

    async def _manage_swap(self, context):
        """Manage swap usage based on context."""
        action = context.get('swap_action', 'status')
        if action == 'clear':
            import subprocess
            subprocess.run(['swapoff', '-a'], capture_output=True)
            subprocess.run(['swapon', '-a'], capture_output=True)
            self.logger.info("Swap cleared and re-enabled")

    async def _kill_process(self, context):
        """Safely kill a problematic process."""
        pid = context.get('pid')
        process_name = context.get('process_name')
        # Add safety checks before killing

    async def _adjust_limits(self, context):
        """Adjust system limits (ulimit, etc.)."""
        limit_type = context.get('limit_type')
        new_value = context.get('value')
        # Implement limit adjustments

    async def _notify_admin_direct(self, context):
        """Send direct notifications without n8n."""
        message = context.get('message', 'System notification')
        priority = context.get('priority', 'medium')
        # Use your existing alert system
        await self.send_alert(priority, message, context)

    async def cleanup_memory(self, parameters: Optional[Dict[str, Any]] = None) -> None:
        self.logger.info("Memory cleanup requested; no-op without custom implementation")

    async def optimize_processes(self, parameters: Optional[Dict[str, Any]] = None) -> None:
        self.logger.info("Process optimization requested with parameters=%s", parameters)

    async def cleanup_disk(self, parameters: Optional[Dict[str, Any]] = None) -> None:
        self.logger.info("Disk cleanup requested with parameters=%s", parameters)

    async def cleanup_temp_files(self, parameters: Optional[Dict[str, Any]] = None) -> None:
        import os
        import tempfile

        temp_dirs = [tempfile.gettempdir()]
        cleaned = 0

        for temp_dir in temp_dirs:
            if not os.path.exists(temp_dir):
                continue
            if not os.access(temp_dir, os.W_OK):
                self.logger.warning("No write permissions for %s", temp_dir)
                continue
            try:
                for entry in os.listdir(temp_dir):
                    entry_path = os.path.join(temp_dir, entry)
                    if entry.endswith(".tmp") and os.path.isfile(entry_path):
                        try:
                            os.remove(entry_path)
                            cleaned += 1
                        except (OSError, PermissionError):
                            continue
            except Exception as exc:
                self.logger.error("Error cleaning %s: %s", temp_dir, exc)

        self.logger.info("Cleaned %s temp files", cleaned)
        return {"cleaned_files": cleaned}

    async def restart_service(self, parameters: Optional[Dict[str, Any]] = None) -> None:
        import shutil
        import sys

        service_name = (parameters or {}).get("service_name")
        if not service_name:
            self.logger.warning("Restart service requested without service_name")
            return

        allowed_services = ["nginx", "redis-server", "postgresql", "mysql"]
        if service_name not in allowed_services:
            self.logger.error("Service %s not allowed for auto-restart", service_name)
            return

        if not shutil.which("systemctl") or not sys.platform.startswith("linux"):
            self.logger.warning("Systemctl not available; cannot restart service '%s'", service_name)
            return

        self.logger.info("Attempting to restart service '%s'", service_name)
        proc = await asyncio.create_subprocess_exec(
            "systemctl",
            "restart",
            service_name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode == 0:
            self.logger.info("Service '%s' restarted successfully", service_name)
        else:
            self.logger.error("Failed to restart service '%s': %s", service_name, stderr.decode().strip())

    async def scale_workload(self, parameters: Optional[Dict[str, Any]] = None) -> None:
        self.logger.info("Scale workload invoked with parameters=%s", parameters)

    async def clear_application_cache(self, parameters: Optional[Dict[str, Any]] = None) -> None:
        from pathlib import Path

        paths = (parameters or {}).get("paths", [])
        if not paths:
            self.logger.info("Cache clear invoked without paths; skipping")
            return

        removed = 0
        for path_str in paths:
            path = Path(path_str).expanduser()
            if not path.exists():
                continue
            try:
                if path.is_file():
                    path.unlink()
                    removed += 1
                elif path.is_dir():
                    for child in path.glob("**/*"):
                        try:
                            if child.is_file():
                                child.unlink()
                                removed += 1
                        except Exception as exc:
                            self.logger.debug("Failed to remove cache file %s: %s", child, exc)
                self.logger.debug("Cleared cache path %s", path)
            except Exception as exc:
                self.logger.warning("Could not clear cache path %s: %s", path, exc)

        self.logger.info("Cleared %s cache entries", removed)

    async def signal_handler(self, signum) -> None:
        self.logger.info("Received signal %s, initiating shutdown...", signum)
        self.running = False

    async def shutdown(self) -> None:
        if not self.running:
            self.logger.info("Cleaning up daemon resources...")
        self.running = False
        self.logger.info("AI System Daemon stopped.")
        if self.memory:
            await self.memory.close()
        if hasattr(self.brain, 'llm_manager'):
            await self.brain.llm_manager.close()
        self.logger.info("AI Daemon shutdown complete")


def setup_logging(log_dir: Path) -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("ai_daemon")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    file_handler = RotatingFileHandler(log_dir / "daemon.log", maxBytes=10 * 1024 * 1024, backupCount=5)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


async def main() -> None:
    daemon = AIDaemon()
    await daemon.start()


if __name__ == "__main__":
    asyncio.run(main())
