"""
Pydantic models for API response validation.
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal


class UploadResponse(BaseModel):
    """Response model for file upload endpoints."""
    
    file_id: str = Field(..., description="Unique identifier for uploaded file")
    filename: str = Field(..., description="Original filename")
    message: str = Field(..., description="Status message")
    
    class Config:
        json_schema_extra = {
            "example": {
                "file_id": "inv_1234567890",
                "filename": "invoice.pdf",
                "message": "Invoice uploaded successfully"
            }
        }


class ValidationResponse(BaseModel):
    """Response model for /process-validation endpoint."""
    
    name: str = Field(..., description="Passenger name from invoice")
    from_location: str = Field(..., alias="from", description="Origin location")
    to_location: str = Field(..., alias="to", description="Destination location")
    date: str = Field(..., description="Travel date")
    fare: float = Field(..., description="Fare amount")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0-1)")
    validation_status: Literal["approved", "rejected"] = Field(..., description="Validation result")
    remarks: str = Field(..., description="Explanation of validation decision")
    session_id: Optional[str] = Field(None, description="Session identifier for tracking")
    
    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "name": "John Doe",
                "from": "Mumbai",
                "to": "Delhi",
                "date": "2025-11-25",
                "fare": 5500.00,
                "confidence": 0.92,
                "validation_status": "approved",
                "remarks": "Fare is within policy limits for employee level",
                "session_id": "sess_abc123"
            }
        }


class SessionResponse(BaseModel):
    """Response model for session creation."""
    
    session_id: str = Field(..., description="Unique session identifier")
    message: str = Field(..., description="Status message")
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "abc123-def456-789",
                "message": "Session created successfully"
            }
        }


class ErrorResponse(BaseModel):
    """Response model for errors."""
    
    error: str = Field(..., description="Error message")
    details: Optional[str] = Field(None, description="Additional error details")
    session_id: Optional[str] = Field(None, description="Session identifier if available")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "File not found",
                "details": "Invoice ID does not exist",
                "session_id": "sess_abc123"
            }
        }
