"""
LastAgent Approval Workflow

Manages human-in-the-loop approval for agent actions.
Supports multiple approval modes:
- AUTO: No approval needed
- APPROVE_ALL: Every action requires approval
- APPROVE_HIGH_RISK: Only high-risk actions require approval
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
import uuid


class ApprovalMode(Enum):
    """Approval mode settings."""
    AUTO = "AUTO"
    APPROVE_ALL = "APPROVE_ALL"
    APPROVE_HIGH_RISK = "APPROVE_HIGH_RISK"


class ApprovalStatus(Enum):
    """Status of an approval request."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    TIMEOUT = "timeout"


class RiskLevel(Enum):
    """Risk level of an action."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# High-risk operations that require approval in APPROVE_HIGH_RISK mode
HIGH_RISK_OPERATIONS = {
    "file_deletion",
    "git_push",
    "deployment",
    "database_modification",
    "external_api_mutation",
    "payment_processing",
    "user_data_access",
    "configuration_change",
}


@dataclass
class ApprovalRequest:
    """A request for human approval."""
    id: str
    action_type: str
    title: str
    description: str
    agent_name: str
    risk_level: RiskLevel
    details: Dict[str, Any] = field(default_factory=dict)
    status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    resolution_reason: Optional[str] = None


@dataclass
class ApprovalResponse:
    """Response to an approval request."""
    request_id: str
    approved: bool
    reason: Optional[str] = None
    responder: str = "user"
    timestamp: datetime = field(default_factory=datetime.utcnow)


class ApprovalManager:
    """
    Manages approval workflows for agent actions.
    
    Usage:
        manager = ApprovalManager(mode=ApprovalMode.APPROVE_HIGH_RISK)
        
        # Check if approval is needed
        if manager.requires_approval("git_push", RiskLevel.HIGH):
            request = manager.create_request(
                action_type="git_push",
                title="Push to main branch",
                description="Push changes to main branch",
                agent_name="aider",
                risk_level=RiskLevel.HIGH,
            )
            
            # Wait for approval (in a real system, this would be async)
            response = manager.auto_approve(request)  # or get_user_approval()
            
            if response.approved:
                # Proceed with action
                pass
    """
    
    def __init__(
        self,
        mode: ApprovalMode = ApprovalMode.AUTO,
        approval_handler: Optional[Callable[[ApprovalRequest], ApprovalResponse]] = None,
    ):
        """
        Initialize the approval manager.
        
        Args:
            mode: Approval mode to use
            approval_handler: Optional custom handler for approvals
        """
        self.mode = mode
        self._approval_handler = approval_handler
        self._pending_requests: Dict[str, ApprovalRequest] = {}
        self._completed_requests: List[ApprovalRequest] = []
        
    def requires_approval(self, action_type: str, risk_level: RiskLevel) -> bool:
        """
        Check if an action requires approval.
        
        Args:
            action_type: Type of action (e.g., "git_push", "file_deletion")
            risk_level: Risk level of the action
            
        Returns:
            True if approval is required
        """
        if self.mode == ApprovalMode.AUTO:
            return False
        elif self.mode == ApprovalMode.APPROVE_ALL:
            return True
        elif self.mode == ApprovalMode.APPROVE_HIGH_RISK:
            return (
                action_type in HIGH_RISK_OPERATIONS or
                risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
            )
        return False
        
    def create_request(
        self,
        action_type: str,
        title: str,
        description: str,
        agent_name: str,
        risk_level: RiskLevel,
        details: Optional[Dict[str, Any]] = None,
    ) -> ApprovalRequest:
        """
        Create an approval request.
        
        Args:
            action_type: Type of action
            title: Human-readable title
            description: Detailed description
            agent_name: Agent requesting approval
            risk_level: Risk level
            details: Additional details
            
        Returns:
            The created ApprovalRequest
        """
        request = ApprovalRequest(
            id=str(uuid.uuid4()),
            action_type=action_type,
            title=title,
            description=description,
            agent_name=agent_name,
            risk_level=risk_level,
            details=details or {},
        )
        self._pending_requests[request.id] = request
        return request
        
    def resolve_request(
        self,
        request_id: str,
        approved: bool,
        reason: Optional[str] = None,
        responder: str = "user",
    ) -> ApprovalResponse:
        """
        Resolve an approval request.
        
        Args:
            request_id: ID of the request
            approved: Whether to approve
            reason: Optional reason
            responder: Who resolved it
            
        Returns:
            ApprovalResponse
        """
        request = self._pending_requests.get(request_id)
        if not request:
            raise ValueError(f"Request not found: {request_id}")
            
        # Update request status
        request.status = ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED
        request.resolved_at = datetime.utcnow()
        request.resolution_reason = reason
        
        # Move to completed
        del self._pending_requests[request_id]
        self._completed_requests.append(request)
        
        return ApprovalResponse(
            request_id=request_id,
            approved=approved,
            reason=reason,
            responder=responder,
        )
        
    def auto_approve(self, request: ApprovalRequest, reason: str = "Auto-approved") -> ApprovalResponse:
        """Auto-approve a request (for AUTO mode)."""
        return self.resolve_request(request.id, approved=True, reason=reason, responder="system")
        
    def auto_reject(self, request: ApprovalRequest, reason: str = "Auto-rejected") -> ApprovalResponse:
        """Auto-reject a request."""
        return self.resolve_request(request.id, approved=False, reason=reason, responder="system")
        
    def get_pending_requests(self) -> List[ApprovalRequest]:
        """Get all pending approval requests."""
        return list(self._pending_requests.values())
        
    def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        """Get a request by ID."""
        return self._pending_requests.get(request_id)
        
    def get_completed_requests(self, limit: int = 100) -> List[ApprovalRequest]:
        """Get completed requests."""
        return self._completed_requests[-limit:]
        
    def set_mode(self, mode: ApprovalMode) -> None:
        """Change the approval mode."""
        self.mode = mode
        
    def classify_risk(self, action_type: str, details: Dict[str, Any]) -> RiskLevel:
        """
        Classify the risk level of an action.
        
        Args:
            action_type: Type of action
            details: Action details
            
        Returns:
            RiskLevel classification
        """
        # Critical operations
        if action_type in ["deployment", "payment_processing", "user_data_access"]:
            return RiskLevel.CRITICAL
            
        # High risk operations
        if action_type in HIGH_RISK_OPERATIONS:
            return RiskLevel.HIGH
            
        # Check for specific risk indicators
        if details.get("destructive", False):
            return RiskLevel.HIGH
        if details.get("external", False):
            return RiskLevel.MEDIUM
            
        return RiskLevel.LOW


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_approval_manager = None


def get_approval_manager(mode: ApprovalMode = ApprovalMode.AUTO) -> ApprovalManager:
    """Get the global approval manager instance."""
    global _approval_manager
    if _approval_manager is None:
        _approval_manager = ApprovalManager(mode=mode)
    return _approval_manager
