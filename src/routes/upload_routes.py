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


@router.post("/upload-invoices-batch")
async def upload_invoices_batch(
    files: list[UploadFile] = File(..., description="Multiple invoice files"),
    session_id: str = Query(None, description="Optional session identifier")
):
    """
    Upload multiple invoice files at once.
    
    Args:
        files: List of invoice files (PDFs or images)
        session_id: Optional session identifier
        
    Returns:
        Dict with:
            - total: Total number of files
            - uploaded: Number successfully uploaded
            - file_ids: List of file IDs
            - results: Detailed results for each file
    """
    try:
        # Normalize single UploadFile to list for robustness (support 1..N files)
        if not isinstance(files, (list, tuple)):
            files = [files]

        logger.info(f"Received batch invoice upload: {len(files)} files (session: {session_id})")
        print(f"\n📤 Uploading {len(files)} invoice files...")
        
        upload_results = []
        file_ids = []
        uploaded_count = 0
        
        for idx, file in enumerate(files, 1):
            try:
                if not file.filename:
                    raise ValueError("Filename is required")
                
                # Save file
                file_id, file_path = await file_storage.save_invoice(file)
                file_ids.append(file_id)
                uploaded_count += 1
                
                upload_results.append({
                    'filename': file.filename,
                    'file_id': file_id,
                    'status': 'success',
                    'index': idx
                })
                
                print(f"✅ {idx}/{len(files)}: {file.filename} → {file_id}")
                
            except Exception as e:
                logger.error(f"Failed to upload file {file.filename}: {str(e)}")
                upload_results.append({
                    'filename': file.filename,
                    'file_id': None,
                    'status': 'error',
                    'error': str(e),
                    'index': idx
                })
                print(f"❌ {idx}/{len(files)}: {file.filename} failed - {str(e)}")
        
        # Update session if provided
        if session_id and file_ids:
            session_routes.update_session(session_id, invoice_ids=file_ids)
        
        print(f"✅ Batch upload completed: {uploaded_count}/{len(files)} successful\n")
        logger.info(f"Batch upload completed: {uploaded_count}/{len(files)}")
        
        return {
            'total': len(files),
            'uploaded': uploaded_count,
            'failed': len(files) - uploaded_count,
            'file_ids': file_ids,
            'results': upload_results
        }
        
    except Exception as e:
        logger.error(f"Batch invoice upload failed: {str(e)}", exc_info=True)
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
