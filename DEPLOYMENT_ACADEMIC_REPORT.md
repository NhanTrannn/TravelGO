# Báo Cáo Học Thuật: Kỹ Thuật Triển Khai Hệ Thống TravelGO

## Academic Report: Deployment Techniques for TravelGO AI Travel Advisory System

---

**Tác giả:** Nguyễn Chơn Nhân
**Ngày:** 19/01/2026
**Phiên bản:** 1.0

---

## Tóm Tắt (Abstract)

Báo cáo này trình bày chi tiết các kỹ thuật triển khai (deployment) được áp dụng cho hệ thống TravelGO - một ứng dụng tư vấn du lịch thông minh sử dụng AI. Hệ thống được xây dựng theo kiến trúc microservices với frontend Next.js triển khai trên Vercel, backend FastAPI chạy trong Docker container trên Viettel Cloud VPS, và cơ sở dữ liệu MongoDB Atlas. Báo cáo phân tích các quyết định kỹ thuật, thách thức gặp phải và giải pháp tương ứng.

**Từ khóa:** Cloud Deployment, Docker, Vercel, FastAPI, MongoDB Atlas, CI/CD, Microservices

---

## 1. Giới Thiệu

### 1.1 Bối Cảnh

Trong bối cảnh phát triển phần mềm hiện đại, việc triển khai ứng dụng lên môi trường production đòi hỏi sự kết hợp của nhiều công nghệ và kỹ thuật khác nhau. Hệ thống TravelGO là một case study điển hình cho việc triển khai ứng dụng full-stack với các thành phần:

- **Frontend:** Next.js 16 với React 19
- **Backend:** Python FastAPI với Uvicorn
- **Database:** MongoDB Atlas (DBaaS)
- **AI/LLM:** FPT AI SaoLa 3.1

### 1.2 Mục Tiêu Triển Khai

1. **High Availability:** Đảm bảo hệ thống hoạt động liên tục 24/7
2. **Scalability:** Khả năng mở rộng khi tải tăng
3. **Security:** Bảo mật dữ liệu và API endpoints
4. **Cost Efficiency:** Tối ưu chi phí vận hành
5. **Developer Experience:** Dễ dàng cập nhật và maintain

---

## 2. Kiến Trúc Hệ Thống

### 2.1 Sơ Đồ Kiến Trúc Tổng Quan

```
                    ┌─────────────────────────────────────┐
                    │           INTERNET                   │
                    └─────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
                    ▼                               ▼
        ┌───────────────────┐           ┌───────────────────┐
        │   Vercel Edge     │           │   Viettel Cloud   │
        │   Network (CDN)   │           │   VPS             │
        └───────────────────┘           └───────────────────┘
                    │                               │
                    ▼                               ▼
        ┌───────────────────┐           ┌───────────────────┐
        │   Next.js App     │──────────►│   FastAPI App     │
        │   (SSR + CSR)     │   REST    │   (Docker)        │
        └───────────────────┘   API     └───────────────────┘
                    │                               │
                    │                               │
                    ▼                               ▼
        ┌───────────────────┐           ┌───────────────────┐
        │   MongoDB Atlas   │◄──────────│   MongoDB Atlas   │
        │   (Auth/Users)    │           │   (Spots/Hotels)  │
        └───────────────────┘           └───────────────────┘
                                                │
                                                ▼
                                    ┌───────────────────┐
                                    │   FPT AI Cloud    │
                                    │   (SaoLa 3.1)     │
                                    └───────────────────┘
```

### 2.2 Phân Tích Các Thành Phần

| Thành phần | Công nghệ  | Nền tảng triển khai  | Lý do chọn                               |
| ---------- | ---------- | -------------------- | ---------------------------------------- |
| Frontend   | Next.js 16 | Vercel               | Native support, Edge Network, Auto CI/CD |
| Backend    | FastAPI    | Viettel VPS + Docker | Cost-effective, Full control             |
| Database   | MongoDB    | Atlas (Cloud)        | Managed service, Auto-scaling            |
| LLM        | SaoLa 3.1  | FPT AI Cloud         | Vietnamese language support              |

---

## 3. Kỹ Thuật Triển Khai Frontend

### 3.1 Vercel Platform

**Vercel** là nền tảng được chọn để triển khai frontend vì những ưu điểm sau:

#### 3.1.1 Tích Hợp Native với Next.js

```javascript
// Vercel tự động tối ưu cho Next.js
// - Server-Side Rendering (SSR)
// - Static Site Generation (SSG)
// - Incremental Static Regeneration (ISR)
// - API Routes
```

