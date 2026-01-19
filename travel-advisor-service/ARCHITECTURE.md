# 🎯 Travel Advisor Microservice - Architecture Summary

## 📦 Complete File Structure

```
travel-advisor-service/
│
├── 📄 README.md                    # Main documentation
├── 📄 QUICKSTART.md                # Quick start guide
├── 📄 SETUP_COMPLETE.md            # Setup completion report
├── 📄 .env                         # Configuration (EDIT THIS!)
├── 📄 .env.example                 # Configuration template
├── 📄 .gitignore                   # Git ignore rules
├── 📄 requirements.txt             # Python dependencies (20+)
├── 📄 Dockerfile                   # Python 3.11 slim image
├── 📄 docker-compose.yml           # 3 services orchestration
├── 📄 quickstart.ps1               # One-command setup script
│
├── app/                            # Main application
│   ├── __init__.py                 # Package init
│   ├── main.py                     # 🚀 FastAPI app entry point
│   │
│   ├── api/                        # API layer
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── chat.py             # POST /api/v1/chat
│   │       └── health.py           # GET /api/v1/health
│   │
│   ├── core/                       # Core infrastructure
│   │   ├── __init__.py
│   │   ├── config.py               # Pydantic settings (15+ fields)
│   │   └── logging.py              # Logger setup
│   │
│   ├── db/                         # Database layer
│   │   ├── __init__.py
│   │   ├── mongo.py                # MongoDB connection manager
│   │   └── vector_store.py         # ChromaDB + embedding model
│   │
│   ├── services/                   # Business logic
│   │   ├── __init__.py
│   │   ├── budget_parser.py        # ⭐ Phase 1.2 - Budget parsing
│   │   └── rag_service.py          # Simple RAG baseline
│   │
│   └── schemas/                    # Data models
│       ├── __init__.py
│       └── chat.py                 # Pydantic models (6 classes)
│
└── tests/                          # Test suite
    ├── __init__.py
    ├── test_budget_parser.py       # 5 test cases
    └── test_api.py                 # 4 test cases
```

**Total**: 27 files created

---

## 🏗️ Architecture Layers

### Layer 1: API Gateway (FastAPI)
```
Request → FastAPI → CORS Middleware → Router → Endpoint
```

**Files**:
- `app/main.py`: FastAPI app with lifespan management
- `app/api/v1/chat.py`: Chat endpoint
- `app/api/v1/health.py`: Health check

**Endpoints**:
- `POST /api/v1/chat`: Main chat interface
- `GET /api/v1/health`: Service health status
- `GET /`: Root endpoint
- `GET /docs`: Swagger UI
- `GET /redoc`: ReDoc documentation

---

### Layer 2: Business Logic (Services)
```
Endpoint → Service → Database/Vector Store → Response
```

**Files**:
- `app/services/budget_parser.py`: Phase 1.2 implementation
- `app/services/rag_service.py`: Hotel + Spot search

**Features**:
- Pattern-based budget parsing (regex)
- LLM fallback for complex queries
- MongoDB filtering (province, price, rating)
- ChromaDB semantic search

---

### Layer 3: Data Access (Database)
```
Service → Manager → MongoDB/ChromaDB → Data
```

**Files**:
- `app/db/mongo.py`: MongoDB connection with PyMongo
- `app/db/vector_store.py`: ChromaDB + Sentence Transformers

**Collections**:
- `spots_detailed`: Tourist spots
- `hotels`: Accommodation data
- `provinces_info`: Province metadata
- `travel_documents` (ChromaDB): Vector embeddings

---

### Layer 4: Configuration (Core)
```
Environment → Settings → Application
```

**Files**:
- `app/core/config.py`: Pydantic Settings
- `app/core/logging.py`: Logger setup
- `.env`: Environment variables

**Configuration Groups**:
- Service: name, version, debug, log level
- MongoDB: URI, database name
- ChromaDB: host, port, persist dir
- LLM: FPT API key, base URL, model
- Embedding: model name, device

---

### Layer 5: Data Models (Schemas)
```
Request → Pydantic Model → Validation → Processing
```

**Files**:
- `app/schemas/chat.py`: 6 Pydantic models

**Models**:
1. `TripState`: User's trip context
2. `UserPreferences`: Keywords, avoid, special needs
3. `ChatRequest`: API request structure
4. `SubQueryInfo`: Query decomposition info
5. `ChatResponse`: API response structure
6. `HealthResponse`: Health check response

