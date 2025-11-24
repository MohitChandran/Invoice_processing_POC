#!/usr/bin/env python3
"""
Simple test script to verify qwen3-vl:32b can extract fields from invoice PDF.
Tests the complete extraction pipeline with your actual PDF.
"""

import sys
import asyncio
import base64
import json
from pathlib import Path
from PIL import Image
import io

# PyMuPDF for PDF processing
import fitz


def pdf_to_image(pdf_path: str, page: int = 0) -> bytes:
    """Convert PDF page to image bytes."""
    print(f"📄 Converting PDF to image...")
    
    doc = fitz.open(pdf_path)
    page_obj = doc[page]
    
    # Render at 200 DPI
    zoom = 200 / 72
    matrix = fitz.Matrix(zoom, zoom)
    pix = page_obj.get_pixmap(matrix=matrix)
    
    # Convert to PNG bytes
    img_bytes = pix.tobytes("png")
    doc.close()
    
    print(f"   ✓ PDF converted: {len(img_bytes)} bytes")
    return img_bytes


def optimize_image(img_bytes: bytes, max_size: int = 1536) -> bytes:
    """Optimize image for VLM processing."""
    print(f"🖼️  Optimizing image...")
    
    img = Image.open(io.BytesIO(img_bytes))
    
    # Convert to RGB
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    # Resize if needed
    width, height = img.size
    max_dim = max(width, height)
    
    if max_dim > max_size:
        scale = max_size / max_dim
        new_width = int(width * scale)
        new_height = int(height * scale)
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        print(f"   ✓ Resized: {width}x{height} → {new_width}x{new_height}")
    
    # Save as JPEG
    output = io.BytesIO()
    img.save(output, format='JPEG', quality=85, optimize=True)
    optimized = output.getvalue()
    
    reduction = 100 - (len(optimized) * 100 / len(img_bytes))
    print(f"   ✓ Optimized: {len(img_bytes)} → {len(optimized)} bytes (↓{reduction:.1f}%)")
    
    return optimized


async def extract_with_qwen(image_bytes: bytes, ollama_url: str = "http://192.168.10.200:11434") -> dict:
    """Send image to gemma3:27b model for extraction (supports vision!)."""
    import httpx
    
    print(f"\n🤖 Sending to gemma3:27b (with vision support)...")
    
    # Encode image
    image_b64 = base64.b64encode(image_bytes).decode('utf-8')
    
    # Create prompt
    prompt = """You are analyzing a TRAVEL INVOICE/TICKET IMAGE. Extract these EXACT fields:

📋 REQUIRED FIELDS:
==================

1. **Passenger Name** (passenger_name)
   - Look for: "Passenger", "Name", "Traveler", "Customer Name"
   
2. **Origin/From** (origin)
   - Look for: "From", "Origin", "Departure", "Starting Point"
   
3. **Destination/To** (destination)
   - Look for: "To", "Destination", "Arrival"
   
4. **Travel Date** (travel_date)
   - Look for: "Date", "Travel Date", "Journey Date"
   - Format: YYYY-MM-DD
   
5. **Fare/Amount** (fare)
   - Look for: "Fare", "Amount", "Total", "Price", "₹", "Rs"
   - Extract ONLY numeric value (e.g., 5500.00)

==================
RESPONSE (JSON ONLY):
==================

{
    "passenger_name": "extracted name",
    "origin": "extracted origin",
    "destination": "extracted destination",
    "travel_date": "YYYY-MM-DD",
    "fare": 0.00,
    "confidence": 0.95,
    "notes": "observations"
}

RULES:
- Read ALL text in the image carefully
- If field not found, use "unknown" for text or 0.0 for fare
- Respond ONLY with JSON, no markdown, no explanation

Extract now:"""
    
    system_prompt = """You are an AI vision model specialized in reading travel documents.
Extract the 5 required fields and return ONLY a valid JSON object.
Do NOT include any explanation or extra text."""
    
    # Prepare request - Using gemma3:27b instead of qwen3-vl (MUCH faster!)
    payload = {
        "model": "gemma3:27b",
        "prompt": prompt,
        "system": system_prompt,
        "images": [image_b64],
        "stream": False,
        "options": {
            "temperature": 0.1
        }
    }
    
    print(f"   • Model: gemma3:27b (supports vision!)")
    print(f"   • Image size: {len(image_bytes)} bytes")
    print(f"   • Timeout: 60 seconds")
    print(f"   • Endpoint: {ollama_url}/api/generate")
    
    print(f"\n⏳ Processing (should take 10-30 seconds)...\n")
    
    # Send request with shorter timeout since gemma3 is faster
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            f"{ollama_url}/api/generate",
            json=payload
        )
        response.raise_for_status()
        result = response.json()
    
    return result


