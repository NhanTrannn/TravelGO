# 🌍 Travel Advisor API Documentation

## 📖 Interactive API Documentation

Truy cập các trang docs sau để xem và test API trực tiếp:

### 🚀 Swagger UI (Recommended)
```
http://localhost:8001/docs
```
- ✅ Interactive testing với "Try it out"
- 📝 Xem request/response schemas
- 🎯 Test endpoints trực tiếp từ browser

### 📘 ReDoc (Alternative)
```
http://localhost:8001/redoc
```
- 📚 Documentation dạng document
- 🎨 UI đẹp hơn, dễ đọc
- 🔍 Search functionality

### 📄 OpenAPI JSON
```
http://localhost:8001/openapi.json
```
- Raw OpenAPI 3.0 specification
- Có thể import vào Postman, Insomnia, etc.

---

## 🎯 Quick Start Testing

### 1. Test Chat (Non-Streaming)

**Endpoint:** `POST /chat`

**Request:**
```json
{
  "messages": [
    {
      "role": "user",
      "content": "Tôi muốn đi du lịch Đà Nẵng 3 ngày"
    }
  ],
  "context": {}
}
```

**Cách test:**
1. Mở http://localhost:8001/docs
2. Click vào endpoint `/chat`
3. Click "Try it out"
4. Paste JSON vào Request body
5. Click "Execute"

---

### 2. Test Streaming Chat (Recommended)

**Endpoint:** `POST /chat/stream`

**Request:**
```json
{
  "messages": [
    {
      "role": "user",
      "content": "Lập lịch trình 3 ngày Đà Nẵng với ngân sách 5 triệu"
    }
  ],
  "context": {
    "destination": "Đà Nẵng",
    "duration": 3,
    "budget": 5000000
  }
}
```

**Response:** Server-Sent Events stream
```
data: {"reply": "🌍 Tuyệt vời! Đà Nẵng là điểm đến...", "status": "partial"}

data: {"reply": "Đây là các địa điểm...", "ui_type": "spots", "ui_data": [...]}

data: [DONE]
```

---

## 🔥 Common Use Cases

### Use Case 1: Lập lịch trình tương tác

**Step 1:** Khởi động planning
```json
{
  "messages": [{"role": "user", "content": "Tôi muốn đi Đà Nẵng 3 ngày"}]
}
```

**Step 2:** Chọn địa điểm (reply với context từ step 1)
```json
{
  "messages": [
    {"role": "user", "content": "Tôi muốn đi Đà Nẵng 3 ngày"},
    {"role": "assistant", "content": "Bạn muốn đi với ngân sách..."},
    {"role": "user", "content": "1, 3, 5"}
  ],
  "context": {
    "destination": "Đà Nẵng",
    "duration": 3,
    "itinerary_builder": {
      "state": "CHOOSING_SPOTS",
      "current_day": 1
    }
  }
}
```

**Step 3:** Đặt khách sạn
```json
{
  "messages": [...],
  "context": {
    "destination": "Đà Nẵng",
    "workflow_state": "CHOOSING_HOTEL",
    "last_hotels": [...]
  }
}
```
User message: `"Tôi muốn đặt phòng tại Khách sạn Dragon Sea"`

**Step 4:** Tính chi phí
```json
{
  "messages": [...],
  "context": {
    "selected_hotel": "Dragon Sea Hotel",
    "selected_hotel_price": "500000",
    "last_itinerary": {...}
  }
}
```
User message: `"Ước tính chi phí toàn bộ chuyến đi"`

---

### Use Case 2: Xem lại lịch trình đã lưu

```json
{
  "messages": [
    {"role": "user", "content": "Hiển thị lại lịch trình"}
  ],
  "context": {
    "last_itinerary": {
      "location": "Đà Nẵng",
      "duration": 3,
      "days": [
        {"day": 1, "spots": ["Bà Nà Hills", "Cầu Vàng"]},
        {"day": 2, "spots": ["Hội An"]},
        {"day": 3, "spots": ["Bãi biển Mỹ Khê"]}
      ]
    }
  }
}
```

---

### Use Case 3: Tìm khách sạn theo ngân sách

```json
{
  "messages": [
    {"role": "user", "content": "Tìm khách sạn ở Đà Nẵng giá dưới 1 triệu"}
  ],
  "context": {
    "destination": "Đà Nẵng",
    "budget": 1000000
  }
}
```

---

## 📊 Context Fields Reference

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `destination` | string | Tỉnh/thành phố | "Đà Nẵng" |
| `duration` | int | Số ngày | 3 |
| `budget` | int | Ngân sách (VNĐ) | 5000000 |
| `people_count` | int | Số người đi | 2 |
| `companion_type` | string | Loại nhóm | "couple", "family", "solo" |
| `workflow_state` | string | State hiện tại | "CHOOSING_SPOTS", "CHOOSING_HOTEL" |
| `itinerary_builder` | object | Builder state | {...} |
| `last_itinerary` | object | Lịch trình đã lưu | {...} |
| `selected_hotel` | string | Khách sạn đã chọn | "Dragon Sea Hotel" |
| `selected_hotel_price` | string | Giá khách sạn | "500000" |
| `last_spots` | array | Địa điểm vừa tìm | [...] |
| `last_hotels` | array | Khách sạn vừa tìm | [...] |

---

## 🎨 UI Types Reference

| UI Type | Description | Use Case |
|---------|-------------|----------|
| `text` | Plain text response | Chit-chat, confirmations |
| `itinerary` | Lịch trình chi tiết | Show full itinerary |
| `spots` | Danh sách địa điểm | Suggest spots to visit |
| `hotels` | Danh sách khách sạn | Hotel search results |
| `cost_breakdown` | Bảng chi phí chi tiết | Cost estimation |
| `tips` | Lời khuyên/lưu ý | Location-specific tips |

---

## 🚀 Advanced Features

### 1. Intent Detection
System tự động detect các intents:
- `plan_trip` - Lập lịch trình mới
- `find_spot` - Tìm địa điểm
- `find_hotel` - Tìm khách sạn
- `book_hotel` - Đặt phòng
- `calculate_cost` - Tính chi phí
- `show_itinerary` - Xem lại lịch trình
- `get_location_tips` - Lời khuyên

### 2. State Machine
```
INITIAL → GATHERING_INFO → CHOOSING_SPOTS 
       → CHOOSING_HOTEL → CALCULATING_COST → COMPLETED
```

### 3. Context Persistence
- Context được giữ qua nhiều turns
- Frontend phải gửi lại context từ response trước
- System merge context cũ + mới

---

## 🐛 Troubleshooting

### Issue: Response quá chậm
**Solution:** Dùng `/chat/stream` thay vì `/chat`

### Issue: Context bị mất
**Solution:** Đảm bảo gửi lại `context` từ response trước vào request mới

### Issue: Intent detection sai
**Solution:** Cung cấp context đầy đủ hơn (destination, duration, workflow_state)

### Issue: Lỗi 500
**Solution:** Check server logs, thường do missing required fields

---

## 📞 Support

- **Logs:** Check terminal running uvicorn
- **Debug:** Set log level to DEBUG
- **Issues:** GitHub Issues

---

**Built with ❤️ using FastAPI, SaoLa 3.1, and MongoDB**
