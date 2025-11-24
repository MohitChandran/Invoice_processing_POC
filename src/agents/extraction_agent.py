"""
Extraction Agent - Extracts invoice data using VLM.
Uses gemma3:27b to extract structured data from invoice images/PDFs.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from src.agents.llm_client import ollama_client
from src.services.extractor_utils import extractor_utils

logger = logging.getLogger(__name__)


class ExtractionAgent:
    """Agent for extracting structured data from invoices using VLM."""
    
    def __init__(self):
        self.llm_client = ollama_client
    
    async def extract_invoice_data(
        self, 
        file_path: Path, 
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract structured data from invoice.
        
        Args:
            file_path: Path to invoice file (PDF or image)
            session_id: Session identifier for logging
            
        Returns:
            Dict with extracted fields:
                - passenger_name: str
                - origin: str
                - destination: str
                - travel_date: str
                - fare: float
                - confidence: float (0-1)
                - raw_text: str (full extracted text)
                
        Raises:
            Exception: If extraction fails
        """
        try:
            log_prefix = f"[{session_id}] " if session_id else ""
            logger.info(f"{log_prefix}Extracting data from invoice: {file_path.name}")
            
            # Load document as image bytes
            image_bytes = extractor_utils.get_document_bytes(file_path)
            
            # Preprocess image
            processed_bytes = extractor_utils.preprocess_image(image_bytes)
            
            # Create extraction prompt
            extraction_prompt = self._create_extraction_prompt()
            
            system_prompt = """You are an AI vision model specialized in reading and extracting data from travel invoice documents.

YOUR TASK:
1. Carefully examine the entire invoice image
2. Locate and read all text fields in the document
3. Extract the 5 required fields: passenger_name, origin, destination, travel_date, fare
4. Return ONLY a valid JSON object with these fields
5. Do NOT include any explanation, markdown, or extra text

CRITICAL: Your response must be ONLY the JSON object, nothing else. No markdown, no code blocks, just pure JSON."""
            
            # Call VLM
            logger.info(f"{log_prefix}Calling VLM ({self.llm_client.vision_model}) for extraction...")
            logger.info(f"{log_prefix}Processing image: {file_path.name} ({len(processed_bytes)} bytes)")
            
            response = await self.llm_client.generate_with_vision(
                prompt=extraction_prompt,
                image_data=processed_bytes,
                system_prompt=system_prompt,
                temperature=0.1  # Low temperature for accuracy
            )
            
            # Parse response
            raw_response = response.get('response', '').strip()
            logger.info(f"{log_prefix}VLM response length: {len(raw_response)} characters")
            logger.info(f"{log_prefix}Raw VLM response (full): {raw_response}")
            
            # Extract JSON from response
            extracted_data = self._parse_extraction_response(raw_response)
            logger.info(f"{log_prefix}Parsed JSON: {json.dumps(extracted_data, indent=2)}")
            
            # Validate and normalize extracted data
            normalized_data = self._normalize_extracted_data(extracted_data)
            
            logger.info(f"{log_prefix}Successfully extracted invoice data")
            logger.info(f"{log_prefix}Normalized data: {json.dumps(normalized_data, indent=2)}")
            
            return normalized_data
            
        except Exception as e:
            logger.error(f"{log_prefix}Invoice extraction failed: {str(e)}", exc_info=True)
            raise Exception(f"Failed to extract invoice data: {str(e)}")
    
    def _create_extraction_prompt(self) -> str:
        """Create prompt for invoice data extraction."""
        
        prompt = """You are analyzing a TRAVEL INVOICE IMAGE. Look at the image carefully and extract these EXACT fields:

📋 REQUIRED FIELDS TO EXTRACT:
================================

1. **Passenger Name** (passenger_name)
   - Look for: "Passenger", "Name", "Traveler", "Customer Name"
   - Extract: Full name of the person traveling

2. **Origin/From** (origin)
   - Look for: "From", "Origin", "Departure", "Starting Point", "Source"
   - Extract: City, airport code, or location where journey starts

3. **Destination/To** (destination)
   - Look for: "To", "Destination", "Arrival", "Ending Point"
   - Extract: City, airport code, or location where journey ends

4. **Travel Date** (travel_date)
   - Look for: "Date", "Travel Date", "Journey Date", "Date of Travel"
   - Extract: Date in YYYY-MM-DD format (e.g., 2025-11-24)
   - If only DD/MM/YYYY or similar format found, convert to YYYY-MM-DD

5. **Fare/Amount** (fare)
   - Look for: "Fare", "Amount", "Total", "Price", "Cost", "₹", "Rs", "INR"
   - Extract: ONLY the numeric value (e.g., if you see "₹5500.00", extract 5500.00)
   - Remove currency symbols, commas, and text

================================
RESPONSE FORMAT (JSON ONLY):
================================

Respond with ONLY this JSON structure, nothing else:

{
    "passenger_name": "John Doe",
    "origin": "Mumbai",
    "destination": "Delhi",
    "travel_date": "2025-11-24",
    "fare": 5500.00,
    "confidence": 0.95,
    "notes": "All fields extracted clearly"
}

RULES:
- Look at EVERY part of the image - top, bottom, left, right, center
- Read ALL text in the image carefully
- If a field is not visible or unclear, use "unknown" for text fields and 0.0 for fare
- Set confidence between 0.0 (very uncertain) to 1.0 (very certain)
- DO NOT add any explanation or text outside the JSON
- DO NOT use markdown code blocks, just raw JSON

Now analyze the image and extract the information in JSON format:"""
        
        return prompt
    
    def _parse_extraction_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse LLM response to extract JSON data.
        
        Args:
            response_text: Raw response from LLM
            
        Returns:
            Parsed dict
            
        Raises:
            Exception: If parsing fails
        """
        try:
            # Try to find JSON in response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                raise Exception("No JSON found in response")
            
            json_str = response_text[json_start:json_end]
            
            # Parse JSON
            data = json.loads(json_str)
            
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {str(e)}")
            logger.error(f"Response text: {response_text}")
            raise Exception(f"Could not parse extraction result as JSON: {str(e)}")
        
        except Exception as e:
            logger.error(f"Response parsing failed: {str(e)}")
            raise Exception(f"Failed to parse extraction response: {str(e)}")
    
    def _normalize_extracted_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize and validate extracted data.
        
        Args:
            data: Raw extracted dict
            
        Returns:
            Normalized dict with required fields
        """
        try:
            normalized = {
                'passenger_name': str(data.get('passenger_name', 'unknown')).strip(),
                'origin': str(data.get('origin', 'unknown')).strip(),
                'destination': str(data.get('destination', 'unknown')).strip(),
                'travel_date': str(data.get('travel_date', 'unknown')).strip(),
                'fare': float(data.get('fare', 0.0)),
                'confidence': float(data.get('confidence', 0.5)),
                'notes': str(data.get('notes', '')).strip()
            }
            
            # Validate confidence range
            if normalized['confidence'] < 0.0:
                normalized['confidence'] = 0.0
            elif normalized['confidence'] > 1.0:
                normalized['confidence'] = 1.0
            
            # Check for missing critical fields
            missing_fields = []
            if normalized['passenger_name'] == 'unknown':
                missing_fields.append('passenger_name')
            if normalized['origin'] == 'unknown':
                missing_fields.append('origin')
            if normalized['destination'] == 'unknown':
                missing_fields.append('destination')
            if normalized['fare'] == 0.0:
                missing_fields.append('fare')
            
            if missing_fields:
                logger.warning(f"Missing fields in extraction: {missing_fields}")
                # Lower confidence if fields are missing
                normalized['confidence'] *= 0.7
            
            return normalized
            
        except Exception as e:
            logger.error(f"Data normalization failed: {str(e)}", exc_info=True)
            # Return minimal valid structure
            return {
                'passenger_name': 'unknown',
                'origin': 'unknown',
                'destination': 'unknown',
                'travel_date': 'unknown',
                'fare': 0.0,
                'confidence': 0.0,
                'notes': f'Normalization failed: {str(e)}'
            }
    
    async def extract_with_fallback(
        self,
        file_path: Path,
        session_id: Optional[str] = None,
        retry_count: int = 2
    ) -> Dict[str, Any]:
        """
        Extract with retry logic for robustness.
        
        Args:
            file_path: Path to invoice
            session_id: Session ID
            retry_count: Number of retries on failure
            
        Returns:
            Extracted data
        """
        last_error = None
        
        for attempt in range(retry_count + 1):
            try:
                if attempt > 0:
                    logger.info(f"Retry attempt {attempt} for extraction")
                
                result = await self.extract_invoice_data(file_path, session_id)
                
                # If confidence is too low, retry
                if result['confidence'] < 0.3 and attempt < retry_count:
                    logger.warning(f"Low confidence ({result['confidence']}), retrying...")
                    continue
                
                return result
                
            except Exception as e:
                last_error = e
                logger.warning(f"Extraction attempt {attempt + 1} failed: {str(e)}")
                
                if attempt >= retry_count:
                    break
        
        # All attempts failed
        logger.error(f"All extraction attempts failed: {str(last_error)}")
        raise Exception(f"Extraction failed after {retry_count + 1} attempts: {str(last_error)}")


# Singleton instance
extraction_agent = ExtractionAgent()
