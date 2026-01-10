"""
Tests for LastAgent Agent Executor

CRITICAL: Agents are NOT LLMs. All execution is via CLI subprocess.
"""

import pytest
from pathlib import Path
from unittest.mock import patch
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.executor import (
    AgentExecutor,
    ExecutionContext,
    ExecutionResult,
    ExecutionMethod,
    get_agent_executor,
)


class TestExecutionContext:
    """Tests for ExecutionContext dataclass."""
    
    def test_context_creation(self):
        """Test creating an execution context."""
        context = ExecutionContext(
            system_prompt="You are a helpful assistant.",
            user_prompt="Write hello world.",
        )
        
        assert context.system_prompt == "You are a helpful assistant."
        assert context.user_prompt == "Write hello world."
        assert context.timeout == 300  # Default
        
    def test_context_with_working_directory(self):
        """Test context with working directory."""
        context = ExecutionContext(
            system_prompt="",
            user_prompt="",
            working_directory="/path/to/project",
        )
        
        assert context.working_directory == "/path/to/project"


class TestExecutionResult:
    """Tests for ExecutionResult dataclass."""
    
    def test_successful_result(self):
        """Test creating a successful result."""
        result = ExecutionResult(
            success=True,
            response="Hello, World!",
            agent_name="claude",
            execution_method=ExecutionMethod.CLI_SUBPROCESS,
            duration_ms=150,
        )
        
        assert result.success
        assert result.response == "Hello, World!"
        assert result.agent_name == "claude"
        assert result.error is None
        
    def test_failed_result(self):
        """Test creating a failed result."""
        result = ExecutionResult(
            success=False,
            response="",
            agent_name="gemini",
            execution_method=ExecutionMethod.CLI_SUBPROCESS,
            duration_ms=50,
            error="CLI not installed",
        )
        
        assert not result.success
        assert result.error == "CLI not installed"


class TestAgentExecutor:
    """Tests for AgentExecutor class."""
    
    @pytest.fixture
    def executor(self):
        """Create an AgentExecutor instance."""
        return AgentExecutor()
    
    def test_executor_initialization(self, executor):
        """Test that executor initializes correctly."""
        assert executor.config is not None
    
    def test_is_cli_available(self, executor):
        """Test CLI availability check."""
        # 'python' should be available
        assert executor._is_cli_available("python") is True
        # Fake command should not be available
        assert executor._is_cli_available("definitely_not_a_real_command_12345") is False
    
    def test_all_agents_are_cli_type(self, executor):
        """Test that all agents have type=cli (agents are NOT LLMs)."""
        for name in executor.config.get_agent_names():
            agent = executor.config.get_agent(name)
            assert agent.type == "cli", f"Agent {name} should be type=cli, not {agent.type}"
        
    @pytest.mark.asyncio
    async def test_execute_returns_result(self, executor):
        """Test that execute returns an ExecutionResult."""
        context = ExecutionContext(
            system_prompt="",
            user_prompt="Test prompt",
        )
        
        # Execute will try CLI - result depends on CLI availability
        result = await executor.execute("claude", context)
        
        assert isinstance(result, ExecutionResult)
        assert result.agent_name == "claude"
        assert result.execution_method == ExecutionMethod.CLI_SUBPROCESS
        
    @pytest.mark.asyncio
    async def test_execute_unknown_agent(self, executor):
        """Test that unknown agent returns error."""
        context = ExecutionContext(
            system_prompt="",
            user_prompt="Test",
        )
        
        result = await executor.execute("unknown_agent", context)
        
        assert not result.success
        assert "Unknown agent" in result.error


class TestGlobalExecutor:
    """Tests for global executor singleton."""
    
    def test_get_agent_executor_returns_instance(self):
        """Test that get_agent_executor returns an instance."""
        executor = get_agent_executor()
        assert isinstance(executor, AgentExecutor)
