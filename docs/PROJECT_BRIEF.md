# LastAgent - Project Brief

## Overview
LastAgent combines llmCouncil, agentsParliament, superAI, and seedGPT into one unified orchestrator that allows users to interact with a "god agent" which controls all other agents.

---

## Two-Phase Architecture

### Phase 1: SELECTION (Council Voting)
- Council of LLMs votes on which **AGENT** is best for the task
- Uses LLM API calls for voting/decision-making only, or agentic calls to other agents
- This is intelligent routing, not execution
- At the end - the orchestrator agent is selected.

### Phase 2: EXECUTION (Agent CLI/SDK)
- Selected **AGENT** runs via its native CLI
- AGENTS have agentic capabilities (tools, file access, autonomous execution)
- Examples: `claude -p prompt`, `aider --message`, `codex --full-auto`, `goose run`

### Phase 3: Communication (Full-Mesh Awareness)
- Each **AGENT** is configured with knowledge of all other agents and their capabilities
- When correctly configured, agents can discover and delegate tasks to the most suitable peer
- Example: Claude delegates git operations to Aider, Aider delegates research to Gemini
- This creates a collaborative mesh where agents leverage each other's strengths

**The council uses LLM for SELECTION. Execution is ALWAYS CLI.**

---

## Critical Distinction

| Component | Method | Purpose |
|-----------|--------|---------|
| Council | LLM API | Vote on which agent to use |
| Executor | CLI/SDK | Run the selected agent |

**AGENTS are NOT LLMs.** They have:
- Tools and file system access
- Autonomous execution capabilities
- Agentic loops (not just text in/out)

---

## Full-Mesh Architecture
All agents can delegate to any other agent via CLI execution, creating a collaborative mesh network.

---

## Documentation
See `.seedgpt` folder for high-level management and planning.
