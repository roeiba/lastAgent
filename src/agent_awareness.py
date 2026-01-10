"""
LastAgent Agent Awareness Module

Provides mechanism for each agent to know about all peer agents and their
capabilities, enabling intelligent inter-agent delegation in the full-mesh.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from .config import get_config


logger = logging.getLogger(__name__)


def get_agents_config() -> dict[str, Any]:
    """Get agents configuration as a dictionary."""
    config = get_config()
    return {
        "agents": {
            name: {
                "display_name": agent.display_name,
                "capabilities": agent.capabilities,
                "strengths": agent.strengths,
            }
            for name, agent in config.agents.items()
        }
    }


# =============================================================================
# AGENT AWARENESS TEMPLATE
# =============================================================================
AGENT_AWARENESS_TEMPLATE = """
## Agent Mesh Awareness

You are part of a collaborative agent mesh. When you encounter a task that would
be better handled by another agent, you can delegate to them.

### Available Peer Agents

{agent_capabilities}

### Delegation Guidelines

- **Git/Code Editing**: Delegate to Aider (has git integration, auto-commits)
- **Real-time Search**: Delegate to Gemini (has Google Search grounding)
- **Sandboxed Execution**: Delegate to Codex (runs in isolated environment)
- **Multi-step Workflows**: Delegate to Goose (excels at complex automation)
- **Deep Reasoning**: Delegate to Claude (best for complex analysis)

### How to Delegate

To delegate a task, output in this exact format:
```
DELEGATE_TO: <agent_name>
TASK: <detailed task description>
CONTEXT: <any relevant context the peer agent needs>
```

Only delegate when the peer agent has clear advantages for the specific subtask.
For most tasks, complete them yourself.
"""


# =============================================================================
# DATA CLASSES
# =============================================================================
@dataclass
class AgentCapability:
    """Represents a single agent's capability profile."""
    name: str
    display_name: str
    capabilities: list[str]
    strengths: list[str]
    
    def to_prompt_text(self) -> str:
        """Format for inclusion in awareness prompt."""
        caps = ", ".join(self.capabilities)
        strengths_text = "\n  - ".join(self.strengths)
        return f"- **{self.display_name}** (`{self.name}`)\n  Capabilities: {caps}\n  Strengths:\n  - {strengths_text}"


@dataclass
class AwarenessContext:
    """Context for building aware prompts."""
    current_agent: str
    peer_agents: list[AgentCapability] = field(default_factory=list)
    delegation_history: list[dict[str, Any]] = field(default_factory=list)
    max_delegation_depth: int = 3


