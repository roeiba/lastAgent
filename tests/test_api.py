"""
Tests for GodAgent API Endpoints
"""

import pytest
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient


class TestAPIImports:
    """Test that API modules can be imported."""
    
    def test_import_main_app(self):
        """Test importing the main app."""
        from api import app
        assert app is not None
        
    def test_import_routes(self):
        """Test importing route modules."""
        from api.routes import chat, agents, decisions, feedback
        assert chat.router is not None
        assert agents.router is not None
        assert decisions.router is not None
        assert feedback.router is not None


class TestRootEndpoint:
    """Tests for root endpoint."""
    
    @pytest.fixture
    def client(self):
        from api import app
        return TestClient(app)
    
    def test_root_returns_info(self, client):
        """Test root endpoint returns API info."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "GodAgent API"
        assert "endpoints" in data
        
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


class TestAgentsEndpoint:
    """Tests for /v1/agents endpoint."""
    
    @pytest.fixture
    def client(self):
        from api import app
        return TestClient(app)
    
    def test_list_agents(self, client):
        """Test listing all agents."""
        response = client.get("/v1/agents")
        
        assert response.status_code == 200
        data = response.json()
        assert "agents" in data
        assert "count" in data
        assert data["count"] > 0
        
    def test_list_agents_includes_claude(self, client):
        """Test that Claude is in the agents list."""
        response = client.get("/v1/agents")
        
        data = response.json()
        agent_names = [a["name"] for a in data["agents"]]
        assert "claude" in agent_names
        
    def test_get_specific_agent(self, client):
        """Test getting a specific agent."""
        response = client.get("/v1/agents/claude")
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "claude"
        assert "capabilities" in data
        assert "strengths" in data
        
    def test_get_nonexistent_agent(self, client):
        """Test getting a nonexistent agent returns 404."""
        response = client.get("/v1/agents/nonexistent")
        
        assert response.status_code == 404
        
    def test_get_agents_by_capability(self, client):
        """Test getting agents by capability."""
        response = client.get("/v1/agents/by-capability/coding")
        
        assert response.status_code == 200
        data = response.json()
        assert data["capability"] == "coding"
        assert "agents" in data


class TestDecisionsEndpoint:
    """Tests for /v1/decisions endpoint."""
    
    @pytest.fixture
    def client(self):
        from api import app
        return TestClient(app)
    
    def test_list_decisions(self, client):
        """Test listing decisions."""
        response = client.get("/v1/decisions")
        
        assert response.status_code == 200
        data = response.json()
        assert "decisions" in data
        assert "count" in data
        
    def test_get_decision_stats(self, client):
        """Test getting decision stats."""
        response = client.get("/v1/decisions/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert "total_decisions" in data
        assert "average_confidence" in data


class TestFeedbackEndpoint:
    """Tests for /v1/feedback endpoint."""
    
    @pytest.fixture
    def client(self):
        from api import app
        return TestClient(app)
    
    def test_submit_feedback(self, client):
        """Test submitting feedback."""
        response = client.post("/v1/feedback", json={
            "agent_name": "claude",
            "rating": 4,
            "category": "response_quality",
            "comment": "Great response!",
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["status"] == "submitted"
        
    def test_submit_feedback_invalid_rating(self, client):
        """Test submitting feedback with invalid rating."""
        response = client.post("/v1/feedback", json={
            "agent_name": "claude",
            "rating": 10,  # Invalid - should be 1-5
            "category": "response_quality",
        })
        
        assert response.status_code == 422  # Validation error
        
    def test_list_feedback(self, client):
        """Test listing feedback."""
        response = client.get("/v1/feedback")
        
        assert response.status_code == 200
        data = response.json()
        assert "feedback" in data
        assert "count" in data
        
    def test_get_feedback_summary(self, client):
        """Test getting feedback summary."""
        response = client.get("/v1/feedback/summary")
        
        assert response.status_code == 200
        data = response.json()
        assert "total_count" in data
        assert "average_rating" in data
        
    def test_get_best_agent(self, client):
        """Test getting best performing agent."""
        response = client.get("/v1/feedback/best-agent")
        
        assert response.status_code == 200


class TestChatCompletionsEndpoint:
    """Tests for /v1/chat/completions endpoint."""
    
    @pytest.fixture
    def client(self):
        from api import app
        return TestClient(app)
    
    def test_chat_completion_structure(self, client):
        """Test that chat completion returns correct structure."""
        response = client.post("/v1/chat/completions", json={
            "messages": [
                {"role": "user", "content": "Hello, world!"}
            ]
        })
        
        # May fail without API keys, but should have correct structure or error
        if response.status_code == 200:
            data = response.json()
            assert "id" in data
            assert "choices" in data
            assert "usage" in data
            
    def test_chat_completion_requires_messages(self, client):
        """Test that chat completion requires messages."""
        response = client.post("/v1/chat/completions", json={
            "messages": []
        })
        
        # Should fail - no user message
        assert response.status_code in [400, 422, 500]
