"""
LastAgent Agent Executor

Executes agents via their native CLI/SDK.
AGENTS ARE NOT LLMs - they have agentic capabilities (tools, file access, execution).

All agents are invoked via CLI subprocess:
  - claude -p "prompt" --output-format text
  - gemini prompt "..."
  - aider --message "..."
  - codex --full-auto "..."
  - goose run "..."
"""

import asyncio
import shutil
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from .config import get_config, AgentConfig

# Enterprise structured logging
try:
    from src.observability import get_logger, log_error
except ImportError:
    from .observability import get_logger, log_error


class ExecutionMethod(Enum):
    """How to execute an agent - CLI ONLY."""
    CLI_SUBPROCESS = "cli"  # All agents use CLI


@dataclass
class ExecutionContext:
    """Context for agent execution."""
    system_prompt: str
    user_prompt: str
    working_directory: Optional[str] = None
    timeout: int = 300  # seconds
    allowed_tools: Optional[List[str]] = None


@dataclass
class ExecutionResult:
    """Result of agent execution."""
    success: bool
    response: str
    agent_name: str
    execution_method: ExecutionMethod
    duration_ms: int
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class AgentExecutor:
    """
    Executes agents via their native CLI/SDK.
    
    CRITICAL: Agents are NOT LLMs. They have agentic capabilities:
    - Tools and file system access
    - Autonomous execution
    - Agentic loops
    
    All execution is via CLI subprocess (no HTTP API calls).
    """
    
    def __init__(self):
        """Initialize the executor."""
        self.config = get_config()
        self._log = get_logger("executor")
        
    def _is_cli_available(self, command: str) -> bool:
        """Check if a CLI command is available on the system."""
        return shutil.which(command) is not None
        
    async def execute(
        self,
        agent_name: str,
        context: ExecutionContext
    ) -> ExecutionResult:
        """
        Execute an agent via its CLI.
        
        Args:
            agent_name: Name of the agent to execute
            context: Execution context with prompts and settings
            
        Returns:
            ExecutionResult with the response
        """
        start_time = time.perf_counter()
        
        try:
            agent = self.config.get_agent(agent_name)
            
            # Check if CLI is available
            cli_command = agent.command or agent_name
            if not self._is_cli_available(cli_command):
                self._log.warning(
                    "cli_not_available",
                    agent=agent_name,
                    command=cli_command,
                )
                return ExecutionResult(
                    success=False,
                    response="",
                    agent_name=agent_name,
                    execution_method=ExecutionMethod.CLI_SUBPROCESS,
                    duration_ms=0,
                    error=f"Agent CLI not installed: {cli_command}. Install it to use this agent.",
                )
            
            # Log CLI execution start
            self._log.info(
                "cli_execution_started",
                agent=agent_name,
                command=cli_command,
                method="CLI_SUBPROCESS",
            )
            
            # Route to the appropriate CLI handler
            result = await self._execute_cli(agent_name, agent, context)
            
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            result.duration_ms = duration_ms
            
            # Log CLI execution complete
            self._log.info(
                "cli_execution_completed",
                agent=agent_name,
                success=result.success,
                duration_ms=duration_ms,
            )
            return result
            
        except KeyError:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            log_error(
                "agent_not_found",
                error_type="KeyError",
                error_message=f"Unknown agent: {agent_name}",
                agent=agent_name,
            )
            return ExecutionResult(
                success=False,
                response="",
                agent_name=agent_name,
                execution_method=ExecutionMethod.CLI_SUBPROCESS,
                duration_ms=duration_ms,
                error=f"Unknown agent: {agent_name}",
            )
        except Exception as e:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            log_error(
                "cli_execution_failed",
                error_type=type(e).__name__,
                error_message=str(e),
                agent=agent_name,
                duration_ms=duration_ms,
            )
            return ExecutionResult(
                success=False,
                response="",
                agent_name=agent_name,
                execution_method=ExecutionMethod.CLI_SUBPROCESS,
                duration_ms=duration_ms,
                error=str(e),
            )
            
    async def _execute_cli(
        self,
        agent_name: str,
        agent: AgentConfig,
        context: ExecutionContext
    ) -> ExecutionResult:
        """Route to the appropriate CLI handler."""
        if agent_name == "claude":
            return await self._execute_claude_cli(agent, context)
        elif agent_name == "gemini":
            return await self._execute_gemini_cli(agent, context)
        elif agent_name == "aider":
            return await self._execute_aider(agent, context)
        elif agent_name == "codex":
            return await self._execute_codex(agent, context)
        elif agent_name == "goose":
            return await self._execute_goose(agent, context)
        else:
            return ExecutionResult(
                success=False,
                response="",
                agent_name=agent_name,
                execution_method=ExecutionMethod.CLI_SUBPROCESS,
                duration_ms=0,
                error=f"No CLI handler for agent: {agent_name}",
            )

    async def _execute_claude_cli(
        self,
        agent: AgentConfig,
        context: ExecutionContext
    ) -> ExecutionResult:
        """
        Execute Claude via CLI.
        
        Claude CLI is an AGENT with:
        - File system access
        - Tool use
        - Autonomous execution
        
        Pattern from seedpy/agents_router/claude_agent/claude_cli_agent.py
        """
        # Build command: claude -p "prompt" --output-format text
        cmd = ["claude", "-p", context.user_prompt, "--output-format", "text"]
        
        # Add system prompt if provided
        if context.system_prompt:
            cmd.extend(["--append-system-prompt", context.system_prompt])
        
        # Auto-accept edits for autonomous mode
        cmd.extend(["--permission-mode", "bypassPermissions"])
        
        cwd = context.working_directory or "."
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=context.timeout
            )
            
            response = stdout.decode() if stdout else ""
            stderr_text = stderr.decode() if stderr else ""
            
            # Handle warnings vs errors
            if stderr_text and process.returncode != 0:
                stderr_lower = stderr_text.lower()
                if not ("warn:" in stderr_lower or "warning:" in stderr_lower):
                    return ExecutionResult(
                        success=False,
                        response=response,
                        agent_name="claude",
                        execution_method=ExecutionMethod.CLI_SUBPROCESS,
                        duration_ms=0,
                        error=f"Claude CLI error: {stderr_text}",
                        metadata={"stderr": stderr_text},
                    )
            
            return ExecutionResult(
                success=process.returncode == 0,
                response=response,
                agent_name="claude",
                execution_method=ExecutionMethod.CLI_SUBPROCESS,
                duration_ms=0,
                error=None if process.returncode == 0 else f"Exit code: {process.returncode}",
            )
        except asyncio.TimeoutError:
            return ExecutionResult(
                success=False,
                response="",
                agent_name="claude",
                execution_method=ExecutionMethod.CLI_SUBPROCESS,
                duration_ms=context.timeout * 1000,
                error="Execution timeout",
            )
            
    async def _execute_gemini_cli(
        self,
        agent: AgentConfig,
        context: ExecutionContext
    ) -> ExecutionResult:
        """
        Execute Gemini via CLI.
        
        Gemini CLI (v0.18+) supports:
          gemini "your prompt here"   # Positional prompt
          gemini -y "prompt"          # YOLO mode (auto-accept)
        """
        # Combine system and user prompt
        full_prompt = context.user_prompt
        if context.system_prompt:
            full_prompt = f"{context.system_prompt}\n\n{context.user_prompt}"
        
        # Use positional prompt with --yolo for autonomous mode
        cmd = ["gemini", "--yolo", full_prompt]
        cwd = context.working_directory or "."
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=context.timeout
            )
            
            response = stdout.decode() if stdout else ""
            
            return ExecutionResult(
                success=process.returncode == 0,
                response=response,
                agent_name="gemini",
                execution_method=ExecutionMethod.CLI_SUBPROCESS,
                duration_ms=0,
                error=None if process.returncode == 0 else f"Exit code: {process.returncode}",
            )
        except asyncio.TimeoutError:
            return ExecutionResult(
                success=False,
                response="",
                agent_name="gemini",
                execution_method=ExecutionMethod.CLI_SUBPROCESS,
                duration_ms=context.timeout * 1000,
                error="Execution timeout",
            )
            
    async def _execute_aider(
        self,
        agent: AgentConfig,
        context: ExecutionContext
    ) -> ExecutionResult:
        """Execute Aider CLI - git-aware code editing agent."""
        cmd = ["aider", "--message", context.user_prompt, "--yes"]
        cwd = context.working_directory or "."
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=context.timeout
            )
            
            response = stdout.decode() if stdout else ""
            if stderr:
                response += f"\n[stderr]: {stderr.decode()}"
                
            return ExecutionResult(
                success=process.returncode == 0,
                response=response,
                agent_name="aider",
                execution_method=ExecutionMethod.CLI_SUBPROCESS,
                duration_ms=0,
                error=None if process.returncode == 0 else f"Exit code: {process.returncode}",
            )
        except asyncio.TimeoutError:
            return ExecutionResult(
                success=False,
                response="",
                agent_name="aider",
                execution_method=ExecutionMethod.CLI_SUBPROCESS,
                duration_ms=context.timeout * 1000,
                error="Execution timeout",
            )
            
    async def _execute_codex(
        self,
        agent: AgentConfig,
        context: ExecutionContext
    ) -> ExecutionResult:
        """Execute Codex CLI - sandboxed autonomous coding agent."""
        cmd = ["codex", "--full-auto", context.user_prompt]
        cwd = context.working_directory or "."
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=context.timeout
            )
            
            response = stdout.decode() if stdout else ""
            
            return ExecutionResult(
                success=process.returncode == 0,
                response=response,
                agent_name="codex",
                execution_method=ExecutionMethod.CLI_SUBPROCESS,
                duration_ms=0,
                error=None if process.returncode == 0 else f"Exit code: {process.returncode}",
            )
        except asyncio.TimeoutError:
            return ExecutionResult(
                success=False,
                response="",
                agent_name="codex",
                execution_method=ExecutionMethod.CLI_SUBPROCESS,
                duration_ms=context.timeout * 1000,
                error="Execution timeout",
            )
            
    async def _execute_goose(
        self,
        agent: AgentConfig,
        context: ExecutionContext
    ) -> ExecutionResult:
        """Execute Goose CLI - multi-step workflow agent."""
        cmd = ["goose", "run", context.user_prompt]
        cwd = context.working_directory or "."
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=context.timeout
            )
            
            response = stdout.decode() if stdout else ""
            
            return ExecutionResult(
                success=process.returncode == 0,
                response=response,
                agent_name="goose",
                execution_method=ExecutionMethod.CLI_SUBPROCESS,
                duration_ms=0,
                error=None if process.returncode == 0 else f"Exit code: {process.returncode}",
            )
        except asyncio.TimeoutError:
            return ExecutionResult(
                success=False,
                response="",
                agent_name="goose",
                execution_method=ExecutionMethod.CLI_SUBPROCESS,
                duration_ms=context.timeout * 1000,
                error="Execution timeout",
            )


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_executor = None


def get_agent_executor() -> AgentExecutor:
    """Get the global agent executor instance."""
    global _executor
    if _executor is None:
        _executor = AgentExecutor()
    return _executor
