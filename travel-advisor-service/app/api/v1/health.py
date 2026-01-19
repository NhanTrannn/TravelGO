"""
Health check endpoint
"""

from fastapi import APIRouter
from app.schemas import HealthResponse
from app.core import settings
from app.db import mongodb_manager, vector_store

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    
    # Check MongoDB
    mongodb_status = mongodb_manager.health_check()
    
    # Check ChromaDB
    chromadb_status = vector_store.health_check()
    
    overall_status = "healthy" if (mongodb_status and chromadb_status) else "unhealthy"
    
    return HealthResponse(
        status=overall_status,
        service=settings.SERVICE_NAME,
        version=settings.SERVICE_VERSION,
        mongodb=mongodb_status,
        chromadb=chromadb_status
    )
