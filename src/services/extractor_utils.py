"""
Extractor utilities for OCR and PDF processing.
"""

import io
import logging
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image
import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


class ExtractorUtils:
    """Utilities for document extraction and OCR."""
    
    @staticmethod
    def load_image_from_file(file_path: Path) -> bytes:
        """
        Load image file and return as bytes.
        
        Args:
            file_path: Path to image file
            
        Returns:
            Image bytes
            
        Raises:
            Exception: If image cannot be loaded
        """
        try:
            # Check if it's an image format
            image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif']
            
            if file_path.suffix.lower() in image_extensions:
                with open(file_path, 'rb') as f:
                    image_bytes = f.read()
                
                logger.info(f"Loaded image: {file_path.name} ({len(image_bytes)} bytes)")
                return image_bytes
            else:
                raise Exception(f"Not an image file: {file_path.suffix}")
                
        except Exception as e:
            logger.error(f"Failed to load image: {str(e)}", exc_info=True)
            raise Exception(f"Image load failed: {str(e)}")
    
    @staticmethod
    def pdf_to_image(file_path: Path, page_number: int = 0, dpi: int = 200) -> bytes:
        """
        Convert PDF page to image bytes.
        
        Args:
            file_path: Path to PDF file
            page_number: Page number (0-indexed)
            dpi: Resolution for conversion
            
        Returns:
            Image bytes (PNG format)
            
        Raises:
            Exception: If conversion fails
        """
        try:
            # Open PDF
            pdf_document = fitz.open(file_path)
            
            if page_number >= len(pdf_document):
                page_number = 0
            
            # Get page
            page = pdf_document[page_number]
            
            # Render page to image
            zoom = dpi / 72  # 72 is default DPI
            matrix = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=matrix)
            
            # Convert to PNG bytes
            img_bytes = pix.tobytes("png")
            
            pdf_document.close()
            
            logger.info(f"Converted PDF page {page_number} to image ({len(img_bytes)} bytes)")
            
            return img_bytes
            
        except Exception as e:
            logger.error(f"PDF to image conversion failed: {str(e)}", exc_info=True)
            raise Exception(f"PDF conversion failed: {str(e)}")
    
    @staticmethod
    def get_document_bytes(file_path: Path) -> bytes:
        """
        Get document as image bytes (handles PDF and images).
        
        Args:
            file_path: Path to document
            
        Returns:
            Image bytes suitable for VLM processing
        """
        try:
            file_ext = file_path.suffix.lower()
            
            # Handle PDFs
            if file_ext == '.pdf':
                return ExtractorUtils.pdf_to_image(file_path)
            
            # Handle images
            image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif']
            if file_ext in image_extensions:
                return ExtractorUtils.load_image_from_file(file_path)
            
            # Unsupported format
            raise Exception(f"Unsupported file format: {file_ext}")
            
        except Exception as e:
            logger.error(f"Document processing failed: {str(e)}", exc_info=True)
            raise
    
    @staticmethod
    def preprocess_image(image_bytes: bytes, resize_max: int = 1536) -> bytes:
        """
        Preprocess image for better OCR/VLM performance.
        Optimized for vision models - reduces size for faster processing.
        
        Args:
            image_bytes: Raw image bytes
            resize_max: Maximum dimension (width or height) - default 1536px for VLM
            
        Returns:
            Preprocessed image bytes
        """
        try:
            # Load image
            img = Image.open(io.BytesIO(image_bytes))
            
            # Convert to RGB if needed
            if img.mode not in ['RGB', 'L']:
                img = img.convert('RGB')
            
            # Resize if too large (VLMs work well with 1024-1536px images)
            width, height = img.size
            max_dim = max(width, height)
            
            if max_dim > resize_max:
                scale = resize_max / max_dim
                new_width = int(width * scale)
                new_height = int(height * scale)
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                logger.info(f"Resized image for VLM: {width}x{height} -> {new_width}x{new_height}")
            
            # Save to bytes with JPEG for smaller size (VLM-friendly)
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=85, optimize=True)
            processed_bytes = output.getvalue()
            
            logger.info(f"Preprocessed image: {len(image_bytes)} bytes -> {len(processed_bytes)} bytes (reduction: {100 - (len(processed_bytes)*100/len(image_bytes)):.1f}%)")
            
            return processed_bytes
            
        except Exception as e:
            logger.warning(f"Image preprocessing failed, using original: {str(e)}")
            return image_bytes


# Singleton instance
extractor_utils = ExtractorUtils()
