"""
LastAgent Agent Matcher

Matches task requirements to agent capabilities to produce a ranked list
of suitable agents for the council to consider.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .config import get_config, AgentConfig
from .task_analyzer import TaskAnalysis, TaskType


@dataclass
class AgentMatch:
    """Result of matching an agent to a task."""
    agent_name: str
    match_score: float  # 0.0 to 1.0
    matched_capabilities: List[str]
    missing_capabilities: List[str]
    is_eligible: bool
    reason: str


@dataclass
class MatchResult:
    """Complete matching result for a task."""
    task_analysis: TaskAnalysis
    matches: List[AgentMatch]
    recommended_agents: List[str]  # Top agents to consider
    

# =============================================================================
# TASK TYPE TO PREFERRED CAPABILITIES
# =============================================================================

TASK_TYPE_PREFERENCES = {
    TaskType.CODING: ["coding", "deep_reasoning"],
    TaskType.RESEARCH: ["research", "realtime_info"],
    TaskType.WRITING: ["writing", "deep_reasoning"],
    TaskType.ANALYSIS: ["deep_reasoning", "research"],
    TaskType.AUTOMATION: ["multistep_workflows", "sandboxed_execution"],
    TaskType.CONVERSATION: ["deep_reasoning"],
    TaskType.UNKNOWN: [],
}


class AgentMatcher:
    """
    Matches tasks to suitable agents based on capabilities.
    
    Usage:
        matcher = AgentMatcher()
        result = matcher.match(task_analysis)
        print(result.recommended_agents)  # ["claude", "gpt", "gemini"]
    """
    
    def __init__(self):
        """Initialize the agent matcher."""
        self.config = get_config()
        
    def match(self, analysis: TaskAnalysis) -> MatchResult:
        """
        Match a task analysis to suitable agents.
        
        Args:
            analysis: TaskAnalysis from the task analyzer
            
        Returns:
            MatchResult with ranked agent matches
        """
        matches = []
        
        for agent_name in self.config.get_agent_names():
            agent = self.config.get_agent(agent_name)
            match = self._score_agent(agent_name, agent, analysis)
            matches.append(match)
            
        # Sort by score (highest first)
        matches.sort(key=lambda m: m.match_score, reverse=True)
        
        # Get eligible agents
        eligible = [m for m in matches if m.is_eligible]
        
        # Recommend top 3 eligible agents
        recommended = [m.agent_name for m in eligible[:3]]
        
        # If less than 3 eligible, add top scoring ineligible ones
        if len(recommended) < 3:
            ineligible = [m for m in matches if not m.is_eligible]
            for m in ineligible:
                if m.agent_name not in recommended:
                    recommended.append(m.agent_name)
                    if len(recommended) >= 3:
                        break
                        
        return MatchResult(
            task_analysis=analysis,
            matches=matches,
            recommended_agents=recommended,
        )
        
    def _score_agent(
        self,
        name: str,
        agent: AgentConfig,
        analysis: TaskAnalysis
    ) -> AgentMatch:
        """Score how well an agent matches a task."""
        agent_caps = set(agent.capabilities)
        required_caps = set(analysis.detected_capabilities)
        
        # Check eligibility
        is_eligible = True
        reason = "Meets requirements"
        
        # Check working directory requirement
        if analysis.requires_working_directory and not agent.requires_working_directory:
            # API agents can't do file operations directly
            if agent.type == "api":
                # Still eligible but may need to use via MCP
                pass
                
        # Calculate matched and missing capabilities
        matched = agent_caps & required_caps
        missing = required_caps - agent_caps
        
        # Calculate base score
        if required_caps:
            base_score = len(matched) / len(required_caps)
        else:
            base_score = 0.5  # Neutral score if no specific requirements
            
        # Apply task type preference bonus
        type_prefs = TASK_TYPE_PREFERENCES.get(analysis.task_type, [])
        type_matches = agent_caps & set(type_prefs)
        type_bonus = len(type_matches) * 0.1 if type_prefs else 0.0
        
        # Apply special requirement penalties/bonuses
        special_bonus = 0.0
        
        # Realtime info - bonus for grok, gemini
        if analysis.requires_realtime_info:
            if "realtime_info" in agent_caps or "search_grounding" in agent_caps:
                special_bonus += 0.1
            else:
                special_bonus -= 0.05
                
        # Multimodal - bonus for gemini, gpt
        if analysis.requires_multimodal:
            if "multimodal" in agent_caps:
                special_bonus += 0.1
            else:
                special_bonus -= 0.1
                is_eligible = False
                reason = "Task requires multimodal but agent doesn't support it"
                
        # Long context - bonus for gemini, claude
        if analysis.requires_long_context:
            if "ultra_long_context" in agent_caps or "long_context" in agent_caps:
                special_bonus += 0.1
                
        # Calculate final score
        final_score = min(1.0, max(0.0, base_score + type_bonus + special_bonus))
        
        return AgentMatch(
            agent_name=name,
            match_score=round(final_score, 3),
            matched_capabilities=list(matched),
            missing_capabilities=list(missing),
            is_eligible=is_eligible,
            reason=reason,
        )
        
    def get_agents_for_capability(self, capability: str) -> List[str]:
        """Get agents that have a specific capability."""
        return self.config.get_agents_by_capability(capability)
        
    def get_best_agents_for_task_type(
        self,
        task_type: TaskType,
        limit: int = 3
    ) -> List[str]:
        """Get the best agents for a specific task type."""
        prefs = TASK_TYPE_PREFERENCES.get(task_type, [])
        
        if not prefs:
            # Return general-purpose agents
            return ["claude", "gpt", "gemini"][:limit]
            
        # Score agents by preference match
        scores = {}
        for agent_name in self.config.get_agent_names():
            agent = self.config.get_agent(agent_name)
            agent_caps = set(agent.capabilities)
            pref_matches = len(agent_caps & set(prefs))
            scores[agent_name] = pref_matches
            
        # Sort and return top agents
        sorted_agents = sorted(scores.keys(), key=lambda a: scores[a], reverse=True)
        return sorted_agents[:limit]


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_matcher = None


def get_agent_matcher() -> AgentMatcher:
    """Get the global agent matcher instance."""
    global _matcher
    if _matcher is None:
        _matcher = AgentMatcher()
    return _matcher
