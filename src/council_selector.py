"""
LastAgent Council Selector

ARCHITECTURE NOTE:
==================
LastAgent has a two-phase architecture:

Phase 1 - SELECTION (this module):
  - Council of LLMs votes on which AGENT is best for the task
  - Uses LLM API calls for voting/decision-making only
  - This is NOT execution - just intelligent routing

Phase 2 - EXECUTION (executor.py):
  - The selected AGENT runs via its native CLI/SDK
  - AGENTS have agentic capabilities (tools, file access, execution)
  - Examples: claude -p prompt, aider --message, codex --full-auto

The council uses LLM APIs to SELECT. Execution is always CLI.
"""

import asyncio
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Enterprise structured logging
try:
    from src.observability import get_logger, log_agent_selected, log_error
except ImportError:
    try:
        from .observability import get_logger, log_agent_selected, log_error
    except ImportError:
        # Fallback for when observability is not available
        def get_logger(name): return None
        def log_agent_selected(*args, **kwargs): pass
        def log_error(*args, **kwargs): pass

# Add llm-council to path for imports
LLM_COUNCIL_PATH = Path(__file__).parent.parent.parent / "llm-council" / "backend"
if str(LLM_COUNCIL_PATH) not in sys.path:
    sys.path.insert(0, str(LLM_COUNCIL_PATH))

from .config import get_config
from .task_analyzer import TaskAnalysis, get_task_analyzer
from .agent_matcher import MatchResult, get_agent_matcher


@dataclass
class CouncilVote:
    """A single council member's vote for which AGENT to use."""
    model: str  # LLM model that voted
    selected_agent: str  # Name of the agent to execute via CLI
    reasoning: str


@dataclass
class CouncilRanking:
    """A council member's ranking of agents."""
    model: str
    ranking: List[str]  # Ordered list of agent names, best first
    raw_text: str


@dataclass 
class CouncilSelection:
    """Result of the council selection process."""
    selected_agent: str  # Agent to execute via CLI
    confidence: float
    reasoning: str
    votes: List[CouncilVote]
    rankings: List[CouncilRanking]
    aggregate_scores: Dict[str, float]
    match_result: Optional[MatchResult] = None