def parse_json_from_response(response_text: str) -> dict:
    """Extract JSON from VLM response."""
    # Find JSON object
    json_start = response_text.find('{')
    json_end = response_text.rfind('}') + 1
    
    if json_start == -1 or json_end == 0:
        raise ValueError("No JSON found in response")
    
    json_str = response_text[json_start:json_end]
    return json.loads(json_str)


async def main():
    """Main test function."""
    
    PDF_PATH = "/home/mohitchandran/Downloads/mohit_dummyticket.pdf"
    
    print("=" * 70)
    print("🧪 GEMMA3 VISION EXTRACTION TEST")
    print("=" * 70)
    print(f"\n📍 PDF Path: {PDF_PATH}\n")
    
    # Check if file exists
    if not Path(PDF_PATH).exists():
        print(f"❌ Error: File not found: {PDF_PATH}")
        return
    
    try:
        # Step 1: Convert PDF to image
        img_bytes = pdf_to_image(PDF_PATH)
        
        # Step 2: Optimize image
        optimized_bytes = optimize_image(img_bytes)
        
        # Step 3: Extract with qwen3-vl
        result = await extract_with_qwen(optimized_bytes)
        
        # Step 4: Parse response
        raw_response = result.get('response', '').strip()
        
        print("=" * 70)
        print("📤 VLM RESPONSE")
        print("=" * 70)
        print(raw_response)
        print()
        
        # Step 5: Parse JSON
        try:
            extracted_data = parse_json_from_response(raw_response)
            
            print("=" * 70)
            print("✅ EXTRACTION SUCCESSFUL")
            print("=" * 70)
            print(f"\n📋 Extracted Fields:\n")
            print(f"   Passenger Name:  {extracted_data.get('passenger_name', 'N/A')}")
            print(f"   From:            {extracted_data.get('origin', 'N/A')}")
            print(f"   To:              {extracted_data.get('destination', 'N/A')}")
            print(f"   Date:            {extracted_data.get('travel_date', 'N/A')}")
            print(f"   Fare:            ₹{extracted_data.get('fare', 0.0)}")
            print(f"   Confidence:      {extracted_data.get('confidence', 0.0):.2%}")
            
            if extracted_data.get('notes'):
                print(f"   Notes:           {extracted_data.get('notes', '')}")
            
            print("\n" + "=" * 70)
            print("📊 FULL JSON OUTPUT")
            print("=" * 70)
            print(json.dumps(extracted_data, indent=2))
            
        except json.JSONDecodeError as e:
            print("=" * 70)
            print("❌ JSON PARSING FAILED")
            print("=" * 70)
            print(f"Error: {e}")
            print(f"\nThe model returned non-JSON text. Full response above.")
        
    except Exception as e:
        print("=" * 70)
        print("❌ TEST FAILED")
        print("=" * 70)
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("Starting extraction test...")
    print("=" * 70 + "\n")
    
    asyncio.run(main())
    
    print("\n" + "=" * 70)
    print("Test complete!")
    print("=" * 70 + "\n")
