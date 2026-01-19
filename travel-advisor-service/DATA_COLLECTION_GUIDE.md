# Query-Driven Data Collection System

## 📋 Tổng quan

Hệ thống **Query-driven Data Collection** tự động phát hiện và ghi nhận các **data gaps** (thiếu dữ liệu) dựa trên queries của người dùng, sau đó ưu tiên việc thu thập dữ liệu cho những gaps quan trọng nhất.

## 🎯 Mục tiêu

Thay vì populate database trước một cách mù quáng, hệ thống:
1. ✅ **Phát hiện** queries nào không trả về kết quả đủ
2. ✅ **Ghi nhận** data gaps với metadata (tỉnh, loại data, keywords, priority)
3. ✅ **Ưu tiên** gaps quan trọng nhất (dựa trên frequency + priority)
4. ✅ **Đề xuất** hành động thu thập data cụ thể

## 🏗️ Kiến trúc

### Components

```
┌─────────────────────────────────────────────────────────┐
│                    User Query                           │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│             Experts (Spot, Hotel, Food)                 │
│  • Execute search                                       │
│  • Check result count                                   │
│  • If insufficient → record_search_failure()            │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│              DataCollector Service                      │
│  • Calculate priority                                   │
│  • Store in data_gaps collection                        │
│  • High priority → Add to collection_queue              │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│              MongoDB Collections                        │
│  • data_gaps: Record all gaps with frequency           │
│  • collection_queue: High-priority tasks               │
└─────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Query Processing**: User query → Expert execution
2. **Gap Detection**: Expert checks `result_count < min_expected`
3. **Recording**: `record_search_failure()` called with metadata
4. **Prioritization**: System calculates priority score
5. **Queue Management**: High-priority items → collection queue
6. **Reporting**: Aggregate statistics for decision making

## 📊 Collections Schema

### `data_gaps`

```javascript
{
  "_id": ObjectId,
  "query": "Tìm điểm tham quan lịch sử chiến tranh ở Quảng Trị",
  "province": "Quảng Trị",
  "data_type": "spots",  // 'spots', 'hotels', 'food', 'transport'
  "keywords": ["lịch sử", "chiến tranh", "di tích"],
  "timestamp": ISODate("2026-01-02T..."),
  "priority": 12,  // Calculated score
  "result_count": 2,  // How many results were found
  "frequency": 5,  // How many times queried
  "last_query": "Latest query text",
  "status": "pending"
}
```

### `collection_queue`

```javascript
{
  "_id": ObjectId,
  "province": "Quảng Trị",
  "data_type": "spots",
  "keywords": ["lịch sử", "chiến tranh"],
  "priority": 12,
  "status": "pending",  // 'pending', 'in_progress', 'completed'
  "created_at": ISODate,
  "completed_at": ISODate,
  "attempts": 0,
  "data_collected": 15  // Number of items collected
}
```

## 🔧 Sử dụng

### 1. Chạy Tests để Trigger Data Gaps

```bash
python test_data_collection.py
```

Script này sẽ:
- Chạy 10 queries có khả năng thiếu data cao
- Ghi nhận data gaps vào database
- Hiển thị summary và suggestions

### 2. Xem Collection Suggestions

```bash
python manage_data_collection.py --action suggestions
```

Output:
```
📊 DATA COLLECTION SUGGESTIONS (Top 10)

Rank   Province             Type         Queries  Priority    Score
--------------------------------------------------------------------------------
1      Quảng Trị           spots        5        12.0        29.0
2      Điện Biên           spots        3        10.0        23.0
3      Phú Quốc            food         2        9.0         20.0
...
```

### 3. Xem Full Report

```bash
python manage_data_collection.py --action report
```

Hiển thị:
- Overview statistics
- Queue status
- Top provinces needing data
- Data types needed
- Recent high-priority gaps

### 4. Xem Action Plan

```bash
python manage_data_collection.py --action plan
```

Output cụ thể từng bước:
```
🎯 ACTION PLAN

1. Collect spots for Quảng Trị
   Priority: HIGH (queried 5 times)
   Focus areas: lịch sử, chiến tranh, di tích, thành cổ
   Action: Use web scraping or API to collect spots data
   Target: Find at least 10-20 items matching keywords
```

### 5. Interactive Mode

```bash
python manage_data_collection.py
```

Menu tương tác để explore data gaps.

## 🎯 Priority Calculation

```python
priority = base_priority + theme_boost

