"""
LastAgent Decision Logger

Logs all decisions made by LastAgent for audit trail and analysis.
Designed to integrate with seedGPT's decision logging patterns.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import json
import uuid


class DecisionType(Enum):
    """Types of decisions that can be logged."""
    # LastAgent-specific decision types
    AGENT_SELECTION = "AGENT_SELECTION"
    AGENT_EXECUTION = "AGENT_EXECUTION"
    INTER_AGENT_CALL = "INTER_AGENT_CALL"
    APPROVAL_REQUEST = "APPROVAL_REQUEST"
    APPROVAL_RESPONSE = "APPROVAL_RESPONSE"
    
    # General decision types (seedGPT compatibility)
    TASK_PRIORITIZATION = "TASK_PRIORITIZATION"
    CODE_GENERATION = "CODE_GENERATION"
    DEPLOYMENT = "DEPLOYMENT"
    RESOURCE_ALLOCATION = "RESOURCE_ALLOCATION"


class DecisionStatus(Enum):
    """Status of a decision."""
    PENDING = "pending"
    EXECUTED = "executed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Alternative:
    """An alternative option that was considered."""
    name: str
    score: float
    reason: str


@dataclass
class Decision:
    """A logged decision."""
    id: str
    decision_type: DecisionType
    title: str
    reasoning: str
    confidence_score: float
    risk_level: str
    agent: str
    status: DecisionStatus = DecisionStatus.PENDING
    alternatives_considered: List[Alternative] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    outcome_status: Optional[str] = None
    outcome_data: Optional[Dict[str, Any]] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    task_id: Optional[str] = None
    session_id: Optional[str] = None


@dataclass
class DecisionStats:
    """Statistics about decisions."""
    total_decisions: int
    decisions_by_type: Dict[str, int]
    decisions_by_status: Dict[str, int]
    average_confidence: float
    success_rate: float


class DecisionLogger:
    """
    Logs decisions for audit trail and analysis.
    
    Designed for integration with seedGPT's decision logging patterns.
    
    Usage:
        logger = DecisionLogger(agent_type="lastagent")
        
        decision_id = logger.log_decision(
            decision_type=DecisionType.AGENT_SELECTION,
            title="Selected Claude for coding task",
            reasoning="Claude has strong coding capabilities",
            confidence_score=0.92,
            risk_level="low",
            alternatives=[
                Alternative("gemini", 0.85, "Good but less focused on code"),
                Alternative("gpt", 0.80, "General purpose"),
            ],
        )
        
        # Later, update outcome
        logger.update_outcome(
            decision_id,
            status=DecisionStatus.EXECUTED,
            outcome_status="success",
            outcome_data={"response_length": 1500},
        )
    """
    
    def __init__(
        self,
        agent_type: str = "lastagent",
        project_id: Optional[str] = None,
        persist_to_file: bool = False,
        file_path: Optional[str] = None,
    ):
        """
        Initialize the decision logger.
        
        Args:
            agent_type: Type of agent logging decisions
            project_id: Optional project ID for grouping
            persist_to_file: Whether to persist to file
            file_path: Path to persist decisions
        """
        self.agent_type = agent_type
        self.project_id = project_id
        self.persist_to_file = persist_to_file
        self.file_path = file_path or ".agents/decisions.jsonl"
        
        self._decisions: Dict[str, Decision] = {}
        
    def log_decision(
        self,
        decision_type: DecisionType,
        title: str,
        reasoning: str,
        confidence_score: float,
        risk_level: str = "low",
        alternatives: Optional[List[Alternative]] = None,
        context: Optional[Dict[str, Any]] = None,
        task_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> str:
        """
        Log a decision.
        
        Returns:
            Decision ID
        """
        decision = Decision(
            id=str(uuid.uuid4()),
            decision_type=decision_type,
            title=title,
            reasoning=reasoning,
            confidence_score=confidence_score,
            risk_level=risk_level,
            agent=self.agent_type,
            alternatives_considered=alternatives or [],
            context=context or {},
            task_id=task_id,
            session_id=session_id,
        )
        
        self._decisions[decision.id] = decision
        
        if self.persist_to_file:
            self._persist_decision(decision)
            
        return decision.id
        
    def update_outcome(
        self,
        decision_id: str,
        status: DecisionStatus,
        outcome_status: str,
        outcome_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Update the outcome of a decision.
        
        Args:
            decision_id: ID of the decision
            status: New status
            outcome_status: Outcome status (e.g., "success", "failure")
            outcome_data: Additional outcome data
        """
        decision = self._decisions.get(decision_id)
        if not decision:
            raise ValueError(f"Decision not found: {decision_id}")
            
        decision.status = status
        decision.outcome_status = outcome_status
        decision.outcome_data = outcome_data
        decision.updated_at = datetime.utcnow()
        
        if self.persist_to_file:
            self._persist_decision(decision)
            
    def get_decision(self, decision_id: str) -> Optional[Decision]:
        """Get a decision by ID."""
        return self._decisions.get(decision_id)
        
    def get_decisions(
        self,
        limit: int = 100,
        decision_type: Optional[DecisionType] = None,
        status: Optional[DecisionStatus] = None,
    ) -> List[Decision]:
        """
        Get decisions with optional filtering.
        
        Args:
            limit: Maximum number to return
            decision_type: Filter by type
            status: Filter by status
            
        Returns:
            List of decisions
        """
        decisions = list(self._decisions.values())
        
        if decision_type:
            decisions = [d for d in decisions if d.decision_type == decision_type]
        if status:
            decisions = [d for d in decisions if d.status == status]
            
        # Sort by created_at descending
        decisions.sort(key=lambda d: d.created_at, reverse=True)
        
        return decisions[:limit]
        
    def get_decisions_for_task(self, task_id: str) -> List[Decision]:
        """Get all decisions for a specific task."""
        return [d for d in self._decisions.values() if d.task_id == task_id]
        
    def get_decisions_for_session(self, session_id: str) -> List[Decision]:
        """Get all decisions for a specific session."""
        return [d for d in self._decisions.values() if d.session_id == session_id]
        
    def get_stats(self) -> DecisionStats:
        """Get statistics about logged decisions."""
        decisions = list(self._decisions.values())
        
        if not decisions:
            return DecisionStats(
                total_decisions=0,
                decisions_by_type={},
                decisions_by_status={},
                average_confidence=0.0,
                success_rate=0.0,
            )
            
        # Count by type
        by_type: Dict[str, int] = {}
        for d in decisions:
            type_name = d.decision_type.value
            by_type[type_name] = by_type.get(type_name, 0) + 1
            
        # Count by status
        by_status: Dict[str, int] = {}
        for d in decisions:
            status_name = d.status.value
            by_status[status_name] = by_status.get(status_name, 0) + 1
            
        # Calculate averages
        avg_confidence = sum(d.confidence_score for d in decisions) / len(decisions)
        
        # Calculate success rate
        executed = [d for d in decisions if d.status == DecisionStatus.EXECUTED]
        successful = [d for d in executed if d.outcome_status == "success"]
        success_rate = len(successful) / len(executed) if executed else 0.0
        
        return DecisionStats(
            total_decisions=len(decisions),
            decisions_by_type=by_type,
            decisions_by_status=by_status,
            average_confidence=round(avg_confidence, 3),
            success_rate=round(success_rate, 3),
        )
        
    def _persist_decision(self, decision: Decision) -> None:
        """Persist a decision to file."""
        import os
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        
        # Convert to dict for JSON serialization
        data = {
            "id": decision.id,
            "decision_type": decision.decision_type.value,
            "title": decision.title,
            "reasoning": decision.reasoning,
            "confidence_score": decision.confidence_score,
            "risk_level": decision.risk_level,
            "agent": decision.agent,
            "status": decision.status.value,
            "alternatives": [
                {"name": a.name, "score": a.score, "reason": a.reason}
                for a in decision.alternatives_considered
            ],
            "context": decision.context,
            "outcome_status": decision.outcome_status,
            "outcome_data": decision.outcome_data,
            "created_at": decision.created_at.isoformat(),
            "updated_at": decision.updated_at.isoformat() if decision.updated_at else None,
            "task_id": decision.task_id,
            "session_id": decision.session_id,
        }
        
        with open(self.file_path, "a") as f:
            f.write(json.dumps(data) + "\n")


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_decision_logger = None


def get_decision_logger(agent_type: str = "lastagent") -> DecisionLogger:
    """Get the global decision logger instance."""
    global _decision_logger
    if _decision_logger is None:
        _decision_logger = DecisionLogger(agent_type=agent_type)
    return _decision_logger
