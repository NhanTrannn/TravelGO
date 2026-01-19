# 🔄 Hybrid Search System: Database + Web Fallback

## 📋 Tổng Quan

Hệ thống tìm kiếm thông minh với **fallback mechanism** tự động:
1. **Bước 1**: Tìm kiếm trong Database (MongoDB + Vector DB)
2. **Bước 2**: Đánh giá độ tin cậy (Confidence Score)
3. **Bước 3**: Nếu confidence thấp → Kích hoạt Web Search Agent
4. **Bước 4**: LLM tổng hợp thông tin từ web và trả lời

## 🏗️ Kiến Trúc

```
User Query
    ↓
┌───────────────────────────────────────────┐
│         SPOT EXPERT (or other Expert)     │
└───────────────────────────────────────────┘
    ↓
┌───────────────────────────────────────────┐
│  STEP 1: DATABASE SEARCH                  │
│  - MongoDB keyword search                 │
│  - Vector semantic search                 │
│  - Hybrid re-ranking                      │
└───────────────────────────────────────────┘
    ↓
    Results (0-N items)
    ↓
┌───────────────────────────────────────────┐
│  STEP 2: CONFIDENCE SCORING               │
│  - Result count (40%)                     │
│  - Data quality (30%)                     │
│  - Relevance (20%)                        │
│  - Completeness (10%)                     │
└───────────────────────────────────────────┘
    ↓
    Confidence: 0.0 - 1.0
    ↓
    ┌─────────────┐
    │ Confidence? │
    └─────────────┘
         ↙         ↘
    High (≥0.8)    Low (<0.5)
         ↓              ↓
    Return DB    ┌──────────────────────┐
    Results      │ STEP 3: WEB SEARCH   │
                 │ - Google/VnExpress   │
                 │ - Extract content    │
                 │ - Top 5 results      │
                 └──────────────────────┘
                         ↓
                 ┌──────────────────────┐
                 │ STEP 4: LLM SYNTHESIS│
                 │ - Combine DB + Web   │
                 │ - Generate answer    │
                 └──────────────────────┘
                         ↓
                 Return Enhanced Results
```

## 📦 Components

### 1. **Web Search Agent** (`web_search_agent.py`)

Tự động tìm kiếm và extract nội dung từ web.

**Features:**
- ✅ DuckDuckGo search (không cần API key)
- ✅ VnExpress direct search
- ✅ Content extraction with BeautifulSoup
- ✅ Relevance scoring
- ✅ LLM synthesis

**Usage:**
```python
from app.services.web_search_agent import search_and_synthesize

result = search_and_synthesize(
    query="Địa điểm lịch sử ở Điện Biên",
    province="Điện Biên",
    context="User tìm địa điểm chiến tranh",
    max_results=5
)

print(result['answer'])        # LLM synthesized answer
print(result['confidence'])    # 0.0 - 1.0
print(result['sources'])       # List of web sources
```

### 2. **Confidence Scorer** (`confidence_scorer.py`)

Đánh giá độ tin cậy của kết quả database.

**Scoring Formula:**
```
Confidence = (Result Count × 0.4) + 
             (Data Quality × 0.3) + 
             (Relevance × 0.2) + 
             (Completeness × 0.1)
```

**Confidence Levels:**
- 🟢 **HIGH (0.8-1.0)**: Rất tin cậy, không cần web search
- 🟡 **MEDIUM (0.5-0.8)**: Tương đối tin cậy
- 🟠 **LOW (0.3-0.5)**: Ít tin cậy, nên dùng web search
- 🔴 **VERY LOW (0.0-0.3)**: Rất ít tin cậy, bắt buộc web search

**Usage:**
```python
from app.services.confidence_scorer import should_use_web_search

need_web, info = should_use_web_search(
    results=spots,
    data_type='spots',
    query="địa điểm lịch sử ở Huế",
    province="Thừa Thiên Huế",
    theme="lịch sử"
)

if need_web:
    print(f"Need web search: {info['reason']}")
    # Trigger web search...
```

### 3. **Integration in Experts** (`spot_expert.py`)

Đã integrate vào SpotExpert, sẵn sàng cho HotelExpert, FoodExpert, etc.

