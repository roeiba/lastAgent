"""
Tests for LastAgent Council Selector
"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.council_selector import (
    CouncilSelector,
    CouncilSelection,
    CouncilVote,
    CouncilRanking,
    get_council_selector,
)


class TestCouncilSelector:
    """Tests for CouncilSelector class."""
    
    @pytest.fixture
    def selector(self):
        """Create a CouncilSelector instance in mock mode."""
        return CouncilSelector(use_mock=True)
    
    @pytest.mark.asyncio
    async def test_select_agent_returns_selection(self, selector):
        """Test that select_agent returns a CouncilSelection."""
        result = await selector.select_agent(
            user_prompt="Write a Python script",
            system_prompt=""
        )
        
        assert isinstance(result, CouncilSelection)
        assert result.selected_agent in selector.config.get_agent_names()
        
    @pytest.mark.asyncio
    async def test_select_agent_has_confidence(self, selector):
        """Test that selection has a confidence score."""
        result = await selector.select_agent(
            user_prompt="Research the latest AI news"
        )
        
        assert 0.0 <= result.confidence <= 1.0
        
    @pytest.mark.asyncio
    async def test_select_agent_has_reasoning(self, selector):
        """Test that selection has reasoning."""
        result = await selector.select_agent(
            user_prompt="Debug this code"
        )
        
        assert result.reasoning
        assert len(result.reasoning) > 0
        
    @pytest.mark.asyncio
    async def test_select_agent_includes_match_result(self, selector):
        """Test that selection includes match result."""
        result = await selector.select_agent(
            user_prompt="Create a git branch"
        )
        
        assert result.match_result is not None
        assert len(result.match_result.matches) > 0
        
    @pytest.mark.asyncio
    async def test_coding_task_selects_appropriate_agent(self, selector):
        """Test that coding tasks select a coding-capable agent."""
        result = await selector.select_agent(
            user_prompt="Write a Python function to calculate fibonacci numbers"
        )
        
        # Should select an agent with coding capability
        agent = selector.config.get_agent(result.selected_agent)
        # Claude or similar should be selected for coding
        assert result.selected_agent in ["claude", "gpt", "gemini", "aider", "codex"]


class TestCouncilVote:
    """Tests for CouncilVote dataclass."""
    
    def test_vote_creation(self):
        """Test creating a vote."""
        vote = CouncilVote(
            model="openai/gpt-4",
            selected_agent="claude",
            reasoning="Best for coding"
        )
        
        assert vote.model == "openai/gpt-4"
        assert vote.selected_agent == "claude"
        assert "coding" in vote.reasoning.lower()


class TestCouncilRanking:
    """Tests for CouncilRanking dataclass."""
    
    def test_ranking_creation(self):
        """Test creating a ranking."""
        ranking = CouncilRanking(
            model="google/gemini",
            ranking=["claude", "gemini", "gpt"],
            raw_text="1. claude\n2. gemini\n3. gpt"
        )
        
        assert ranking.model == "google/gemini"
        assert ranking.ranking[0] == "claude"
        assert len(ranking.ranking) == 3


class TestParsingHelpers:
    """Tests for parsing helper methods."""
    
    @pytest.fixture
    def selector(self):
        return CouncilSelector(use_mock=True)
    
    def test_parse_agent_suggestion(self, selector):
        """Test parsing agent suggestions."""
        agent, reason = selector._parse_agent_suggestion("claude: Best for complex reasoning")
        
        assert agent == "claude"
        assert "reasoning" in reason.lower()
        
    def test_parse_agent_suggestion_just_name(self, selector):
        """Test parsing suggestion with just agent name."""
        agent, reason = selector._parse_agent_suggestion("gemini")
        
        assert agent == "gemini"
        
    def test_parse_ranking(self, selector):
        """Test parsing rankings."""
        text = """1. claude
2. gemini
3. aider"""
        valid = ["claude", "gemini", "aider", "gpt"]
        
        ranked = selector._parse_ranking(text, valid)
        
        assert ranked == ["claude", "gemini", "aider"]


class TestGlobalSelector:
    """Tests for global selector singleton."""
    
    def test_get_council_selector_returns_instance(self):
        """Test that get_council_selector returns an instance."""
        selector = get_council_selector(use_mock=True)
        assert isinstance(selector, CouncilSelector)
