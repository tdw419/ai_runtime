import json
import logging
import sys
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum

class LogSeverity(Enum):
    EMERGENCY = 0
    ALERT = 1
    CRITICAL = 2
    ERROR = 3
    WARNING = 4
    NOTICE = 5
    INFO = 6
    DEBUG = 7

class IncidentSeverity(Enum):
    SEV1 = "critical"
    SEV2 = "high" 
    SEV3 = "medium"
    SEV4 = "low"
    SEV5 = "info"

@dataclass
class ECSBase:
    """Elastic Common Schema base fields"""
    timestamp: str
    log_level: str
    message: str
    service_name: str = "ai_system_daemon"
    service_version: str = "1.0.0"
    
    def to_dict(self):
        return {
            "@timestamp": self.timestamp,
            "log": {"level": self.log_level},
            "message": self.message,
            "service": {
                "name": self.service_name,
                "version": self.service_version,
                "type": "system_daemon"
            }
        }

@dataclass
class SecurityFinding:
    """AWS Security Finding Format compatible security event"""
    # Fields from ECSBase without default
    timestamp: str
    log_level: str
    message: str
    # Fields from SecurityFinding without default
    finding_id: str
    severity: str
    risk_score: float
    # Fields from ECSBase with default
    service_name: str = "ai_system_daemon"
    service_version: str = "1.0.0"
    # Fields from SecurityFinding with default
    resource_type: str = "Process"
    resource_name: str = "ai_daemon"

    def to_dict(self):
        return {
            "@timestamp": self.timestamp,
            "log": {"level": self.log_level},
            "message": self.message,
            "service": {
                "name": self.service_name,
                "version": self.service_version,
                "type": "system_daemon"
            }
        }

    def to_asff(self):
        base = self.to_dict()
        base.update({
            "SchemaVersion": "2018-10-08",
            "Id": self.finding_id,
            "ProductArn": f"arn:aws:securityhub:region:account:product/company/ai-daemon",
            "GeneratorId": "ai-daemon-security-scanner",
            "AwsAccountId": "123456789012",  # Would be configured
            "Types": ["Software and Configuration Checks/Security Best Practices"],
            "CreatedAt": self.timestamp,
            "UpdatedAt": self.timestamp,
            "Severity": {
                "Label": self.severity.upper(),
                "Original": str(self.risk_score)
            },
            "Resources": [{
                "Type": self.resource_type,
                "Id": self.resource_name
            }],
            "Workflow": {"Status": "NEW"},
            "RecordState": "ACTIVE"
        })
        return base

class StructuredLogger:
    """High-assurance structured logging with ECS/ASFF compliance"""
    
    def __init__(self, config):
        self.config = config
        self.logger = self._setup_logger()
        self.incident_map = self._setup_severity_mapping()
        
    def _setup_logger(self):
        """Configure structured JSON logging"""
        logger = logging.getLogger('ai_daemon_structured')
        logger.setLevel(logging.INFO)
        logger.propagate = False
        
        # JSON formatter for ECS compliance
        class ECSFormatter(logging.Formatter):
            def format(self, record):
                log_entry = {
                    "@timestamp": datetime.now(timezone.utc).isoformat(),
                    "log.level": record.levelname,
                    "message": record.getMessage(),
                    "process": {"pid": record.process},
                    "thread": {"id": record.thread},
                    "log": {"logger": record.name},
                    "ecs": {"version": "1.6.0"}
                }
                
                # Add extra fields if present
                if hasattr(record, 'extra_fields'):
                    log_entry.update(record.extra_fields)
                    
                return json.dumps(log_entry)
        
        # Console handler for development
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(ECSFormatter())
        logger.addHandler(console_handler)
        
        # File handler for production
        file_handler = logging.FileHandler('logs/structured_daemon.log')
        file_handler.setFormatter(ECSFormatter())
        logger.addHandler(file_handler)
        
        return logger
    
    def _setup_severity_mapping(self) -> Dict[LogSeverity, IncidentSeverity]:
        """Map internal log levels to incident response tiers"""
        return {
            LogSeverity.EMERGENCY: IncidentSeverity.SEV1,
            LogSeverity.ALERT: IncidentSeverity.SEV1,
            LogSeverity.CRITICAL: IncidentSeverity.SEV2,
            LogSeverity.ERROR: IncidentSeverity.SEV3,
            LogSeverity.WARNING: IncidentSeverity.SEV4,
            LogSeverity.NOTICE: IncidentSeverity.SEV5,
            LogSeverity.INFO: IncidentSeverity.SEV5,
            LogSeverity.DEBUG: IncidentSeverity.SEV5
        }
    
    def log_security_event(self, severity, message, finding_id, risk_score, context=None):
        """Log security event with ASFF compliance - simplified signature"""
        timestamp = datetime.now(timezone.utc).isoformat()
        
        security_finding = SecurityFinding(
            timestamp=timestamp,
            log_level=severity.name.lower(),
            message=message,
            finding_id=finding_id,
            severity=self.incident_map[severity].value,
            risk_score=risk_score
        )
        
        # Log as both ECS and ASFF
        ecs_entry = security_finding.to_dict()
        asff_entry = security_finding.to_asff()
        
        if context:
            ecs_entry.update({"event": context})
            asff_entry.update({"Note": json.dumps(context)})
        
        # Log to structured logger with extra fields
        log_method = getattr(self.logger, severity.name.lower())
        log_method(message, extra={'extra_fields': ecs_entry})
        
        # Also write ASFF format to security-specific log
        self._write_security_finding(asff_entry)
    
    def _write_security_finding(self, finding: Dict):
        """Write security finding to dedicated security log"""
        try:
            with open('logs/security_findings.jsonl', 'a') as f:
                f.write(json.dumps(finding) + '\n')
        except Exception as e:
            self.logger.error(f"Failed to write security finding: {e}")
    
    def log_performance_event(self,
                            severity: LogSeverity,
                            message: str,
                            metrics: Dict[str, Any],
                            context: Dict[str, Any] = None):
        """Log performance event with structured metrics"""
        timestamp = datetime.now(timezone.utc).isoformat()
        
        base_event = ECSBase(
            timestamp=timestamp,
            log_level=severity.name.lower(),
            message=message
        )
        
        event_data = base_event.to_dict()
        event_data.update({
            "event": {
                "category": ["performance"],
                "type": ["metrics"],
                "dataset": "ai_daemon.performance"
            },
            "metrics": metrics
        })
        
        if context:
            event_data["event"].update(context)
        
        log_method = getattr(self.logger, severity.name.lower())
        log_method(message, extra={'extra_fields': event_data})
    
    def log_system_operation(self,
                           severity: LogSeverity,
                           message: str,
                           operation: str,
                           resource: str,
                           outcome: str,
                           context: Dict[str, Any] = None):
        """Log system operation for audit trail"""
        timestamp = datetime.now(timezone.utc).isoformat()
        
        base_event = ECSBase(
            timestamp=timestamp,
            log_level=severity.name.lower(),
            message=message
        )
        
        event_data = base_event.to_dict()
        event_data.update({
            "event": {
                "category": ["system"],
                "type": ["operation"],
                "action": operation,
                "outcome": outcome
            },
            "resource": {"name": resource},
            "user": {"name": "ai_daemon"}  # Would be actual user in real system
        })
        
        if context:
            event_data["event"].update(context)
        
        log_method = getattr(self.logger, severity.name.lower())
        log_method(message, extra={'extra_fields': event_data})
    
    def get_incident_severity(self, log_severity: LogSeverity) -> IncidentSeverity:
        """Map log severity to incident response tier"""
        return self.incident_map[log_severity]
