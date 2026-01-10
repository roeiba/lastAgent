"""
LastAgent Feedback System

Collects user feedback on agent responses and decisions.
Used to improve agent selection and future performance.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


class FeedbackRating(Enum):
    """Rating scale for feedback."""
    VERY_BAD = 1
    BAD = 2
    NEUTRAL = 3
    GOOD = 4
    VERY_GOOD = 5


class FeedbackCategory(Enum):
    """Categories of feedback."""
    RESPONSE_QUALITY = "response_quality"
    AGENT_SELECTION = "agent_selection"
    SPEED = "speed"
    ACCURACY = "accuracy"
    HELPFULNESS = "helpfulness"
    OTHER = "other"


@dataclass
class Feedback:
    """User feedback on a response or decision."""
    id: str
    task_id: Optional[str]
    session_id: Optional[str]
    agent_name: str
    rating: FeedbackRating
    category: FeedbackCategory
    comment: Optional[str] = None
    suggestions: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class FeedbackSummary:
    """Summary statistics for feedback."""
    total_count: int
    average_rating: float
    ratings_distribution: Dict[int, int]
    by_category: Dict[str, float]
    by_agent: Dict[str, float]


class FeedbackCollector:
    """
    Collects and analyzes user feedback.
    
    Usage:
        collector = FeedbackCollector()
        
        # Submit feedback
        collector.submit_feedback(
            task_id="task-123",
            agent_name="claude",
            rating=FeedbackRating.GOOD,
            category=FeedbackCategory.RESPONSE_QUALITY,
            comment="Clear and helpful response",
        )
        
        # Get summary
        summary = collector.get_summary()
        print(f"Average rating: {summary.average_rating}")
    """
    
    def __init__(self):
        """Initialize the feedback collector."""
        self._feedback: Dict[str, Feedback] = {}
        
    def submit_feedback(
        self,
        agent_name: str,
        rating: FeedbackRating,
        category: FeedbackCategory,
        task_id: Optional[str] = None,
        session_id: Optional[str] = None,
        comment: Optional[str] = None,
        suggestions: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Submit feedback.
        
        Returns:
            Feedback ID
        """
        feedback = Feedback(
            id=str(uuid.uuid4()),
            task_id=task_id,
            session_id=session_id,
            agent_name=agent_name,
            rating=rating,
            category=category,
            comment=comment,
            suggestions=suggestions,
            metadata=metadata or {},
        )
        
        self._feedback[feedback.id] = feedback
        return feedback.id
        
    def get_feedback(self, feedback_id: str) -> Optional[Feedback]:
        """Get feedback by ID."""
        return self._feedback.get(feedback_id)
        
    def get_feedback_for_task(self, task_id: str) -> List[Feedback]:
        """Get all feedback for a task."""
        return [f for f in self._feedback.values() if f.task_id == task_id]
        
    def get_feedback_for_agent(self, agent_name: str) -> List[Feedback]:
        """Get all feedback for an agent."""
        return [f for f in self._feedback.values() if f.agent_name == agent_name]
        
    def get_recent_feedback(self, limit: int = 100) -> List[Feedback]:
        """Get recent feedback."""
        feedback = list(self._feedback.values())
        feedback.sort(key=lambda f: f.created_at, reverse=True)
        return feedback[:limit]
        
    def get_summary(
        self,
        agent_name: Optional[str] = None,
        category: Optional[FeedbackCategory] = None,
    ) -> FeedbackSummary:
        """
        Get feedback summary with optional filtering.
        
        Args:
            agent_name: Filter by agent
            category: Filter by category
            
        Returns:
            FeedbackSummary
        """
        feedback = list(self._feedback.values())
        
        if agent_name:
            feedback = [f for f in feedback if f.agent_name == agent_name]
        if category:
            feedback = [f for f in feedback if f.category == category]
            
        if not feedback:
            return FeedbackSummary(
                total_count=0,
                average_rating=0.0,
                ratings_distribution={1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
                by_category={},
                by_agent={},
            )
            
        # Calculate average rating
        ratings = [f.rating.value for f in feedback]
        avg_rating = sum(ratings) / len(ratings)
        
        # Ratings distribution
        distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for f in feedback:
            distribution[f.rating.value] = distribution.get(f.rating.value, 0) + 1
            
        # By category
        by_category: Dict[str, List[int]] = {}
        for f in feedback:
            cat = f.category.value
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(f.rating.value)
        by_category_avg = {
            cat: sum(ratings) / len(ratings)
            for cat, ratings in by_category.items()
        }
        
        # By agent
        by_agent: Dict[str, List[int]] = {}
        for f in feedback:
            if f.agent_name not in by_agent:
                by_agent[f.agent_name] = []
            by_agent[f.agent_name].append(f.rating.value)
        by_agent_avg = {
            agent: sum(ratings) / len(ratings)
            for agent, ratings in by_agent.items()
        }
        
        return FeedbackSummary(
            total_count=len(feedback),
            average_rating=round(avg_rating, 2),
            ratings_distribution=distribution,
            by_category=by_category_avg,
            by_agent=by_agent_avg,
        )
        
    def get_best_performing_agent(self) -> Optional[str]:
        """Get the agent with highest average rating."""
        summary = self.get_summary()
        if not summary.by_agent:
            return None
        return max(summary.by_agent, key=summary.by_agent.get)
        
    def get_improvement_suggestions(self, agent_name: str) -> List[str]:
        """Get improvement suggestions for an agent."""
        feedback = self.get_feedback_for_agent(agent_name)
        return [
            f.suggestions
            for f in feedback
            if f.suggestions and f.rating.value <= 3
        ]


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_feedback_collector = None


def get_feedback_collector() -> FeedbackCollector:
    """Get the global feedback collector instance."""
    global _feedback_collector
    if _feedback_collector is None:
        _feedback_collector = FeedbackCollector()
    return _feedback_collector
