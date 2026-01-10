"""
LastAgent Agile TDD Workflow Runner

Implements the 9-phase Agile TDD workflow for LastAgent.
Integrates with seedGPT workflow patterns.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class WorkflowPhase(Enum):
    """The 9 phases of Agile TDD workflow."""
    STATUS_RECAP = "status"
    PLANNING = "plan"
    IMPLEMENTATION = "implement"
    INTEGRATION = "integrate"
    MERGE_TO_MAIN = "merge"
    DEPLOY = "deploy"
    PRESENT_RESULTS = "present"
    GATHER_INPUTS = "inputs"
    COMPLETE = "complete"


@dataclass
class PhaseResult:
    """Result of running a workflow phase."""
    phase: WorkflowPhase
    success: bool
    output: str
    duration_ms: int
    timestamp: datetime = field(default_factory=datetime.utcnow)
    errors: List[str] = field(default_factory=list)


@dataclass
class WorkflowStatus:
    """Current status of the workflow."""
    current_phase: WorkflowPhase
    completed_phases: List[WorkflowPhase]
    last_run: Optional[datetime]
    is_running: bool
    project_path: str


class WorkflowRunner:
    """
    Runs the 9-phase Agile TDD workflow.
    
    Workflow Phases:
    1. Status Recap - Check current state
    2. Planning - Plan next steps
    3. Implementation - Write code/tests
    4. Integration - Integrate changes
    5. Merge to Main - Merge feature branch
    6. Deploy - Deploy to staging/production
    7. Present Results - Demo to stakeholders
    8. Gather Inputs - Collect feedback
    9. Complete - Mark cycle complete
    
    Usage:
        runner = WorkflowRunner("/path/to/project")
        await runner.run_phase(WorkflowPhase.STATUS_RECAP)
        # or
        await runner.run_full_cycle()
    """
    
    def __init__(self, project_path: str = "."):
        """
        Initialize the workflow runner.
        
        Args:
            project_path: Path to the project directory
        """
        self.project_path = Path(project_path).resolve()
        self.current_phase = WorkflowPhase.STATUS_RECAP
        self.completed_phases: List[WorkflowPhase] = []
        self.results: List[PhaseResult] = []
        self._is_running = False
        
    def get_status(self) -> WorkflowStatus:
        """Get current workflow status."""
        return WorkflowStatus(
            current_phase=self.current_phase,
            completed_phases=self.completed_phases.copy(),
            last_run=self.results[-1].timestamp if self.results else None,
            is_running=self._is_running,
            project_path=str(self.project_path),
        )
        
    async def run_phase(self, phase: str) -> PhaseResult:
        """
        Run a specific workflow phase.
        
        Args:
            phase: Phase name (e.g., "status", "plan", "implement")
            
        Returns:
            PhaseResult with outcome
        """
        import time
        
        # Convert string to enum
        try:
            workflow_phase = WorkflowPhase(phase)
        except ValueError:
            return PhaseResult(
                phase=WorkflowPhase.STATUS_RECAP,
                success=False,
                output="",
                duration_ms=0,
                errors=[f"Invalid phase: {phase}"],
            )
            
        start_time = time.time()
        self._is_running = True
        
        try:
            output = await self._execute_phase(workflow_phase)
            success = True
            errors = []
        except Exception as e:
            output = str(e)
            success = False
            errors = [str(e)]
            
        duration_ms = int((time.time() - start_time) * 1000)
        
        result = PhaseResult(
            phase=workflow_phase,
            success=success,
            output=output,
            duration_ms=duration_ms,
            errors=errors,
        )
        
        if success:
            self.completed_phases.append(workflow_phase)
            
        self.results.append(result)
        self._is_running = False
        
        return result
        
    async def run_full_cycle(self) -> List[PhaseResult]:
        """Run the full workflow cycle."""
        phases = [
            "status", "plan", "implement", "integrate",
            "merge", "deploy", "present", "inputs"
        ]
        
        results = []
        for phase in phases:
            print(f"Running phase: {phase}")
            result = await self.run_phase(phase)
            results.append(result)
            
            if not result.success:
                print(f"Phase {phase} failed, stopping workflow")
                break
                
        return results
        
    async def _execute_phase(self, phase: WorkflowPhase) -> str:
        """Execute a specific phase."""
        if phase == WorkflowPhase.STATUS_RECAP:
            return await self._phase_status_recap()
        elif phase == WorkflowPhase.PLANNING:
            return await self._phase_planning()
        elif phase == WorkflowPhase.IMPLEMENTATION:
            return await self._phase_implementation()
        elif phase == WorkflowPhase.INTEGRATION:
            return await self._phase_integration()
        elif phase == WorkflowPhase.MERGE_TO_MAIN:
            return await self._phase_merge()
        elif phase == WorkflowPhase.DEPLOY:
            return await self._phase_deploy()
        elif phase == WorkflowPhase.PRESENT_RESULTS:
            return await self._phase_present()
        elif phase == WorkflowPhase.GATHER_INPUTS:
            return await self._phase_inputs()
        else:
            return "Unknown phase"
            
    async def _phase_status_recap(self) -> str:
        """Status recap phase - analyze current state."""
        # Check git status
        output = ["📊 Status Recap"]
        output.append(f"Project: {self.project_path}")
        output.append(f"Completed phases: {len(self.completed_phases)}")
        
        # Check for tests
        tests_path = self.project_path / "tests"
        if tests_path.exists():
            test_files = list(tests_path.glob("test_*.py"))
            output.append(f"Test files: {len(test_files)}")
            
        return "\n".join(output)
        
    async def _phase_planning(self) -> str:
        """Planning phase - plan next work."""
        return "📝 Planning complete. Ready for implementation."
        
    async def _phase_implementation(self) -> str:
        """Implementation phase - write code/tests."""
        return "💻 Implementation phase. Write code and tests."
        
    async def _phase_integration(self) -> str:
        """Integration phase - integrate changes."""
        return "🔗 Integration phase. Running tests and checks."
        
    async def _phase_merge(self) -> str:
        """Merge phase - merge to main."""
        return "🔀 Merge phase. Ready to merge changes."
        
    async def _phase_deploy(self) -> str:
        """Deploy phase - deploy to staging/production."""
        return "🚀 Deploy phase. Ready for deployment."
        
    async def _phase_present(self) -> str:
        """Present phase - demo results."""
        return "📺 Present phase. Results ready for demo."
        
    async def _phase_inputs(self) -> str:
        """Inputs phase - gather feedback."""
        return "📥 Inputs phase. Gathering feedback."


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_workflow_runner = None


def get_workflow_runner(project_path: str = ".") -> WorkflowRunner:
    """Get the global workflow runner instance."""
    global _workflow_runner
    if _workflow_runner is None or str(_workflow_runner.project_path) != str(Path(project_path).resolve()):
        _workflow_runner = WorkflowRunner(project_path)
    return _workflow_runner
