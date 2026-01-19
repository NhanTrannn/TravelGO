# TravelGO - Hướng Dẫn Triển Khai (Deployment Guide)

## 📋 Tổng Quan Kiến Trúc

```
┌─────────────────────────────────────────────────────────────────┐
│                        PRODUCTION ARCHITECTURE                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐         ┌──────────────────────────────────┐  │
│  │   Frontend   │         │         Backend (VPS)            │  │
│  │   (Vercel)   │ ──────► │   ┌─────────────────────────┐    │  │
│  │              │   API   │   │  FastAPI + Uvicorn      │    │  │
│  │  Next.js 16  │         │   │  (Docker Container)     │    │  │
│  │  React 19    │         │   │  Port 8000              │    │  │
│  └──────────────┘         │   └─────────────────────────┘    │  │
│        │                  │              │                    │  │
│        │                  │              ▼                    │  │
│        │                  │   ┌─────────────────────────┐    │  │
│        │                  │   │  MongoDB Atlas          │    │  │
│        │                  │   │  (Cloud Database)       │    │  │
│        │                  │   └─────────────────────────┘    │  │
│        │                  │              │                    │  │
│        │                  │              ▼                    │  │
│        │                  │   ┌─────────────────────────┐    │  │
│        │                  │   │  FPT AI SaoLa 3.1       │    │  │
│        │                  │   │  (LLM API)              │    │  │
│        │                  │   └─────────────────────────┘    │  │
│        │                  └──────────────────────────────────┘  │
│        │                                                         │
│        ▼                                                         │
│  ┌──────────────┐                                               │
│  │ MongoDB Atlas│ (NextAuth sessions, user data)                │
│  └──────────────┘                                               │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 1. Frontend Deployment (Vercel)

### 1.1 Chuẩn bị

```bash
cd travel-advisor-service/frontend
```

### 1.2 Environment Variables trên Vercel

Vào **Vercel Dashboard → Project → Settings → Environment Variables**, thêm:

| Variable          | Value                            | Description                     |
| ----------------- | -------------------------------- | ------------------------------- |
| `MONGODB_URI`     | `mongodb+srv://...`              | MongoDB Atlas connection string |
| `NEXTAUTH_SECRET` | `your-secret-key`                | NextAuth.js secret (32+ chars)  |
| `NEXTAUTH_URL`    | `https://your-domain.vercel.app` | Production URL                  |
| `BACKEND_ORIGIN`  | `http://171.244.139.129:8000`    | Backend API URL                 |

### 1.3 Deploy Commands

```bash
# Install Vercel CLI
npm i -g vercel

# Login
vercel login

# Deploy (production)
vercel --prod

# Hoặc connect GitHub repo và auto-deploy
```

### 1.4 Cấu hình Next.js cho Production

```typescript
// next.config.ts
const nextConfig = {
  images: {
    remotePatterns: [{ protocol: "https", hostname: "**" }],
  },
  // Disable strict mode for production if needed
  reactStrictMode: true,
};
```

### 1.5 Fix Common Vercel Errors

**TypeScript Errors:**

```bash
# Check locally before deploy
npm run build
```

**Environment Variables không load:**

- Đảm bảo biến có prefix phù hợp
- Server-side: không cần prefix
- Client-side: cần `NEXT_PUBLIC_` prefix

---

## 🖥️ 2. Backend Deployment (Viettel VPS + Docker)

### 2.1 Chuẩn bị VPS

```bash
# SSH vào VPS
ssh root@171.244.139.129

# Update system
apt update && apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Git
apt install git -y
```

### 2.2 Clone Repository

```bash
cd /opt
git clone https://github.com/NhanTrannn/TravelGO.git
cd TravelGO
```

### 2.3 Cấu hình Environment Variables

```bash
# Tạo file .env
nano /opt/TravelGO/.env
```

Nội dung file `.env`:

```env
# FPT AI Configuration
FPT_API_KEY=sk-xxxxx
FPT_BASE_URL=https://mkp-api.fptcloud.com
FPT_MODEL_NAME=SaoLa3.1-medium
FPT_DEFAULT_TEMPERATURE=0.7
FPT_MAX_TOKENS=12800
ENABLE_PROMPT_TIMING=1

# MongoDB Configuration
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/db_name
SPOTS_MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/spots_db
SPOTS_DB_NAME=spots_db
```

**⚠️ Lưu ý quan trọng:**

- KHÔNG dùng dấu ngoặc kép `"` cho giá trị
- KHÔNG có dòng comment không bắt đầu bằng `#`

### 2.4 Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY ./app ./app

# Copy data files (CSV, JSON for weather/geography)
COPY ./data ./data

# Create data directory for ChromaDB
RUN mkdir -p /data/chroma

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2.5 Build và Run Docker

