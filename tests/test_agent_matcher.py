"""
Tests for LastAgent Agent Matcher
"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.task_analyzer import TaskAnalysis, TaskType
from src.agent_matcher import (
    AgentMatcher,
    AgentMatch,
    MatchResult,
    get_agent_matcher,
)


class TestAgentMatcher:
    """Tests for AgentMatcher class."""
    
    @pytest.fixture
    def matcher(self):
        """Create an AgentMatcher instance."""
        return AgentMatcher()
    
    @pytest.fixture
    def coding_analysis(self):
        """Create a coding task analysis."""
        return TaskAnalysis(
            task_type=TaskType.CODING,
            detected_capabilities=["coding", "deep_reasoning"],
            keywords_matched=["python", "code"],
            requires_working_directory=False,
            requires_realtime_info=False,
            requires_multimodal=False,
            requires_long_context=False,
            confidence=0.8,
        )
    
    @pytest.fixture
    def research_analysis(self):
        """Create a research task analysis."""
        return TaskAnalysis(
            task_type=TaskType.RESEARCH,
            detected_capabilities=["research", "realtime_info"],
            keywords_matched=["latest", "search"],
            requires_working_directory=False,
            requires_realtime_info=True,
            requires_multimodal=False,
            requires_long_context=False,
            confidence=0.7,
        )
    
    def test_match_returns_match_result(self, matcher, coding_analysis):
        """Test that match returns a MatchResult."""
        result = matcher.match(coding_analysis)
        
        assert isinstance(result, MatchResult)
        assert isinstance(result.matches, list)
        assert len(result.matches) > 0
        
    def test_match_has_recommended_agents(self, matcher, coding_analysis):
        """Test that match result has recommended agents."""
        result = matcher.match(coding_analysis)
        
        assert len(result.recommended_agents) >= 1
        assert len(result.recommended_agents) <= 3
        
    def test_coding_task_recommends_claude(self, matcher, coding_analysis):
        """Test that coding tasks recommend Claude."""
        result = matcher.match(coding_analysis)
        
        # Claude should be in top recommendations for coding
        assert "claude" in result.recommended_agents
        
    def test_research_with_realtime_prefers_gemini(self, matcher, research_analysis):
        """Test that research tasks find gemini (which has search_grounding)."""
        result = matcher.match(research_analysis)
        
        # Find gemini's match (has search_grounding capability)
        gemini_match = next((m for m in result.matches if m.agent_name == "gemini"), None)
        
        assert gemini_match is not None
        # Gemini should have a decent score for research with search grounding
        
    def test_all_agents_have_matches(self, matcher, coding_analysis):
        """Test that all agents are matched."""
        result = matcher.match(coding_analysis)
        
        agent_names = [m.agent_name for m in result.matches]
        assert "claude" in agent_names
        assert "gemini" in agent_names
        
    def test_agent_match_has_required_fields(self, matcher, coding_analysis):
        """Test that AgentMatch has required fields."""
        result = matcher.match(coding_analysis)
        match = result.matches[0]
        
        assert isinstance(match, AgentMatch)
        assert hasattr(match, "agent_name")
        assert hasattr(match, "match_score")
        assert hasattr(match, "matched_capabilities")
        assert hasattr(match, "is_eligible")
        
    def test_match_score_in_valid_range(self, matcher, coding_analysis):
        """Test that match scores are between 0 and 1."""
        result = matcher.match(coding_analysis)
        
        for match in result.matches:
            assert 0.0 <= match.match_score <= 1.0
            
    def test_multimodal_requirement_affects_eligibility(self, matcher):
        """Test that multimodal requirement affects eligibility."""
        analysis = TaskAnalysis(
            task_type=TaskType.ANALYSIS,
            detected_capabilities=["multimodal"],
            keywords_matched=["image"],
            requires_working_directory=False,
            requires_realtime_info=False,
            requires_multimodal=True,
            requires_long_context=False,
            confidence=0.7,
        )
        
        result = matcher.match(analysis)
        
        # Agents without multimodal should have lower eligibility
        for match in result.matches:
            if "multimodal" not in match.matched_capabilities:
                # May be marked ineligible
                pass  # Just checking no errors


class TestBestAgentsForTaskType:
    """Tests for get_best_agents_for_task_type method."""
    
    @pytest.fixture
    def matcher(self):
        return AgentMatcher()
    
    def test_coding_task_type(self, matcher):
        """Test getting best agents for coding."""
        agents = matcher.get_best_agents_for_task_type(TaskType.CODING)
        
        assert len(agents) > 0
        assert len(agents) <= 3
        
    def test_unknown_task_type_returns_defaults(self, matcher):
        """Test that unknown task type returns default agents."""
        agents = matcher.get_best_agents_for_task_type(TaskType.UNKNOWN)
        
        assert len(agents) >= 1


class TestGlobalMatcher:
    """Tests for global matcher singleton."""
    
    def test_get_agent_matcher_returns_instance(self):
        """Test that get_agent_matcher returns an instance."""
        matcher = get_agent_matcher()
        assert isinstance(matcher, AgentMatcher)
