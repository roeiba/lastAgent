"""
Tests for LastAgent Workflow Runner
"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.workflow import (
    WorkflowRunner,
    WorkflowPhase,
    PhaseResult,
    WorkflowStatus,
    get_workflow_runner,
)


class TestWorkflowPhase:
    """Tests for WorkflowPhase enum."""
    
    def test_all_phases_defined(self):
        """Test that all 9 phases are defined."""
        phases = [
            WorkflowPhase.STATUS_RECAP,
            WorkflowPhase.PLANNING,
            WorkflowPhase.IMPLEMENTATION,
            WorkflowPhase.INTEGRATION,
            WorkflowPhase.MERGE_TO_MAIN,
            WorkflowPhase.DEPLOY,
            WorkflowPhase.PRESENT_RESULTS,
            WorkflowPhase.GATHER_INPUTS,
            WorkflowPhase.COMPLETE,
        ]
        assert len(phases) == 9


class TestPhaseResult:
    """Tests for PhaseResult dataclass."""
    
    def test_result_creation(self):
        """Test creating a phase result."""
        result = PhaseResult(
            phase=WorkflowPhase.PLANNING,
            success=True,
            output="Planning complete",
            duration_ms=100,
        )
        
        assert result.success
        assert result.phase == WorkflowPhase.PLANNING


class TestWorkflowRunner:
    """Tests for WorkflowRunner."""
    
    @pytest.fixture
    def runner(self):
        return WorkflowRunner(".")
    
    def test_initialization(self, runner):
        """Test runner initializes correctly."""
        assert runner.current_phase == WorkflowPhase.STATUS_RECAP
        assert len(runner.completed_phases) == 0
        
    def test_get_status(self, runner):
        """Test getting workflow status."""
        status = runner.get_status()
        
        assert isinstance(status, WorkflowStatus)
        assert status.current_phase == WorkflowPhase.STATUS_RECAP
        assert not status.is_running
        
    @pytest.mark.asyncio
    async def test_run_status_phase(self, runner):
        """Test running status recap phase."""
        result = await runner.run_phase("status")
        
        assert result.success
        assert result.phase == WorkflowPhase.STATUS_RECAP
        assert "Status Recap" in result.output
        
    @pytest.mark.asyncio
    async def test_run_planning_phase(self, runner):
        """Test running planning phase."""
        result = await runner.run_phase("plan")
        
        assert result.success
        assert result.phase == WorkflowPhase.PLANNING
        
    @pytest.mark.asyncio
    async def test_run_invalid_phase(self, runner):
        """Test running invalid phase returns error."""
        result = await runner.run_phase("invalid_phase")
        
        assert not result.success
        assert len(result.errors) > 0
        
    @pytest.mark.asyncio
    async def test_completed_phases_tracked(self, runner):
        """Test that completed phases are tracked."""
        await runner.run_phase("status")
        await runner.run_phase("plan")
        
        status = runner.get_status()
        assert len(status.completed_phases) == 2
        
    @pytest.mark.asyncio
    async def test_results_stored(self, runner):
        """Test that results are stored."""
        await runner.run_phase("status")
        
        assert len(runner.results) == 1
        assert runner.results[0].phase == WorkflowPhase.STATUS_RECAP


class TestGlobalRunner:
    """Tests for global runner singleton."""
    
    def test_get_workflow_runner(self):
        """Test getting workflow runner."""
        runner = get_workflow_runner(".")
        assert isinstance(runner, WorkflowRunner)
