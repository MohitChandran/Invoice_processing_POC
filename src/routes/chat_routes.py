"""
Chat Routes - User chat with orchestrator for Q&A about validation results.
"""

import logging
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from src.agents.orchestrator import orchestrator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])


class ChatRequest(BaseModel):
    """Chat request model."""
    question: str = Field(..., description="User's question about the validation")
    
    class Config:
        json_schema_extra = {
            "example": {
                "question": "Why was my document rejected?"
            }
        }


class ChatResponse(BaseModel):
    """Chat response model."""
    session_id: str
    question: str
    answer: str
    has_context: bool
    context_items: int


@router.post("/user-chat", response_model=ChatResponse)
async def user_chat(
    chat_request: ChatRequest,
    session_id: str = Query(..., description="Session ID to get context from")
):
    """
    Chat with the orchestrator about validation results.
    
    Ask questions about:
    - Why a document was rejected or approved
    - Maximum fare limits for employee levels
    - Where the employee is traveling to/from
    - What policies were applied
    - Any violations found
    - Extracted invoice details
    
    **Requires**: An existing session with completed validation.
    
    **Examples**:
    - "Why was this document rejected?"
    - "What is the maximum fare for L2 employee?"
    - "Where is the employee traveling to?"
    - "What policies were checked?"
    - "What was the extracted fare amount?"
    """
    try:
        logger.info(f"Chat request for session {session_id}: {chat_request.question}")
        
        # Call orchestrator chat method
        result = await orchestrator.chat_with_context(
            session_id=session_id,
            user_question=chat_request.question
        )
        
        return ChatResponse(**result)
        
    except Exception as e:
        logger.error(f"Chat endpoint error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Chat request failed: {str(e)}"
        )
