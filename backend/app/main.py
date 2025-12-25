"""
Main FastAPI application.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db.database import init_db, close_db
from app.pricing.scheduler import pricing_scheduler
from app.api import upload, analysis, results, pricing

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting AWS Terraform Cost Calculator")
    
    # Initialize database
    await init_db()
    logger.info("Database initialized")
    
    # Start pricing scheduler
    pricing_scheduler.start()
    logger.info("Pricing scheduler started")
    
    yield
    
    # Shutdown
    logger.info("Shutting down")
    pricing_scheduler.stop()
    await close_db()


# Create FastAPI app
app = FastAPI(
    title="AWS Terraform Cost Calculator",
    description="Calculate AWS costs from Terraform files",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(upload.router, prefix="/api", tags=["upload"])
app.include_router(analysis.router, prefix="/api", tags=["analysis"])
app.include_router(results.router, prefix="/api", tags=["results"])
app.include_router(pricing.router, prefix="/api", tags=["pricing"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "pricing_scheduler": pricing_scheduler.is_running
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "AWS Terraform Cost Calculator API",
        "version": "1.0.0",
        "docs": "/docs"
    }
