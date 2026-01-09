"""
Chat Completions Endpoint

OpenAI-compatible chat completions endpoint.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
import uuid

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.orchestrator import get_orchestrator
from src.council_selector import get_council_selector
from src.approvals import ApprovalMode


router = APIRouter()


# =============================================================================
# REQUEST/RESPONSE MODELS (OpenAI-compatible)
# =============================================================================

class Message(BaseModel):
    """A chat message."""
    role: str = Field(..., description="Role: system, user, or assistant")
    content: str = Field(..., description="Message content")


class ChatCompletionRequest(BaseModel):
    """Request body for chat completions."""
    model: Optional[str] = Field(None, description="Model to use (agent name)")
    messages: List[Message] = Field(..., description="Conversation messages")
    temperature: Optional[float] = Field(0.7, ge=0, le=2)
    max_tokens: Optional[int] = Field(None)
    stream: Optional[bool] = Field(False)
    working_directory: Optional[str] = Field(
        None, description="Working directory for CLI agents"
    )
    approval_mode: Optional[str] = Field(
        None, description="Approval mode: AUTO, APPROVE_ALL, APPROVE_HIGH_RISK"
    )


class Choice(BaseModel):
    """A completion choice."""
    index: int
    message: Message
    finish_reason: str


class Usage(BaseModel):
    """Token usage statistics."""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponse(BaseModel):
    """Response body for chat completions."""
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Choice]
    usage: Usage
    godagent_metadata: Optional[Dict[str, Any]] = None


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/chat/completions", response_model=ChatCompletionResponse)
async def create_chat_completion(request: ChatCompletionRequest):
    """
    Create a chat completion.
    
    This is the main endpoint for task submission. GodAgent will:
    1. Analyze the task
    2. Select the best agent via council
    3. Execute the agent with the original prompts
    4. Return the response
    """
    import time
    
    # Extract system and user prompts from messages
    system_prompt = ""
    user_prompt = ""
    
    for msg in request.messages:
        if msg.role == "system":
            system_prompt = msg.content
        elif msg.role == "user":
            user_prompt = msg.content
            
    if not user_prompt:
        raise HTTPException(status_code=400, detail="At least one user message is required")
        
    # Get orchestrator
    orchestrator = get_orchestrator()
    
    # Determine approval mode
    approval_mode = None
    if request.approval_mode:
        try:
            approval_mode = ApprovalMode(request.approval_mode)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid approval_mode: {request.approval_mode}"
            )
    
    # Process the task
    try:
        result = await orchestrator.process_task(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            working_directory=request.working_directory,
            approval_mode=approval_mode,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    # Build response
    response = ChatCompletionResponse(
        id=f"chatcmpl-{uuid.uuid4().hex[:8]}",
        created=int(time.time()),
        model=result.agent,
        choices=[
            Choice(
                index=0,
                message=Message(role="assistant", content=result.response),
                finish_reason="stop",
            )
        ],
        usage=Usage(
            prompt_tokens=len(user_prompt.split()),
            completion_tokens=len(result.response.split()),
            total_tokens=len(user_prompt.split()) + len(result.response.split()),
        ),
        godagent_metadata={
            "task_id": result.task_id,
            "agent": result.agent,
            "duration_ms": result.duration_ms,
            "success": result.success,
        },
    )
    
    return response
