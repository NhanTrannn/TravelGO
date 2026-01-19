# TravelGO - AI Travel Assistant 🌏

Hệ thống tư vấn du lịch thông minh sử dụng kiến trúc Plan-RAG, tích hợp LLM và semantic search.

**🔗 Live Demo:** [https://travel-go-dbmk.vercel.app](https://travel-go-dbmk.vercel.app)

---

## 📋 Tổng Quan

TravelGO là chatbot du lịch Việt Nam với các tính năng:

- 🗺️ **Lên lịch trình tương tác** - Chọn địa điểm từng ngày
- 🏨 **Tìm khách sạn** - Lọc theo ngân sách, rating
- 📍 **Gợi ý địa điểm** - Semantic search với Vietnamese-SBERT
- 🌤️ **Thông tin thời tiết** - Best time to visit, avoid months
- 💰 **Ước tính chi phí** - Tính toán tự động

---

## 🏗️ Kiến Trúc Hệ Thống

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND                              │
│              Next.js 16+ (Vercel)                           │
│         travel-go-dbmk.vercel.app                           │
└─────────────────────┬───────────────────────────────────────┘
                      │ HTTPS
┌─────────────────────▼───────────────────────────────────────┐
│                        BACKEND                               │
│              FastAPI (Viettel VPS)                          │
│              171.244.139.129:8000                           │
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Intent    │  │   Planner   │  │  Response   │         │
│  │  Extractor  │──│    Agent    │──│  Aggregator │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│         │                │                │                  │
│  ┌──────▼────────────────▼────────────────▼──────┐         │
│  │              Expert Executors                  │         │
│  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌─────┐ │         │
│  │  │Spots │ │Hotels│ │ Food │ │Itin. │ │Cost │ │         │
│  │  └──────┘ └──────┘ └──────┘ └──────┘ └─────┘ │         │
│  └───────────────────────────────────────────────┘         │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                    EXTERNAL SERVICES                         │
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │  MongoDB    │  │  FPT SaoLa  │  │ Vietnamese  │         │
│  │   Atlas     │  │   LLM API   │  │   SBERT     │         │
│  │  (spots_db) │  │  (SaoLa 3.1)│  │ (Embedding) │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

### Plan-RAG Pipeline

```
User Query → Intent Extraction → Multi-Intent Planner → Expert Execution → Response Aggregation
     │              │                    │                    │                   │
     │         (2-stage:           (Task graph         (Parallel/         (Progressive
     │       rule + LLM)           generation)         Sequential)         disclosure)
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose (optional)
- MongoDB Atlas account
- FPT AI API key

### 1. Clone & Install

```bash
git clone https://github.com/NhanTrannn/TravelGO.git
cd TravelGO/travel-advisor-service

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Setup

```bash
cp .env.example .env
```

Cấu hình `.env`:

```env
# MongoDB Atlas
MONGO_URI=mongodb+srv://<user>:<pass>@cluster.mongodb.net
MONGO_DB_NAME=spots_db

# FPT AI LLM
FPT_API_KEY=your_fpt_api_key
FPT_BASE_URL=https://mkp-api.fptcloud.com
FPT_MODEL_NAME=meta-llama/Llama-3.1-70B-Instruct

# Embedding
EMBEDDING_MODEL=keepitreal/vietnamese-sbert
EMBEDDING_DEVICE=cpu

# Service
LOG_LEVEL=INFO
DEBUG=false
```

### 3. Run Locally

```bash
# Development mode
uvicorn app.main:app --reload --port 8000

# Test API
curl http://localhost:8000/health
```

### 4. Test Chatbot

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Lịch trình Đà Nẵng 3 ngày budget 5 triệu",
    "trip_state": {},
    "user_preferences": {}
  }'
```

---

## 🐳 Docker Deployment

### Build & Run with Docker

```bash
# Build image
docker build -t travelgo-backend:latest .

# Run container
docker run -d \
  --name travelgo-api \
  -p 8000:8000 \
  --env-file .env \
  --restart unless-stopped \
  travelgo-backend:latest
```

### Docker Compose (Full Stack)

```bash
docker-compose up -d
```

---

## ☁️ Production Deployment

### Option 1: Viettel VPS (Current Setup)

**Server:** 171.244.139.129 | **RAM:** 4GB | **vCPU:** 2

#### Step 1: SSH & Clone

```bash
ssh root@171.244.139.129
cd /opt
git clone https://github.com/NhanTrannn/TravelGO.git
cd TravelGO/travel-advisor-service
```

#### Step 2: Create .env

```bash
cat > .env << 'EOF'
MONGO_URI=mongodb+srv://<user>:<pass>@cluster.mongodb.net
MONGO_DB_NAME=spots_db
FPT_API_KEY=your_key_here
FPT_BASE_URL=https://mkp-api.fptcloud.com
FPT_MODEL_NAME=meta-llama/Llama-3.1-70B-Instruct
EMBEDDING_MODEL=keepitreal/vietnamese-sbert
EMBEDDING_DEVICE=cpu
LOG_LEVEL=INFO
DEBUG=false
EOF
```

#### Step 3: Build & Deploy

```bash
# Build Docker image
docker build -t travelgo-backend:latest .

