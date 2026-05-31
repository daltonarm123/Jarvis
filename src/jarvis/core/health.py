"""Agent health monitoring and issue tracking."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import time


@dataclass
class AgentIssue:
    agent_name: str
    issue_type: str  # "error", "timeout", "hallucination", "performance"
    description: str
    timestamp: float = field(default_factory=time.time)
    context: Dict[str, Any] = field(default_factory=dict)
    severity: str = "medium"  # "low", "medium", "high", "critical"
    resolved: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent": self.agent_name,
            "type": self.issue_type,
            "description": self.description,
            "timestamp": self.timestamp,
            "severity": self.severity,
            "resolved": self.resolved,
        }


class HealthMonitor:
    """Track agent health and issues."""

    def __init__(self) -> None:
        self.issues: List[AgentIssue] = []
        self.error_counts: Dict[str, int] = {}
        self.last_success: Dict[str, float] = {}

    def record_error(
        self,
        agent_name: str,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
    ) -> AgentIssue:
        """Log an agent error."""
        self.error_counts[agent_name] = self.error_counts.get(agent_name, 0) + 1
        severity = "critical" if self.error_counts[agent_name] > 3 else "high"

        issue = AgentIssue(
            agent_name=agent_name,
            issue_type="error",
            description=f"{type(error).__name__}: {str(error)}",
            context=context or {},
            severity=severity,
        )
        self.issues.append(issue)
        return issue

    def record_success(self, agent_name: str) -> None:
        """Mark successful agent execution."""
        self.last_success[agent_name] = time.time()
        self.error_counts[agent_name] = 0

    def get_unresolved_issues(self) -> List[AgentIssue]:
        """Get all unresolved issues."""
        return [i for i in self.issues if not i.resolved]

    def get_critical_issues(self) -> List[AgentIssue]:
        """Get critical/high severity unresolved issues."""
        return [
            i
            for i in self.issues
            if not i.resolved and i.severity in ("critical", "high")
        ]

    def resolve_issue(self, issue_index: int) -> bool:
        """Mark an issue as resolved."""
        if 0 <= issue_index < len(self.issues):
            self.issues[issue_index].resolved = True
            return True
        return False

    def format_issues_for_dev(self) -> str:
        """Format issues for dev agent analysis."""
        issues = self.get_critical_issues()
        if not issues:
            return "No critical issues detected."

        lines = ["Critical Agent Issues Detected:\n"]
        for i, issue in enumerate(issues, 1):
            lines.append(f"{i}. [{issue.severity.upper()}] {issue.agent_name}")
            lines.append(f"   Type: {issue.issue_type}")
            lines.append(f"   Issue: {issue.description}")
            if issue.context:
                lines.append(f"   Context: {issue.context}")
            lines.append("")
        return "\n".join(lines)
