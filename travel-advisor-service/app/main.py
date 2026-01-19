# -*- coding: utf-8 -*-
"""
FastAPI main application
"""

import json
import numpy as np
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core import settings, logger
from app.db import mongodb_manager, vector_store

# NOTE: Removed api_router import - /api/v1/* endpoints not used by frontend
# from app.api import api_router


class NumpyEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles numpy arrays and other non-serializable types"""

    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if hasattr(obj, "to_dict"):
            return obj.to_dict()
        return super().default(obj)


def clean_for_json(data):
    """Recursively clean data for JSON serialization"""
    if isinstance(data, dict):
        cleaned = {}
        for k, v in data.items():
            # Skip embedding fields entirely
            if k in ["embedding", "embeddings", "vector", "_id"]:
                continue
            cleaned[k] = clean_for_json(v)
        return cleaned
    elif isinstance(data, list):
        return [clean_for_json(item) for item in data]
    elif isinstance(data, np.ndarray):
        return data.tolist()
    elif isinstance(data, (np.integer, np.floating)):
        return float(data)
    else:
        return data


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""

    # Startup
    logger.info(f"🚀 Starting {settings.SERVICE_NAME} v{settings.SERVICE_VERSION}")

    try:
        # Connect to MongoDB
        mongodb_manager.connect()

        # Connect to ChromaDB
        vector_store.connect()

        logger.info("✅ All services ready!")

    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise

    yield

    # Shutdown
    logger.info("🔒 Shutting down...")
    mongodb_manager.close()
    logger.info("👋 Goodbye!")


# Create FastAPI app with enhanced documentation
app = FastAPI(
    title="Travel Advisor AI - SaoLa 3.1 Powered",
    version=settings.SERVICE_VERSION,
    description="AI-powered travel advisor for Vietnam with interactive itinerary builder, hotel booking, and cost calculation. Uses SaoLa 3.1 LLM and Plan-RAG architecture.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# NOTE: Removed /api/v1/* routes - not used by frontend
# Frontend uses /chat and /chat/stream at root level instead
# app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": settings.SERVICE_NAME,
        "version": settings.SERVICE_VERSION,
        "status": "running",
        "docs": "/docs",
    }


@app.get("/endpoints", response_class=HTMLResponse)
async def list_endpoints():
    """Display all available API endpoints in a nice HTML page"""
    html_content = """
    <!DOCTYPE html>
    <html lang="vi">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Travel Advisor API - Endpoints</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                border-radius: 20px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                overflow: hidden;
            }
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 40px;
                text-align: center;
            }
            .header h1 {
                font-size: 2.5em;
                margin-bottom: 10px;
            }
            .header p {
                font-size: 1.2em;
                opacity: 0.9;
            }
            .content {
                padding: 40px;
            }
            .endpoint-section {
                margin-bottom: 40px;
            }
            .endpoint-section h2 {
                color: #667eea;
                font-size: 1.8em;
                margin-bottom: 20px;
                padding-bottom: 10px;
                border-bottom: 3px solid #667eea;
            }
            .endpoint {
                background: #f8f9fa;
                border-left: 5px solid #667eea;
                padding: 20px;
                margin-bottom: 15px;
                border-radius: 8px;
                transition: transform 0.2s, box-shadow 0.2s;
            }
            .endpoint:hover {
                transform: translateX(5px);
                box-shadow: 0 5px 15px rgba(102, 126, 234, 0.3);
            }
            .endpoint-header {
                display: flex;
                align-items: center;
                margin-bottom: 10px;
            }
            .method {
                display: inline-block;
                padding: 5px 15px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 0.9em;
                margin-right: 15px;
            }
            .method.get {
                background: #28a745;
                color: white;
            }
            .method.post {
                background: #007bff;
                color: white;
            }
            .endpoint-path {
                font-family: 'Courier New', monospace;
                font-size: 1.1em;
                font-weight: bold;
                color: #333;
            }
            .endpoint-desc {
                color: #666;
                margin-top: 10px;
                line-height: 1.6;
            }
            .badge {
                display: inline-block;
                padding: 3px 10px;
                border-radius: 12px;
                font-size: 0.8em;
                margin-left: 10px;
            }
            .badge.recommended {
                background: #ffc107;
                color: #000;
            }
            .badge.legacy {
                background: #6c757d;
                color: white;
            }
            .badge.streaming {
                background: #17a2b8;
                color: white;
            }
            .footer {
                background: #f8f9fa;
                padding: 20px;
                text-align: center;
                color: #666;
            }
            .quick-links {
                display: flex;
                gap: 15px;
                justify-content: center;
                margin-top: 30px;
            }
            .quick-link {
                padding: 12px 30px;
                background: white;
                border: 2px solid #667eea;
                color: #667eea;
                text-decoration: none;
                border-radius: 25px;
                font-weight: bold;
                transition: all 0.3s;
            }
            .quick-link:hover {
                background: #667eea;
                color: white;
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(102, 126, 234, 0.3);
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🌍 Travel Advisor API</h1>
                <p>SaoLa 3.1 Powered - Plan-RAG Architecture</p>
                <div class="quick-links">
                    <a href="/docs" class="quick-link">📚 Swagger UI</a>
                    <a href="/redoc" class="quick-link">📖 ReDoc</a>
                    <a href="/" class="quick-link">🏠 API Root</a>
                </div>
            </div>

            <div class="content">
                <!-- Chat Endpoints -->
                <div class="endpoint-section">
                    <h2>💬 Chat Endpoints</h2>

                    <div class="endpoint">
                        <div class="endpoint-header">
                            <span class="method post">POST</span>
                            <span class="endpoint-path">/chat/stream</span>
                            <span class="badge recommended">⭐ RECOMMENDED</span>
                            <span class="badge streaming">🚀 STREAMING</span>
                        </div>
                        <div class="endpoint-desc">
                            <strong>Streaming chat với Travel Advisor AI</strong><br>
                            • Real-time response với Server-Sent Events (SSE)<br>
                            • Low latency, user thấy reply ngay lập tức<br>
                            • Hỗ trợ tất cả intents: plan_trip, find_spot, find_hotel, book_hotel, calculate_cost, show_itinerary, get_location_tips<br>
                            • State management tự động
                        </div>
                    </div>

                    <div class="endpoint">
                        <div class="endpoint-header">
                            <span class="method post">POST</span>
                            <span class="endpoint-path">/chat</span>
                            <span class="badge legacy">LEGACY</span>
                        </div>
                        <div class="endpoint-desc">
                            <strong>Non-streaming chat endpoint</strong><br>
                            • Response một lần (không streaming)<br>
                            • Tương thích với frontend cũ<br>
                            • Có thể chậm với responses dài
                        </div>
                    </div>
                </div>

                <!-- Province Endpoints -->
                <div class="endpoint-section">
                    <h2>🗺️ Province Endpoints</h2>

                    <div class="endpoint">
                        <div class="endpoint-header">
                            <span class="method get">GET</span>
                            <span class="endpoint-path">/api/provinces/featured</span>
                        </div>
                        <div class="endpoint-desc">
                            <strong>Lấy danh sách tỉnh/thành nổi bật</strong><br>
                            • Query params: ?limit=3 (default)<br>
                            • Trả về provinces có nhiều địa điểm du lịch nhất
                        </div>
                    </div>

                    <div class="endpoint">
                        <div class="endpoint-header">
                            <span class="method get">GET</span>
                            <span class="endpoint-path">/api/provinces/{province_id}</span>
                        </div>
                        <div class="endpoint-desc">
                            <strong>Lấy thông tin chi tiết một tỉnh/thành</strong><br>
                            • Path param: province_id (vd: "da-nang", "ha-noi")<br>
                            • Trả về full info + top spots
                        </div>
                    </div>
                </div>

                <!-- Spot Endpoints -->
                <div class="endpoint-section">
                    <h2>📍 Tourist Spot Endpoints</h2>

                    <div class="endpoint">
                        <div class="endpoint-header">
                            <span class="method get">GET</span>
                            <span class="endpoint-path">/api/spots/search</span>
                        </div>
                        <div class="endpoint-desc">
                            <strong>Tìm kiếm địa điểm du lịch</strong><br>
                            • Query params: ?query=bãi_biển&province=da-nang&limit=10<br>
                            • Semantic search với vietnamese-sbert embeddings<br>
                            • Kết quả được rank theo relevance score
                        </div>
                    </div>

                    <div class="endpoint">
                        <div class="endpoint-header">
                            <span class="method get">GET</span>
                            <span class="endpoint-path">/api/spots/{spot_id}</span>
                        </div>
                        <div class="endpoint-desc">
                            <strong>Lấy thông tin chi tiết một địa điểm</strong><br>
                            • Path param: spot_id (MongoDB ObjectId)<br>
                            • Trả về full details: địa chỉ, giá vé, giờ mở cửa, mô tả, tips
                        </div>
                    </div>
                </div>

                <!-- Hotel Endpoints -->
                <div class="endpoint-section">
                    <h2>🏨 Hotel Endpoints</h2>

                    <div class="endpoint">
                        <div class="endpoint-header">
                            <span class="method get">GET</span>
                            <span class="endpoint-path">/api/hotels/search</span>
                        </div>
                        <div class="endpoint-desc">
                            <strong>Tìm kiếm khách sạn</strong><br>
                            • Query params: ?province=da-nang&min_price=500000&max_price=2000000&limit=10<br>
                            • Filter theo tỉnh/thành, khoảng giá, rating<br>
                            • Fuzzy matching cho tên khách sạn
                        </div>
                    </div>

                    <div class="endpoint">
                        <div class="endpoint-header">
                            <span class="method get">GET</span>
                            <span class="endpoint-path">/api/hotels/{hotel_id}</span>
                        </div>
                        <div class="endpoint-desc">
                            <strong>Lấy thông tin chi tiết một khách sạn</strong><br>
                            • Path param: hotel_id (MongoDB ObjectId)<br>
                            • Trả về: tên, địa chỉ, giá, rating, amenities, rooms
                        </div>
                    </div>
                </div>

                <!-- System Endpoints -->
                <div class="endpoint-section">
                    <h2>⚙️ System Endpoints</h2>

                    <div class="endpoint">
                        <div class="endpoint-header">
                            <span class="method get">GET</span>
                            <span class="endpoint-path">/</span>
                        </div>
                        <div class="endpoint-desc">
                            <strong>Root endpoint - Service info</strong><br>
                            • Trả về service name, version, status
                        </div>
                    </div>

                    <div class="endpoint">
                        <div class="endpoint-header">
                            <span class="method get">GET</span>
                            <span class="endpoint-path">/docs</span>
                        </div>
                        <div class="endpoint-desc">
                            <strong>Swagger UI - Interactive API documentation</strong><br>
                            • Test endpoints trực tiếp từ browser<br>
                            • Xem request/response schemas
                        </div>
                    </div>

                    <div class="endpoint">
                        <div class="endpoint-header">
                            <span class="method get">GET</span>
                            <span class="endpoint-path">/redoc</span>
                        </div>
                        <div class="endpoint-desc">
                            <strong>ReDoc - Alternative API documentation</strong><br>
                            • Clean, đẹp hơn Swagger UI<br>
                            • Tốt cho reading
                        </div>
                    </div>

                    <div class="endpoint">
                        <div class="endpoint-header">
                            <span class="method get">GET</span>
                            <span class="endpoint-path">/openapi.json</span>
                        </div>
                        <div class="endpoint-desc">
                            <strong>OpenAPI specification (JSON)</strong><br>
                            • Machine-readable API schema<br>
                            • Dùng để generate client code
                        </div>
                    </div>
                </div>
            </div>

            <div class="footer">
                <p><strong>Travel Advisor Service v1.0.0</strong></p>
                <p>Built with ❤️ using FastAPI, MongoDB, SaoLa 3.1 LLM & Plan-RAG Architecture</p>
                <p style="margin-top: 10px; font-size: 0.9em;">
                    🔗 <a href="/docs" style="color: #667eea;">Swagger UI</a> |
                    <a href="/redoc" style="color: #667eea;">ReDoc</a> |
                    <a href="/openapi.json" style="color: #667eea;">OpenAPI JSON</a>
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


# === LEGACY ENDPOINT FOR FRONTEND COMPATIBILITY ===
# Frontend calls POST /chat, we redirect to Plan-RAG

from pydantic import BaseModel
from typing import List, Dict, Any, Optional


class LegacyChatRequest(BaseModel):
    messages: List[Dict[str, str]]
    context: Optional[Dict[str, Any]] = None
    temperature: Optional[float] = 0.7


# Lazy-load controller
_controller = None


def get_controller():
    global _controller
    if _controller is None:
        from app.services.master_controller import create_master_controller

        _controller = create_master_controller()
    return _controller


@app.post("/chat", summary="Chat Endpoint (Non-Streaming)", tags=["Chat"])
async def legacy_chat(request: LegacyChatRequest):
    """
    Legacy /chat endpoint for frontend compatibility
    Redirects to Plan-RAG controller
    """
    try:
        logger.info(f"📩 Legacy /chat request: {len(request.messages)} messages")

        controller = get_controller()

        result = controller.process_request(
            messages=request.messages, context=request.context
        )

        return result

    except Exception as e:
        logger.error(f"❌ Legacy chat error: {e}", exc_info=True)
        return {
            "reply": f"Xin lỗi, có lỗi xảy ra: {str(e)}",
            "ui_type": "none",
            "context": request.context,
        }


@app.post(
    "/chat/stream",
    summary="Chat Endpoint - Streaming (RECOMMENDED)",
    response_description="Server-Sent Events stream with AI responses",
    tags=["Chat"],
)
async def chat_stream(request: LegacyChatRequest):
    """
    Streaming chat endpoint with real-time responses. Supports all intents: plan_trip, find_spot,
    find_hotel, book_hotel, calculate_cost, show_itinerary, get_location_tips.
    Uses Server-Sent Events (SSE) format. Frontend should listen for 'data:' events until '[DONE]'.
    """
    from fastapi.responses import StreamingResponse
    import asyncio

    async def generate_stream():
        try:
            logger.info(
                f"📡 Legacy streaming request: {len(request.messages)} messages"
            )

            controller = get_controller()

            # Process with streaming
            async for chunk in controller.process_stream(
                messages=request.messages, context=request.context
            ):
                # Clean data before JSON serialization to remove numpy arrays etc.
                cleaned_chunk = clean_for_json(chunk)
                data = json.dumps(cleaned_chunk, ensure_ascii=False, cls=NumpyEncoder)
                yield f"data: {data}\n\n"

                # Small delay for frontend processing
                await asyncio.sleep(0.1)

            # Send completion signal
            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error(f"❌ Legacy streaming error: {e}", exc_info=True)
            error_data = json.dumps(
                {
                    "error": str(e),
                    "reply": "⚠️ Xin lỗi, có lỗi xảy ra khi xử lý yêu cầu của bạn.",
                    "ui_type": "none",
                },
                ensure_ascii=False,
            )
            yield f"data: {error_data}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# === LEGACY API ENDPOINTS FOR FRONTEND ===


@app.get("/api/provinces/featured")
async def get_featured_provinces(limit: int = 3):
    """Get featured provinces for homepage"""
    try:
        collection = mongodb_manager.get_collection("provinces_info")

        # Get provinces with most spots
        provinces = list(collection.find({}).limit(limit))

        result = []
        for p in provinces:
            result.append(
                {
                    "id": p.get("province_id", ""),
                    "name": p.get("name", ""),
                    "slug": p.get("province_id", ""),
                    "image": p.get("image", "/images/default-province.jpg"),
                    "description": (
                        p.get("description", "")[:150] + "..."
                        if p.get("description")
                        else ""
                    ),
                    "spotCount": p.get("spot_count", 0),
                }
            )

        # Return object with 'provinces' key for frontend compatibility
        return {"provinces": result}

    except Exception as e:
        logger.error(f"❌ Get provinces error: {e}")
        return {"provinces": []}


@app.get("/api/spots/featured")
async def get_featured_spots(limit: int = 6):
    """Get featured spots for homepage"""
    try:
        collection = mongodb_manager.get_collection("spots_detailed")

        # Get top rated spots
        spots = list(collection.find({}).sort("rating", -1).limit(limit))

        result = []
        for s in spots:
            result.append(
                {
                    "id": s.get("id", ""),
                    "name": s.get("name", ""),
                    "slug": s.get("id", ""),
                    "province_id": s.get("province_id", ""),
                    "image": s.get("image", "/images/default-spot.jpg"),
                    "description": (
                        s.get("description_short", "")[:100] + "..."
                        if s.get("description_short")
                        else ""
                    ),
                    "rating": s.get("rating", 0),
                    "reviews_count": s.get("reviews_count", 0),
                }
            )

        # Return object with 'spots' key for frontend compatibility
        return {"spots": result}

    except Exception as e:
        logger.error(f"❌ Get spots error: {e}")
        return {"spots": []}


@app.get("/api/hotels/featured")
async def get_featured_hotels(limit: int = 6):
    """Get featured hotels for homepage"""
    try:
        collection = mongodb_manager.get_collection("hotels")

        # Get top rated hotels
        hotels = list(collection.find({}).sort("rating", -1).limit(limit))

        result = []
        for h in hotels:
            result.append(
                {
                    "id": str(h.get("_id", "")),
                    "name": h.get("name", ""),
                    "province_id": h.get("province_id", ""),
                    "image": h.get("image_url")
                    or h.get("image", "/images/default-hotel.jpg"),
                    "price": h.get("price", 0),
                    "rating": h.get("rating", 0),
                    "address": h.get("address", ""),
                }
            )

        # Return object with 'hotels' key for frontend compatibility
        return {"hotels": result}

    except Exception as e:
        logger.error(f"❌ Get hotels error: {e}")
        return {"hotels": []}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8001, reload=True)
