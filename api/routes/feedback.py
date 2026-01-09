"""
Feedback Endpoint

Submit and view feedback on agent responses.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from datetime import datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.feedback import (
    get_feedback_collector,
    FeedbackRating,
    FeedbackCategory,
)


router = APIRouter()


# =============================================================================
# MODELS
# =============================================================================

class FeedbackSubmission(BaseModel):
    """Request body for submitting feedback."""
    agent_name: str = Field(..., description="Name of the agent")
    rating: int = Field(..., ge=1, le=5, description="Rating from 1-5")
    category: str = Field(
        "response_quality",
        description="Category: response_quality, agent_selection, speed, accuracy, helpfulness, other"
    )
    task_id: Optional[str] = None
    session_id: Optional[str] = None
    comment: Optional[str] = None
    suggestions: Optional[str] = None


class FeedbackInfo(BaseModel):
    """Information about feedback."""
    id: str
    agent_name: str
    rating: int
    category: str
    comment: Optional[str]
    suggestions: Optional[str]
    created_at: datetime
    task_id: Optional[str]
    session_id: Optional[str]


class FeedbackListResponse(BaseModel):
    """Response for listing feedback."""
    feedback: List[FeedbackInfo]
    count: int


class FeedbackSummaryResponse(BaseModel):
    """Response for feedback summary."""
    total_count: int
    average_rating: float
    ratings_distribution: Dict[str, int]
    by_category: Dict[str, float]
    by_agent: Dict[str, float]


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/feedback")
async def submit_feedback(submission: FeedbackSubmission):
    """
    Submit feedback for an agent response.
    
    Use this to rate the quality of responses and suggest improvements.
    """
    collector = get_feedback_collector()
    
    # Parse rating
    try:
        rating = FeedbackRating(submission.rating)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid rating: {submission.rating}. Must be 1-5."
        )
        
    # Parse category
    try:
        category = FeedbackCategory(submission.category)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category: {submission.category}"
        )
        
    feedback_id = collector.submit_feedback(
        agent_name=submission.agent_name,
        rating=rating,
        category=category,
        task_id=submission.task_id,
        session_id=submission.session_id,
        comment=submission.comment,
        suggestions=submission.suggestions,
    )
    
    return {
        "id": feedback_id,
        "status": "submitted",
        "message": "Thank you for your feedback!",
    }


@router.get("/feedback", response_model=FeedbackListResponse)
async def list_feedback(
    limit: int = 100,
    agent_name: Optional[str] = None,
):
    """
    List feedback with optional filtering.
    
    Args:
        limit: Maximum number of feedback items to return
        agent_name: Filter by agent name
    """
    collector = get_feedback_collector()
    
    if agent_name:
        feedback = collector.get_feedback_for_agent(agent_name)
    else:
        feedback = collector.get_recent_feedback(limit)
        
    result = []
    for f in feedback[:limit]:
        result.append(FeedbackInfo(
            id=f.id,
            agent_name=f.agent_name,
            rating=f.rating.value,
            category=f.category.value,
            comment=f.comment,
            suggestions=f.suggestions,
            created_at=f.created_at,
            task_id=f.task_id,
            session_id=f.session_id,
        ))
        
    return FeedbackListResponse(feedback=result, count=len(result))


@router.get("/feedback/summary", response_model=FeedbackSummaryResponse)
async def get_feedback_summary(agent_name: Optional[str] = None):
    """
    Get feedback summary statistics.
    
    Args:
        agent_name: Optional filter by agent
    """
    collector = get_feedback_collector()
    summary = collector.get_summary(agent_name=agent_name)
    
    return FeedbackSummaryResponse(
        total_count=summary.total_count,
        average_rating=summary.average_rating,
        ratings_distribution={str(k): v for k, v in summary.ratings_distribution.items()},
        by_category=summary.by_category,
        by_agent=summary.by_agent,
    )


@router.get("/feedback/best-agent")
async def get_best_performing_agent():
    """Get the best performing agent based on feedback."""
    collector = get_feedback_collector()
    best = collector.get_best_performing_agent()
    
    if not best:
        return {"best_agent": None, "message": "No feedback available yet"}
        
    summary = collector.get_summary(agent_name=best)
    
    return {
        "best_agent": best,
        "average_rating": summary.average_rating,
        "feedback_count": summary.total_count,
    }
