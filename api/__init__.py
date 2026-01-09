"""
GodAgent API - Main FastAPI Application

OpenAI-compatible API endpoints for task submission and agent management.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import chat, agents, decisions, feedback


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    # Startup
    print("🚀 GodAgent API starting up...")
    yield
    # Shutdown
    print("👋 GodAgent API shutting down...")


app = FastAPI(
    title="GodAgent API",
    description="Full-mesh AI orchestration system - One Agent to Rule Them All",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat.router, prefix="/v1", tags=["chat"])
app.include_router(agents.router, prefix="/v1", tags=["agents"])
app.include_router(decisions.router, prefix="/v1", tags=["decisions"])
app.include_router(feedback.router, prefix="/v1", tags=["feedback"])


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "GodAgent API",
        "version": "0.1.0",
        "description": "Full-mesh AI orchestration system",
        "endpoints": {
            "chat": "/v1/chat/completions",
            "agents": "/v1/agents",
            "decisions": "/v1/decisions",
            "feedback": "/v1/feedback",
        },
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
