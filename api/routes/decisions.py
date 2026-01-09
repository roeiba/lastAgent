"""
Decisions Endpoint

View and manage decision history.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from datetime import datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.decision_log import get_decision_logger, DecisionType, DecisionStatus


router = APIRouter()


# =============================================================================
# MODELS
# =============================================================================

class AlternativeInfo(BaseModel):
    """Information about a considered alternative."""
    name: str
    score: float
    reason: str


class DecisionInfo(BaseModel):
    """Information about a decision."""
    id: str
    decision_type: str
    title: str
    reasoning: str
    confidence_score: float
    risk_level: str
    agent: str
    status: str
    alternatives_considered: List[AlternativeInfo]
    outcome_status: Optional[str]
    created_at: datetime
    task_id: Optional[str]
    session_id: Optional[str]


class DecisionsListResponse(BaseModel):
    """Response for listing decisions."""
    decisions: List[DecisionInfo]
    count: int


class DecisionStatsResponse(BaseModel):
    """Response for decision statistics."""
    total_decisions: int
    decisions_by_type: Dict[str, int]
    decisions_by_status: Dict[str, int]
    average_confidence: float
    success_rate: float


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/decisions", response_model=DecisionsListResponse)
async def list_decisions(
    limit: int = 100,
    decision_type: Optional[str] = None,
    status: Optional[str] = None,
):
    """
    List decisions with optional filtering.
    
    Args:
        limit: Maximum number of decisions to return
        decision_type: Filter by decision type
        status: Filter by status
    """
    logger = get_decision_logger()
    
    # Parse filters
    dt = None
    if decision_type:
        try:
            dt = DecisionType(decision_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid decision_type: {decision_type}"
            )
            
    s = None
    if status:
        try:
            s = DecisionStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
            
    decisions = logger.get_decisions(limit=limit, decision_type=dt, status=s)
    
    result = []
    for d in decisions:
        result.append(DecisionInfo(
            id=d.id,
            decision_type=d.decision_type.value,
            title=d.title,
            reasoning=d.reasoning,
            confidence_score=d.confidence_score,
            risk_level=d.risk_level,
            agent=d.agent,
            status=d.status.value,
            alternatives_considered=[
                AlternativeInfo(name=a.name, score=a.score, reason=a.reason)
                for a in d.alternatives_considered
            ],
            outcome_status=d.outcome_status,
            created_at=d.created_at,
            task_id=d.task_id,
            session_id=d.session_id,
        ))
        
    return DecisionsListResponse(decisions=result, count=len(result))


@router.get("/decisions/stats", response_model=DecisionStatsResponse)
async def get_decision_stats():
    """Get statistics about decisions."""
    logger = get_decision_logger()
    stats = logger.get_stats()
    
    return DecisionStatsResponse(
        total_decisions=stats.total_decisions,
        decisions_by_type=stats.decisions_by_type,
        decisions_by_status=stats.decisions_by_status,
        average_confidence=stats.average_confidence,
        success_rate=stats.success_rate,
    )


@router.get("/decisions/{decision_id}", response_model=DecisionInfo)
async def get_decision(decision_id: str):
    """Get a specific decision by ID."""
    logger = get_decision_logger()
    decision = logger.get_decision(decision_id)
    
    if not decision:
        raise HTTPException(status_code=404, detail=f"Decision not found: {decision_id}")
        
    return DecisionInfo(
        id=decision.id,
        decision_type=decision.decision_type.value,
        title=decision.title,
        reasoning=decision.reasoning,
        confidence_score=decision.confidence_score,
        risk_level=decision.risk_level,
        agent=decision.agent,
        status=decision.status.value,
        alternatives_considered=[
            AlternativeInfo(name=a.name, score=a.score, reason=a.reason)
            for a in decision.alternatives_considered
        ],
        outcome_status=decision.outcome_status,
        created_at=decision.created_at,
        task_id=decision.task_id,
        session_id=decision.session_id,
    )
