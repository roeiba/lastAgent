"""
Tests for GodAgent Human Controls (approvals, decision logging, feedback)
"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.approvals import (
    ApprovalManager,
    ApprovalMode,
    ApprovalStatus,
    ApprovalRequest,
    RiskLevel,
    get_approval_manager,
)
from src.decision_log import (
    DecisionLogger,
    DecisionType,
    DecisionStatus,
    Decision,
    Alternative,
    get_decision_logger,
)
from src.feedback import (
    FeedbackCollector,
    FeedbackRating,
    FeedbackCategory,
    get_feedback_collector,
)


class TestApprovalManager:
    """Tests for ApprovalManager."""
    
    @pytest.fixture
    def manager(self):
        return ApprovalManager(mode=ApprovalMode.AUTO)
    
    def test_initialization(self, manager):
        """Test manager initializes correctly."""
        assert manager.mode == ApprovalMode.AUTO
        
    def test_auto_mode_no_approval(self, manager):
        """Test AUTO mode doesn't require approval."""
        requires = manager.requires_approval("git_push", RiskLevel.HIGH)
        assert not requires
        
    def test_approve_all_mode(self):
        """Test APPROVE_ALL mode requires all approvals."""
        manager = ApprovalManager(mode=ApprovalMode.APPROVE_ALL)
        
        requires = manager.requires_approval("simple_task", RiskLevel.LOW)
        assert requires
        
    def test_approve_high_risk_mode(self):
        """Test APPROVE_HIGH_RISK mode."""
        manager = ApprovalManager(mode=ApprovalMode.APPROVE_HIGH_RISK)
        
        # High risk should require approval
        assert manager.requires_approval("deployment", RiskLevel.HIGH)
        assert manager.requires_approval("git_push", RiskLevel.MEDIUM)
        
        # Low risk, non-sensitive should not
        assert not manager.requires_approval("read_file", RiskLevel.LOW)
        
    def test_create_request(self, manager):
        """Test creating an approval request."""
        request = manager.create_request(
            action_type="git_push",
            title="Push to main",
            description="Push changes",
            agent_name="aider",
            risk_level=RiskLevel.HIGH,
        )
        
        assert request.id is not None
        assert request.status == ApprovalStatus.PENDING
        assert request.agent_name == "aider"
        
    def test_resolve_request(self, manager):
        """Test resolving a request."""
        request = manager.create_request(
            action_type="test",
            title="Test",
            description="Test",
            agent_name="claude",
            risk_level=RiskLevel.LOW,
        )
        
        response = manager.resolve_request(request.id, approved=True)
        
        assert response.approved
        assert request.status == ApprovalStatus.APPROVED
        
    def test_get_pending_requests(self, manager):
        """Test getting pending requests."""
        manager.create_request(
            action_type="test",
            title="Test 1",
            description="",
            agent_name="claude",
            risk_level=RiskLevel.LOW,
        )
        
        pending = manager.get_pending_requests()
        assert len(pending) >= 1


