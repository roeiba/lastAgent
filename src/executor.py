"""
GodAgent Agent Executor

Executes selected agents with original prompts.
Supports direct API calls, OpenRouter, and CLI subprocess execution.
Integrates with agents-parliament MCP servers for unified interface.
"""

import asyncio
import subprocess
import sys
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from .config import get_config, AgentConfig


class ExecutionMethod(Enum):
    """How to execute an agent."""
    DIRECT_API = "direct_api"      # Direct API call (Anthropic, Google, etc.)
    OPENROUTER = "openrouter"      # Via OpenRouter
    CLI_SUBPROCESS = "cli"         # CLI subprocess (aider, codex, goose)
    MCP_SERVER = "mcp"             # Via MCP server


@dataclass
class ExecutionContext:
    """Context for agent execution."""
    system_prompt: str
    user_prompt: str
    working_directory: Optional[str] = None
    timeout: int = 300  # seconds
    model_override: Optional[str] = None
    allowed_tools: Optional[List[str]] = None


@dataclass
class ExecutionResult:
    """Result of agent execution."""
    success: bool
    response: str
    agent_name: str
    execution_method: ExecutionMethod
    duration_ms: int
    model_used: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class AgentExecutor:
    """
    Executes agents with the original prompts.
    
    This is the core execution engine that:
    - Routes to the correct execution method based on agent type
    - Handles API calls for cloud agents (Claude, Gemini, GPT)
    - Handles OpenRouter for unified LLM access
    - Handles CLI subprocess for local agents (Aider, Codex, Goose)
    - Supports MCP server integration
    
    Usage:
        executor = AgentExecutor()
        result = await executor.execute(
            agent_name="claude",
            context=ExecutionContext(
                system_prompt="You are a helpful assistant.",
                user_prompt="Write hello world in Python."
            )
        )
    """
    
    def __init__(self):
        """Initialize the executor."""
        self.config = get_config()
        self._http_client = None
        
    async def execute(
        self,
        agent_name: str,
        context: ExecutionContext
    ) -> ExecutionResult:
        """
        Execute an agent with the given context.
        
        Args:
            agent_name: Name of the agent to execute
            context: Execution context with prompts and settings
            
        Returns:
            ExecutionResult with the response
        """
        start_time = time.time()
        
        try:
            agent = self.config.get_agent(agent_name)
            method = self._determine_execution_method(agent)
            
            if method == ExecutionMethod.DIRECT_API:
                result = await self._execute_direct_api(agent_name, agent, context)
            elif method == ExecutionMethod.OPENROUTER:
                result = await self._execute_openrouter(agent_name, agent, context)
            elif method == ExecutionMethod.CLI_SUBPROCESS:
                result = await self._execute_cli(agent_name, agent, context)
            else:
                result = await self._execute_mcp(agent_name, agent, context)
                
            duration_ms = int((time.time() - start_time) * 1000)
            result.duration_ms = duration_ms
            return result
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return ExecutionResult(
                success=False,
                response="",
                agent_name=agent_name,
                execution_method=ExecutionMethod.DIRECT_API,
                duration_ms=duration_ms,
                error=str(e),
            )
            
    def _determine_execution_method(self, agent: AgentConfig) -> ExecutionMethod:
        """Determine the best execution method for an agent."""
        if agent.type == "cli":
            return ExecutionMethod.CLI_SUBPROCESS
        elif agent.type == "openrouter":
            return ExecutionMethod.OPENROUTER
        elif agent.type == "api":
            # Could use MCP if available, otherwise direct API
            if agent.mcp_server:
                return ExecutionMethod.MCP_SERVER
            return ExecutionMethod.DIRECT_API
        else:
            return ExecutionMethod.OPENROUTER  # Fallback
            
    async def _execute_direct_api(
        self,
        agent_name: str,
        agent: AgentConfig,
        context: ExecutionContext
    ) -> ExecutionResult:
        """Execute via direct API call."""
        import os
        
        model = context.model_override or agent.default_model
        
        if agent.provider == "anthropic":
            return await self._execute_anthropic(agent_name, model, context)
        elif agent.provider == "google":
            return await self._execute_google(agent_name, model, context)
        else:
            # Fallback to OpenRouter
            return await self._execute_openrouter(agent_name, agent, context)
            
    async def _execute_anthropic(
        self,
        agent_name: str,
        model: str,
        context: ExecutionContext
    ) -> ExecutionResult:
        """Execute via Anthropic API."""
        import os
        
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return ExecutionResult(
                success=False,
                response="",
                agent_name=agent_name,
                execution_method=ExecutionMethod.DIRECT_API,
                duration_ms=0,
                model_used=model,
                error="ANTHROPIC_API_KEY not set",
            )
            
        async with httpx.AsyncClient(timeout=context.timeout) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": model,
                    "max_tokens": 8192,
                    "system": context.system_prompt,
                    "messages": [{"role": "user", "content": context.user_prompt}],
                },
            )
            response.raise_for_status()
            data = response.json()
            
            # Extract text from content blocks
            content = data.get("content", [])
            text_parts = [c.get("text", "") for c in content if c.get("type") == "text"]
            response_text = "\n".join(text_parts)
            
            return ExecutionResult(
                success=True,
                response=response_text,
                agent_name=agent_name,
                execution_method=ExecutionMethod.DIRECT_API,
                duration_ms=0,
                model_used=model,
            )
            
    async def _execute_google(
        self,
        agent_name: str,
        model: str,
        context: ExecutionContext
    ) -> ExecutionResult:
        """Execute via Google Generative AI API."""
        import os
        
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            return ExecutionResult(
                success=False,
                response="",
                agent_name=agent_name,
                execution_method=ExecutionMethod.DIRECT_API,
                duration_ms=0,
                model_used=model,
                error="GOOGLE_API_KEY not set",
            )
            
        # Format prompt with system context
        full_prompt = f"{context.system_prompt}\n\n{context.user_prompt}"
        
        async with httpx.AsyncClient(timeout=context.timeout) as client:
            response = await client.post(
                f"https://generativelanguage.googleapis.com/v1/models/{model}:generateContent",
                headers={"Content-Type": "application/json"},
                params={"key": api_key},
                json={
                    "contents": [{"parts": [{"text": full_prompt}]}],
                },
            )
            response.raise_for_status()
            data = response.json()
            
            # Extract text from candidates
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                response_text = "".join(p.get("text", "") for p in parts)
            else:
                response_text = ""
                
            return ExecutionResult(
                success=True,
                response=response_text,
                agent_name=agent_name,
                execution_method=ExecutionMethod.DIRECT_API,
                duration_ms=0,
                model_used=model,
            )
            
    async def _execute_openrouter(
        self,
        agent_name: str,
        agent: AgentConfig,
        context: ExecutionContext
    ) -> ExecutionResult:
        """Execute via OpenRouter."""
        import os
        
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            return ExecutionResult(
                success=False,
                response="",
                agent_name=agent_name,
                execution_method=ExecutionMethod.OPENROUTER,
                duration_ms=0,
                error="OPENROUTER_API_KEY not set",
            )
            
        model = context.model_override or agent.default_model
        
        messages = []
        if context.system_prompt:
            messages.append({"role": "system", "content": context.system_prompt})
        messages.append({"role": "user", "content": context.user_prompt})
        
        async with httpx.AsyncClient(timeout=context.timeout) as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": messages,
                },
            )
            response.raise_for_status()
            data = response.json()
            
            choices = data.get("choices", [])
            if choices:
                response_text = choices[0].get("message", {}).get("content", "")
            else:
                response_text = ""
                
            return ExecutionResult(
                success=True,
                response=response_text,
                agent_name=agent_name,
                execution_method=ExecutionMethod.OPENROUTER,
                duration_ms=0,
                model_used=model,
            )
            
    async def _execute_cli(
        self,
        agent_name: str,
        agent: AgentConfig,
        context: ExecutionContext
    ) -> ExecutionResult:
        """Execute via CLI subprocess."""
        if agent_name == "aider":
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
                error=f"Unknown CLI agent: {agent_name}",
            )
            
    async def _execute_aider(
        self,
        agent: AgentConfig,
        context: ExecutionContext
    ) -> ExecutionResult:
        """Execute aider CLI."""
        cmd = ["aider", "--message", context.user_prompt, "--yes"]
        
        if context.working_directory:
            cwd = context.working_directory
        else:
            cwd = "."
            
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
        """Execute codex CLI."""
        cmd = ["codex", "--full-auto", context.user_prompt]
        
        if context.working_directory:
            cwd = context.working_directory
        else:
            cwd = "."
            
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
        """Execute goose CLI."""
        cmd = ["goose", "run", context.user_prompt]
        
        if context.working_directory:
            cwd = context.working_directory
        else:
            cwd = "."
            
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
            
    async def _execute_mcp(
        self,
        agent_name: str,
        agent: AgentConfig,
        context: ExecutionContext
    ) -> ExecutionResult:
        """Execute via MCP server (placeholder for future integration)."""
        # For now, fall back to direct API
        # In full implementation, would connect to MCP server
        return await self._execute_direct_api(agent_name, agent, context)


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