#### 3.1.2 Edge Network và CDN

Vercel sử dụng Edge Network toàn cầu với các điểm hiện diện (PoPs) tại nhiều quốc gia, giúp:

- Giảm latency cho người dùng
- Cache static assets hiệu quả
- Auto SSL/TLS certificates

#### 3.1.3 Continuous Deployment

```yaml
# Workflow tự động khi push code
1. Developer push to GitHub main branch
2. Vercel webhook triggered
3. Build process starts
- npm install
- npm run build
- Type checking
4. Deployment to production
5. Preview URLs for PRs
```

### 3.2 Environment Variables Management

```typescript
// Phân loại biến môi trường trong Next.js

// Server-side only (không exposed to browser)
MONGODB_URI=mongodb+srv://...
NEXTAUTH_SECRET=...
BACKEND_ORIGIN=http://171.244.139.129:8000

// Client-side (exposed to browser)
NEXT_PUBLIC_API_URL=...
```

### 3.3 Thách Thức và Giải Pháp

| Thách thức                       | Giải pháp                                     |
| -------------------------------- | --------------------------------------------- |
| TypeScript build errors          | Strict type checking locally trước khi deploy |
| Environment variables không load | Sử dụng đúng naming convention                |
| API routes gọi backend           | Sử dụng `BACKEND_ORIGIN` env var              |
| CORS issues                      | Cấu hình CORS trên backend                    |

---

## 4. Kỹ Thuật Triển Khai Backend

### 4.1 Containerization với Docker

#### 4.1.1 Tại Sao Chọn Docker?

Docker được chọn vì các lý do:

1. **Consistency:** "Works on my machine" → "Works everywhere"
2. **Isolation:** Tách biệt dependencies giữa các ứng dụng
3. **Portability:** Dễ dàng di chuyển giữa các môi trường
4. **Scalability:** Dễ dàng scale với orchestration tools

#### 4.1.2 Dockerfile Analysis

```dockerfile
# Base image - Python 3.11 slim để giảm size
FROM python:3.11-slim

WORKDIR /app

# System dependencies cho các Python packages
RUN apt-get update && apt-get install -y \
    build-essential \  # Cho các packages cần compile
    curl \             # Cho health checks
    && rm -rf /var/lib/apt/lists/*  # Cleanup để giảm image size

# Dependencies installation (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code (separate layer for caching)
COPY ./app ./app
COPY ./data ./data  # Data files cho weather/geography

# Health check configuration
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Run với Uvicorn ASGI server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### 4.1.3 Layer Caching Strategy

```
┌─────────────────────────────────────┐
│  Layer 1: Base Image (python:3.11)  │  ← Ít thay đổi
├─────────────────────────────────────┤
│  Layer 2: System Dependencies       │  ← Ít thay đổi
├─────────────────────────────────────┤
│  Layer 3: Python Dependencies       │  ← Thay đổi khi requirements.txt đổi
├─────────────────────────────────────┤
│  Layer 4: Application Code          │  ← Thay đổi thường xuyên
├─────────────────────────────────────┤
│  Layer 5: Data Files                │  ← Thay đổi khi có data mới
└─────────────────────────────────────┘
```

### 4.2 VPS Deployment

#### 4.2.1 Viettel Cloud VPS Specifications

| Specification | Value            |
| ------------- | ---------------- |
| Provider      | Viettel IDC      |
| OS            | Ubuntu 22.04 LTS |
| CPU           | 2 vCPUs          |
| RAM           | 4 GB             |
| Storage       | 40 GB SSD        |
| Network       | 1 Gbps           |
| IP            | 171.244.139.129  |

#### 4.2.2 Docker Run Configuration

```bash
docker run -d \
  -p 8000:8000 \                    # Port mapping
  --env-file /opt/TravelGO/.env \   # Environment variables
  --restart=always \                # Auto-restart on failure
  --name travel-api \               # Container name
  traveladvisor                     # Image name
```

### 4.3 Environment Variables Best Practices

```bash
# ❌ SAI - Có dấu ngoặc kép (Docker không parse đúng)
FPT_API_KEY="sk-xxxxx"
FPT_MAX_TOKENS="12800"

# ✅ ĐÚNG - Không có dấu ngoặc kép
FPT_API_KEY=sk-xxxxx
FPT_MAX_TOKENS=12800

# ❌ SAI - Comment không có #
===== Section Header =====

