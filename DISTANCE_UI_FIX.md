# ✅ FIX: DISTANCE INFO UI DISPLAY

**Ngày:** 16/01/2026  
**Vấn đề:** Backend đã tính khoảng cách nhưng frontend không hiển thị

---

## 🔍 ROOT CAUSE

Backend trả về `ui_type: "distance_info"` với data:
```json
{
  "ui_type": "distance_info",
  "ui_data": {
    "hotel": "Tên khách sạn",
    "distances": [
      {
        "name": "Tên địa điểm",
        "distance_km": 5.2,
        "address": "Địa chỉ"
      }
    ]
  }
}
```

Nhưng frontend [ChatWidget.tsx](frontend/src/components/features/chatbot/ChatWidget.tsx) **chưa có case render** cho `ui_type="distance_info"`.

---

## ✅ SOLUTION IMPLEMENTED

### 1. Cập nhật Message Type
```typescript
// frontend/src/components/features/chatbot/ChatWidget.tsx

type Message = {
  ui_type?: "... | "distance_info" | ...
  ui_data?: {
    // ... existing fields
    // NEW: Distance Info fields
    hotel?: string
    distances?: Array<{
      name: string
      distance_km: number
      address: string
    }>
  }
}
```

### 2. Thêm Render Case
```typescript
case "distance_info": {
  const hotelName = ui_data.hotel || "Khách sạn";
  const distances = ui_data.distances || [];
  
  return (
    <motion.div className="...">
      <div className="header">
        📏 Khoảng cách từ {hotelName}
      </div>
      <div className="distances-list">
        {distances.map((dist, idx) => (
          <div key={idx}>
            <span>{dist.name}</span>
            <span>📍 {dist.distance_km} km</span>
            <span>🕐 ~{timeStr}</span>
          </div>
        ))}
      </div>
    </motion.div>
  );
}
```

---

## 📊 UI DESIGN

```
┌─────────────────────────────────────────────┐
│ 📏 Khoảng cách từ [Khách sạn]              │
├─────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────┐ │
│ │ 1  Bà Nà Hills                          │ │
│ │    Ngũ Hành Sơn                         │ │
│ │    📍 12.5 km    🕐 ~25 phút            │ │
│ └─────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────┐ │
│ │ 2  Bãi biển Mỹ Khê                      │ │
│ │    Sơn Trà                              │ │
│ │    📍 3.2 km     🕐 ~6 phút             │ │
│ └─────────────────────────────────────────┘ │
│ ...                                         │
│                                             │
│ 💡 Thời gian ước tính với tốc độ 30 km/h   │
└─────────────────────────────────────────────┘
```

---

## 🧪 TEST SCENARIO

### Trigger Query:
```
User: "Khoảng cách từ khách sạn đến các địa điểm như thế nào?"
```

### Backend Detection:
```python
# master_controller.py
def _is_distance_query(self, message: str) -> bool:
    distance_patterns = [
        "khoảng cách", "xa không", "xa gần", "bao xa",
        "đi lại", "quãng đường", ...
    ]
    return any(pattern in message_lower for pattern in distance_patterns)
```

### Backend Response:
```json
{
  "reply": "📏 **Khoảng cách từ Khách sạn A:**\n📍 **Bà Nà Hills**: 12.5 km (~25 phút)\n...",
  "ui_type": "distance_info",
  "ui_data": {
    "hotel": "Khách sạn A",
    "distances": [...]
  }
}
```

### Frontend Render:
✅ Now displays distance card with:
- Hotel name header
- List of spots with distances
- Estimated travel time
- Visual ranking (1, 2, 3...)

---

## 📝 NOTES

### Distance Calculation (Backend)
- Uses **Haversine formula** for geographic distance
- Requires `coordinates.lat` and `coordinates.lon` in spot data
- Falls back to N/A if coordinates missing

### Time Estimation
- Assumes **30 km/h average speed** in city
- Formula: `time_minutes = (distance_km / 30) * 60`
- Display: "X phút" or "Xh Ym"

### Prerequisites
1. User must have **selected hotel** (`context.selected_hotel`)
2. Hotel must have **coordinates** (`latitude`, `longitude`)
3. Spots in itinerary must have **coordinates**

---

## ✅ FILES CHANGED

| File | Changes |
|------|---------|
| [ChatWidget.tsx](frontend/src/components/features/chatbot/ChatWidget.tsx) | • Added `distance_info` to Message type<br>• Added `hotel` and `distances` fields to `ui_data`<br>• Added `case "distance_info":` render logic |

---

## 🚀 DEPLOYMENT

Frontend cần rebuild:
```bash
cd frontend
npm run build
```

Backend không cần thay đổi (đã có logic sẵn).

---

**Status:** ✅ FIXED - Distance info now displays correctly in frontend
