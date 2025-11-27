"""
Processing routes for validation workflow.
"""

import uuid
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
        
        # Run orchestrator (pass session_id if available)
        result = await orchestrator.process_validation(
            invoice_id=invoice_id,
            proposal_id=proposal_id,
            session_id=session_id
        )
        
        # Ensure session_id is in result (orchestrator should set it, but ensure it's there)
        if session_id:
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


@router.post("/process-batch-validation")
async def process_batch_validation(
    invoice_ids: list[str] = Query(..., description="List of invoice file IDs"),
    proposal_id: str = Query(..., description="Proposal Excel file ID"),
    session_id: Optional[str] = Query(None, description="Optional session ID")
):
    """
    Process multiple invoices in batch.
    
    Validates multiple invoices against a single Excel proposal.
    Each invoice is processed independently and matched to its row in Excel.
    
    Args:
        invoice_ids: List of invoice file IDs to process
        proposal_id: Proposal Excel file ID
        session_id: Optional session ID (creates new if not provided)
        
    Returns:
        Dict with batch results:
            - batch_id: Batch identifier
            - total_invoices: Total number of invoices
            - processed: Number successfully processed
            - results: List of ValidationResponse for each invoice
    """
    try:
        logger.info(f"Processing batch validation: {len(invoice_ids)} invoices, proposal={proposal_id}")
        print(f"\n{'='*80}")
        print(f"📦 BATCH VALIDATION REQUEST")
        print(f"{'='*80}")
        print(f"Total Invoices: {len(invoice_ids)}")
        print(f"Proposal ID: {proposal_id}")
        print(f"Session ID: {session_id or 'Will create new'}")
        
        batch_results = []
        processed_count = 0
        
        # Process each invoice
        for idx, invoice_id in enumerate(invoice_ids, 1):
            print(f"\n--- Processing Invoice {idx}/{len(invoice_ids)} ---")
            print(f"Invoice ID: {invoice_id}")
            
            try:
                # Process this invoice (create new session for each or reuse if provided)
                result = await orchestrator.process_validation(
                    invoice_id=invoice_id,
                    proposal_id=proposal_id,
                    session_id=None  # Let each invoice have its own session
                )
                
                batch_results.append({
                    'invoice_id': invoice_id,
                    'status': 'success',
                    'result': result
                })
                processed_count += 1
                print(f"✅ Invoice {idx} processed: {result['validation_status']}")
                
            except Exception as e:
                logger.error(f"Failed to process invoice {invoice_id}: {str(e)}")
                batch_results.append({
                    'invoice_id': invoice_id,
                    'status': 'error',
                    'error': str(e),
                    'result': None
                })
                print(f"❌ Invoice {idx} failed: {str(e)}")
        
        print(f"\n{'='*80}")
        print(f"📦 BATCH VALIDATION COMPLETED")
        print(f"{'='*80}")
        print(f"Processed: {processed_count}/{len(invoice_ids)}")
        print(f"{'='*80}\n")
        
        return {
            'batch_id': session_id or f"batch_{uuid.uuid4().hex[:12]}",
            'total_invoices': len(invoice_ids),
            'processed': processed_count,
            'failed': len(invoice_ids) - processed_count,
            'results': batch_results
        }
        
    except Exception as e:
        logger.error(f"Batch validation failed: {str(e)}", exc_info=True)
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


@router.post("/process-batch-validation")
async def process_batch_validation(
    invoice_ids: list[str] = Query(..., description="List of invoice file IDs"),
    proposal_id: str = Query(..., description="Proposal Excel file ID"),
    session_id: str = Query(None, description="Session identifier")
):
    """
    Process multiple invoices in batch mode.
    
    Args:
        invoice_ids: List of invoice file IDs
        proposal_id: Proposal Excel file ID
        session_id: Optional session identifier
        
    Returns:
        Dict with:
            - total_invoices: Total number of invoices
            - processed: Number successfully processed
            - failed: Number failed
            - results: List of validation results for each invoice
    """
    try:
        logger.info(f"Processing batch validation: {len(invoice_ids)} invoices, proposal={proposal_id}, session={session_id}")
        print(f"\n{'='*80}")
        print(f"🚀 BATCH VALIDATION REQUEST")
        print(f"{'='*80}")
        print(f"Total invoices: {len(invoice_ids)}")
        print(f"Proposal ID: {proposal_id}")
        print(f"Session ID: {session_id}")
        
        results = []
        processed_count = 0
        failed_count = 0
        
        # Process each invoice
        for idx, invoice_id in enumerate(invoice_ids, 1):
            try:
                print(f"\n📄 Processing invoice {idx}/{len(invoice_ids)}: {invoice_id}")
                
                # Create unique session ID for this invoice if not provided
                invoice_session_id = f"{session_id}_invoice_{idx}" if session_id else f"sess_{uuid.uuid4().hex[:8]}"
                
                # Run validation for this invoice
                result = await orchestrator.process_validation(
                    invoice_id=invoice_id,
                    proposal_id=proposal_id,
                    session_id=invoice_session_id
                )
                
                results.append({
                    'invoice_id': invoice_id,
                    'index': idx,
                    'status': 'success',
                    'result': result
                })
                
                processed_count += 1
                print(f"✅ Invoice {idx} processed: {result.get('validation_status', 'unknown').upper()}")
                
            except Exception as e:
                logger.error(f"Failed to process invoice {invoice_id}: {str(e)}")
                results.append({
                    'invoice_id': invoice_id,
                    'index': idx,
                    'status': 'error',
                    'error': str(e),
                    'result': None
                })
                
                failed_count += 1
                print(f"❌ Invoice {idx} failed: {str(e)}")
        
        # Build summary response
        summary = {
            'total_invoices': len(invoice_ids),
            'processed': processed_count,
            'failed': failed_count,
            'session_id': session_id,
            'results': results
        }
        
        print(f"\n{'='*80}")
        print(f"✅ BATCH VALIDATION COMPLETED")
        print(f"{'='*80}")
        print(f"Total: {len(invoice_ids)} | Processed: {processed_count} | Failed: {failed_count}")
        print(f"{'='*80}\n")
        
        logger.info(f"Batch validation completed: {processed_count}/{len(invoice_ids)} successful")
        
        return summary
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch validation failed: {str(e)}", exc_info=True)
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