# ✅ ĐÚNG - Comment có #
# ===== Section Header =====
```

---

## 5. Database Deployment

### 5.1 MongoDB Atlas (DBaaS)

#### 5.1.1 Tại Sao Chọn MongoDB Atlas?

| Tiêu chí          | Lý do                               |
| ----------------- | ----------------------------------- |
| Managed Service   | Không cần quản lý infrastructure    |
| Auto-scaling      | Tự động scale theo workload         |
| Global Clusters   | Multi-region replication            |
| Built-in Security | Encryption at rest, VPC peering     |
| Free Tier         | M0 cluster miễn phí cho development |

#### 5.1.2 Connection String Analysis

```
mongodb+srv://username:password@cluster0.xxxxx.mongodb.net/dbname
           │         │                    │                  │
           │         │                    │                  └─ Database name
           │         │                    └─ Cluster hostname
           │         └─ Password (URL encoded)
           └─ Username
```

#### 5.1.3 Network Security Configuration

```
┌─────────────────────────────────────────────────────────┐
│                    MongoDB Atlas                         │
├─────────────────────────────────────────────────────────┤
│  Network Access Rules:                                   │
│  ┌─────────────────────────────────────────────────┐    │
│  │  IP Whitelist:                                   │    │
│  │  • 171.244.139.129/32 (Viettel VPS)             │    │
│  │  • Vercel IP ranges (for serverless functions)  │    │
│  │  • 0.0.0.0/0 (Development only - NOT SECURE)    │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

---

## 6. Continuous Integration/Continuous Deployment (CI/CD)

### 6.1 Frontend CI/CD (Vercel)

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  Local   │────►│  GitHub  │────►│  Vercel  │────►│Production│
│  Dev     │push │   Repo   │hook │  Build   │     │  Deploy  │
└──────────┘     └──────────┘     └──────────┘     └──────────┘
                      │
                      ▼
               ┌──────────┐
               │ Preview  │ (for PRs)
               │   URL    │
               └──────────┘
```

### 6.2 Backend CI/CD (Manual)

```bash
#!/bin/bash
# deploy.sh - Manual deployment script

cd /opt/TravelGO

# 1. Pull latest code
git fetch origin
git reset --hard origin/main

# 2. Navigate to backend directory
cd travel-advisor-service

# 3. Stop existing container
docker stop $(docker ps -q) 2>/dev/null || true

# 4. Build new image
docker build -t traveladvisor .

# 5. Run new container
docker run -d -p 8000:8000 --env-file /opt/TravelGO/.env traveladvisor

# 6. Health check
sleep 10
curl -f http://localhost:8000/health && echo "Deployment successful!" || echo "Deployment failed!"
```

---

## 7. Các Thách Thức và Giải Pháp

### 7.1 Bảng Tổng Hợp Các Vấn Đề Gặp Phải

| #   | Vấn đề                              | Nguyên nhân                          | Giải pháp                                     |
| --- | ----------------------------------- | ------------------------------------ | --------------------------------------------- |
| 1   | TypeScript build errors trên Vercel | Missing types, strict mode           | Fix type errors locally, add type definitions |
| 2   | Environment variables không load    | Sai naming convention                | Dùng NEXT*PUBLIC* prefix cho client-side      |
| 3   | Backend container crash             | Missing env vars                     | Dùng --env-file flag                          |
| 4   | .env file parse error               | Dấu ngoặc kép và comments sai format | Remove quotes, add # to comments              |
| 5   | FileNotFoundError trong Docker      | Data files không được copy           | Thêm `COPY ./data ./data` vào Dockerfile      |
| 6   | MongoDB connection failed           | IP not whitelisted                   | Add VPS IP to Atlas Network Access            |
| 7   | CORS errors                         | Backend không cho phép origin        | Cấu hình CORS middleware                      |

### 7.2 Case Study: Data Files Missing in Docker

**Vấn đề:**

```
FileNotFoundError: [Errno 2] No such file or directory:
'/app/data/geographical_information.csv'
```

**Phân tích:**

- Dockerfile ban đầu chỉ copy `./app` folder
- Các file CSV data nằm trong `./data` folder
- Docker container không có access đến host filesystem

**Giải pháp:**

```dockerfile
# Trước (thiếu data)
COPY ./app ./app

# Sau (đầy đủ)
COPY ./app ./app
COPY ./data ./data
```

---

## 8. Security Considerations

### 8.1 Secrets Management

```
┌─────────────────────────────────────────────────────────┐
│                 Secrets Management                       │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Frontend (Vercel):                                      │
│  • Encrypted environment variables                       │
│  • Không commit .env.local vào git                       │
│  • Sử dụng Vercel Dashboard để manage                    │
│                                                          │
│  Backend (VPS):                                          │
│  • .env file với permissions 600                         │
│  • Không commit vào git (.gitignore)                     │
│  • Docker --env-file flag                                │
│                                                          │
│  Database:                                               │
│  • MongoDB Atlas built-in encryption                     │
│  • Network Access restrictions                           │
│  • Database user với minimal privileges                  │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### 8.2 Network Security

