from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import os
from llm_monitor.logging_config import setup_logging
setup_logging()
from llm_monitor import init_discovery_manager, get_discovery_manager
from llm_monitor.env_config import load_discovery_config, load_endpoints_refresh_interval
from llm_monitor.endpoints import router as llmm
from llm_monitor.endpoints_cache import get_endpoints_cache
from loguru import logger


async def start_endpoints_refresh_loop():
    """
    Background task that periodically refreshes the endpoints cache.
    
    This reduces load on Ollama hosts when multiple clients are polling
    the /llmm endpoint by serving cached data instead of querying hosts
    on every request.
    """
    refresh_interval = load_endpoints_refresh_interval()
    endpoints_cache = get_endpoints_cache()
    
    logger.info(f"Starting endpoints refresh loop (interval: {refresh_interval}s)")
    
    while True:
        try:
            json_endpoints = {}
            for label, endpoint in get_discovery_manager().get_plugin_service().llm_endpoints().items():
                json_endpoints[label] = endpoint.model_dump()
            
            # Update cache
            await endpoints_cache.update_endpoints(json_endpoints)
            
            logger.debug(f"Endpoints cache refreshed: {len(json_endpoints)} endpoint(s)")
            
        except Exception as e:
            logger.error(f"Error refreshing endpoints cache: {e}")
        
        # Wait for next refresh interval
        await asyncio.sleep(refresh_interval)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan event handler for startup and shutdown.
    Manages the discovery loop and endpoints cache refresh lifecycle.
    """
    # Startup
    logger.info("Starting application...")
    try:
        asyncio.create_task(get_discovery_manager().start_discovery_loop())
        logger.info("Discovery loop started")
        
        # Start endpoints cache refresh loop as background task
        asyncio.create_task(start_endpoints_refresh_loop())
        logger.info("Endpoints refresh loop started")
    except Exception as e:
        logger.error(f"Failed to start background tasks: {e}")
        raise
    
    yield  # Application is running
    
    # Shutdown
    logger.info("Shutting down application...")
    try:
        await get_discovery_manager().stop()
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
@app.post("/health")
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
