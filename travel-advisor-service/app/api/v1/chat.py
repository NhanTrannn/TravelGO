"""
Chat API endpoint
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json
import asyncio
from app.schemas import ChatRequest, ChatResponse
from app.services import rag_service
from app.core import logger

router = APIRouter()


# === PLAN-RAG ENDPOINT (NEW) ===

class PlanRAGRequest(BaseModel):
    """Request for Plan-RAG endpoint"""
    messages: List[Dict[str, str]]  # [{"role": "user", "content": "..."}]
    context: Optional[Dict[str, Any]] = None


class PlanRAGResponse(BaseModel):
    """Response from Plan-RAG endpoint"""
    reply: str
    ui_type: str = "none"
    ui_data: Optional[Dict[str, Any]] = None
    intent: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    data: Optional[Dict[str, Any]] = None
    execution_time_ms: Optional[int] = None


# Lazy-load controller
_master_controller = None

def get_master_controller():
    global _master_controller
    if _master_controller is None:
        from app.services.master_controller import create_master_controller
        _master_controller = create_master_controller()
    return _master_controller


@router.post("/plan-rag", response_model=PlanRAGResponse)
async def plan_rag_chat(request: PlanRAGRequest):
    """
    Plan-RAG endpoint - Advanced query processing
    
    Uses Plan-RAG architecture:
    1. Preprocess: Extract intent, entities, constraints
    2. Plan: Decompose into sub-tasks
    3. Execute: Run expert executors
    4. Generate: Create response
    """
    try:
        logger.info(f"📩 Plan-RAG request: {len(request.messages)} messages")
        
        controller = get_master_controller()
        
        result = controller.process_request(
            messages=request.messages,
            context=request.context
        )
        
        return PlanRAGResponse(**result)
        
    except Exception as e:
        logger.error(f"❌ Plan-RAG error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# === STREAMING ENDPOINT (NEW) ===

@router.post("/chat/stream")
async def chat_stream(request: PlanRAGRequest):
    """
    Streaming chat endpoint - Progressive response
    
    Returns results as they become available:
    1. First spots found → Send immediately
    2. Hotels found → Send next
    3. Itinerary generated → Send next
    4. Cost calculated → Send final
    
    Uses Server-Sent Events (SSE) format
    """
    
    async def generate_stream():
        """Generate SSE stream"""
        try:
            logger.info(f"📡 Streaming request: {len(request.messages)} messages")
            
            controller = get_master_controller()
            
            # Process with streaming
            async for chunk in controller.process_stream(
                messages=request.messages,
                context=request.context
            ):
                # Send each chunk as SSE
                data = json.dumps(chunk, ensure_ascii=False)
                yield f"data: {data}\n\n"
                
                # Small delay for frontend processing
                await asyncio.sleep(0.1)
            
            # Send completion signal
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            logger.error(f"❌ Streaming error: {e}", exc_info=True)
            error_data = json.dumps({
                "error": str(e),
                "reply": "⚠️ Xin lỗi, có lỗi xảy ra khi xử lý yêu cầu của bạn.",
                "ui_type": "none"
            }, ensure_ascii=False)
            yield f"data: {error_data}\n\n"
            yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


# === LEGACY ENDPOINT ===

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Legacy chat endpoint for travel advisor
    Uses simple RAG service
    
    Handles:
    - Hotel search with budget parsing
    - Spot search with semantic similarity
    - Itinerary generation (future)
    """
    try:
        logger.info(f"📩 Received chat request: {request.message[:50]}...")
        
        # Convert trip_state to dict
        trip_state_dict = request.trip_state.model_dump() if request.trip_state else {}
        
        # Call RAG service
        result = rag_service.chat(
            message=request.message,
            trip_state=trip_state_dict
        )
        
        return ChatResponse(**result)
        
    except Exception as e:
        logger.error(f"❌ Chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

