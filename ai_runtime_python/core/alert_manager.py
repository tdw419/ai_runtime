import asyncio
import aiohttp
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timezone
from .structured_logger import LogSeverity, IncidentSeverity

class AlertChannel(Enum):
    PAGERDUTY = "pagerduty"
    SLACK = "slack"
    EMAIL = "email"
    WEBHOOK = "webhook"
    JIRA = "jira"

@dataclass
class Alert:
    title: str
    description: str
    severity: IncidentSeverity
    source: str
    timestamp: str
    context: Dict[str, Any]
    deduplication_key: str
    
    @property
    def requires_immediate_action(self) -> bool:
        return self.severity in [IncidentSeverity.SEV1, IncidentSeverity.SEV2]

class AlertManager:
    """Actionable alerting system with automated ticket creation"""
    
    def __init__(self, config):
        self.config = config
        self.alert_channels = self._setup_channels()
        self.sent_alerts = {}  # For deduplication
        
    def _setup_channels(self) -> Dict[AlertChannel, Dict]:
        """Configure alert channels from config"""
        channels = {}
        notifications_config = self.config.get("notifications", {})
        
        if notifications_config.get("slack", {}).get("enabled"):
            channels[AlertChannel.SLACK] = notifications_config["slack"]
        
        if notifications_config.get("email", {}).get("enabled"):
            channels[AlertChannel.EMAIL] = notifications_config["email"]
            
        if notifications_config.get("webhook", {}).get("enabled"):
            channels[AlertChannel.WEBHOOK] = notifications_config["webhook"]
            channels[AlertChannel.PAGERDUTY] = notifications_config["webhook"]  # Can reuse webhook
        
        # JIRA configuration
        jira_config = self.config.get("jira", {})
        if jira_config.get("enabled"):
            channels[AlertChannel.JIRA] = jira_config
            
        return channels
    
    async def send_alert(self, alert: Alert) -> bool:
        """Send alert through configured channels"""
        # Deduplication check
        if alert.deduplication_key in self.sent_alerts:
            time_since_last = asyncio.get_event_loop().time() - self.sent_alerts[alert.deduplication_key]
            if time_since_last < 300:  # 5 minute deduplication window
                return True  # Consider it "sent" due to deduplication
        
        self.sent_alerts[alert.deduplication_key] = asyncio.get_event_loop().time()
        
        # Clean old deduplication keys
        self._clean_old_alerts()
        
        # Send to appropriate channels based on severity
        success = True
        
        if alert.requires_immediate_action:
            # SEV1/SEV2: All channels including pager
            success &= await self._send_pagerduty_alert(alert)
            success &= await self._send_slack_alert(alert, urgent=True)
            success &= await self._create_jira_ticket(alert, priority="Highest")
            
        elif alert.severity == IncidentSeverity.SEV3:
            # SEV3: Slack + Jira
            success &= await self._send_slack_alert(alert, urgent=False)
            success &= await self._create_jira_ticket(alert, priority="High")
            
        else:
            # SEV4/SEV5: Log and optional low-priority ticket
            success &= await self._send_slack_alert(alert, urgent=False)
            if alert.severity == IncidentSeverity.SEV4:
                success &= await self._create_jira_ticket(alert, priority="Medium")
        
        return success
    
    async def _send_pagerduty_alert(self, alert: Alert) -> bool:
        """Send alert to PagerDuty via webhook"""
        if AlertChannel.PAGERDUTY not in self.alert_channels:
            return True  # Not configured, consider successful
            
        webhook_url = self.alert_channels[AlertChannel.PAGERDUTY].get("url")
        if not webhook_url:
            return False
            
        payload = {
            "routing_key": self.alert_channels[AlertChannel.PAGERDUTY].get("routing_key"),
            "event_action": "trigger",
            "dedup_key": alert.deduplication_key,
            "payload": {
                "summary": alert.title,
                "source": alert.source,
                "severity": alert.severity.value,
                "timestamp": alert.timestamp,
                "custom_details": alert.context
            }
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as response:
                    return response.status == 202
        except Exception:
            return False
    
    async def _send_slack_alert(self, alert: Alert, urgent: bool = False) -> bool:
        """Send alert to Slack"""
        if AlertChannel.SLACK not in self.alert_channels:
            return True
            
        webhook_url = self.alert_channels[AlertChannel.SLACK].get("webhook_url")
        if not webhook_url:
            return False
            
        # Color coding based on severity
        color_map = {
            IncidentSeverity.SEV1: "#FF0000",  # Red
            IncidentSeverity.SEV2: "#FF6B00",  # Orange
            IncidentSeverity.SEV3: "#FFD700",  # Yellow
            IncidentSeverity.SEV4: "#1E90FF",  # Blue
            IncidentSeverity.SEV5: "#808080"   # Gray
        }
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{ '🚨' if urgent else '⚠️' } {alert.title}"
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Severity:*\n{alert.severity.value.upper()}"},
                    {"type": "mrkdwn", "text": f"*Source:*\n{alert.source}"},
                    {"type": "mrkdwn", "text": f"*Time:*\n{alert.timestamp}"}
                ]
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": alert.description}
            }
        ]
        
        # Add context if available
        if alert.context:
            context_text = "\n".join([f"• {k}: {v}" for k, v in alert.context.items()])
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Context:*\n{context_text}"}
            })
        
        payload = {
            "blocks": blocks,
            "attachments": [{"color": color_map.get(alert.severity, "#808080")}]
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as response:
                    return response.status == 200
        except Exception:
            return False
    
    async def _create_jira_ticket(self, alert: Alert, priority: str = "Medium") -> bool:
        """Create JIRA ticket for tracking"""
        if AlertChannel.JIRA not in self.alert_channels:
            return True
            
        jira_config = self.alert_channels[AlertChannel.JIRA]
        
        # Map our severity to JIRA priority
        priority_map = {
            "Highest": "1",
            "High": "2", 
            "Medium": "3",
            "Low": "4",
            "Lowest": "5"
        }
        
        payload = {
            "fields": {
                "project": {"key": jira_config.get("project_key", "AI")},
                "summary": f"[AI Daemon] {alert.title}",
                "description": f"{alert.description}\n\n*Context:*\n{json.dumps(alert.context, indent=2)}",
                "issuetype": {"name": "Bug"},
                "priority": {"id": priority_map.get(priority, "3")},
                "labels": ["ai-daemon", "auto-generated", alert.severity.value],
                "customfield_10001": alert.deduplication_key  # Epic Link or similar
            }
        }
        
        try:
            auth = aiohttp.BasicAuth(
                jira_config.get("username"),
                jira_config.get("password")
            )
            
            async with aiohttp.ClientSession(auth=auth) as session:
                url = f"{jira_config['base_url']}/rest/api/2/issue"
                async with session.post(url, json=payload) as response:
                    return response.status in [200, 201]
        except Exception:
            return False
    
    def _clean_old_alerts(self):
        """Clean old deduplication keys to prevent memory leaks"""
        current_time = asyncio.get_event_loop().time()
        old_keys = [
            key for key, timestamp in self.sent_alerts.items()
            if current_time - timestamp > 3600  # 1 hour retention
        ]
        for key in old_keys:
            del self.sent_alerts[key]
    
    def create_alert_from_log(self, 
                            log_severity: LogSeverity,
                            incident_severity: IncidentSeverity,
                            title: str,
                            description: str,
                            source: str,
                            context: Dict[str, Any] = None) -> Alert:
        """Create alert from log event"""
        timestamp = datetime.now(timezone.utc).isoformat()
        deduplication_key = f"{source}_{title}_{timestamp}"
        
        return Alert(
            title=title,
            description=description,
            severity=incident_severity,
            source=source,
            timestamp=timestamp,
            context=context or {},
            deduplication_key=deduplication_key
        )
