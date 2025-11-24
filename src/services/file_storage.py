"""
File storage service for managing uploaded invoices and proposals.
"""

import uuid
import shutil
import logging
from pathlib import Path
from typing import Tuple
from fastapi import UploadFile
from src.config.settings import settings

logger = logging.getLogger(__name__)


class FileStorage:
    """Handles file upload and storage."""
    
    @staticmethod
    def generate_file_id(prefix: str) -> str:
        """
        Generate unique file ID.
        
        Args:
            prefix: Prefix for the ID (e.g., 'inv' or 'prop')
            
        Returns:
            Unique file ID
        """
        unique_id = str(uuid.uuid4()).replace('-', '')[:12]
        return f"{prefix}_{unique_id}"
    
    @staticmethod
    async def save_invoice(file: UploadFile) -> Tuple[str, Path]:
        """
        Save uploaded invoice file.
        
        Args:
            file: Uploaded file from FastAPI
            
        Returns:
            Tuple of (file_id, file_path)
            
        Raises:
            Exception: If file save fails
        """
        try:
            # Validate file size
            file_content = await file.read()
            if len(file_content) > settings.MAX_FILE_SIZE:
                raise Exception(f"File size exceeds limit of {settings.MAX_FILE_SIZE / 1024 / 1024}MB")
            
            # Generate unique ID
            file_id = FileStorage.generate_file_id("inv")
            
            # Extract file extension
            original_name = file.filename or "invoice"
            file_ext = Path(original_name).suffix or ".pdf"
            
            # Save file
            file_path = settings.INVOICE_DIR / f"{file_id}{file_ext}"
            
            with open(file_path, "wb") as f:
                f.write(file_content)
            
            logger.info(f"Saved invoice: {file_id} ({len(file_content)} bytes)")
            
            return file_id, file_path
            
        except Exception as e:
            logger.error(f"Failed to save invoice: {str(e)}", exc_info=True)
            raise Exception(f"Failed to save invoice: {str(e)}")
    
    @staticmethod
    async def save_proposal(file: UploadFile) -> Tuple[str, Path]:
        """
        Save uploaded proposal Excel file.
        
        Args:
            file: Uploaded Excel file
            
        Returns:
            Tuple of (file_id, file_path)
            
        Raises:
            Exception: If file save fails
        """
        try:
            # Validate file size
            file_content = await file.read()
            if len(file_content) > settings.MAX_FILE_SIZE:
                raise Exception(f"File size exceeds limit of {settings.MAX_FILE_SIZE / 1024 / 1024}MB")
            
            # Validate file extension
            original_name = file.filename or "proposal.xlsx"
            file_ext = Path(original_name).suffix.lower()
            
            if file_ext not in ['.xlsx', '.xls', '.csv']:
                raise Exception(f"Invalid file type: {file_ext}. Expected Excel or CSV file.")
            
            # Generate unique ID
            file_id = FileStorage.generate_file_id("prop")
            
            # Save file
            file_path = settings.PROPOSAL_DIR / f"{file_id}{file_ext}"
            
            with open(file_path, "wb") as f:
                f.write(file_content)
            
            logger.info(f"Saved proposal: {file_id} ({len(file_content)} bytes)")
            
            return file_id, file_path
            
        except Exception as e:
            logger.error(f"Failed to save proposal: {str(e)}", exc_info=True)
            raise Exception(f"Failed to save proposal: {str(e)}")
    
    @staticmethod
    def get_invoice_path(file_id: str) -> Path:
        """
        Get path to saved invoice file.
        
        Args:
            file_id: Invoice file ID
            
        Returns:
            Path to file
            
        Raises:
            FileNotFoundError: If file doesn't exist
        """
        # Search for file with any extension
        for file_path in settings.INVOICE_DIR.glob(f"{file_id}.*"):
            if file_path.is_file():
                logger.debug(f"Found invoice: {file_path}")
                return file_path
        
        logger.error(f"Invoice not found: {file_id}")
        raise FileNotFoundError(f"Invoice {file_id} not found")
    
    @staticmethod
    def get_proposal_path(file_id: str) -> Path:
        """
        Get path to saved proposal file.
        
        Args:
            file_id: Proposal file ID
            
        Returns:
            Path to file
            
        Raises:
            FileNotFoundError: If file doesn't exist
        """
        # Search for file with any extension
        for file_path in settings.PROPOSAL_DIR.glob(f"{file_id}.*"):
            if file_path.is_file():
                logger.debug(f"Found proposal: {file_path}")
                return file_path
        
        logger.error(f"Proposal not found: {file_id}")
        raise FileNotFoundError(f"Proposal {file_id} not found")
    
    @staticmethod
    def cleanup_old_files(max_age_hours: int = 24):
        """
        Remove files older than specified age.
        
        Args:
            max_age_hours: Maximum file age in hours
        """
        try:
            import time
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            
            deleted_count = 0
            
            for directory in [settings.INVOICE_DIR, settings.PROPOSAL_DIR]:
                for file_path in directory.iterdir():
                    if file_path.is_file():
                        file_age = current_time - file_path.stat().st_mtime
                        if file_age > max_age_seconds:
                            file_path.unlink()
                            deleted_count += 1
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old files")
                
        except Exception as e:
            logger.error(f"File cleanup failed: {str(e)}", exc_info=True)


# Singleton instance
file_storage = FileStorage()
