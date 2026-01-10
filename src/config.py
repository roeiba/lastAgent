"""
LastAgent Configuration Loader

Loads and validates configuration from YAML files.
Provides easy access to agent registry, council config, and settings.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field


# =============================================================================
# CONFIGURATION MODELS
# =============================================================================

class AgentConfig(BaseModel):
    """
    Configuration for a single agent.
    
    CRITICAL: These are AGENTS, not LLMs.
    Agents have CLI/SDK with agentic capabilities (tools, file access, execution).
    """
    display_name: str
    type: str  # Always "cli" for agents
    command: Optional[str] = None  # CLI command (e.g., "claude", "aider")
    capabilities: List[str] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    mcp_server: Optional[str] = None
    requires_working_directory: bool = False


class CouncilMember(BaseModel):
    """Configuration for a council member."""
    model: str
    weight: float = 1.0
    role: str = "member"


class ChairmanConfig(BaseModel):
    """Configuration for the council chairman."""
    model: str
    temperature: float = 0.3
    max_tokens: int = 500


class CouncilConfig(BaseModel):
    """Full council configuration."""
    council_models: List[CouncilMember]
    chairman: ChairmanConfig
    selection_process: Dict[str, Any] = Field(default_factory=dict)
    fallback: Dict[str, Any] = Field(default_factory=dict)


class Settings(BaseModel):
    """General LastAgent settings."""
    approval: Dict[str, Any] = Field(default_factory=dict)
    logging: Dict[str, Any] = Field(default_factory=dict)
    api: Dict[str, Any] = Field(default_factory=dict)
    project_paths: Dict[str, str] = Field(default_factory=dict)
    execution: Dict[str, Any] = Field(default_factory=dict)
    mesh: Dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# CONFIGURATION LOADER
# =============================================================================

class ConfigLoader:
    """
    Loads and manages LastAgent configuration.
    
    Usage:
        config = ConfigLoader()
        config.load()
        
        # Access agents
        claude = config.get_agent("claude")
        
        # Access council
        council = config.council
        
        # Access settings
        approval_mode = config.settings.approval.get("mode")
    """
    
    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize the config loader.
        
        Args:
            config_dir: Path to config directory. Defaults to ./config
        """
        if config_dir is None:
            # Default to config/ relative to this file's parent
            self.config_dir = Path(__file__).parent.parent / "config"
        else:
            self.config_dir = Path(config_dir)
            
        self._agents: Dict[str, AgentConfig] = {}
        self._council: Optional[CouncilConfig] = None
        self._settings: Optional[Settings] = None
        self._loaded = False
        
    def load(self) -> None:
        """Load all configuration files."""
        self._load_agents()
        self._load_council()
        self._load_settings()
        self._loaded = True
        
    def _load_yaml(self, filename: str) -> Dict[str, Any]:
        """Load a YAML file from the config directory."""
        path = self.config_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        with open(path, "r") as f:
            return yaml.safe_load(f)
            
    def _load_agents(self) -> None:
        """Load agent configurations."""
        data = self._load_yaml("agents.yml")
        agents_data = data.get("agents", {})
        for name, agent_data in agents_data.items():
            self._agents[name] = AgentConfig(**agent_data)
            
    def _load_council(self) -> None:
        """Load council configuration."""
        data = self._load_yaml("council.yml")
        # Parse council members
        council_models = [
            CouncilMember(**m) for m in data.get("council_models", [])
        ]
        chairman = ChairmanConfig(**data.get("chairman", {}))
        self._council = CouncilConfig(
            council_models=council_models,
            chairman=chairman,
            selection_process=data.get("selection_process", {}),
            fallback=data.get("fallback", {}),
        )
        
    def _load_settings(self) -> None:
        """Load general settings."""
        data = self._load_yaml("settings.yml")
        self._settings = Settings(
            approval=data.get("approval", {}),
            logging=data.get("logging", {}),
            api=data.get("api", {}),
            project_paths=data.get("project_paths", {}),
            execution=data.get("execution", {}),
            mesh=data.get("mesh", {}),
        )
        
    @property
    def agents(self) -> Dict[str, AgentConfig]:
        """Get all agent configurations."""
        if not self._loaded:
            self.load()
        return self._agents
        
    @property
    def council(self) -> CouncilConfig:
        """Get council configuration."""
        if not self._loaded:
            self.load()
        if self._council is None:
            raise ValueError("Council config not loaded")
        return self._council
        
    @property
    def settings(self) -> Settings:
        """Get general settings."""
        if not self._loaded:
            self.load()
        if self._settings is None:
            raise ValueError("Settings not loaded")
        return self._settings
        
    def get_agent(self, name: str) -> AgentConfig:
        """
        Get configuration for a specific agent.
        
        Args:
            name: Agent name (e.g., "claude", "gemini")
            
        Returns:
            AgentConfig for the agent
            
        Raises:
            KeyError: If agent not found
        """
        if not self._loaded:
            self.load()
        if name not in self._agents:
            raise KeyError(f"Agent not found: {name}")
        return self._agents[name]
        
    def get_agents_by_capability(self, capability: str) -> List[str]:
        """
        Get agents that have a specific capability.
        
        Args:
            capability: Capability name (e.g., "coding", "research")
            
        Returns:
            List of agent names
        """
        if not self._loaded:
            self.load()
        return [
            name for name, agent in self._agents.items()
            if capability in agent.capabilities
        ]
        
    def get_agent_names(self) -> List[str]:
        """Get list of all agent names."""
        if not self._loaded:
            self.load()
        return list(self._agents.keys())


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_config: Optional[ConfigLoader] = None


def get_config() -> ConfigLoader:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = ConfigLoader()
        _config.load()
    return _config


def reload_config() -> ConfigLoader:
    """Reload configuration from files."""
    global _config
    _config = ConfigLoader()
    _config.load()
    return _config
