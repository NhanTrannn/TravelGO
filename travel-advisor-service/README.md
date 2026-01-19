# Travel Advisor Microservice

FastAPI-based microservice for Travel Planning with Plan-RAG architecture.

## Features

- **Plan-RAG Architecture**: Query decomposition with Planner → Experts → Critic
- **Dynamic Budget Parsing**: Natural language → Structured filters
- **Parent Document Retrieval**: Search small chunks, return full context
- **Self-Query Retrieval**: Automatic metadata filtering
- **Expert System**: Hotel, Spot, Itinerary specialists

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Setup Environment

```bash
cp .env.example .env
# Edit .env với API keys và database URIs
```

### 3. Run Service

```bash
# Development
uvicorn app.main:app --reload --port 8000

# Production (with Docker)
docker-compose up -d
```

### 4. Test API

```bash
# Health check
curl http://localhost:8000/health

# Chat endpoint
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Lịch trình Đà Lạt 3 ngày dưới 5 triệu",
    "trip_state": {},
    "user_preferences": {}
  }'
```

## API Documentation

Access interactive docs at: http://localhost:8000/docs

## Architecture

```
User Query
    ↓
Planner Agent (Query Decomposition)
    ↓
Expert Executors (Parallel)
    ├── Hotel Expert
    ├── Spot Expert
    └── Itinerary Expert
    ↓
Critic Agent (Validation)
    ↓
Response Generation
```

## Development

```bash
# Run tests
pytest tests/

# Format code
black app/

# Type check
mypy app/
```

## Project Structure

```
travel-advisor-service/
├── app/
│   ├── api/v1/          # API endpoints
│   ├── core/            # Config, logging
│   ├── services/        # Business logic
│   │   ├── experts/     # Expert executors
│   │   ├── planner_agent.py
│   │   └── critic_agent.py
│   ├── db/              # Database connections
│   ├── schemas/         # Pydantic models
│   └── main.py          # FastAPI app
├── tests/               # Unit tests
├── docker-compose.yml
└── Dockerfile
```

## License

MIT
