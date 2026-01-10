"""
LastAgent Mesh Coordinator

Manages the full-mesh agent network where any agent can delegate to any other.

ARCHITECTURE:
=============
All inter-agent calls are executed via CLI:
- claude -p "delegation prompt"
- aider --message "..."
- codex --full-auto "..."

**This is NOT LLM-to-LLM chat.** Each agent runs as an autonomous CLI process
with tools, file access, and agentic capabilities.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

from .config import get_config
from .executor import AgentExecutor, ExecutionContext, ExecutionResult, get_agent_executor


@dataclass
class InterAgentCall:
    """Record of an inter-agent call (executed via CLI)."""
    id: str
    caller_agent: str
    target_agent: str  # Agent to execute via CLI
    prompt: str
    response: Optional[str] = None
    success: bool = False
    duration_ms: int = 0
    depth: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class MeshSession:
    """Tracks a mesh execution session."""
    id: str
    initial_agent: str  # All agents executed via CLI
    initial_prompt: str
    calls: List[InterAgentCall] = field(default_factory=list)
    current_depth: int = 0
    max_depth: int = 5
    start_time: datetime = field(default_factory=datetime.utcnow)
    final_response: Optional[str] = None


class MeshCoordinator:
    """
    Coordinates the full-mesh agent network via CLI execution.
    
    IMPORTANT: All agents execute via CLI/SDK, not LLM API.
    Inter-agent calls are CLI subprocess invocations.
    
    Features:
    - Any agent can delegate to any other agent (via CLI)
    - Call depth tracking to prevent infinite loops
    - Session management for audit trail
    
    Usage:
        mesh = MeshCoordinator()
        session = await mesh.start_session(
            initial_agent="claude",  # Runs: claude -p "prompt"
            user_prompt="Research AI trends and write a summary.",
        )
    """
    
    def __init__(self, max_depth: int = 5):
        """
        Initialize the mesh coordinator.
        
        Args:
            max_depth: Maximum inter-agent call depth
        """
        self.config = get_config()
        self.executor = get_agent_executor()
        self.max_depth = max_depth
        self._sessions: Dict[str, MeshSession] = {}
        
    async def start_session(
        self,
        initial_agent: str,
        system_prompt: str,
        user_prompt: str,
        working_directory: Optional[str] = None,
    ) -> MeshSession:
        """
        Start a new mesh execution session.
        
        Args:
            initial_agent: The agent to start with
            system_prompt: System prompt for the session
            user_prompt: User prompt/task
            working_directory: Optional working directory
            
        Returns:
            MeshSession with execution results
        """
        session = MeshSession(
            id=str(uuid.uuid4()),
            initial_agent=initial_agent,
            initial_prompt=user_prompt,
            max_depth=self.max_depth,
        )
        self._sessions[session.id] = session
        
        # Execute the initial agent
        context = ExecutionContext(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            working_directory=working_directory,
        )
        
        result = await self.executor.execute(initial_agent, context)
        
        # Record the initial call
        call = InterAgentCall(
            id=str(uuid.uuid4()),
            caller_agent="user",
            target_agent=initial_agent,
            prompt=user_prompt,
            response=result.response,
            success=result.success,
            duration_ms=result.duration_ms,
            depth=0,
        )
        session.calls.append(call)
        
        # Check if the response contains delegation requests
        # In a full implementation, we would parse the response for
        # inter-agent call requests and handle them recursively
        
        session.final_response = result.response
        return session
        
    async def delegate(
        self,
        session_id: str,
        caller_agent: str,
        target_agent: str,
        prompt: str,
        working_directory: Optional[str] = None,
    ) -> ExecutionResult:
        """
        Delegate a task from one agent to another.
        
        Args:
            session_id: Current session ID
            caller_agent: Agent making the request
            target_agent: Agent to execute the task
            prompt: The task prompt
            working_directory: Optional working directory
            
        Returns:
            ExecutionResult from the target agent
        """
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
            
        # Check depth limit
        session.current_depth += 1
        if session.current_depth > session.max_depth:
            session.current_depth -= 1
            return ExecutionResult(
                success=False,
                response="",
                agent_name=target_agent,
                execution_method=self.executor._determine_execution_method(
                    self.config.get_agent(target_agent)
                ),
                duration_ms=0,
                error=f"Max call depth ({session.max_depth}) exceeded",
            )
            
        # Execute the target agent
        context = ExecutionContext(
            system_prompt=f"You are being called by {caller_agent} to assist with a task.",
            user_prompt=prompt,
            working_directory=working_directory,
        )
        
        result = await self.executor.execute(target_agent, context)
        
        # Record the call
        call = InterAgentCall(
            id=str(uuid.uuid4()),
            caller_agent=caller_agent,
            target_agent=target_agent,
            prompt=prompt,
            response=result.response,
            success=result.success,
            duration_ms=result.duration_ms,
            depth=session.current_depth,
        )
        session.calls.append(call)
        
        session.current_depth -= 1
        return result
        
    def get_session(self, session_id: str) -> Optional[MeshSession]:
        """Get a session by ID."""
        return self._sessions.get(session_id)
        
    def get_session_calls(self, session_id: str) -> List[InterAgentCall]:
        """Get all calls from a session."""
        session = self._sessions.get(session_id)
        return session.calls if session else []
        
    def get_available_agents(self) -> List[str]:
        """Get list of available agents for delegation."""
        return self.config.get_agent_names()
        
    def create_delegation_prompt(
        self,
        caller: str,
        target: str,
        task: str,
        context: Optional[str] = None,
    ) -> str:
        """
        Create a prompt for inter-agent delegation.
        
        Args:
            caller: The agent making the request
            target: The target agent
            task: The task to delegate
            context: Optional context
            
        Returns:
            Formatted delegation prompt
        """
        agent_info = self.config.get_agent(target)
        
        prompt = f"""You ({target}) are being called by {caller} to help with a task.

Task: {task}
"""
        
        if context:
            prompt += f"\nContext from {caller}:\n{context}\n"
            
        prompt += f"""
Your strengths: {', '.join(agent_info.strengths[:2])}
Your capabilities: {', '.join(agent_info.capabilities[:3])}

Please complete this task to the best of your ability."""
        
        return prompt


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_mesh = None


def get_mesh_coordinator() -> MeshCoordinator:
    """Get the global mesh coordinator instance."""
    global _mesh
    if _mesh is None:
        _mesh = MeshCoordinator()
    return _mesh
