"""
Chat request/response schemas
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any


class TripState(BaseModel):
    """Trip planning state"""
    destination: Optional[str] = None
    days: int = 0
    budget_level: Optional[str] = None
    companions: Optional[str] = None
    preferences: Dict[str, Any] = Field(default_factory=dict)


class UserPreferences(BaseModel):
    """User preferences for personalization"""
    keywords: List[str] = Field(default_factory=list)
    avoid: List[str] = Field(default_factory=list)
    special_needs: List[str] = Field(default_factory=list)


class ChatRequest(BaseModel):
    """Request model for chat endpoint"""
    message: str = Field(..., description="User message/query")
    trip_state: Optional[TripState] = Field(default_factory=TripState)
    user_preferences: Optional[UserPreferences] = Field(default_factory=UserPreferences)
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Lịch trình Đà Lạt 3 ngày dưới 5 triệu",
                "trip_state": {
                    "destination": "Đà Lạt",
                    "days": 3,
                    "budget_level": "medium"
                },
                "user_preferences": {
                    "keywords": ["yên tĩnh", "thiên nhiên"],
                    "avoid": ["đông người"]
                }
            }
        }


class SubQueryInfo(BaseModel):
    """Information about a sub-query in the plan"""
    query_id: str
    query_type: str
    query_text: str
    filters: Dict[str, Any] = Field(default_factory=dict)
    priority: int


class ChatResponse(BaseModel):
    """Response model for chat endpoint"""
    response: str = Field(..., description="AI generated response")
    results: Dict[str, Any] = Field(default_factory=dict, description="Structured results from experts")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score")
    plan: List[SubQueryInfo] = Field(default_factory=list, description="Query execution plan")
    sources: List[Dict[str, Any]] = Field(default_factory=list, description="Source documents")
    suggested_actions: List[str] = Field(default_factory=list, description="Suggested next actions")
    
    class Config:
        json_schema_extra = {
            "example": {
                "response": "Đây là lịch trình 3 ngày tại Đà Lạt...",
                "results": {
                    "hotels": [...],
                    "spots": [...],
                    "itinerary": [...]
                },
                "confidence": 0.95,
                "plan": [
                    {
                        "query_id": "q1",
                        "query_type": "hotel",
                        "query_text": "Tìm khách sạn ở Đà Lạt",
                        "filters": {"price": {"$lte": 5000000}},
                        "priority": 1
                    }
                ],
                "sources": [],
                "suggested_actions": ["Đặt khách sạn", "Xem chi tiết địa điểm"]
            }
        }


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    service: str
    version: str
    mongodb: str
    chromadb: str