**Flow in Expert:**
```python
# 1. Search database
results = self._search_database(query, params)

# 2. Calculate confidence
need_web, confidence = should_use_web_search(results, ...)

# 3. If low confidence, use web search
if need_web:
    web_result = search_and_synthesize(query, ...)
    # Enhance results with web info

# 4. Return enhanced results
return ExpertResult(..., metadata={
    'confidence': confidence,
    'web_search_used': need_web,
    'web_search_answer': web_answer
})
```

## 🧪 Testing

### Run Integration Test:
```bash
cd travel-advisor-service
python test_web_search_integration.py
```

### Test Cases:
1. **HIGH CONFIDENCE**: Hội An (nhiều dữ liệu) → No web search
2. **LOW CONFIDENCE**: Điện Biên (ít dữ liệu lịch sử) → Trigger web search
3. **ZERO RESULTS**: Quảng Trị (căn cứ Khe Sanh) → Must use web search
4. **SPECIFIC QUERY**: Địa điểm miễn phí Hà Nội → No web search needed

### Expected Output:
```
📋 TEST 2: LOW CONFIDENCE - Điện Biên (ít dữ liệu lịch sử)
========================================
Query: các địa điểm lịch sử chiến tranh ở Điện Biên

📊 DATABASE RESULTS:
   Count: 2
   1. Đồi A1 - 4.5⭐
   2. Nghĩa trang liệt sĩ - 4.3⭐

🎯 CONFIDENCE ASSESSMENT:
   Score: 0.45
   Level: LOW
   Reason: ⚠️ Quá ít kết quả (2/5) | ✓ Dữ liệu chấp nhận được
   Should use web search: YES

🌐 WEB SEARCH:
   ✅ WEB SEARCH ACTIVATED
   Answer preview: Điện Biên Phủ có nhiều di tích lịch sử quan trọng như...

✓ VERIFICATION:
   ✅ PASS - Web search behavior as expected
```

## 📊 Confidence Scoring Details

### Factor 1: Result Count (40%)
- 0 results → 0.0
- < min_expected → 0.2
- ≥ min_expected → 0.3
- ≥ 2× min_expected → 0.4

**Min Expected:**
- Spots: 5
- Hotels: 3
- Food: 3
- Transport: 2

### Factor 2: Data Quality (30%)
Checks for required fields:
- **Spots**: name (0.3), description >50 chars (0.3), location (0.2), tags (0.2)
- **Hotels**: name (0.3), price (0.2), address (0.2), rating (0.3)
- **Food**: name (0.3), type (0.3), description (0.2), price_range (0.2)

### Factor 3: Relevance (20%)
- Keyword matching in name/description/tags
- Theme matching
- Formula: `(matches / total_keywords) × 0.6 + theme_match × 0.4`

### Factor 4: Completeness (10%)
- Has province: +0.05
- Has theme: +0.05

## 🌐 Web Search Sources

### Priority Order:
1. **VnExpress.net** (0.9 relevance) - Most trusted
2. **DuckDuckGo** (0.5-0.8) - Aggregates multiple sources
3. **Other trusted sources**:
   - dantri.com.vn
   - vi.wikipedia.org
   - dulich.cntraveller.vn
   - travel.com.vn
   - vietnamnet.vn

### Content Extraction:
- Removes: scripts, styles, nav, footer, header, ads
- Targets: article, .article-content, .content, main
- Fallback: All paragraphs in body
- Max length: 2000 chars

## 🔧 Configuration

### Minimum Expected Results:
```python
# In confidence_scorer.py
min_expected_results = {
    'spots': 5,      # Adjust based on your needs
    'hotels': 3,
    'food': 3,
    'transport': 2
}
```

### Confidence Thresholds:
```python
threshold_high = 0.8    # High confidence
threshold_medium = 0.5  # Medium confidence
threshold_low = 0.3     # Low confidence
```

### Web Search Settings:
```python
# In web_search_agent.py
max_results = 5         # Top N search results
max_content_length = 2000  # Max chars per page
timeout = 10            # Request timeout (seconds)
```

## 📈 Performance Impact

### Database Only:
- ⏱️ ~50-200ms per query
- 💾 No external requests
- 📊 Limited to existing data

### With Web Search:
- ⏱️ ~2-5 seconds per query (when triggered)
- 🌐 External HTTP requests
- 📊 Access to latest information