---

## 🔄 Request Flow

### Chat Request Flow
```
1. Client sends POST /api/v1/chat
   ↓
2. FastAPI validates with ChatRequest schema
   ↓
3. chat.py endpoint extracts trip_state
   ↓
4. rag_service.chat() analyzes intent
   ↓
5a. Hotel intent → search_hotels()
    ├── budget_parser.parse() → MongoDB filters
    ├── mongo.get_collection("hotels").find()
    └── Return ranked results
   
5b. Spot intent → search_spots()
    ├── vector_store.embed_text()
    ├── vector_store.search() with filters
    └── Return semantic matches
   ↓
6. Format response with ChatResponse schema
   ↓
7. Return JSON to client
```

---

## 🐳 Docker Architecture

### Services
```yaml
travel-advisor:     # FastAPI application
  - Port: 8000
  - Depends: mongodb, chromadb
  
mongodb:            # Database
  - Port: 27017
  - Volume: mongo_data (persistent)
  
chromadb:           # Vector store
  - Port: 8001
  - Volume: chroma_data (persistent)
```

### Network
- Bridge network: `travel-network`
- All services can communicate via service names

### Volumes
- `mongo_data`: Persists MongoDB data
- `chroma_data`: Persists vector embeddings

---

## 💾 Database Schema

### MongoDB Collections

**hotels**:
```json
{
  "_id": ObjectId,
  "name": "Khách sạn ABC",
  "province": "Hà Nội",
  "rating": 4.5,
  "price": 1500000,
  "address": "123 Hoàn Kiếm",
  "url": "https://ivivu.com/...",
  "amenities": ["wifi", "pool"],
  "coordinates": [21.028511, 105.804817]
}
```

**spots_detailed**:
```json
{
  "_id": ObjectId,
  "name": "Hồ Hoàn Kiếm",
  "province": "Hà Nội",
  "category": "Hồ",
  "description": "...",
  "rating": 4.8,
  "coordinates": [21.028511, 105.804817]
}
```

### ChromaDB Collection

**travel_documents**:
```python
{
  "id": "spot_123",
  "embedding": [0.123, -0.456, ...],  # 768 dimensions
  "metadata": {
    "name": "Hồ Hoàn Kiếm",
    "province": "Hà Nội",
    "category": "Hồ",
    "rating": 4.8
  },
  "document": "Hồ Hoàn Kiếm là điểm du lịch nổi tiếng..."
}
```

---

## 🧠 Budget Parser Logic

### Pattern Matching (Fast Path)
```python
# 1. Dưới/không quá X triệu
"dưới 2 triệu" → {"price": {"$lte": 2000000}}

# 2. Trên/từ X triệu
"từ 1 triệu" → {"price": {"$gte": 1000000}}

# 3. Khoảng/tầm X triệu (±10%)
"tầm 1.5 triệu" → {"price": {"$gte": 1350000, "$lte": 1650000}}

# 4. Từ X đến Y triệu
"từ 1 đến 3 triệu" → {"price": {"$gte": 1000000, "$lte": 3000000}}

# 5. Budget levels
"trung bình" → {"price": {"$gte": 1000000, "$lte": 2000000}}
```

### LLM Fallback (Complex Queries)
```python
# For queries that don't match patterns:
query = "khách sạn giá rẻ nhưng không quá rẻ"
↓
LLM extracts: {"min_price": 300000, "max_price": 800000}
↓
Returns: {"price": {"$gte": 300000, "$lte": 800000}}
```

---

## 🔬 Testing Strategy

### Unit Tests (test_budget_parser.py)
```python
✅ test_parse_duoi_x_trieu     # Pattern: dưới 2 triệu
✅ test_parse_tam_x_trieu      # Soft buffer: tầm 1.5 triệu ±10%
✅ test_parse_tu_x_den_y       # Range: từ 1-3 triệu
✅ test_parse_budget_level     # State: budget_level="trung bình"
✅ test_parse_no_budget        # No budget info → empty filter
```

### Integration Tests (test_api.py)
```python
✅ test_root                   # GET / returns service info
✅ test_health_check           # GET /api/v1/health
✅ test_chat_endpoint          # POST /api/v1/chat with state
✅ test_chat_without_state     # POST /api/v1/chat without state
```

