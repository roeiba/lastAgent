# LastAgent Deployment Guide

## Quick Start

### Local Development
```bash
# Install dependencies
pip install -e ".[dev]"

# Set environment variables
export ANTHROPIC_API_KEY="your-key"
export GOOGLE_API_KEY="your-key"

# Run API server
lastagent server --port 8000
```

### Docker
```bash
# Build and run
docker-compose up -d

# Check logs
docker-compose logs -f lastagent-api

# Stop
docker-compose down
```

### Test the API
```bash
curl http://localhost:8000/health
curl http://localhost:8000/v1/agents
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Hello!"}]}'
```

## Production Deployment

### Google Cloud Run
```bash
# Build and push
gcloud builds submit --tag gcr.io/PROJECT_ID/lastagent

# Deploy
gcloud run deploy lastagent-api \
  --image gcr.io/PROJECT_ID/lastagent \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars "ANTHROPIC_API_KEY=xxx,GOOGLE_API_KEY=xxx"
```

### AWS ECS / Fargate
```bash
# Push to ECR
aws ecr get-login-password | docker login --username AWS --password-stdin ACCOUNT.dkr.ecr.REGION.amazonaws.com
docker build -t lastagent .
docker tag lastagent:latest ACCOUNT.dkr.ecr.REGION.amazonaws.com/lastagent:latest
docker push ACCOUNT.dkr.ecr.REGION.amazonaws.com/lastagent:latest
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Claude API key |
| `GOOGLE_API_KEY` | Yes | Gemini API key |
| `OPENROUTER_API_KEY` | Yes | OpenRouter for GPT/Grok |
| `OPENAI_API_KEY` | No | Direct OpenAI access |
| `XAI_API_KEY` | No | Direct Grok access |

## Health Checks

- **Endpoint:** `GET /health`
- **Expected:** `{"status": "healthy"}`
- **Interval:** 30 seconds
