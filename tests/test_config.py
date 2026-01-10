"""
Tests for LastAgent Configuration Loader
"""

import pytest
from pathlib import Path
import sys

# Add src to path for direct imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import (
    ConfigLoader,
    AgentConfig,
    CouncilConfig,
    Settings,
    get_config,
    reload_config,
)


class TestConfigLoader:
    """Tests for ConfigLoader class."""
    
    @pytest.fixture
    def config_dir(self):
        """Get the config directory path."""
        return Path(__file__).parent.parent / "config"
    
    @pytest.fixture
    def loader(self, config_dir):
        """Create a ConfigLoader instance."""
        return ConfigLoader(config_dir=config_dir)
    
    def test_load_agents(self, loader):
        """Test that agents.yml loads correctly."""
        loader.load()
        
        # Should have multiple agents
        assert len(loader.agents) > 0
        
        # Check specific agents exist
        assert "claude" in loader.agents
        assert "gemini" in loader.agents
        assert "aider" in loader.agents
        
    def test_agent_has_required_fields(self, loader):
        """Test that each agent has required fields."""
        loader.load()
        
        for name, agent in loader.agents.items():
            assert isinstance(agent, AgentConfig)
            assert agent.display_name
            # All agents are CLI type (agents are NOT LLMs)
            assert agent.type == "cli"
            assert isinstance(agent.capabilities, list)
            
    def test_get_agent(self, loader):
        """Test getting a specific agent."""
        loader.load()
        
        claude = loader.get_agent("claude")
        assert claude.display_name == "Claude Agent"
        assert "coding" in claude.capabilities
        assert claude.type == "cli"  # Agents are CLI, not LLM
        
    def test_get_agent_not_found(self, loader):
        """Test KeyError for nonexistent agent."""
        loader.load()
        
        with pytest.raises(KeyError):
            loader.get_agent("nonexistent_agent")
            
    def test_get_agents_by_capability(self, loader):
        """Test filtering agents by capability."""
        loader.load()
        
        coding_agents = loader.get_agents_by_capability("coding")
        assert "claude" in coding_agents
        
        git_agents = loader.get_agents_by_capability("git_integration")
        assert "aider" in git_agents
        
    def test_load_council(self, loader):
        """Test that council.yml loads correctly."""
        loader.load()
        
        assert loader.council is not None
        assert isinstance(loader.council, CouncilConfig)
        assert len(loader.council.council_models) > 0
        assert loader.council.chairman is not None
        
    def test_council_has_chairman(self, loader):
        """Test that council has a chairman configured."""
        loader.load()
        
        chairman = loader.council.chairman
        assert chairman.model
        assert chairman.temperature >= 0
        assert chairman.max_tokens > 0
        
    def test_load_settings(self, loader):
        """Test that settings.yml loads correctly."""
        loader.load()
        
        assert loader.settings is not None
        assert isinstance(loader.settings, Settings)
        
    def test_settings_has_approval_mode(self, loader):
        """Test that settings has approval configuration."""
        loader.load()
        
        approval = loader.settings.approval
        assert "mode" in approval
        assert approval["mode"] in ["AUTO", "APPROVE_ALL", "APPROVE_HIGH_RISK"]
        
    def test_settings_has_project_paths(self, loader):
        """Test that settings has project paths."""
        loader.load()
        
        paths = loader.settings.project_paths
        assert "llm_council" in paths
        assert "agents_parliament" in paths
        assert "super_ai" in paths
        assert "seed_gpt" in paths
        
    def test_auto_load_on_property_access(self, config_dir):
        """Test that accessing properties triggers load."""
        loader = ConfigLoader(config_dir=config_dir)
        
        # Should auto-load when accessing agents
        _ = loader.agents
        assert loader._loaded is True
        
    def test_get_agent_names(self, loader):
        """Test getting list of agent names."""
        loader.load()
        
        names = loader.get_agent_names()
        assert isinstance(names, list)
        assert len(names) > 0
        assert "claude" in names


class TestGlobalConfig:
    """Tests for global config singleton."""
    
    def test_get_config_returns_loader(self):
        """Test that get_config returns a ConfigLoader."""
        config = get_config()
        assert isinstance(config, ConfigLoader)
        
    def test_get_config_is_singleton(self):
        """Test that get_config returns the same instance."""
        config1 = get_config()
        config2 = get_config()
        assert config1 is config2
        
    def test_reload_config_creates_new(self):
        """Test that reload_config creates new instance."""
        config1 = get_config()
        config2 = reload_config()
        
        # Should still work (both have same data)
        assert len(config2.agents) > 0