### Optimization:
- ✅ Web search only when confidence < threshold
- ✅ Caching web results (TODO)
- ✅ Async requests (TODO)
- ✅ Rate limiting (TODO)

## 🚀 Extending to Other Experts

### HotelExpert Example:
```python
# In hotel_expert.py
from app.services.confidence_scorer import should_use_web_search
from app.services.web_search_agent import search_and_synthesize

# After database search...
need_web, confidence = should_use_web_search(
    results=hotels,
    data_type='hotels',
    query=query,
    province=province,
    theme=price_range
)

if need_web:
    web_result = search_and_synthesize(
        query=f"khách sạn {price_range} ở {province}",
        province=province,
        context=f"Found {len(hotels)} hotels in DB"
    )
    # Add to response...
```

### FoodExpert Example:
```python
# Similar pattern
need_web, confidence = should_use_web_search(
    results=restaurants,
    data_type='food',
    query=query,
    province=province,
    theme=cuisine_type
)

if need_web:
    web_result = search_and_synthesize(
        query=f"nhà hàng {cuisine_type} nổi tiếng ở {province}",
        province=province
    )
```

## 🎯 Best Practices

### 1. When to Use Web Search:
- ✅ User asks for latest/current information
- ✅ Specific/rare queries (war sites, hidden gems)
- ✅ Database returns < 3 results
- ✅ User mentions "mới", "hiện tại", "trending"

### 2. When to Skip Web Search:
- ⏭️ Popular destinations (Hà Nội, Hội An, HCMC)
- ⏭️ General queries with good DB results
- ⏭️ High confidence scores (> 0.8)
- ⏭️ Performance-critical scenarios

### 3. Error Handling:
```python
try:
    web_result = search_and_synthesize(...)
    if web_result['confidence'] > 0.5:
        # Use web result
    else:
        # Fallback to DB only
except Exception as e:
    logger.error(f"Web search failed: {e}")
    # Continue with DB results
```

## 📚 Dependencies

```bash
# Install required packages
pip install requests beautifulsoup4 lxml

# Already in requirements.txt
```

## 🔍 Monitoring & Logging

### Key Metrics to Track:
- 📊 Web search trigger rate
- ⏱️ Average web search latency
- 💯 Web search success rate
- 🎯 Confidence score distribution
- 📈 Result quality improvements

### Log Examples:
```
🎯 Confidence: 0.45 (low) - ⚠️ Quá ít kết quả (2/5)
🌐 Low confidence (0.45), activating web search...
✅ Web search successful (confidence: 0.85)
📰 Sources: vnexpress, duckduckgo
```

## 🎉 Benefits

1. **Better Coverage**: Access to web when DB lacks data
2. **Latest Information**: Fresh content from web
3. **User Satisfaction**: Always have an answer
4. **Smart Resource Usage**: Web search only when needed
5. **Transparent**: Users see confidence levels
6. **Extensible**: Easy to add new sources

## 🔮 Future Enhancements

- [ ] Cache web search results (Redis)
- [ ] Async web requests (parallel)
- [ ] More web sources (Foody, Tripadvisor)
- [ ] User feedback loop (rate answers)
- [ ] A/B testing (DB-only vs Hybrid)
- [ ] Query rewriting for better web results
- [ ] Structured data extraction (JSON-LD)
- [ ] Image extraction from web

## ✅ Testing Checklist

- [x] Web Search Agent implementation
- [x] Confidence Scorer implementation
- [x] Integration into SpotExpert
- [x] Test suite created
- [ ] Install dependencies (`requests`, `beautifulsoup4`, `lxml`)
- [ ] Run integration tests
- [ ] Monitor performance
- [ ] Extend to HotelExpert
- [ ] Extend to FoodExpert
- [ ] Production testing

## 📝 Quick Start

```bash
# 1. Install dependencies
pip install requests beautifulsoup4 lxml

# 2. Run tests
python test_web_search_integration.py

# 3. Try in API
curl -X POST http://localhost:8001/api/v1/experts/spots \
  -H "Content-Type: application/json" \
  -d '{
    "query": "địa điểm lịch sử chiến tranh ở Điện Biên",
    "parameters": {
      "location": "Điện Biên",
      "province": "Điện Biên",
      "theme": "lịch sử"
    }
  }'
```

---

**🎯 Hệ thống đã sẵn sàng! Test ngay để xem kết quả!**