```
Internet ─────► Vercel CDN (HTTPS) ─────► Next.js App
                                              │
                                              │ (HTTP - internal)
                                              ▼
                                         FastAPI Backend
                                              │
                                              │ (TLS)
                                              ▼
                                         MongoDB Atlas
```

**Lưu ý:** Connection từ Vercel đến Backend hiện tại là HTTP. Trong production thực tế, nên:

1. Sử dụng HTTPS với SSL certificate
2. Hoặc đặt backend sau reverse proxy (nginx) với SSL

---

## 9. Performance Optimization

### 9.1 Frontend Optimization

| Kỹ thuật           | Mô tả                                         |
| ------------------ | --------------------------------------------- |
| Edge Caching       | Vercel CDN cache static assets                |
| Code Splitting     | Next.js automatic code splitting              |
| Image Optimization | next/image với automatic webp conversion      |
| SSR/SSG            | Server-side rendering cho SEO và initial load |

### 9.2 Backend Optimization

| Kỹ thuật           | Mô tả                                |
| ------------------ | ------------------------------------ |
| Async/Await        | FastAPI async endpoints              |
| Connection Pooling | MongoDB connection pool              |
| Response Caching   | Cache frequent queries               |
| Health Checks      | Docker HEALTHCHECK for auto-recovery |

---

## 10. Monitoring và Logging

### 10.1 Health Check Endpoint

```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "travel-advisor-service",
        "version": "1.0.0",
        "mongodb": mongodb_manager.health_check(),
        "chromadb": vector_store.health_check(),
    }
```

### 10.2 Docker Logging

```bash
# Realtime logs
docker logs -f <container_id>

# Last N lines
docker logs --tail 100 <container_id>

# With timestamps
docker logs -t <container_id>
```

---

## 11. Kết Luận

### 11.1 Tổng Kết Kỹ Thuật Đã Sử Dụng

| Lĩnh vực         | Kỹ thuật                                    |
| ---------------- | ------------------------------------------- |
| Frontend Hosting | Vercel (Serverless, Edge Network)           |
| Backend Hosting  | Docker on VPS                               |
| Database         | MongoDB Atlas (DBaaS)                       |
| Containerization | Docker                                      |
| CI/CD            | Vercel auto-deploy, Manual scripts          |
| Security         | Environment variables, Network restrictions |

### 11.2 Bài Học Kinh Nghiệm

1. **Environment Variables:** Format của .env file rất quan trọng trong Docker
2. **Data Files:** Phải explicit copy data files trong Dockerfile
3. **Type Safety:** TypeScript strict mode catch errors sớm
4. **Health Checks:** Essential cho monitoring và auto-recovery
5. **Layered Architecture:** Separation of concerns giúp dễ maintain

### 11.3 Hướng Phát Triển

1. **Kubernetes:** Migrate từ single Docker container sang K8s cluster
2. **CI/CD Pipeline:** GitHub Actions cho automated testing và deployment
3. **SSL/TLS:** HTTPS cho backend API
4. **Monitoring:** Prometheus + Grafana cho metrics
5. **Logging:** ELK Stack (Elasticsearch, Logstash, Kibana)

---

## Tài Liệu Tham Khảo

1. Vercel Documentation. https://vercel.com/docs
2. Docker Documentation. https://docs.docker.com
3. FastAPI Documentation. https://fastapi.tiangolo.com
4. MongoDB Atlas Documentation. https://docs.atlas.mongodb.com
5. Next.js Documentation. https://nextjs.org/docs

---

## Phụ Lục

### A. Commands Reference

```bash
# Docker
docker build -t <image> .
docker run -d -p 8000:8000 --env-file .env <image>
docker logs -f <container>
docker stop $(docker ps -q)

# Git
git fetch origin
git reset --hard origin/main

# Vercel
vercel --prod
vercel env pull
```

### B. File Structure

```
TravelGO/
├── travel-advisor-service/
│   ├── frontend/           # Next.js app
│   │   ├── src/
│   │   ├── package.json
│   │   └── next.config.ts
│   └── travel-advisor-service/  # FastAPI backend
│       ├── app/
│       ├── data/
│       ├── Dockerfile
│       └── requirements.txt
├── .env                    # Environment variables
└── README.md
```
