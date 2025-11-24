"""
FastAPI main application entry point.
Initializes logging, routes, and starts the server.
"""

import logging
import logging.handlers
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import time
import uuid

from src.config.settings import settings
from src.routes import upload_routes, process_routes, session_routes
from src.agents.llm_client import ollama_client


# Custom logging filter to add session_id to log records
class SessionContextFilter(logging.Filter):
    """Add session_id to log records."""
    
    def filter(self, record):
        if not hasattr(record, 'session_id'):
            record.session_id = 'no-session'
        return True


def setup_logging():
    """
    Configure centralized logging system.
    All logs written to logs/app.log with proper formatting.
    """
    # Create logs directory
    settings.LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    # Create formatter
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - [%(session_id)s] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        settings.LOG_FILE,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    file_handler.addFilter(SessionContextFilter())
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(SessionContextFilter())
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Reduce noise from external libraries
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    logging.getLogger('chromadb').setLevel(logging.WARNING)
    logging.getLogger('sentence_transformers').setLevel(logging.WARNING)
    
    logging.info("Logging system initialized")
    logging.info(f"Log file: {settings.LOG_FILE}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup/shutdown events.
    """
    # Startup
    logger = logging.getLogger(__name__)
    logger.info("=" * 80)
    logger.info("AI Travel Invoice Validator Starting...")
    logger.info("=" * 80)
    
    # Health check Ollama
    logger.info("Checking Ollama connection...")
    try:
        health = await ollama_client.health_check()
        if health:
            logger.info(f"✓ Ollama connected: {settings.OLLAMA_URL}")
            logger.info(f"✓ Model available: {settings.MODEL_NAME}")
        else:
            logger.warning(f"⚠ Ollama health check failed - some features may not work")
    except Exception as e:
        logger.error(f"⚠ Ollama connection error: {str(e)}")
    
    # Check RAG system
    try:
        from src.agents.rules_rag.query_vectorstore import rules_retriever
        rules_retriever._initialize()
        logger.info("✓ RAG system initialized")
    except Exception as e:
        logger.warning(f"⚠ RAG system initialization failed: {str(e)}")
        logger.warning("  Run build_vectorstore.py to create embeddings")
    
    logger.info("Application ready!")
    logger.info("=" * 80)
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    logger.info("Goodbye!")


# Initialize FastAPI app
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description=settings.API_DESCRIPTION,
    lifespan=lifespan
)

# CORS middleware (adjust for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests with timing."""
    request_id = str(uuid.uuid4())[:8]
    start_time = time.time()
    
    logger = logging.getLogger(__name__)
    logger.info(f"Request {request_id}: {request.method} {request.url.path}")
    
    # Add request_id to request state
    request.state.request_id = request_id
    
    try:
        response = await call_next(request)
        
        duration = time.time() - start_time
        logger.info(f"Request {request_id} completed: {response.status_code} ({duration:.2f}s)")
        
        return response
        
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Request {request_id} failed: {str(e)} ({duration:.2f}s)", exc_info=True)
        raise


# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions."""
    logger = logging.getLogger(__name__)
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc)
        }
    )


# Include routers
app.include_router(session_routes.router)
app.include_router(upload_routes.router)
app.include_router(process_routes.router)


# Health check endpoint
@app.get("/")
async def root():
    """Root endpoint - API info."""
    return {
        "service": settings.API_TITLE,
        "version": settings.API_VERSION,
        "status": "running",
        "endpoints": {
            "upload_invoice": "/api/upload-invoice",
            "upload_proposal": "/api/upload-proposal",
            "process_validation": "/api/process-validation"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    health_status = {
        "status": "healthy",
        "ollama": "unknown",
        "rag": "unknown"
    }
    
    # Check Ollama
    try:
        ollama_health = await ollama_client.health_check()
        health_status["ollama"] = "connected" if ollama_health else "disconnected"
    except:
        health_status["ollama"] = "error"
    
    # Check RAG
    try:
        from src.agents.rules_rag.query_vectorstore import rules_retriever
        rules = rules_retriever.retrieve_rules("test", top_k=1)
        health_status["rag"] = "ready" if rules else "not_ready"
    except:
        health_status["rag"] = "error"
    
    return health_status


# Initialize logging on module import
setup_logging()
logger = logging.getLogger(__name__)


if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting server directly...")
    
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_config=None  # Use our custom logging
    )
