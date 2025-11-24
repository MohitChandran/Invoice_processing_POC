"""
Session management routes.
"""

import logging
import uuid
from fastapi import APIRouter, HTTPException
from src.models.response_models import SessionResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Session"])

# In-memory session store (simple implementation)
sessions = {}


@router.post("/session", response_model=SessionResponse)
async def create_session():
    """
    Create a new session.
    
    Returns:
        SessionResponse with session_id
    """
    try:
        session_id = str(uuid.uuid4())
        
        sessions[session_id] = {
            "session_id": session_id,
            "invoice_id": None,
            "proposal_id": None,
            "created_at": None
        }
        
        logger.info(f"Created session: {session_id}")
        
        return SessionResponse(
            session_id=session_id,
            message="Session created successfully"
        )
        
    except Exception as e:
        logger.error(f"Session creation failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}")
async def get_session(session_id: str):
    """
    Get session information.
    
    Args:
        session_id: Session identifier
        
    Returns:
        Session data
    """
    try:
        if session_id not in sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return sessions[session_id]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


def get_session_data(session_id: str):
    """Helper to get session data."""
    return sessions.get(session_id)


def update_session(session_id: str, **kwargs):
    """Helper to update session data."""
    if session_id in sessions:
        sessions[session_id].update(kwargs)
