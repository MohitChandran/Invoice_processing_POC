"""
Configuration settings for the AI Travel Validator.
All environment variables and constants are defined here.
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Ollama Configuration
    OLLAMA_URL: str = "http://192.168.10.200:11434"  # Remote Ollama server
    MODEL_NAME: str = "gemma3:27b"  # Text LLM for policy validation
    VISION_MODEL: str = "gemma3:27b"  # Vision-Language Model for invoice extraction (supports vision!)
    LLM_TIMEOUT: int = 120  # seconds
    VISION_TIMEOUT: int = 60  # seconds (gemma3 is fast!)
    
    # File Storage
    UPLOAD_DIR: Path = BASE_DIR / "data" / "uploads"
    INVOICE_DIR: Path = UPLOAD_DIR / "invoices"
    PROPOSAL_DIR: Path = UPLOAD_DIR / "proposals"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    
    # Logging Configuration
    LOG_DIR: Path = BASE_DIR / "logs"
    LOG_FILE: Path = LOG_DIR / "app.log"
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(session_id)s - %(message)s"
    
    # RAG Configuration
    RAG_DIR: Path = BASE_DIR / "src" / "agents" / "rules_rag"
    RULES_FILE: Path = BASE_DIR / "smaple_business_policies.txt"  # Business policies file (note: user's filename has typo)
    VECTORSTORE_DIR: Path = RAG_DIR / "vs"
    EMBEDDING_MODEL: str = "mxbai-embed-large:latest"  # Ollama embedding model (available on server)
    TOP_K_RULES: int = 5  # Number of rules to retrieve
    CHUNK_SIZE: int = 500  # Characters per chunk
    CHUNK_OVERLAP: int = 50  # Overlap between chunks
    
    # Session Management
    SESSION_TIMEOUT: int = 3600  # 1 hour in seconds
    SESSION_CLEANUP_INTERVAL: int = 300  # 5 minutes
    
    # Excel Configuration
    EXPECTED_EXCEL_COLUMNS: list = ["name", "employee_level", "fare_limit"]
    FUZZY_MATCH_THRESHOLD: int = 85  # Minimum similarity score
    
    # API Configuration
    API_TITLE: str = "AI Travel Invoice Validator"
    API_VERSION: str = "1.0.0"
    API_DESCRIPTION: str = "Backend POC for AI-powered travel invoice validation"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Singleton instance
settings = Settings()

# Create required directories
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
settings.INVOICE_DIR.mkdir(parents=True, exist_ok=True)
settings.PROPOSAL_DIR.mkdir(parents=True, exist_ok=True)
settings.LOG_DIR.mkdir(parents=True, exist_ok=True)
settings.RAG_DIR.mkdir(parents=True, exist_ok=True)
settings.VECTORSTORE_DIR.mkdir(parents=True, exist_ok=True)
