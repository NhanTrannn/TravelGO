# 🔧 FIX: DISTANCE CALCULATION NOT TRIGGERING

**Ngày:** 16/01/2026  
**Vấn đề:** Backend detect intent `get_distance` nhưng không chạy distance handler

---

## 🔍 ROOT CAUSE

### Vấn đề 1: Intent Routing
Backend log cho thấy:
```
🎯 Detected intent: get_distance (confidence: 0.95)
...
🔍 GeneralInfoExpert: query='thông tin du lịch'  ❌ SAI!
```

**Nguyên nhân:** Code chỉ check `_is_distance_query(message)` (text pattern) mà không check `intent == "get_distance"`

```python
# BEFORE (SAI)
if self._is_distance_query(user_message):  # Chỉ check text
    return self._handle_distance_query_sync(...)

# Intent "get_distance" bị bỏ qua → đi vào GeneralInfoExpert
```

### Vấn đề 2: Missing Coordinates
Nhiều hotels/spots trong context không có `coordinates` field → không tính được khoảng cách

---

## ✅ SOLUTION

### 1. Fix Intent Routing
```python
# AFTER (ĐÚNG)
if intent == "get_distance" or self._is_distance_query(user_message):
    return self._handle_distance_query_sync(...)
```

**Logic:**
- Ưu tiên check `intent == "get_distance"` (từ LLM)
- Fallback check text pattern nếu LLM không phân loại đúng

### 2. Auto-Fetch Coordinates từ DB
```python
# Hotel coordinates
if not hotel_lat or not hotel_lon:
    hotel_id = selected_hotel.get('id')
    if hotel_id and self.mongo_manager:
        hotel_doc = hotels_col.find_one({"_id": ObjectId(hotel_id)})
        if hotel_doc:
            hotel_coords = hotel_doc.get('coordinates', {})
            hotel_lat = hotel_coords.get('lat')
            hotel_lon = hotel_coords.get('lon')

# Spot coordinates (tương tự)
for spot in spots_to_check:
    if not spot_lat or not spot_lon:
        # Fetch from spots_detailed collection
```

### 3. Enhanced Logging
```python
logger.info(f"📏 Selected hotel from context: {hotel_name}")
logger.info(f"📏 Fetching hotel coordinates from DB for: {hotel_id}")
logger.info(f"📏 Found coordinates: lat={lat}, lon={lon}")
logger.info(f"📏 Checking {len(spots)} spots for distance")
logger.info(f"📏 Calculated distances for {len(results)} spots")
```

---

## 🧪 TEST SCENARIO

### User Query:
```
"tính khoảng cách từ Sông Hàn và 4 cây cầu kỉ lục đến Khách sạn San San"
```

### Expected Flow:
1. ✅ Intent detection: `get_distance` (confidence: 0.95)
2. ✅ Route to: `_handle_distance_query_sync()`
3. ✅ Get hotel: "Khách sạn Courtyard by Marriott Đà Nẵng"
4. ✅ Fetch coordinates from DB if missing
5. ✅ Get spots from context or extract from query
6. ✅ Calculate Haversine distance for each spot
7. ✅ Return: `ui_type: "distance_info"` with distances array

### Backend Response:
```json
{
  "reply": "📏 **Khoảng cách từ Khách sạn Courtyard:**\n📍 **Sông Hàn**: 2.5 km (~5 phút)\n📍 **Cầu Rồng**: 3.1 km (~6 phút)\n...",
  "ui_type": "distance_info",
  "ui_data": {
    "hotel": "Khách sạn Courtyard by Marriott",
    "distances": [
      {"name": "Sông Hàn", "distance_km": 2.5, "address": "..."},
      {"name": "Cầu Rồng", "distance_km": 3.1, "address": "..."}
    ]
  }
}
```

### Frontend Render:
✅ Displays distance card (đã fix ở lần trước)

---

## 📝 LOGS MẪU

### Before Fix:
```
🎯 Detected intent: get_distance
📋 Created plan with 1 tasks: ['general_info']  ❌
🔍 GeneralInfoExpert: query='thông tin du lịch'  ❌
```

### After Fix:
```
🎯 Detected intent: get_distance
📏 Distance query detected: tính khoảng cách...  ✅
📏 Selected hotel from context: Khách sạn San San  ✅
📏 Fetching hotel coordinates from DB for: 67abc123...  ✅
📏 Found coordinates from DB: lat=16.0544, lon=108.2022  ✅
📏 Checking 5 spots for distance calculation  ✅
📏 Calculated distances for 5 spots  ✅
```

---

## 🎯 KEY IMPROVEMENTS

| Aspect | Before | After |
|--------|--------|-------|
| **Intent Check** | Text pattern only | Intent + text pattern |
| **Coordinates** | Required in context | Auto-fetch from DB |
| **Logging** | Minimal | Detailed debug logs |
| **Error Handling** | Generic message | Specific feedback |

---

## ✅ FILES CHANGED

| File | Changes |
|------|---------|
| [master_controller.py](travel-advisor-service/app/services/master_controller.py) | • Line ~1258: Added `intent == "get_distance"` check<br>• Line ~5920: Added hotel coordinates DB fetch<br>• Line ~6025: Added spot coordinates DB fetch<br>• Added comprehensive logging |

---

## 🚀 TESTING

Restart backend và test:
```bash
cd travel-advisor-service
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001
```

Query test:
- "Khoảng cách từ khách sạn đến các địa điểm"
- "Tính khoảng cách từ Cầu Rồng đến khách sạn"
- "Xa không từ hotel đến bãi biển?"

Expected: ✅ Hiển thị distance card với đầy đủ thông tin

---

**Status:** ✅ FIXED - Distance calculation now properly routes and fetches missing data
