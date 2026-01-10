"""
Tests for LastAgent Agent Awareness Module
"""
import pytest
from src.agent_awareness import (
    AgentAwarenessBuilder,
    AgentCapability,
    AwarenessContext,
    DelegationRequest,
    parse_delegation_request,
    get_awareness_builder,
    build_aware_prompt,
    AGENT_AWARENESS_TEMPLATE,
)


# =============================================================================
# TEST FIXTURES
# =============================================================================
@pytest.fixture
def sample_agents_config():
    """Sample agents configuration for testing."""
    return {
        "agents": {
            "claude": {
                "display_name": "Claude Agent",
                "capabilities": ["deep_reasoning", "coding", "analysis"],
                "strengths": ["Complex reasoning", "Code generation"],
            },
            "gemini": {
                "display_name": "Gemini Agent",
                "capabilities": ["research", "search_grounding", "multimodal"],
                "strengths": ["Real-time search", "1M+ context"],
            },
            "aider": {
                "display_name": "Aider Agent",
                "capabilities": ["git_integration", "code_editing", "auto_commits"],
                "strengths": ["Git-aware editing", "Auto commits"],
            },
        }
    }


@pytest.fixture
def awareness_builder(sample_agents_config):
    """AgentAwarenessBuilder instance for testing."""
    return AgentAwarenessBuilder(sample_agents_config)


# =============================================================================
# AGENT CAPABILITY TESTS
# =============================================================================
class TestAgentCapability:
    """Tests for AgentCapability dataclass."""
    
    def test_to_prompt_text_includes_name(self):
        """Test that prompt text includes agent name."""
        cap = AgentCapability(
            name="claude",
            display_name="Claude Agent",
            capabilities=["coding", "analysis"],
            strengths=["Great at coding"],
        )
        text = cap.to_prompt_text()
        assert "Claude Agent" in text
        assert "claude" in text
        
    def test_to_prompt_text_includes_capabilities(self):
        """Test that prompt text includes capabilities."""
        cap = AgentCapability(
            name="test",
            display_name="Test Agent",
            capabilities=["cap1", "cap2"],
            strengths=["strength1"],
        )
        text = cap.to_prompt_text()
        assert "cap1" in text
        assert "cap2" in text
        
    def test_to_prompt_text_includes_strengths(self):
        """Test that prompt text includes strengths."""
        cap = AgentCapability(
            name="test",
            display_name="Test Agent",
            capabilities=["cap1"],
            strengths=["Very strong", "Also powerful"],
        )
        text = cap.to_prompt_text()
        assert "Very strong" in text
        assert "Also powerful" in text


# =============================================================================
# AGENT AWARENESS BUILDER TESTS
# =============================================================================
class TestAgentAwarenessBuilder:
    """Tests for AgentAwarenessBuilder class."""
    
    def test_get_peer_agents_excludes_current(self, awareness_builder):
        """Test that get_peer_agents excludes current agent."""
        peers = awareness_builder.get_peer_agents("claude")
        peer_names = [p.name for p in peers]
        assert "claude" not in peer_names
        assert "gemini" in peer_names
        assert "aider" in peer_names
        
    def test_get_peer_agents_returns_all_others(self, awareness_builder):
        """Test that get_peer_agents returns all other agents."""
        peers = awareness_builder.get_peer_agents("claude")
        assert len(peers) == 2  # gemini and aider
        
    def test_build_awareness_section_contains_template_parts(self, awareness_builder):
        """Test that awareness section contains expected parts."""
        section = awareness_builder.build_awareness_section("claude")
        assert "Agent Mesh Awareness" in section
        assert "Delegation Guidelines" in section
        assert "How to Delegate" in section
        
    def test_build_awareness_section_excludes_current_agent(self, awareness_builder):
        """Test that awareness section excludes current agent."""
        section = awareness_builder.build_awareness_section("claude")
        # Claude should not be listed as a peer
        assert "Claude Agent" not in section or section.count("Claude") == 1  # Only in guidelines
        
    def test_build_aware_system_prompt_appends_awareness(self, awareness_builder):
        """Test that aware prompt appends awareness to base prompt."""
        base = "You are a helpful assistant."
        aware = awareness_builder.build_aware_system_prompt("claude", base)
        assert aware.startswith(base)
        assert "Agent Mesh Awareness" in aware
        
    def test_build_aware_system_prompt_with_disabled_awareness(self, awareness_builder):
        """Test that awareness can be disabled."""
        base = "You are a helpful assistant."
        aware = awareness_builder.build_aware_system_prompt(
            "claude", base, include_awareness=False
        )
        assert aware == base
        
    def test_get_best_delegate_for_capability(self, awareness_builder):
        """Test finding best delegate for a capability."""
        delegate = awareness_builder.get_best_delegate_for_capability("git_integration")
        assert delegate == "aider"
        
    def test_get_best_delegate_for_unknown_capability(self, awareness_builder):
        """Test that unknown capability returns None."""
        delegate = awareness_builder.get_best_delegate_for_capability("unknown_cap")
        assert delegate is None
        
    def test_get_delegation_recommendations(self, awareness_builder):
        """Test getting delegation recommendations."""
        recommendations = awareness_builder.get_delegation_recommendations(
            task_capabilities_needed=["coding", "git_integration", "search_grounding"],
            current_agent="claude",
        )
        # Claude has coding, so should recommend aider for git and gemini for search
        assert "aider" in recommendations
        assert "git_integration" in recommendations["aider"]
        assert "gemini" in recommendations
        assert "search_grounding" in recommendations["gemini"]


