"""
Upload routes for invoice and proposal files.
"""

import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from src.models.response_models import UploadResponse, ErrorResponse
from src.services.file_storage import file_storage
from src.routes import session_routes

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Upload"])


@router.post("/upload-invoice", response_model=UploadResponse)
async def upload_invoice(file: UploadFile = File(...), session_id: str = Query(None)):
    """
    Upload invoice file (PDF or image).
    
    Args:
        file: Invoice file
        session_id: Optional session identifier
        
    Returns:
        UploadResponse with file_id
    """
    try:
        logger.info(f"Received invoice upload: {file.filename} (session: {session_id})")
        
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="Filename is required")
        
        # Save file
        file_id, file_path = await file_storage.save_invoice(file)
        
        # Update session if provided
        if session_id:
            session_routes.update_session(session_id, invoice_id=file_id)
        
        logger.info(f"Invoice saved: {file_id}")
        
        return UploadResponse(
            file_id=file_id,
            filename=file.filename,
            message="Invoice uploaded successfully"
        )
        
    except Exception as e:
        logger.error(f"Invoice upload failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload-proposal", response_model=UploadResponse)
async def upload_proposal(file: UploadFile = File(...), session_id: str = Query(None)):
    """
    Upload proposal Excel file.
    
    Args:
        file: Excel file
        session_id: Optional session identifier
        
    Returns:
        UploadResponse with file_id
    """
    try:
        logger.info(f"Received proposal upload: {file.filename} (session: {session_id})")
        
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="Filename is required")
        
        # Save file
        file_id, file_path = await file_storage.save_proposal(file)
        
        # Update session if provided
        if session_id:
            session_routes.update_session(session_id, proposal_id=file_id)
        
        logger.info(f"Proposal saved: {file_id}")
        
        return UploadResponse(
            file_id=file_id,
            filename=file.filename,
            message="Proposal uploaded successfully"
        )
        
    except Exception as e:
        logger.error(f"Proposal upload failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
