"""
Processing routes for validation workflow.
"""

import logging
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from src.models.request_models import ProcessValidationRequest
from src.models.response_models import ValidationResponse, ErrorResponse
from src.agents.orchestrator import orchestrator
from src.routes import session_routes

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Processing"])


@router.post("/process-validation", response_model=ValidationResponse)
async def process_validation(
    request: Optional[ProcessValidationRequest] = None,
    session_id: str = Query(None),
    invoice_id: str = Query(None),
    proposal_id: str = Query(None)
):
    """
    Process invoice validation.
    
    Runs full workflow:
    1. Extract data from invoice
    2. Match employee in proposal
    3. Validate against business rules
    4. Return validation decision
    
    Args:
        request: ProcessValidationRequest with invoice_id and proposal_id (body)
        session_id: Session identifier (query param)
        invoice_id: Invoice file ID (query param)
        proposal_id: Proposal file ID (query param)
        
    Returns:
        ValidationResponse with validation result
    """
    try:
        # Get IDs from session if session_id provided
        if session_id:
            session_data = session_routes.get_session_data(session_id)
            if not session_data:
                raise HTTPException(status_code=404, detail="Session not found")
            
            invoice_id = session_data.get("invoice_id") or invoice_id
            proposal_id = session_data.get("proposal_id") or proposal_id
        
        # Get IDs from request body if provided
        if request:
            invoice_id = request.invoice_id or invoice_id
            proposal_id = request.proposal_id or proposal_id
        
        # Validate we have both IDs
        if not invoice_id or not proposal_id:
            raise HTTPException(
                status_code=400,
                detail="Both invoice_id and proposal_id are required"
            )
        
        logger.info(f"Processing validation: invoice={invoice_id}, proposal={proposal_id}, session={session_id}")
        
        # Run orchestrator
        result = await orchestrator.process_validation(
            invoice_id=invoice_id,
            proposal_id=proposal_id
        )
        
        # Add session_id to result
        result["session_id"] = session_id
        
        logger.info(f"Validation completed: {result['validation_status']}")
        
        return ValidationResponse(**result)
        
    except HTTPException:
        raise
    except FileNotFoundError as e:
        logger.error(f"File not found: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
        
    except Exception as e:
        logger.error(f"Validation processing failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}")
async def get_session_info(session_id: str):
    """
    Get session information (for debugging).
    
    Args:
        session_id: Session identifier
        
    Returns:
        Session data
    """
    try:
        session_info = orchestrator.get_session_info(session_id)
        
        if not session_info:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return session_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session info: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cleanup-sessions")
async def cleanup_sessions():
    """
    Manually trigger session cleanup.
    
    Returns:
        Cleanup status
    """
    try:
        orchestrator.cleanup_sessions()
        return {"message": "Session cleanup completed"}
        
    except Exception as e:
        logger.error(f"Session cleanup failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