class CouncilSelector:
    """
    Council of LLMs that SELECTS which AGENT to use for a task.
    
    IMPORTANT: This module uses LLM APIs for VOTING/SELECTION only.
    The selected agent is then EXECUTED via CLI in executor.py.
    
    Process:
    1. Analyze task requirements
    2. Council members vote on best agent
    3. Chairman synthesizes final selection
    4. Return agent name -> executor runs via CLI
    
    Usage:
        selector = CouncilSelector()
        result = await selector.select_agent("Write a Python script")
        # result.selected_agent = "claude" -> executor calls: claude -p prompt
    """
    
    def __init__(self, use_mock: bool = False):
        """
        Initialize the council selector.
        
        Args:
            use_mock: If True, use mock responses instead of real LLM calls
        """
        self.config = get_config()
        self.task_analyzer = get_task_analyzer()
        self.agent_matcher = get_agent_matcher()
        self.use_mock = use_mock
        self._log = get_logger("council")
        
        # Try to import llm-council modules
        self._council_available = False
        try:
            from openrouter import query_model, query_models_parallel
            from config import COUNCIL_MODELS, CHAIRMAN_MODEL
            self._query_model = query_model
            self._query_models_parallel = query_models_parallel
            self._council_models = COUNCIL_MODELS
            self._chairman_model = CHAIRMAN_MODEL
            self._council_available = True
        except ImportError:
            # Will use fallback selection
            pass
            
    async def select_agent(
        self,
        user_prompt: str,
        system_prompt: str = "",
        working_directory: Optional[str] = None,
    ) -> CouncilSelection:
        """
        Select the best agent for a task using council voting.
        
        Args:
            user_prompt: The user's request
            system_prompt: Optional system prompt
            working_directory: Optional working directory for context
            
        Returns:
            CouncilSelection with the selected agent and voting details
        """
        # Analyze the task
        analysis = self.task_analyzer.analyze(user_prompt, system_prompt)
        
        # Get agent matches
        match_result = self.agent_matcher.match(analysis)
        
        # If mock mode or council unavailable, use local selection
        if self.use_mock or not self._council_available:
            if self._log:
                self._log.info(
                    "fallback_selection_used",
                    reason="mock_mode" if self.use_mock else "council_unavailable",
                )
            return self._fallback_selection(analysis, match_result)
            
        # Run 3-stage council process
        try:
            if self._log:
                self._log.info(
                    "council_selection_started",
                    available_agents=self.config.get_agent_names(),
                    council_models=getattr(self, '_council_models', []),
                )
            return await self._run_council_selection(
                user_prompt,
                system_prompt,
                analysis,
                match_result,
            )
        except Exception as e:
            # Fallback on error
            log_error(
                "council_selection_failed",
                error_type=type(e).__name__,
                error_message=str(e),
            )
            return self._fallback_selection(analysis, match_result, error=str(e))
            
    async def _run_council_selection(
        self,
        user_prompt: str,
        system_prompt: str,
        analysis: TaskAnalysis,
        match_result: MatchResult,
    ) -> CouncilSelection:
        """Run the full 3-stage council selection process."""
        available_agents = self.config.get_agent_names()
        agents_description = self._format_agents_for_prompt(available_agents)
        
        # Stage 1: Collect agent suggestions from each council member
        votes = await self._stage1_collect_votes(
            user_prompt, system_prompt, agents_description
        )
        
        if not votes:
            return self._fallback_selection(analysis, match_result, error="No council votes")
            
        # Stage 2: Have each member rank the suggested agents
        suggestions = list(set(v.selected_agent for v in votes if v.selected_agent))
        rankings = await self._stage2_collect_rankings(
            user_prompt, system_prompt, suggestions
        )
        
        # Stage 3: Chairman synthesizes final selection
        selected, confidence, reasoning = await self._stage3_select_final(
            user_prompt, system_prompt, votes, rankings, match_result.recommended_agents
        )
        
        # Calculate aggregate scores
        aggregate_scores = self._calculate_aggregate_scores(votes, rankings)
        
        return CouncilSelection(
            selected_agent=selected,
            confidence=confidence,
            reasoning=reasoning,
            votes=votes,
            rankings=rankings,
            aggregate_scores=aggregate_scores,
            match_result=match_result,
        )
        
    async def _stage1_collect_votes(
        self,
        user_prompt: str,
        system_prompt: str,
        agents_description: str,
    ) -> List[CouncilVote]:
        """Stage 1: Each council member suggests an agent."""
        prompt = f"""You are helping to select the best AI agent for a task.

Task Context:
{system_prompt}

User Request:
{user_prompt}

Available Agents:
{agents_description}

Based on the task requirements, which agent would be BEST suited to handle this task?

Reply with ONLY the agent name (e.g., "claude", "gemini", "aider") followed by a brief reason.
Format: <agent_name>: <brief reason>"""

        messages = [{"role": "user", "content": prompt}]
        responses = await self._query_models_parallel(self._council_models, messages)
        
        votes = []
        for model, response in responses.items():
            if response:
                selected, reasoning = self._parse_agent_suggestion(response.get("content", ""))
                votes.append(CouncilVote(
                    model=model,
                    selected_agent=selected,
                    reasoning=reasoning,
                ))
                if self._log:
                    self._log.debug(
                        "stage1_vote_collected",
                        model=model,
                        vote=selected,
                    )
                
        return votes
        
    async def _stage2_collect_rankings(
        self,
        user_prompt: str,
        system_prompt: str,
        suggestions: List[str],
    ) -> List[CouncilRanking]:
        """Stage 2: Each council member ranks the suggestions."""
        if len(suggestions) < 2:
            return []
            
        suggestions_text = ", ".join(suggestions)
        prompt = f"""The following agents were suggested for this task:
{suggestions_text}

Task: {user_prompt}

Rank these agents from best to worst for this specific task.
Reply with a numbered list:
1. <best agent>
2. <second best>
...etc"""

        messages = [{"role": "user", "content": prompt}]
        responses = await self._query_models_parallel(self._council_models, messages)
        
        rankings = []
        for model, response in responses.items():
            if response:
                raw_text = response.get("content", "")
                ranked_agents = self._parse_ranking(raw_text, suggestions)
                rankings.append(CouncilRanking(
                    model=model,
                    ranking=ranked_agents,
                    raw_text=raw_text,
                ))
                
        return rankings
        
    async def _stage3_select_final(
        self,
        user_prompt: str,
        system_prompt: str,
        votes: List[CouncilVote],
        rankings: List[CouncilRanking],
        recommended: List[str],
    ) -> Tuple[str, float, str]:
        """Stage 3: Chairman makes final selection."""
        # Summarize votes
        votes_summary = "\n".join([
            f"- {v.model}: {v.selected_agent} ({v.reasoning})"
            for v in votes
        ])
        
        # Summarize rankings
        rankings_summary = "\n".join([
            f"- {r.model}: {', '.join(r.ranking[:3])}"
            for r in rankings if r.ranking
        ])
        
        prompt = f"""You are the Chairman making the final agent selection.

Task: {user_prompt}

Council Votes:
{votes_summary}

Council Rankings:
{rankings_summary}

Local Analysis Recommendation: {', '.join(recommended)}

Make the final selection. Reply with:
SELECTED: <agent_name>
CONFIDENCE: <0.0 to 1.0>
REASONING: <brief explanation>"""

        messages = [{"role": "user", "content": prompt}]
        response = await self._query_model(self._chairman_model, messages)
        
        if response is None:
            # Fallback: pick the most voted agent
            vote_counts = {}
            for v in votes:
                vote_counts[v.selected_agent] = vote_counts.get(v.selected_agent, 0) + 1
            if vote_counts:
                selected = max(vote_counts, key=vote_counts.get)
                return selected, 0.7, "Selected by majority vote (chairman unavailable)"
            return recommended[0] if recommended else "claude", 0.5, "Default selection"
            
        # Parse chairman response
        content = response.get("content", "")
        selected, confidence, reasoning = self._parse_chairman_response(content, votes, recommended)
        
        if self._log:
            self._log.info(
                "stage3_chairman_decided",
                selected_agent=selected,
                confidence=confidence,
            )
        log_agent_selected(selected, 0, reasoning)
        
        return selected, confidence, reasoning
        
    def _fallback_selection(
        self,
        analysis: TaskAnalysis,
        match_result: MatchResult,
        error: Optional[str] = None,
    ) -> CouncilSelection:
        """Use local matching as fallback when council is unavailable."""
        if match_result.recommended_agents:
            selected = match_result.recommended_agents[0]
            confidence = 0.7
        else:
            selected = "claude"  # Default fallback
            confidence = 0.5
            
        reason = "Selected based on local capability matching"
        if error:
            reason += f" (council error: {error})"
            
        return CouncilSelection(
            selected_agent=selected,
            confidence=confidence,
            reasoning=reason,
            votes=[],
            rankings=[],
            aggregate_scores={selected: 1.0},
            match_result=match_result,
        )
        
    def _format_agents_for_prompt(self, agents: List[str]) -> str:
        """Format agent list for the selection prompt."""
        lines = []
        for agent_name in agents:
            agent = self.config.get_agent(agent_name)
            caps = ", ".join(agent.capabilities[:3])
            strengths = agent.strengths[0] if agent.strengths else ""
            lines.append(f"- {agent_name}: {strengths} (capabilities: {caps})")
        return "\n".join(lines)
        
    def _parse_agent_suggestion(self, text: str) -> Tuple[str, str]:
        """Parse an agent suggestion from model response."""
        import re
        
        # Try to find pattern like "claude: because..."
        match = re.match(r"(\w+)\s*:\s*(.*)", text.strip())
        if match:
            return match.group(1).lower(), match.group(2)
            
        # Try to find just the agent name at the start
        words = text.strip().split()
        if words:
            first_word = words[0].lower().rstrip(":.,")
            valid_agents = self.config.get_agent_names()
            if first_word in valid_agents:
                return first_word, text
                
        return "", text
        
    def _parse_ranking(self, text: str, valid_agents: List[str]) -> List[str]:
        """Parse a ranking from model response."""
        import re
        
        ranked = []
        # Look for numbered list items
        for line in text.split("\n"):
            match = re.match(r"\d+\.\s*(\w+)", line)
            if match:
                agent = match.group(1).lower()
                if agent in valid_agents and agent not in ranked:
                    ranked.append(agent)
                    
        return ranked
        
    def _parse_chairman_response(
        self,
        text: str,
        votes: List[CouncilVote],
        recommended: List[str],
    ) -> Tuple[str, float, str]:
        """Parse the chairman's final response."""
        import re
        
        selected = None
        confidence = 0.7
        reasoning = "Chairman selection"
        
        for line in text.split("\n"):
            line = line.strip()
            if line.upper().startswith("SELECTED:"):
                agent = line.split(":", 1)[1].strip().lower()
                if agent in self.config.get_agent_names():
                    selected = agent
            elif line.upper().startswith("CONFIDENCE:"):
                try:
                    confidence = float(line.split(":", 1)[1].strip())
                except ValueError:
                    pass
            elif line.upper().startswith("REASONING:"):
                reasoning = line.split(":", 1)[1].strip()
                
        if not selected:
            # Fallback to most voted
            vote_counts = {}
            for v in votes:
                vote_counts[v.selected_agent] = vote_counts.get(v.selected_agent, 0) + 1
            if vote_counts:
                selected = max(vote_counts, key=vote_counts.get)
            else:
                selected = recommended[0] if recommended else "claude"
                
        return selected, confidence, reasoning
        
    def _calculate_aggregate_scores(
        self,
        votes: List[CouncilVote],
        rankings: List[CouncilRanking],
    ) -> Dict[str, float]:
        """Calculate aggregate scores for each agent."""
        scores = {}
        
        # Count votes
        for vote in votes:
            if vote.selected_agent:
                scores[vote.selected_agent] = scores.get(vote.selected_agent, 0) + 1
                
        # Add ranking-based scores (inverse position)
        for ranking in rankings:
            for i, agent in enumerate(ranking.ranking):
                # First place gets N points, second gets N-1, etc.
                position_score = len(ranking.ranking) - i
                scores[agent] = scores.get(agent, 0) + position_score * 0.5
                
        # Normalize to 0-1 range
        if scores:
            max_score = max(scores.values())
            if max_score > 0:
                scores = {k: v / max_score for k, v in scores.items()}
                
        return scores


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_selector = None


def get_council_selector(use_mock: bool = False) -> CouncilSelector:
    """Get the global council selector instance."""
    global _selector
    if _selector is None:
        _selector = CouncilSelector(use_mock=use_mock)
    return _selector
