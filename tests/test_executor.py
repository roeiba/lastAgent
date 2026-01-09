"""
Tests for GodAgent Agent Executor
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
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
            execution_method=ExecutionMethod.DIRECT_API,
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
            execution_method=ExecutionMethod.OPENROUTER,
            duration_ms=50,
            error="API key not set",
        )
        
        assert not result.success
        assert result.error == "API key not set"


class TestAgentExecutor:
    """Tests for AgentExecutor class."""
    
    @pytest.fixture
    def executor(self):
        """Create an AgentExecutor instance."""
        return AgentExecutor()
    
    def test_executor_initialization(self, executor):
        """Test that executor initializes correctly."""
        assert executor.config is not None
        
    def test_determine_execution_method_cli(self, executor):
        """Test determining CLI execution method."""
        aider = executor.config.get_agent("aider")
        method = executor._determine_execution_method(aider)
        
        assert method == ExecutionMethod.CLI_SUBPROCESS
        
    def test_determine_execution_method_api(self, executor):
        """Test determining API execution method."""
        claude = executor.config.get_agent("claude")
        method = executor._determine_execution_method(claude)
        
        # Claude has MCP server configured, so it should use MCP
        assert method in [ExecutionMethod.MCP_SERVER, ExecutionMethod.DIRECT_API]
        
    def test_determine_execution_method_openrouter(self, executor):
        """Test determining OpenRouter execution method."""
        grok = executor.config.get_agent("grok")
        method = executor._determine_execution_method(grok)
        
        assert method == ExecutionMethod.OPENROUTER
        
    @pytest.mark.asyncio
    async def test_execute_returns_result(self, executor):
        """Test that execute returns an ExecutionResult."""
        context = ExecutionContext(
            system_prompt="",
            user_prompt="Test prompt",
        )
        
        # This will fail without API keys, but should return a result
        result = await executor.execute("claude", context)
        
        assert isinstance(result, ExecutionResult)
        assert result.agent_name == "claude"
        
    @pytest.mark.asyncio
    async def test_execute_handles_missing_api_key(self, executor):
        """Test that execute handles missing API keys gracefully."""
        context = ExecutionContext(
            system_prompt="",
            user_prompt="Test",
        )
        
        with patch.dict('os.environ', {}, clear=True):
            result = await executor.execute("claude", context)
            
        # Should fail gracefully with an error
        assert not result.success or result.error is not None


class TestGlobalExecutor:
    """Tests for global executor singleton."""
    
    def test_get_agent_executor_returns_instance(self):
        """Test that get_agent_executor returns an instance."""
        executor = get_agent_executor()
        assert isinstance(executor, AgentExecutor)