# =============================================================================
# AGENT AWARENESS BUILDER
# =============================================================================
class AgentAwarenessBuilder:
    """Builds system prompts with peer agent awareness."""
    
    def __init__(self, agents_config: dict[str, Any] | None = None):
        """Initialize with agents configuration.
        
        Args:
            agents_config: Agent registry, defaults to loading from config.
        """
        self.agents_config = agents_config or get_agents_config()
        self._capability_cache: dict[str, AgentCapability] = {}
        self._build_capability_cache()
    
    def _build_capability_cache(self) -> None:
        """Build cache of agent capabilities."""
        agents = self.agents_config.get("agents", {})
        for name, config in agents.items():
            self._capability_cache[name] = AgentCapability(
                name=name,
                display_name=config.get("display_name", name.title()),
                capabilities=config.get("capabilities", []),
                strengths=config.get("strengths", []),
            )
    
    def get_peer_agents(self, current_agent: str) -> list[AgentCapability]:
        """Get all agents except the current one.
        
        Args:
            current_agent: Name of the agent to exclude.
            
        Returns:
            List of peer agent capabilities.
        """
        return [
            cap for name, cap in self._capability_cache.items()
            if name != current_agent
        ]
    
    def build_awareness_section(self, current_agent: str) -> str:
        """Build the awareness section for a system prompt.
        
        Args:
            current_agent: Name of the agent receiving the prompt.
            
        Returns:
            Formatted awareness text to append to system prompt.
        """
        peers = self.get_peer_agents(current_agent)
        if not peers:
            return ""
        
        capabilities_text = "\n\n".join(peer.to_prompt_text() for peer in peers)
        return AGENT_AWARENESS_TEMPLATE.format(agent_capabilities=capabilities_text)
    
    def build_aware_system_prompt(
        self,
        current_agent: str,
        base_system_prompt: str,
        include_awareness: bool = True,
    ) -> str:
        """Build complete system prompt with agent awareness.
        
        Args:
            current_agent: Name of the agent receiving the prompt.
            base_system_prompt: Original system prompt from user.
            include_awareness: Whether to include awareness section.
            
        Returns:
            Complete system prompt with awareness appended.
        """
        if not include_awareness:
            return base_system_prompt
        
        awareness_section = self.build_awareness_section(current_agent)
        if not awareness_section:
            return base_system_prompt
        
        return f"{base_system_prompt}\n\n{awareness_section}"
    
    def get_best_delegate_for_capability(self, capability: str) -> str | None:
        """Find the best agent for a specific capability.
        
        Args:
            capability: The capability needed.
            
        Returns:
            Agent name or None if no agent has the capability.
        """
        for name, cap in self._capability_cache.items():
            if capability in cap.capabilities:
                return name
        return None
    
    def get_delegation_recommendations(
        self,
        task_capabilities_needed: list[str],
        current_agent: str,
    ) -> dict[str, list[str]]:
        """Get delegation recommendations for a task.
        
        Args:
            task_capabilities_needed: Capabilities required for the task.
            current_agent: Current agent handling the task.
            
        Returns:
            Dict mapping agent names to capabilities they can handle.
        """
        current_caps = set(
            self._capability_cache.get(current_agent, AgentCapability(
                name=current_agent, display_name=current_agent,
                capabilities=[], strengths=[]
            )).capabilities
        )
        
        # Find capabilities current agent lacks
        missing_caps = set(task_capabilities_needed) - current_caps
        
        recommendations: dict[str, list[str]] = {}
        for cap in missing_caps:
            delegate = self.get_best_delegate_for_capability(cap)
            if delegate and delegate != current_agent:
                if delegate not in recommendations:
                    recommendations[delegate] = []
                recommendations[delegate].append(cap)
        
        return recommendations


# =============================================================================
# DELEGATION PARSER
# =============================================================================
@dataclass
class DelegationRequest:
    """Parsed delegation request from agent output."""
    target_agent: str
    task: str
    context: str = ""
    valid: bool = True
    error: str = ""


def parse_delegation_request(agent_output: str) -> DelegationRequest | None:
    """Parse a delegation request from agent output.
    
    Args:
        agent_output: Raw output from an agent.
        
    Returns:
        DelegationRequest if found, None otherwise.
    """
    if "DELEGATE_TO:" not in agent_output:
        return None
    
    try:
        lines = agent_output.split("\n")
        target_agent = ""
        task = ""
        context = ""
        
        for i, line in enumerate(lines):
            if line.strip().startswith("DELEGATE_TO:"):
                target_agent = line.split(":", 1)[1].strip()
            elif line.strip().startswith("TASK:"):
                task = line.split(":", 1)[1].strip()
            elif line.strip().startswith("CONTEXT:"):
                context = line.split(":", 1)[1].strip()
        
        if not target_agent or not task:
            return DelegationRequest(
                target_agent=target_agent,
                task=task,
                context=context,
                valid=False,
                error="Missing required fields (DELEGATE_TO and TASK)",
            )
        
        return DelegationRequest(
            target_agent=target_agent.lower(),
            task=task,
            context=context,
        )
        
    except Exception as e:
        logger.warning(f"Failed to parse delegation request: {e}")
        return DelegationRequest(
            target_agent="",
            task="",
            valid=False,
            error=str(e),
        )


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================
_awareness_builder: AgentAwarenessBuilder | None = None


def get_awareness_builder() -> AgentAwarenessBuilder:
    """Get the global AgentAwarenessBuilder instance."""
    global _awareness_builder
    if _awareness_builder is None:
        _awareness_builder = AgentAwarenessBuilder()
    return _awareness_builder


def build_aware_prompt(agent_name: str, system_prompt: str) -> str:
    """Convenience function to build an aware system prompt.
    
    Args:
        agent_name: Name of the agent.
        system_prompt: Base system prompt.
        
    Returns:
        System prompt with awareness section.
    """
    return get_awareness_builder().build_aware_system_prompt(
        current_agent=agent_name,
        base_system_prompt=system_prompt,
    )
