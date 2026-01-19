"""
API v1 routes
"""

from fastapi import APIRouter
from .chat import router as chat_router
from .health import router as health_router
from .b2b_auth import router as b2b_auth_router

api_router = APIRouter()

api_router.include_router(chat_router, tags=["chat"])
api_router.include_router(health_router, tags=["health"])
api_router.include_router(b2b_auth_router, tags=["b2b"])
