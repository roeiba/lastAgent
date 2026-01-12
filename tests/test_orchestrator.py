"""
Tests for LastAgent Orchestrator
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch
import sys

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.orchestrator import (
    Orchestrator,
    Task,
    TaskStatus,
    ApprovalMode,
    AgentSelection,
    ExecutionResult,
    Decision,
    get_orchestrator,
)


class TestTask:
    """Tests for Task dataclass."""
    
    def test_task_creation(self):
        """Test creating a task."""
        task = Task(
            id="test-123",
            system_prompt="You are a helpful assistant.",
            user_prompt="Write hello world in Python.",
        )
        
        assert task.id == "test-123"
        assert task.system_prompt == "You are a helpful assistant."
        assert task.user_prompt == "Write hello world in Python."
        assert task.status == TaskStatus.PENDING
        assert task.working_directory is None
        
    def test_task_with_working_directory(self):
        """Test task with working directory."""
        task = Task(
            id="test-456",
            system_prompt="",
            user_prompt="",
            working_directory="/path/to/project",
        )
        
        assert task.working_directory == "/path/to/project"


class TestAgentSelection:
    """Tests for AgentSelection dataclass."""
    
    def test_selection_creation(self):
        """Test creating an agent selection."""
        selection = AgentSelection(
            selected_agent="claude",
            confidence=0.95,
            reasoning="Claude is best for coding tasks.",
        )
        
        assert selection.selected_agent == "claude"
        assert selection.confidence == 0.95
        assert "Claude" in selection.reasoning


class TestOrchestrator:
    """Tests for Orchestrator class."""
    
    @pytest.fixture
    def orchestrator(self):
        """Create an Orchestrator instance."""
        return Orchestrator()
    
    def test_orchestrator_initialization(self, orchestrator):
        """Test that orchestrator initializes correctly."""
        assert orchestrator.config is not None
        assert orchestrator._log is not None
        
    def test_get_available_agents(self, orchestrator):
        """Test getting available agents."""
        agents = orchestrator.get_available_agents()
        
        assert isinstance(agents, list)
        assert len(agents) > 0
        assert "claude" in agents
        assert "gemini" in agents
        
    def test_get_agent_info(self, orchestrator):
        """Test getting agent info."""
        info = orchestrator.get_agent_info("claude")
        
        assert info.display_name == "Claude Agent"
        assert "coding" in info.capabilities
        
    def test_get_agent_info_not_found(self, orchestrator):
        """Test KeyError for unknown agent."""
        with pytest.raises(KeyError):
            orchestrator.get_agent_info("unknown_agent")
            
    @pytest.mark.asyncio
    async def test_process_task_returns_result(self, orchestrator):
        """Test that process_task returns an ExecutionResult."""
        result = await orchestrator.process_task(
            system_prompt="You are a helpful assistant.",
            user_prompt="Write hello world.",
        )
        
        assert isinstance(result, ExecutionResult)
        assert result.task_id
        assert result.agent
        assert result.success
        
    @pytest.mark.asyncio
    async def test_process_task_default_agent_selection(self, orchestrator):
        """Test that default agent is selected (before Phase 2)."""
        result = await orchestrator.process_task(
            system_prompt="",
            user_prompt="Test prompt",
        )
        
        # Default is Claude until council is implemented
        assert result.agent == "claude"
        
    @pytest.mark.asyncio
    async def test_process_task_logs_decision(self, orchestrator):
        """Test that processing a task logs a decision."""
        initial_count = len(orchestrator.get_decisions())
        
        await orchestrator.process_task(
            system_prompt="",
            user_prompt="Test prompt",
        )
        
        decisions = orchestrator.get_decisions()
        assert len(decisions) == initial_count + 1
        
        last_decision = decisions[-1]
        assert last_decision.decision_type == "AGENT_SELECTION"
        
    @pytest.mark.asyncio
    async def test_process_task_updates_status(self, orchestrator):
        """Test that task status updates during processing."""
        result = await orchestrator.process_task(
            system_prompt="",
            user_prompt="Test prompt",
        )
        
        # Task should be completed
        task = orchestrator._tasks[result.task_id]
        assert task.status == TaskStatus.COMPLETED
        
    @pytest.mark.asyncio
    async def test_process_task_with_approval_mode(self, orchestrator):
        """Test processing with explicit approval mode."""
        result = await orchestrator.process_task(
            system_prompt="",
            user_prompt="Test prompt",
            approval_mode=ApprovalMode.AUTO,
        )
        
        assert result.success
        
    def test_get_decisions_empty(self, orchestrator):
        """Test getting decisions when none exist."""
        decisions = orchestrator.get_decisions()
        assert isinstance(decisions, list)
        
    def test_get_decisions_with_limit(self, orchestrator):
        """Test getting decisions with limit."""
        decisions = orchestrator.get_decisions(limit=10)
        assert len(decisions) <= 10


class TestGlobalOrchestrator:
    """Tests for global orchestrator singleton."""
    
    def test_get_orchestrator_returns_instance(self):
        """Test that get_orchestrator returns an Orchestrator."""
        orch = get_orchestrator()
        assert isinstance(orch, Orchestrator)
        
    def test_get_orchestrator_is_singleton(self):
        """Test that get_orchestrator returns same instance."""
        orch1 = get_orchestrator()
        orch2 = get_orchestrator()
        assert orch1 is orch2
