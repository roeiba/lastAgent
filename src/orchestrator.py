"""
LastAgent Orchestrator

ARCHITECTURE:
=============
Phase 1 - SELECTION: Council of LLMs votes on which agent to use
Phase 2 - EXECUTION: Selected agent runs via CLI/SDK (not LLM API)

This orchestrator coordinates:
1. Receiving tasks from users
2. Using Council to SELECT the best agent (via LLM voting)
3. EXECUTING the selected agent via CLI (claude -p, aider --message, etc.)
4. Managing inter-agent communication (full-mesh, via CLI)
5. Logging decisions and collecting feedback
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

# Enterprise structured logging
try:
    from src.observability import (
        get_logger,
        set_correlation_context,
        log_phase_start,
        log_phase_end,
        log_agent_selected,
        log_agent_execution_start,
        log_agent_execution_end,
        log_error,
    )
except ImportError:
    from .observability import (
        get_logger,
        set_correlation_context,
        log_phase_start,
        log_phase_end,
        log_agent_selected,
        log_agent_execution_start,
        log_agent_execution_end,
        log_error,
    )

try:
    from src.config import get_config, AgentConfig
    from src.council_selector import get_council_selector, CouncilSelector
    from src.executor import get_agent_executor, AgentExecutor, ExecutionContext
    from src.mesh import get_mesh_coordinator, MeshCoordinator
    from src.approvals import get_approval_manager, ApprovalManager, RiskLevel
    from src.decision_log import get_decision_logger, DecisionLogger, DecisionType, Alternative
except ImportError:
    from .config import get_config, AgentConfig
    from .council_selector import get_council_selector, CouncilSelector
    from .executor import get_agent_executor, AgentExecutor, ExecutionContext
    from .mesh import get_mesh_coordinator, MeshCoordinator
    from .approvals import get_approval_manager, ApprovalManager, RiskLevel
    from .decision_log import get_decision_logger, DecisionLogger, DecisionType, Alternative


# =============================================================================
# ENUMS AND TYPES
# =============================================================================

class ApprovalMode(Enum):
    """Approval mode settings."""
    AUTO = "AUTO"
    APPROVE_ALL = "APPROVE_ALL"
    APPROVE_HIGH_RISK = "APPROVE_HIGH_RISK"


class TaskStatus(Enum):
    """Status of a task in the orchestration pipeline."""
    PENDING = "pending"
    COUNCIL_SELECTING = "council_selecting"  # Phase 1: LLM council voting
    AWAITING_APPROVAL = "awaiting_approval"
    EXECUTING = "executing"  # Phase 2: Agent running via CLI
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class Task:
    """Represents a task submitted to LastAgent."""
    id: str
    system_prompt: str
    user_prompt: str
    working_directory: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    status: TaskStatus = TaskStatus.PENDING


@dataclass
class AgentSelection:
    """Result of the council agent selection (Phase 1)."""
    selected_agent: str  # Agent to execute via CLI in Phase 2
    confidence: float
    reasoning: str
    votes: Dict[str, str] = field(default_factory=dict)
    rankings: Dict[str, List[str]] = field(default_factory=dict)


@dataclass
class ExecutionResult:
    """Result of agent execution (Phase 2 - via CLI)."""
    task_id: str
    agent: str  # Agent that was executed via CLI
    response: str
    success: bool
    duration_ms: int
    error: Optional[str] = None
    inter_agent_calls: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class Decision:
    """A logged decision for audit trail."""
    id: str
    task_id: str
    decision_type: str
    title: str
    reasoning: str
    confidence: float
    alternatives: List[str] = field(default_factory=list)
    outcome: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


# =============================================================================
# ORCHESTRATOR
# =============================================================================

class Orchestrator:
    """
    Main LastAgent orchestrator - coordinates SELECTION and EXECUTION.
    
    Architecture:
    - Phase 1: Council of LLMs SELECTS which agent to use
    - Phase 2: Selected agent EXECUTES via CLI/SDK
    
    The council uses LLM API calls for voting decisions.
    Execution is ALWAYS via agent CLI (claude, aider, codex, goose, etc.)
    
    Usage:
        orchestrator = Orchestrator()
        result = await orchestrator.process_task(
            user_prompt="Write a Python script...",
        )
        # Council selects "claude" -> Executor runs: claude -p "prompt"
    """
    
    def __init__(self):
        """Initialize the orchestrator."""
        self.config = get_config()
        self._log = get_logger("orchestrator")
        
        # Internal state
        self._tasks: Dict[str, Task] = {}
        self._decisions: List[Decision] = []
        
        # Initialize all components
        self._council_selector = get_council_selector(use_mock=True)
        self._executor = get_agent_executor()
        self._mesh = get_mesh_coordinator()
        self._approval_manager = get_approval_manager()
        self._decision_logger = get_decision_logger()
        
    async def process_task(
        self,
        system_prompt: str,
        user_prompt: str,
        working_directory: Optional[str] = None,
        approval_mode: Optional[ApprovalMode] = None,
    ) -> ExecutionResult:
        """
        Process a task through the full LastAgent pipeline.
        
        Args:
            system_prompt: System prompt for the task
            user_prompt: User prompt for the task
            working_directory: Optional working directory for CLI agents
            approval_mode: Override approval mode for this task
            
        Returns:
            ExecutionResult with the agent's response
        """
        import uuid
        
        start_time = time.perf_counter()
        
        # Create task
        task = Task(
            id=str(uuid.uuid4()),
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            working_directory=working_directory,
        )
        self._tasks[task.id] = task
        
        # Log task received
        self._log.info(
            "task_received",
            task_id=task.id,
            prompt_preview=user_prompt[:100],
        )
        
        try:
            # Step 1: Select agent via council
            task.status = TaskStatus.COUNCIL_SELECTING
            log_phase_start("SELECTION")
            selection_start = time.perf_counter()
            selection = await self._select_agent(task)
            selection_duration = (time.perf_counter() - selection_start) * 1000
            log_phase_end("SELECTION", selection_duration, agent=selection.selected_agent)
            
            # Step 2: Check approval if needed
            mode = approval_mode or ApprovalMode(
                self.config.settings.approval.get("mode", "AUTO")
            )
            if mode != ApprovalMode.AUTO:
                task.status = TaskStatus.AWAITING_APPROVAL
                approved = await self._check_approval(task, selection, mode)
                if not approved:
                    task.status = TaskStatus.REJECTED
                    return ExecutionResult(
                        task_id=task.id,
                        agent=selection.selected_agent,
                        response="",
                        success=False,
                        duration_ms=0,
                        error="User rejected agent selection",
                    )
            
            # Step 3: Execute agent
            task.status = TaskStatus.EXECUTING
            log_phase_start("EXECUTION")
            execution_start = time.perf_counter()
            result = await self._execute_agent(task, selection.selected_agent)
            execution_duration = (time.perf_counter() - execution_start) * 1000
            log_phase_end("EXECUTION", execution_duration, agent=selection.selected_agent, success=result.success)
            
            # Step 4: Log decision
            await self._log_decision(task, selection, result)
            
            task.status = TaskStatus.COMPLETED
            total_duration = (time.perf_counter() - start_time) * 1000
            self._log.info(
                "task_completed",
                task_id=task.id,
                agent=selection.selected_agent,
                success=result.success,
                duration_ms=round(total_duration, 2),
            )
            return result
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            log_error(
                "task_failed",
                error_type=type(e).__name__,
                error_message=str(e),
                task_id=task.id,
                duration_ms=duration_ms,
            )
            return ExecutionResult(
                task_id=task.id,
                agent="unknown",
                response="",
                success=False,
                duration_ms=duration_ms,
                error=str(e),
            )
            
    async def _select_agent(self, task: Task) -> AgentSelection:
        """
        Select the best agent for the task using LLM Council.
        """
        self._log.info("council_selection_started", available_agents=self.config.get_agent_names())
        
        # Use the real council selector
        council_result = await self._council_selector.select_agent(
            user_prompt=task.user_prompt,
            system_prompt=task.system_prompt,
            working_directory=task.working_directory,
        )
        
        # Convert votes and rankings to dicts
        votes = {v.model: v.selected_agent for v in council_result.votes}
        rankings = {r.model: r.ranking for r in council_result.rankings}
        
        return AgentSelection(
            selected_agent=council_result.selected_agent,
            confidence=council_result.confidence,
            reasoning=council_result.reasoning,
            votes=votes,
            rankings=rankings,
        )
        
    async def _check_approval(
        self,
        task: Task,
        selection: AgentSelection,
        mode: ApprovalMode,
    ) -> bool:
        """
        Check if user approves the agent selection.
        """
        self.logger.info(f"Approval mode: {mode.value}")
        
        # Use the approval manager
        from .approvals import ApprovalMode as AM
        
        # Determine risk level
        risk_level = self._approval_manager.classify_risk(
            "agent_execution",
            {"agent": selection.selected_agent}
        )
        
        if not self._approval_manager.requires_approval("agent_execution", risk_level):
            return True
            
        # Create approval request
        request = self._approval_manager.create_request(
            action_type="agent_execution",
            title=f"Execute {selection.selected_agent}",
            description=f"Task: {task.user_prompt[:100]}...",
            agent_name=selection.selected_agent,
            risk_level=risk_level,
        )
        
        # Auto-approve for now (would be UI in production)
        response = self._approval_manager.auto_approve(request)
        return response.approved
        
    async def _execute_agent(
        self,
        task: Task,
        agent_name: str,
    ) -> ExecutionResult:
        """
        Execute the selected agent with the original prompts.
        """
        log_agent_execution_start(agent_name)
        
        # Use the real executor
        context = ExecutionContext(
            system_prompt=task.system_prompt,
            user_prompt=task.user_prompt,
            working_directory=task.working_directory,
        )
        
        result = await self._executor.execute(agent_name, context)
        
        return ExecutionResult(
            task_id=task.id,
            agent=agent_name,
            response=result.response,
            success=result.success,
            duration_ms=result.duration_ms,
            error=result.error,
        )
        
    async def _log_decision(
        self,
        task: Task,
        selection: AgentSelection,
        result: ExecutionResult,
    ) -> None:
        """
        Log the decision for audit trail.
        """
        import uuid
        
        # Log to decision logger
        alternatives = [
            Alternative(name=agent, score=0.5, reason="Alternative considered")
            for agent in self.config.get_agent_names()
            if agent != selection.selected_agent
        ][:3]
        
        self._decision_logger.log_decision(
            decision_type=DecisionType.AGENT_SELECTION,
            title=f"Selected {selection.selected_agent}",
            reasoning=selection.reasoning,
            confidence_score=selection.confidence,
            risk_level="low",
            alternatives=alternatives,
            task_id=task.id,
        )
        
        # Also keep local record
        decision = Decision(
            id=str(uuid.uuid4()),
            task_id=task.id,
            decision_type="AGENT_SELECTION",
            title=f"Selected {selection.selected_agent} for task",
            reasoning=selection.reasoning,
            confidence=selection.confidence,
            alternatives=list(self.config.agents.keys()),
            outcome="success" if result.success else "failure",
        )
        self._decisions.append(decision)
        
        self._log.info(
            "decision_logged",
            decision_type=decision.decision_type,
            agent=selection.selected_agent,
        )
        
    def get_available_agents(self) -> List[str]:
        """Get list of available agent names."""
        return self.config.get_agent_names()
        
    def get_agent_info(self, name: str) -> AgentConfig:
        """Get detailed info about an agent."""
        return self.config.get_agent(name)
        
    def get_decisions(self, limit: int = 100) -> List[Decision]:
        """Get recent decisions for audit."""
        return self._decisions[-limit:]


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_orchestrator: Optional[Orchestrator] = None


def get_orchestrator() -> Orchestrator:
    """Get the global orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator
