from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import asyncio
import os

# Setup logging first, before any other imports that might log
from llm_monitor.logging_config import setup_logging
setup_logging()

from llm_monitor import init_discovery_manager, get_discovery_manager
from llm_monitor.env_config import load_discovery_config
from llm_monitor.endpoints import router as llmm
from loguru import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan event handler for startup and shutdown.
    Manages the discovery loop lifecycle.
    """
    # Startup
    logger.info("Starting application...")
    try:
        discovery_manager = get_discovery_manager()
        # Start discovery loop as background task
        asyncio.create_task(discovery_manager.start_discovery_loop())
        logger.info("Discovery loop started")
    except Exception as e:
        logger.error(f"Failed to start discovery loop: {e}")
        raise
    
    yield  # Application is running
    
    # Shutdown
    logger.info("Shutting down application...")
    try:
        discovery_manager = get_discovery_manager()
        await discovery_manager.stop()
        logger.info("Discovery manager stopped")
    except Exception as e:
        logger.error(f"Error stopping discovery manager: {e}")


# Initialize FastAPI app with lifespan handler
app = FastAPI(
    title="LLM Monitor",
    description="Network discovery and monitoring for Ollama hosts",
    lifespan=lifespan
)

# Add CORS middleware
allowed_origins = os.getenv('ALLOWED_ORIGINS', 'http://localhost:3000,http://localhost:5173').split(',')
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Add security middleware
trusted_hosts = os.getenv('TRUSTED_HOSTS', 'localhost,127.0.0.1').split(',')
app.add_middleware(TrustedHostMiddleware, allowed_hosts=trusted_hosts)

# Initialize discovery manager
try:
    logger.info("Initializing discovery manager...")
    discovery_config = load_discovery_config()
    discovery_manager = init_discovery_manager(discovery_config)
    logger.info("Discovery manager initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize discovery manager: {e}")
    raise


# Include routers
router = APIRouter()
app.include_router(router)
app.include_router(llmm, prefix="/llmm", tags=["LLM-Monitor"])


@app.get("/")
def read_root():
    """Root endpoint"""
    logger.info("Root endpoint called")
    return {"message": "LLM Monitor API", "status": "running"}


@app.get("/health")
def health_check():
    """Health check endpoint for Kubernetes/Docker health probes"""
    try:
        discovery_manager = get_discovery_manager()
        stats = discovery_manager.get_stats()
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "healthy",
                "service": "llm-monitor",
                "discovery": stats
            }
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "service": "llm-monitor",
                "error": str(e)
            }
        )