```bash
cd /opt/TravelGO/travel-advisor-service

# Build image
docker build -t traveladvisor .

# Run container với env file
docker run -d -p 8000:8000 --env-file /opt/TravelGO/.env traveladvisor

# Kiểm tra container
docker ps

# Xem logs
docker logs -f <container_id>
```

### 2.6 Useful Docker Commands

```bash
# Stop all containers
docker stop $(docker ps -q)

# Remove container
docker rm <container_id>

# Rebuild without cache
docker build --no-cache -t traveladvisor .

# View container logs in realtime
docker logs -f <container_id>

# Execute command inside container
docker exec -it <container_id> bash

# Check container health
curl http://localhost:8000/health
```

### 2.7 Update Code trên VPS

```bash
cd /opt/TravelGO

# Pull latest code
git fetch origin
git reset --hard origin/main

# Rebuild và restart
cd travel-advisor-service
docker stop $(docker ps -q)
docker build -t traveladvisor .
docker run -d -p 8000:8000 --env-file /opt/TravelGO/.env traveladvisor
```

---

## 🗄️ 3. Database (MongoDB Atlas)

### 3.1 Tạo Cluster

1. Vào [MongoDB Atlas](https://cloud.mongodb.com)
2. Create Cluster → Free Tier (M0)
3. Chọn region gần nhất (Singapore/Hong Kong)

### 3.2 Cấu hình Network Access

1. **Network Access → Add IP Address**
2. Thêm `0.0.0.0/0` cho development (hoặc IP cụ thể cho production)

### 3.3 Tạo Database User

1. **Database Access → Add New Database User**
2. Authentication: Password
3. Lưu username và password

### 3.4 Connection String

```
mongodb+srv://<username>:<password>@cluster0.xxxxx.mongodb.net/<dbname>?retryWrites=true&w=majority
```

---

## 🔧 4. Troubleshooting

### 4.1 Frontend Issues

**Build fails với TypeScript errors:**

```bash
npm run build
# Fix errors locally before pushing
```

**Environment variables không load:**

- Kiểm tra tên biến trên Vercel Dashboard
- Redeploy sau khi thêm biến mới

### 4.2 Backend Issues

**Container crash ngay sau khi start:**

```bash
docker logs <container_id>
# Thường do thiếu env variables hoặc syntax error trong .env
```

**Connection refused:**

```bash
# Kiểm tra container đang chạy
docker ps

# Kiểm tra port binding
netstat -tlnp | grep 8000
```

**MongoDB connection failed:**

- Kiểm tra Network Access trên Atlas
- Kiểm tra connection string trong .env

### 4.3 Common Fixes

**File .env có format sai:**

```bash
# Xóa dấu ngoặc kép
sed -i 's/"//g' /opt/TravelGO/.env

# Thêm # vào comment
sed -i 's/^====/# ====/' /opt/TravelGO/.env
```

**Data files không có trong Docker:**

```dockerfile
# Đảm bảo Dockerfile có dòng này
COPY ./data ./data
```

---

## 📊 5. Monitoring

### 5.1 Health Check

```bash
# Backend health
curl http://171.244.139.129:8000/health

# Expected response
{
  "status": "healthy",
  "service": "travel-advisor-service",
  "version": "1.0.0",
  "mongodb": true,
  "chromadb": true
}
```

### 5.2 Logs

```bash
# Realtime logs
docker logs -f <container_id>

# Last 100 lines
docker logs --tail 100 <container_id>
```

---

## 🔄 6. CI/CD Workflow

### 6.1 Frontend (Automatic via Vercel)

1. Push code to GitHub `main` branch
2. Vercel auto-detects và deploy
3. Preview URL cho mỗi PR

### 6.2 Backend (Manual)

```bash
# On VPS
cd /opt/TravelGO
git fetch origin
git reset --hard origin/main
cd travel-advisor-service
docker stop $(docker ps -q)
docker build -t traveladvisor .
docker run -d -p 8000:8000 --env-file /opt/TravelGO/.env traveladvisor
```

---

## 📝 Checklist Deployment

### Frontend (Vercel)

- [ ] Environment variables configured
- [ ] `npm run build` passes locally
- [ ] Connected to GitHub repo
- [ ] Custom domain (optional)

### Backend (VPS)

- [ ] Docker installed
- [ ] Repository cloned
- [ ] `.env` file configured (no quotes!)
- [ ] Data files included in Docker image
- [ ] Container running and healthy
- [ ] Port 8000 accessible

### Database

- [ ] MongoDB Atlas cluster created
- [ ] Network access configured
- [ ] Database user created
- [ ] Connection string tested

---

## 📞 Support

- **Frontend URL:** https://travel-go-dbmk.vercel.app
- **Backend API:** http://171.244.139.129:8000
- **API Docs:** http://171.244.139.129:8000/docs
