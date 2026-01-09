"""
Tests for GodAgent Mesh Coordinator
"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.mesh import (
    MeshCoordinator,
    MeshSession,
    InterAgentCall,
    get_mesh_coordinator,
)
from src.executor import ExecutionContext, ExecutionResult


class TestInterAgentCall:
    """Tests for InterAgentCall dataclass."""
    
    def test_call_creation(self):
        """Test creating an inter-agent call record."""
        call = InterAgentCall(
            id="test-123",
            caller_agent="claude",
            target_agent="gemini",
            prompt="Research this topic",
        )
        
        assert call.caller_agent == "claude"
        assert call.target_agent == "gemini"
        assert call.depth == 0
        

class TestMeshSession:
    """Tests for MeshSession dataclass."""
    
    def test_session_creation(self):
        """Test creating a mesh session."""
        session = MeshSession(
            id="session-123",
            initial_agent="claude",
            initial_prompt="Do something complex",
        )
        
        assert session.initial_agent == "claude"
        assert session.current_depth == 0
        assert len(session.calls) == 0


class TestMeshCoordinator:
    """Tests for MeshCoordinator class."""
    
    @pytest.fixture
    def mesh(self):
        """Create a MeshCoordinator instance."""
        return MeshCoordinator(max_depth=3)
    
    def test_mesh_initialization(self, mesh):
        """Test that mesh initializes correctly."""
        assert mesh.max_depth == 3
        assert mesh.config is not None
        assert mesh.executor is not None
        
    def test_get_available_agents(self, mesh):
        """Test getting available agents."""
        agents = mesh.get_available_agents()
        
        assert isinstance(agents, list)
        assert len(agents) > 0
        assert "claude" in agents
        
    def test_create_delegation_prompt(self, mesh):
        """Test creating a delegation prompt."""
        prompt = mesh.create_delegation_prompt(
            caller="claude",
            target="gemini",
            task="Find the latest AI news",
            context="We're researching trends",
        )
        
        assert "claude" in prompt
        assert "gemini" in prompt
        assert "Find the latest AI news" in prompt
        assert "Research" in prompt or "trends" in prompt
        
    @pytest.mark.asyncio
    async def test_start_session_returns_session(self, mesh):
        """Test that start_session returns a session."""
        session = await mesh.start_session(
            initial_agent="claude",
            system_prompt="You are helpful.",
            user_prompt="Say hello",
        )
        
        assert isinstance(session, MeshSession)
        assert session.initial_agent == "claude"
        assert len(session.calls) >= 1
        
    @pytest.mark.asyncio
    async def test_session_records_initial_call(self, mesh):
        """Test that session records the initial call."""
        session = await mesh.start_session(
            initial_agent="gemini",
            system_prompt="",
            user_prompt="Test prompt",
        )
        
        assert len(session.calls) >= 1
        first_call = session.calls[0]
        assert first_call.caller_agent == "user"
        assert first_call.target_agent == "gemini"
        
    def test_get_session(self, mesh):
        """Test getting a session by ID."""
        # Session should not exist
        session = mesh.get_session("nonexistent")
        assert session is None
        
    @pytest.mark.asyncio
    async def test_get_session_after_start(self, mesh):
        """Test getting a session after starting it."""
        started = await mesh.start_session(
            initial_agent="claude",
            system_prompt="",
            user_prompt="Test",
        )
        
        retrieved = mesh.get_session(started.id)
        assert retrieved is not None
        assert retrieved.id == started.id


class TestGlobalMesh:
    """Tests for global mesh singleton."""
    
    def test_get_mesh_coordinator_returns_instance(self):
        """Test that get_mesh_coordinator returns an instance."""
        mesh = get_mesh_coordinator()
        assert isinstance(mesh, MeshCoordinator)