class TestDecisionLogger:
    """Tests for DecisionLogger."""
    
    @pytest.fixture
    def logger(self):
        return DecisionLogger(agent_type="godagent")
    
    def test_initialization(self, logger):
        """Test logger initializes correctly."""
        assert logger.agent_type == "godagent"
        
    def test_log_decision(self, logger):
        """Test logging a decision."""
        decision_id = logger.log_decision(
            decision_type=DecisionType.AGENT_SELECTION,
            title="Selected Claude",
            reasoning="Best for coding",
            confidence_score=0.9,
            risk_level="low",
        )
        
        assert decision_id is not None
        
    def test_get_decision(self, logger):
        """Test getting a decision."""
        decision_id = logger.log_decision(
            decision_type=DecisionType.AGENT_EXECUTION,
            title="Executed task",
            reasoning="User requested",
            confidence_score=0.8,
        )
        
        decision = logger.get_decision(decision_id)
        
        assert decision is not None
        assert decision.title == "Executed task"
        
    def test_log_with_alternatives(self, logger):
        """Test logging with alternatives."""
        decision_id = logger.log_decision(
            decision_type=DecisionType.AGENT_SELECTION,
            title="Selected Claude",
            reasoning="Best for coding",
            confidence_score=0.9,
            alternatives=[
                Alternative("gemini", 0.85, "Good for research"),
                Alternative("gpt", 0.80, "General purpose"),
            ],
        )
        
        decision = logger.get_decision(decision_id)
        assert len(decision.alternatives_considered) == 2
        
    def test_update_outcome(self, logger):
        """Test updating decision outcome."""
        decision_id = logger.log_decision(
            decision_type=DecisionType.AGENT_EXECUTION,
            title="Test",
            reasoning="Test",
            confidence_score=0.8,
        )
        
        logger.update_outcome(
            decision_id,
            status=DecisionStatus.EXECUTED,
            outcome_status="success",
            outcome_data={"response_length": 100},
        )
        
        decision = logger.get_decision(decision_id)
        assert decision.status == DecisionStatus.EXECUTED
        assert decision.outcome_status == "success"
        
    def test_get_stats(self, logger):
        """Test getting decision stats."""
        logger.log_decision(
            decision_type=DecisionType.AGENT_SELECTION,
            title="Test 1",
            reasoning="Test",
            confidence_score=0.9,
        )
        logger.log_decision(
            decision_type=DecisionType.AGENT_EXECUTION,
            title="Test 2",
            reasoning="Test",
            confidence_score=0.8,
        )
        
        stats = logger.get_stats()
        
        assert stats.total_decisions >= 2
        assert stats.average_confidence > 0


class TestFeedbackCollector:
    """Tests for FeedbackCollector."""
    
    @pytest.fixture
    def collector(self):
        return FeedbackCollector()
    
    def test_submit_feedback(self, collector):
        """Test submitting feedback."""
        feedback_id = collector.submit_feedback(
            agent_name="claude",
            rating=FeedbackRating.GOOD,
            category=FeedbackCategory.RESPONSE_QUALITY,
            comment="Great response!",
        )
        
        assert feedback_id is not None
        
    def test_get_feedback(self, collector):
        """Test getting feedback."""
        feedback_id = collector.submit_feedback(
            agent_name="gemini",
            rating=FeedbackRating.VERY_GOOD,
            category=FeedbackCategory.HELPFULNESS,
        )
        
        feedback = collector.get_feedback(feedback_id)
        
        assert feedback is not None
        assert feedback.agent_name == "gemini"
        assert feedback.rating == FeedbackRating.VERY_GOOD
        
    def test_get_feedback_for_agent(self, collector):
        """Test getting feedback for an agent."""
        collector.submit_feedback(
            agent_name="claude",
            rating=FeedbackRating.GOOD,
            category=FeedbackCategory.ACCURACY,
        )
        collector.submit_feedback(
            agent_name="claude",
            rating=FeedbackRating.VERY_GOOD,
            category=FeedbackCategory.SPEED,
        )
        
        feedback = collector.get_feedback_for_agent("claude")
        
        assert len(feedback) >= 2
        
    def test_get_summary(self, collector):
        """Test getting feedback summary."""
        collector.submit_feedback(
            agent_name="claude",
            rating=FeedbackRating.GOOD,
            category=FeedbackCategory.RESPONSE_QUALITY,
        )
        collector.submit_feedback(
            agent_name="gemini",
            rating=FeedbackRating.VERY_GOOD,
            category=FeedbackCategory.RESPONSE_QUALITY,
        )
        
        summary = collector.get_summary()
        
        assert summary.total_count >= 2
        assert summary.average_rating > 0
        assert "claude" in summary.by_agent or "gemini" in summary.by_agent


class TestGlobalInstances:
    """Tests for global singleton instances."""
    
    def test_get_approval_manager(self):
        manager = get_approval_manager()
        assert isinstance(manager, ApprovalManager)
        
    def test_get_decision_logger(self):
        logger = get_decision_logger()
        assert isinstance(logger, DecisionLogger)
        
    def test_get_feedback_collector(self):
        collector = get_feedback_collector()
        assert isinstance(collector, FeedbackCollector)