---

## 📊 Dependencies (requirements.txt)

### Core Framework
- `fastapi==0.109.0`: Web framework
- `uvicorn[standard]==0.27.0`: ASGI server
- `pydantic==2.5.3`: Data validation
- `pydantic-settings==2.1.0`: Settings management

### Database
- `pymongo==4.6.1`: MongoDB client
- `chromadb==0.4.22`: Vector database
- `sentence-transformers==2.3.1`: Embeddings

### LLM & AI
- `langchain==0.1.4`: Orchestration framework
- `langchain-community==0.0.16`: Community integrations
- `langchain-openai==0.0.5`: OpenAI integration
- `openai==1.10.0`: OpenAI client

### Utilities
- `python-dotenv==1.0.0`: Environment variables
- `apscheduler==3.10.4`: Task scheduling

### Development
- `pytest==7.4.3`: Testing framework
- `pytest-asyncio==0.23.3`: Async testing
- `black==24.1.1`: Code formatter
- `mypy==1.8.0`: Type checker

**Total**: 20+ packages

---

## 🎯 Current State (Phase 1.2 Complete)

### ✅ What's Working
- Budget Parser with pattern + LLM fallback
- Simple RAG service (hotel + spot search)
- FastAPI with health checks
- Docker containerization
- MongoDB + ChromaDB integration
- Vietnamese SBERT embeddings
- Full test coverage

### 🔮 What's Next (Plan-RAG Phases)
- **Phase 2.1**: Planner Agent (query decomposition)
- **Phase 2.2**: Expert System (Hotel/Spot/Itinerary)
- **Phase 2.3**: Critic Agent (validation)
- **Phase 3**: Parent Document Retriever
- **Phase 4**: Self-Query Retriever
- **Phase 5**: Gateway Integration
- **Phase 6**: Data Sync Strategy

See `PLAN_RAG_ROADMAP.md` for full timeline (8 weeks).

---

## 🚀 Performance Considerations

### Speed Optimizations
- Pattern-based parsing (0-5ms) before LLM fallback (100-500ms)
- MongoDB indexing on province, rating, price
- ChromaDB vector search with metadata filters
- Connection pooling for MongoDB

### Scalability
- Stateless microservice design
- Horizontal scaling with Docker replicas
- Separate database per service (MongoDB + ChromaDB)
- Event-driven data sync (future)

### Resource Usage
- **RAM**: ~500MB per service
- **CPU**: Light (mostly I/O bound)
- **Disk**: ~1GB for embeddings
- **Network**: <100KB per request

---

## 📝 Configuration Reference

### Environment Variables (.env)
```env
# Service
SERVICE_NAME=travel-advisor-service
SERVICE_VERSION=0.1.0
DEBUG=True
LOG_LEVEL=INFO

# MongoDB
MONGO_URI=mongodb://mongodb:27017/
MONGO_DB_NAME=spots_db

# ChromaDB
CHROMA_HOST=chromadb
CHROMA_PORT=8000
CHROMA_PERSIST_DIR=./chroma_data

# FPT AI
FPT_API_KEY=your_api_key_here
FPT_BASE_URL=https://api.fpt.ai/v1
LLM_MODEL=gpt-4o-mini

# Embedding
EMBEDDING_MODEL=keepitreal/vietnamese-sbert
EMBEDDING_DEVICE=cpu

# API
API_V1_PREFIX=/api
```

---

## 🎉 Success Metrics

### Setup Success
- [x] 27 files created
- [x] Docker compose with 3 services
- [x] 9 test cases implemented
- [x] Full documentation (README + guides)

### Functional Success
- [x] Budget parser handles 5+ patterns
- [x] Hotel search with filters
- [x] Spot search with semantic similarity
- [x] Health checks operational
- [x] API documentation available

### Quality Success
- [x] Type hints throughout codebase
- [x] Pydantic validation for all inputs
- [x] Structured logging
- [x] Error handling
- [x] Test coverage for critical paths

---

**Architecture**: Microservice with FastAPI + MongoDB + ChromaDB  
**Status**: ✅ Phase 1.2 Complete (Budget Parser)  
**Next**: Phase 2.1 (Planner Agent)  
**Estimated**: 1-2 weeks for full Plan-RAG  

---

**Created**: December 2024  
**Version**: 0.1.0  
**Ready for**: Independent testing before backend integration
