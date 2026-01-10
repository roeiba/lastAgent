"""
Tests for LastAgent Task Analyzer
"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.task_analyzer import (
    TaskAnalyzer,
    TaskType,
    TaskAnalysis,
    get_task_analyzer,
)


class TestTaskAnalyzer:
    """Tests for TaskAnalyzer class."""
    
    @pytest.fixture
    def analyzer(self):
        """Create a TaskAnalyzer instance."""
        return TaskAnalyzer()
    
    def test_analyze_coding_task(self, analyzer):
        """Test analyzing a coding task."""
        analysis = analyzer.analyze("Write a Python script that fetches weather data")
        
        assert analysis.task_type == TaskType.CODING
        assert "coding" in analysis.detected_capabilities
        
    def test_analyze_research_task(self, analyzer):
        """Test analyzing a research task."""
        analysis = analyzer.analyze("What is the latest news about AI in 2025?")
        
        assert TaskType.RESEARCH == analysis.task_type or "research" in analysis.detected_capabilities
        assert analysis.requires_realtime_info  # "latest" and "2025"
        
    def test_analyze_git_task(self, analyzer):
        """Test analyzing a git-related task."""
        analysis = analyzer.analyze("Create a pull request for the new feature branch")
        
        assert "git_integration" in analysis.detected_capabilities
        assert analysis.requires_working_directory
        
    def test_analyze_multimodal_task(self, analyzer):
        """Test analyzing a multimodal task."""
        analysis = analyzer.analyze("Analyze this image and describe what you see")
        
        assert "multimodal" in analysis.detected_capabilities
        assert analysis.requires_multimodal
        
    def test_analyze_empty_prompt(self, analyzer):
        """Test analyzing an empty prompt."""
        analysis = analyzer.analyze("")
        
        assert analysis.task_type == TaskType.UNKNOWN
        assert len(analysis.detected_capabilities) == 0
        
    def test_analyze_returns_task_analysis(self, analyzer):
        """Test that analyze returns correct type."""
        analysis = analyzer.analyze("hello")
        
        assert isinstance(analysis, TaskAnalysis)
        assert hasattr(analysis, "task_type")
        assert hasattr(analysis, "detected_capabilities")
        assert hasattr(analysis, "confidence")
        
    def test_working_directory_detection(self, analyzer):
        """Test working directory requirement detection."""
        # Should need working dir
        analysis1 = analyzer.analyze("Run the tests in ./tests directory")
        assert analysis1.requires_working_directory
        
        # Shouldn't need working dir
        analysis2 = analyzer.analyze("What is 2 + 2?")
        assert not analysis2.requires_working_directory
        
    def test_realtime_info_detection(self, analyzer):
        """Test realtime info requirement detection."""
        analysis1 = analyzer.analyze("What are the trending topics today?")
        assert analysis1.requires_realtime_info
        
        analysis2 = analyzer.analyze("Explain how photosynthesis works")
        assert not analysis2.requires_realtime_info


class TestGlobalAnalyzer:
    """Tests for global analyzer singleton."""
    
    def test_get_task_analyzer_returns_instance(self):
        """Test that get_task_analyzer returns an instance."""
        analyzer = get_task_analyzer()
        assert isinstance(analyzer, TaskAnalyzer)
        
    def test_get_task_analyzer_is_singleton(self):
        """Test that get_task_analyzer returns same instance."""
        analyzer1 = get_task_analyzer()
        analyzer2 = get_task_analyzer()
        assert analyzer1 is analyzer2
