"""
Pydantic models for API request validation.
"""

from pydantic import BaseModel, Field
from typing import Optional


class ProcessValidationRequest(BaseModel):
    """Request model for /process-validation endpoint."""
    
    invoice_id: str = Field(..., description="Unique ID of uploaded invoice")
    proposal_id: str = Field(..., description="Unique ID of uploaded proposal Excel")
    
    class Config:
        json_schema_extra = {
            "example": {
                "invoice_id": "inv_1234567890",
                "proposal_id": "prop_0987654321"
            }
        }