base_priority:
  - spots: 10
  - hotels: 8
  - food: 7
  - transport: 6

theme_boost (+2 each):
  - biển, beach
  - lịch sử, history
  - ẩm thực, food
  - miễn phí, free
  - tiết kiệm, budget
```

**Score Formula:**
```python
score = (avg_priority × 2) + total_queries
```

## 📈 Workflow Example

### Scenario: User queries about Quảng Trị war sites

1. **User Query**: "Tìm điểm tham quan lịch sử chiến tranh ở Quảng Trị"

2. **SpotExpert executes**:
   - Searches MongoDB: finds 2 spots
   - Result count (2) < min_expected (5)
   - Calls `record_search_failure()`

3. **DataCollector records**:
   ```python
   {
     'province': 'Quảng Trị',
     'data_type': 'spots',
     'keywords': ['lịch sử', 'chiến tranh'],
     'priority': 12,  # High priority!
     'result_count': 2
   }
   ```

4. **High Priority → Add to Queue**:
   - Priority ≥ 8 and result_count == 0
   - Added to `collection_queue`

5. **Next time queried**:
   - Frequency counter incremented
   - Score increases
   - Moved higher in suggestions

6. **Admin checks suggestions**:
   ```bash
   python manage_data_collection.py --action plan
   ```
   
7. **Admin takes action**:
   - Use MyDataCrawler to scrape war memorial sites
   - Collect 15 spots about Quảng Trị history
   - Import to MongoDB via script

8. **Mark task completed**:
   ```python
   data_collector.mark_task_completed(task_id, data_collected=15)
   ```

## 🔍 Integration Points

### In SpotExpert

```python
# After executing search
if len(results) < min_expected:
    record_search_failure(
        query=original_query,
        province=location,
        data_type='spots',
        keywords=search_terms,
        result_count=len(results)
    )
```

### In HotelExpert

```python
if len(hotels) < 3:  # Expected at least 3 hotels
    record_search_failure(
        query=query,
        province=province,
        data_type='hotels',
        keywords=price_keywords,
        result_count=len(hotels)
    )
```

### In FoodExpert

```python
if len(restaurants) == 0:
    record_search_failure(
        query=query,
        province=province,
        data_type='food',
        keywords=food_keywords,
        result_count=0
    )
```

## 📊 Metrics to Track

1. **Gap Coverage**: % of gaps filled over time
2. **Query Success Rate**: Before vs After data collection
3. **High-frequency Gaps**: Most queried missing data
4. **Province Coverage**: Which provinces need most work
5. **Data Type Balance**: Spots vs Hotels vs Food gaps

## 🚀 Future Enhancements

### Phase 1: Current (Implemented)
- ✅ Automatic gap detection
- ✅ Priority calculation
- ✅ Collection suggestions
- ✅ Reporting tools

### Phase 2: Automation
- 🔄 Auto-trigger web scraping
- 🔄 API integration for data collection
- 🔄 Scheduled collection jobs
- 🔄 Quality validation

### Phase 3: Intelligence
- 🔄 ML-based priority prediction
- 🔄 Semantic similarity to existing data
- 🔄 Auto-fill from external sources
- 🔄 User feedback loop

## 💡 Best Practices

1. **Run tests regularly** to identify new gaps
2. **Prioritize high-frequency gaps** first
3. **Batch collect similar data** (same province/type)
4. **Validate quality** before importing
5. **Mark tasks completed** to track progress
6. **Review reports weekly** for trends

## 🛠️ Troubleshooting

### No suggestions appearing

**Check:**
- Are queries actually running? (test_data_collection.py)
- Is MongoDB connection working?
- Are collections created? (data_gaps, collection_queue)

**Fix:**
```bash
# Run tests to trigger gaps
python test_data_collection.py

# Check if collections exist
python -c "from app.db import mongodb_manager; print(mongodb_manager.database.list_collection_names())"
```

### False positives (gaps for good data)

**Adjust min_expected threshold:**
```python
# In spot_expert.py
min_expected = 5  # Increase to 7-10 for stricter detection
```

### Priority not reflecting importance

**Review keywords in data_collector.py:**
```python
important_themes = ['biển', 'beach', ...]  # Add more themes
```

## 📚 References

- `app/services/data_collector.py` - Core logic
- `app/services/experts/spot_expert.py` - Gap detection
- `manage_data_collection.py` - Management tool
- `test_data_collection.py` - Testing script

---

**Nguyên tắc chính:** *"Collect what users need, not what we think they need"* ✨