# =============================================================================
# DELEGATION PARSER TESTS
# =============================================================================
class TestDelegationParser:
    """Tests for parse_delegation_request function."""
    
    def test_parse_valid_delegation(self):
        """Test parsing a valid delegation request."""
        output = """
        I need help with git operations.
        
        DELEGATE_TO: aider
        TASK: Commit the changes with a good message
        CONTEXT: Working in /project/src
        """
        request = parse_delegation_request(output)
        assert request is not None
        assert request.valid
        assert request.target_agent == "aider"
        assert "Commit" in request.task
        assert "Working" in request.context
        
    def test_parse_no_delegation(self):
        """Test that non-delegation output returns None."""
        output = "Here is your code solution..."
        request = parse_delegation_request(output)
        assert request is None
        
    def test_parse_incomplete_delegation(self):
        """Test parsing incomplete delegation request."""
        output = "DELEGATE_TO: aider"  # Missing TASK
        request = parse_delegation_request(output)
        assert request is not None
        assert not request.valid
        assert "Missing required fields" in request.error
        
    def test_parse_delegation_normalizes_agent_name(self):
        """Test that agent name is normalized to lowercase."""
        output = """
        DELEGATE_TO: AIDER
        TASK: Do something
        """
        request = parse_delegation_request(output)
        assert request.target_agent == "aider"


# =============================================================================
# GLOBAL INSTANCE TESTS
# =============================================================================
class TestGlobalInstances:
    """Tests for global singleton functions."""
    
    def test_get_awareness_builder_returns_instance(self):
        """Test that get_awareness_builder returns an instance."""
        builder = get_awareness_builder()
        assert isinstance(builder, AgentAwarenessBuilder)
        
    def test_get_awareness_builder_returns_same_instance(self):
        """Test that get_awareness_builder returns same instance."""
        builder1 = get_awareness_builder()
        builder2 = get_awareness_builder()
        assert builder1 is builder2
        
    def test_build_aware_prompt_convenience_function(self):
        """Test the convenience function works."""
        prompt = build_aware_prompt("claude", "Base prompt")
        assert "Base prompt" in prompt
        # May or may not have awareness depending on config
        assert len(prompt) >= len("Base prompt")


# =============================================================================
# AWARENESS CONTEXT TESTS
# =============================================================================
class TestAwarenessContext:
    """Tests for AwarenessContext dataclass."""
    
    def test_default_values(self):
        """Test default values are set correctly."""
        ctx = AwarenessContext(current_agent="claude")
        assert ctx.current_agent == "claude"
        assert ctx.peer_agents == []
        assert ctx.delegation_history == []
        assert ctx.max_delegation_depth == 3
        
    def test_custom_values(self):
        """Test custom values are set correctly."""
        ctx = AwarenessContext(
            current_agent="gemini",
            max_delegation_depth=5,
        )
        assert ctx.current_agent == "gemini"
        assert ctx.max_delegation_depth == 5