# Stop old container (if exists)
docker stop travelgo-api 2>/dev/null || true
docker rm travelgo-api 2>/dev/null || true

# Run new container
docker run -d \
  --name travelgo-api \
  -p 8000:8000 \
  --env-file .env \
  --restart unless-stopped \
  travelgo-backend:latest

# Verify
docker logs -f travelgo-api --tail 50
```

#### Step 4: Verify Deployment

```bash
# Health check
curl http://171.244.139.129:8000/health

# Test chat API
curl -X POST http://171.244.139.129:8000/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Xin chào"}]}'
```

### Option 2: Vercel (Frontend)

Frontend được deploy tự động khi push lên `main` branch:

```bash
cd frontend
vercel --prod
```

**Environment Variables trên Vercel:**

- `NEXT_PUBLIC_API_URL=http://171.244.139.129:8000`

---

## 📊 Monitoring & Operations

### Check Container Status

```bash
# Container health
docker ps
docker stats travelgo-api

# Logs
docker logs -f travelgo-api --tail 100

# Resource usage
docker stats --no-stream
```

### Update Deployment

```bash
cd /opt/TravelGO
git pull origin main

# Rebuild and restart
docker build -t travelgo-backend:latest ./travel-advisor-service
docker stop travelgo-api && docker rm travelgo-api
docker run -d --name travelgo-api -p 8000:8000 --env-file ./travel-advisor-service/.env --restart unless-stopped travelgo-backend:latest
```

### Rollback

```bash
# List images
docker images | grep travelgo

# Rollback to previous version
docker stop travelgo-api
docker run -d --name travelgo-api -p 8000:8000 --env-file .env travelgo-backend:<previous-tag>
```

---

## 📈 Capacity & Performance

### Current Infrastructure Limits

| Component         | Limit                | Notes                 |
| ----------------- | -------------------- | --------------------- |
| **VPS RAM**       | 4 GB                 | Container uses ~1.2GB |
| **MongoDB Atlas** | 500 connections (M0) | Free tier             |
| **FPT LLM API**   | Rate limited         | ~10-20 req/s          |
| **Vercel**        | 100GB bandwidth      | Free tier             |

### Estimated Concurrent Users

| Scenario               | Users   | Bottleneck |
| ---------------------- | ------- | ---------- |
| Burst (chat liên tục)  | 20-30   | LLM API    |
| Normal (vài phút/chat) | 50-100  | MongoDB    |
| With caching           | 100-150 | VPS RAM    |

### Performance Tips

1. **LLM Caching**: Cache common intent patterns
2. **Connection Pooling**: MongoDB pool size = 10
3. **Embedding**: Pre-load model on startup (~60s)

---

## 🔌 API Reference

### Endpoints

| Method | Path                        | Description            |
| ------ | --------------------------- | ---------------------- |
| GET    | `/health`                   | Health check           |
| POST   | `/api/v1/chat`              | Sync chat              |
| POST   | `/api/v1/chat/stream`       | Streaming chat (SSE)   |
| GET    | `/api/best-time/{location}` | Weather/best time data |

### Example: Streaming Chat

```javascript
const response = await fetch("http://171.244.139.129:8000/api/v1/chat/stream", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    messages: [{ role: "user", content: "Lịch trình Đà Nẵng 3 ngày" }],
    context: {},
  }),
});

const reader = response.body.getReader();
while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  const chunk = JSON.parse(new TextDecoder().decode(value));
  console.log(chunk);
}
```

---

## 📁 Project Structure

```
travel-advisor-service/
├── app/
│   ├── api/v1/              # API endpoints
│   ├── core/                # Config, logging
│   ├── db/                  # MongoDB connection
│   ├── services/
│   │   ├── experts/         # SpotExpert, HotelExpert, etc.
│   │   ├── intent_extractor.py
│   │   ├── planner_agent.py
│   │   ├── master_controller.py
│   │   └── embedding_service.py
│   └── main.py
├── data/
│   ├── best_time_to_visit.csv
│   └── geographical_information.csv
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## 🤝 Contributing

1. Fork the repo
2. Create feature branch: `git checkout -b feature/amazing`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push: `git push origin feature/amazing`
5. Open Pull Request

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

## 👥 Authors

- **Nhan Tran** - [GitHub](https://github.com/NhanTrannn)

---

## 🙏 Acknowledgments

- FPT AI - SaoLa LLM API
- MongoDB Atlas - Database hosting
- Vercel - Frontend hosting
- keepitreal/vietnamese-sbert - Embedding model
