# Integration Guide: LastAgent with Dependent Projects

This guide shows how to integrate LastAgent with its underlying projects.

## Project Dependencies

LastAgent uses these projects as runtime dependencies:
- **llmCouncil** - OpenRouter access, council voting
- **agentsParliament** - MCP servers for agent execution
- **SuperAI** - Response evaluation, LLM-as-judge
- **seedGPT** - Decision logging, workflow patterns

## Integration Examples

### 1. Using llmCouncil for OpenRouter Access

```python
# In lastAgent/src/council_selector.py
import sys
sys.path.insert(0, "/path/to/llmCouncil/backend")

from openrouter import query_model, query_models_parallel
from council import run_full_council, collect_responses, collect_rankings

# Query multiple models in parallel
responses = await query_models_parallel(
    prompt="Which agent is best for coding tasks?",
    models=["anthropic/claude-3.5-sonnet", "google/gemini-2.5-flash"],
    temperature=0.7,
)

# Run full council process
result = await run_full_council(prompt, council_config)
```

### 2. Using agentsParliament MCP Servers

```python
# In lastAgent/src/executor.py
import sys
sys.path.insert(0, "/path/to/agentsParliament/src")

from agenters.claude_mcp_server import ask_claude, ask_claude_in_directory
from agenters.gemini_mcp_server import ask_gemini
from agenters.aider_mcp_server import run_aider

# Execute Claude via MCP
response = await ask_claude(
    prompt="Write a hello world function",
    system="You are a helpful coding assistant",
)

# Execute Aider for git-aware coding
response = await run_aider(
    prompt="Fix the bug in main.py",
    working_dir="/path/to/project",
)
```

### 3. Using SuperAI for Evaluation

```python
# In lastAgent/src/orchestrator.py
import sys
sys.path.insert(0, "/path/to/SuperAI/src")

from superai.judge import evaluate_response, compare_responses

# Evaluate a response quality
score = await evaluate_response(
    response=agent_response,
    criteria=["correctness", "helpfulness", "clarity"],
)

# Compare multiple responses
best = await compare_responses(
    responses=[response_a, response_b, response_c],
    prompt=original_prompt,
)
```

### 4. Using seedGPT Decision Patterns

```python
# In lastAgent/src/decision_log.py
import sys
sys.path.insert(0, "/path/to/seedGPT")

from seedpy.core.decision_logger import DecisionLogger
from seedpy.core.workflow import WorkflowManager

# Log a LastAgent decision
logger = DecisionLogger(project_id="lastagent")
logger.log_decision(
    decision_type="AGENT_SELECTION",
    title="Selected Claude for coding task",
    reasoning="Claude has best coding capabilities",
    confidence=0.92,
)
```

## Directory Structure

```
AgenticCompany/
├── lastAgent/           # This project
├── llm-council/        # OpenRouter + council voting
├── agents-parliament/  # MCP servers for agents
├── SuperAI/            # LLM evaluation
└── seed-gpt/           # Workflow patterns
```

## Full Integration Flow

```
User Request
     │
     ▼
┌─────────────────┐
│    LastAgent     │
│  orchestrator   │
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌───────┐ ┌───────┐
│ llm   │ │Agents │
│Council│ │Parlmt │
└───┬───┘ └───┬───┘
    │         │
    ▼         ▼
 Vote for   Execute
 best agent  agent
    │         │
    └────┬────┘
         ▼
┌─────────────────┐
│    SuperAI      │
│ evaluate result │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    seedGPT      │
│  log decision   │
└─────────────────┘
```
