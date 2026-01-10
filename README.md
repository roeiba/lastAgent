# 🤖 LastAgent

**One Agent to Rule Them All** - Full-mesh AI orchestration system that dynamically selects and executes the best AI agent for any task.

## Features

- **🧠 LLM Council Selection** - 4 AI models vote to select the best agent for each task
- **🌐 Full-Mesh Architecture** - Any agent can call any other agent
- **🔧 7 Agents Supported** - Claude, Gemini, GPT, Grok, Aider, Codex, Goose
- **🔄 OpenAI-Compatible API** - Drop-in replacement for `/v1/chat/completions`
- **✅ Human-in-the-Loop** - Configurable approval modes for high-risk actions
- **📊 Decision Logging** - Full audit trail of all agent selections

## Quick Start

```bash
# Install dependencies
pip install -e .

# Set API keys
export ANTHROPIC_API_KEY="your-key"
export GOOGLE_API_KEY="your-key"
export OPENROUTER_API_KEY="your-key"

# Start the API server
lastagent server --port 8000

# Or submit a task directly
lastagent chat "Write a Python function to calculate fibonacci numbers"
```

## Architecture

```
User Request → Task Analyzer → LLM Council → Agent Selection → Execution → Response
                    ↓               ↓              ↓
              Capabilities    4 Models Vote    Direct API/CLI
```

## Available Agents

| Agent | Type | Best For |
|-------|------|----------|
| Claude | API | Complex reasoning, coding, long-form writing |
| Gemini | API | Research, multimodal, ultra-long context |
| GPT | OpenRouter | General purpose, function calling |
| Grok | OpenRouter | Real-time information, trending topics |
| Aider | CLI | Git-aware code editing |
| Codex | CLI | Autonomous coding tasks |
| Goose | CLI | Multi-step workflows |

## API Endpoints

```
POST /v1/chat/completions  - Submit a task (OpenAI-compatible)
GET  /v1/agents            - List available agents
GET  /v1/agents/{name}     - Get agent details
GET  /v1/decisions         - View decision history
POST /v1/feedback          - Submit feedback
GET  /health               - Health check
```

## CLI Commands

```bash
lastagent chat "prompt"       # Submit a task
lastagent agents              # List agents
lastagent agents -c coding    # Filter by capability
lastagent server              # Start API server
lastagent workflow status     # Check workflow status
```

## Configuration

Edit `config/settings.yml` to configure:
- `approval_mode`: AUTO, APPROVE_ALL, APPROVE_HIGH_RISK
- `logging`: Level, file logging, decision logging
- `execution`: Timeout, concurrency, retries

## Testing

```bash
pytest tests/ -v
# 132 tests passing
```

## License

MIT
