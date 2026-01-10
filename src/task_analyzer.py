"""
LastAgent Task Analyzer

Analyzes incoming tasks to determine their requirements and characteristics.
This helps the council select the most appropriate agent.
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Set


class TaskType(Enum):
    """High-level task type categories."""
    CODING = "coding"
    RESEARCH = "research"
    WRITING = "writing"
    ANALYSIS = "analysis"
    AUTOMATION = "automation"
    CONVERSATION = "conversation"
    UNKNOWN = "unknown"


@dataclass
class TaskAnalysis:
    """Result of analyzing a task."""
    task_type: TaskType
    detected_capabilities: List[str]
    keywords_matched: List[str]
    requires_working_directory: bool
    requires_realtime_info: bool
    requires_multimodal: bool
    requires_long_context: bool
    confidence: float
    raw_text: str = ""


# =============================================================================
# KEYWORD PATTERNS
# =============================================================================

# Capability keywords - maps capability names to detection patterns
CAPABILITY_PATTERNS = {
    "coding": [
        r"\b(code|program|script|function|class|method|implement|debug|fix|bug)\b",
        r"\b(python|javascript|typescript|java|rust|go|c\+\+|ruby|php)\b",
        r"\b(api|endpoint|backend|frontend|database|sql|nosql)\b",
        r"\b(test|unittest|pytest|jest|spec)\b",
        r"\b(refactor|optimize|performance)\b",
    ],
    "git_integration": [
        r"\b(git|commit|branch|merge|pull request|pr|push|clone)\b",
        r"\b(github|gitlab|bitbucket)\b",
        r"\b(version control|vcs|repository|repo)\b",
    ],
    "research": [
        r"\b(research|find|search|lookup|discover|explore)\b",
        r"\b(what is|how does|explain|compare|contrast)\b",
        r"\b(latest|current|recent|2024|2025|2026)\b",
        r"\b(documentation|docs|reference)\b",
    ],
    "realtime_info": [
        r"\b(today|now|current|latest|recent|news|trending)\b",
        r"\b(weather|stock|price|live|real-?time)\b",
        r"\b(2025|2026|this week|this month|yesterday)\b",
    ],
    "deep_reasoning": [
        r"\b(analyze|evaluate|compare|contrast|reason)\b",
        r"\b(why|explain|understand|deduce|infer)\b",
        r"\b(complex|detailed|thorough|comprehensive)\b",
        r"\b(pros and cons|trade-?offs|implications)\b",
    ],
    "writing": [
        r"\b(write|draft|compose|create|generate)\b",
        r"\b(essay|article|blog|post|story|document)\b",
        r"\b(email|message|letter|proposal)\b",
        r"\b(summarize|summary|rewrite|paraphrase)\b",
    ],
    "multimodal": [
        r"\b(image|picture|photo|screenshot|diagram)\b",
        r"\b(video|audio|sound|visual)\b",
        r"\b(pdf|document with images)\b",
    ],
    "long_context": [
        r"\b(entire|whole|all|complete|full)\s+(file|document|codebase)\b",
        r"\b(large|long|extensive)\s+(document|file|context)\b",
        r"\b(multiple files|many files|all files)\b",
    ],
    "sandboxed_execution": [
        r"\b(run|execute|test|try|sandbox)\b",
        r"\b(shell|command|terminal|bash|zsh)\b",
        r"\b(install|pip|npm|brew)\b",
    ],
    "multistep_workflows": [
        r"\b(workflow|pipeline|automation|orchestrate)\b",
        r"\b(step by step|multiple steps|sequence)\b",
        r"\b(then|after that|next|finally)\b",
    ],
}

# Task type detection patterns
TASK_TYPE_PATTERNS = {
    TaskType.CODING: [
        r"\b(code|program|script|implement|debug|fix|build|create)\b.*\b(function|class|api|app|program|script)\b",
        r"\b(python|javascript|typescript|java|rust|go)\b",
        r"\b(fix.*bug|debug|refactor)\b",
    ],
    TaskType.RESEARCH: [
        r"\b(research|find out|look up|search for|discover)\b",
        r"\b(what is|who is|when did|where is|how does)\b",
    ],
    TaskType.WRITING: [
        r"\b(write|draft|compose|create)\b.*\b(essay|article|blog|email|document)\b",
        r"\b(summarize|rewrite|paraphrase)\b",
    ],
    TaskType.ANALYSIS: [
        r"\b(analyze|evaluate|compare|review)\b",
        r"\b(pros and cons|trade-?offs|assessment)\b",
    ],
    TaskType.AUTOMATION: [
        r"\b(automate|script|workflow|pipeline)\b",
        r"\b(set up|configure|deploy)\b",
    ],
    TaskType.CONVERSATION: [
        r"\b(chat|talk|discuss|conversation)\b",
        r"\b(hello|hi|hey|thanks)\b",
    ],
}


class TaskAnalyzer:
    """
    Analyzes tasks to determine requirements and characteristics.
    
    Usage:
        analyzer = TaskAnalyzer()
        analysis = analyzer.analyze(
            "Write a Python script that fetches weather data"
        )
        print(analysis.task_type)  # TaskType.CODING
        print(analysis.detected_capabilities)  # ["coding", "research"]
    """
    
    def __init__(self):
        """Initialize the task analyzer."""
        # Compile all patterns for performance
        self._capability_patterns = {
            cap: [re.compile(p, re.IGNORECASE) for p in patterns]
            for cap, patterns in CAPABILITY_PATTERNS.items()
        }
        self._task_type_patterns = {
            task_type: [re.compile(p, re.IGNORECASE) for p in patterns]
            for task_type, patterns in TASK_TYPE_PATTERNS.items()
        }
        
    def analyze(self, user_prompt: str, system_prompt: str = "") -> TaskAnalysis:
        """
        Analyze a task to determine its requirements.
        
        Args:
            user_prompt: The user's request
            system_prompt: Optional system prompt for context
            
        Returns:
            TaskAnalysis with detected requirements
        """
        full_text = f"{system_prompt} {user_prompt}".strip()
        
        # Detect capabilities
        capabilities, keywords = self._detect_capabilities(full_text)
        
        # Detect task type
        task_type, type_confidence = self._detect_task_type(full_text)
        
        # Detect special requirements
        requires_working_dir = self._requires_working_directory(full_text, capabilities)
        requires_realtime = "realtime_info" in capabilities
        requires_multimodal = "multimodal" in capabilities
        requires_long_context = "long_context" in capabilities
        
        return TaskAnalysis(
            task_type=task_type,
            detected_capabilities=list(capabilities),
            keywords_matched=keywords,
            requires_working_directory=requires_working_dir,
            requires_realtime_info=requires_realtime,
            requires_multimodal=requires_multimodal,
            requires_long_context=requires_long_context,
            confidence=type_confidence,
            raw_text=full_text,
        )
        
    def _detect_capabilities(self, text: str) -> tuple[Set[str], List[str]]:
        """Detect which capabilities are needed based on text patterns."""
        detected = set()
        keywords = []
        
        for capability, patterns in self._capability_patterns.items():
            for pattern in patterns:
                matches = pattern.findall(text)
                if matches:
                    detected.add(capability)
                    keywords.extend(matches)
                    
        return detected, keywords
        
    def _detect_task_type(self, text: str) -> tuple[TaskType, float]:
        """Detect the primary task type."""
        scores = {}
        
        for task_type, patterns in self._task_type_patterns.items():
            score = 0
            for pattern in patterns:
                if pattern.search(text):
                    score += 1
            if score > 0:
                scores[task_type] = score
                
        if not scores:
            return TaskType.UNKNOWN, 0.0
            
        # Return highest scoring type
        best_type = max(scores, key=scores.get)
        max_possible = len(self._task_type_patterns[best_type])
        confidence = scores[best_type] / max_possible if max_possible > 0 else 0.0
        
        return best_type, min(confidence, 1.0)
        
    def _requires_working_directory(self, text: str, capabilities: Set[str]) -> bool:
        """Determine if task requires a working directory."""
        # Tasks that typically need a working directory
        dir_capabilities = {"git_integration", "sandboxed_execution"}
        if capabilities & dir_capabilities:
            return True
            
        # Check for file/directory references
        dir_patterns = [
            r"\./",
            r"\b(file|directory|folder|path|project)\b",
            r"\b(codebase|repo|repository)\b",
        ]
        for pattern in dir_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
                
        return False


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_analyzer = None


def get_task_analyzer() -> TaskAnalyzer:
    """Get the global task analyzer instance."""
    global _analyzer
    if _analyzer is None:
        _analyzer = TaskAnalyzer()
    return _analyzer
