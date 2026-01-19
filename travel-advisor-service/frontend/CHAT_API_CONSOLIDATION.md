# 💬 Chat API Endpoints Analysis & Consolidation Plan

## Current State (4 Chat Endpoints)

### 1. `/api/fpt-chat` 📡
**File:** `src/app/api/fpt-chat/route.ts` (40 lines)

**Purpose:** Simple proxy to Python FPT service

**Features:**
- Forwards messages to `http://127.0.0.1:8001/chat`
- No data processing
- Just proxy layer

**Complexity:** ⭐ (Very Simple)

**Usage:** Testing/prototyping

**Recommendation:** ❌ **ARCHIVE** - Redundant với nlp-fpt/chat

---

### 2. `/api/simple-chat` 💭
**File:** `src/app/api/simple-chat/route.ts` (70 lines)

**Purpose:** Simple chatbot without intent detection

**Features:**
- No intent detection
- No GenUI
- No info extraction
- Pure conversational AI
- Calls Python service with temperature/max_tokens

**Complexity:** ⭐⭐ (Simple)

**Usage:** Chitchat, general Q&A about travel

**Use Cases:**
- Chitchat thông thường
- Hỏi đáp chung về du lịch (không cần plan)
- Câu hỏi về văn hóa, ẩm thực, tips
- Follow-up questions không cần UI

**Recommendation:** ✅ **KEEP** - Useful for non-planning conversations

---

### 3. `/api/nlp/chat` 🧠
**File:** `src/app/api/nlp/chat/route.ts` (146 lines)

**Purpose:** Complex chat with NLP + listing search

**Features:**
- Intent detection (search vs info)
- **Uses OLD Python NLP service** (not FPT)
- Prisma for listing queries
- Context-rich AI generation
- Extracts: location, price_max, keywords
- Returns: text response + hotel listings

**Complexity:** ⭐⭐⭐⭐ (Complex)

**Dependencies:**
- Prisma (legacy database)
- Old Python NLP service

**Recommendation:** ⚠️ **MIGRATE or ARCHIVE**
- If old NLP service is deprecated → Archive
- If still used → Migrate to use nlp-fpt pattern

---

### 4. `/api/nlp-fpt/chat` 🚀
**File:** `src/app/api/nlp-fpt/chat/route.ts` (192 lines)

**Purpose:** Advanced chat with FPT AI + listing search

**Features:**
- Intent detection (search vs info)
- Uses **FPT Qwen 2.5 32B** (modern)
- Prisma for listing queries
- Context-rich AI generation
- Extracts: location, price_max, keywords
- Returns: text response + hotel listings
- Better error handling

**Complexity:** ⭐⭐⭐⭐ (Complex)

**Dependencies:**
- Prisma (needs migration to Mongoose)
- FPT service at localhost:8001

**Recommendation:** ✅ **MAIN ENDPOINT** - Most advanced, should be primary

---

## 📊 Comparison Matrix

| Feature | fpt-chat | simple-chat | nlp/chat | nlp-fpt/chat |
|---------|----------|-------------|----------|--------------|
| **Intent Detection** | ❌ | ❌ | ✅ | ✅ |
| **Hotel Search** | ❌ | ❌ | ✅ | ✅ |
| **AI Model** | FPT | FPT | Old NLP | FPT Qwen 32B |
| **Context Aware** | ❌ | ❌ | ✅ | ✅ |
| **Database** | - | - | Prisma | Prisma |
| **Complexity** | Low | Low | High | High |
| **Error Handling** | Basic | Good | Basic | Excellent |
| **Use Case** | Proxy test | Chitchat | Search (old) | Search (main) |

---

## 🎯 Consolidation Strategy

### ✅ Keep These:

#### 1. `/api/simple-chat` (Rename to `/api/chat/simple`)
**Use for:** General conversations, chitchat
- No intent detection needed
- No database queries
- Pure AI conversation

#### 2. `/api/nlp-fpt/chat` (Rename to `/api/chat` - MAIN ENDPOINT)
**Use for:** Smart search, hotel recommendations
- Intent detection
- Hotel search
- Context-aware responses
- **TODO:** Migrate from Prisma to Mongoose

---

### ❌ Archive These:

#### 1. `/api/fpt-chat` → `archive/api/fpt-chat/`
**Reason:** Redundant - Same functionality as simple-chat but less features

#### 2. `/api/nlp/chat` → `archive/api/nlp-old-service/`
**Reason:** Uses old NLP service (deprecated)
- If old service is still needed, document separately
- If deprecated, archive completely

---

## 🚀 Proposed New Structure

```
src/app/api/
├── chat/                          # 🆕 MAIN CHAT ENDPOINT
│   └── route.ts                   # From nlp-fpt/chat (migrated to Mongoose)
│
├── chat/simple/                   # 🆕 SIMPLE CHAT (No DB)
│   └── route.ts                   # From simple-chat/
│
├── fpt-planner/                   # Trip planning (existing)
│   └── route.ts
│
├── trip-planner/                  # Trip planning (existing)
│   └── route.ts
│
└── [other endpoints...]

archive/api/
├── fpt-chat/                      # ❌ Archived: Simple proxy (redundant)
│   └── route.ts
│
└── nlp-old-service/               # ❌ Archived: Old NLP service
    └── chat/route.ts
```

---

## 📋 Migration Checklist

### Phase 1: Archive Legacy Endpoints ✅
- [x] Create archive/api/ folder
- [x] Move api/fpt-chat/ → archive/api/fpt-chat/
- [x] Move api/nlp/ → archive/api/nlp-old-service/
- [x] Update documentation

### Phase 2: Refactor Main Endpoint ⏳
- [ ] Migrate nlp-fpt/chat from Prisma to Mongoose
  - Replace `import prisma from "@/lib/prisma"`
  - Use `import Listing from "@/models/Listing"`
  - Update query syntax
- [ ] Test hotel search functionality
- [ ] Test intent detection

### Phase 3: Reorganize Structure ⏳
- [ ] Rename `/api/nlp-fpt/chat` → `/api/chat`
- [ ] Rename `/api/simple-chat` → `/api/chat/simple`
- [ ] Update frontend imports
- [ ] Test all chat features

### Phase 4: Update Frontend ⏳
- [ ] Update ChatWidget.tsx to use new endpoints
- [ ] Update any components calling old endpoints
- [ ] Remove references to archived endpoints

---

## 🧪 Testing Requirements

After consolidation, test:
- [ ] Simple chat works (no DB queries)
- [ ] Hotel search works (with DB queries)
- [ ] Intent detection correctly routes requests
- [ ] Context-aware responses
- [ ] Error handling for failed DB queries
- [ ] FPT service integration

---

## 📞 Frontend Impact

### Components likely affected:
- `src/components/features/chatbot/ChatWidget.tsx`
- `src/app/chat/page.tsx` (if exists)
- Any component importing from:
  - `/api/fpt-chat`
  - `/api/simple-chat`
  - `/api/nlp/chat`
  - `/api/nlp-fpt/chat`

### Required updates:
```typescript
// Before:
fetch('/api/nlp-fpt/chat', { ... })
fetch('/api/simple-chat', { ... })

// After:
fetch('/api/chat', { ... })           // For smart search
fetch('/api/chat/simple', { ... })    // For chitchat
```

---

## ⏰ Timeline Estimate

| Task | Effort | Priority |
|------|--------|----------|
| Archive fpt-chat | 5 min | High |
| Archive nlp/chat | 5 min | High |
| Document decision | 10 min | High |
| Migrate Prisma → Mongoose | 1 hour | High |
| Reorganize structure | 30 min | Medium |
| Update frontend | 30 min | Medium |
| Testing | 30 min | Critical |
| **TOTAL** | **~3 hours** | - |

---

## 🎓 Decision Rationale

### Why Archive fpt-chat?
- Only 40 lines
- No additional features vs simple-chat
- Just a proxy layer
- Redundant with nlp-fpt/chat

### Why Archive nlp/chat?
- Uses old NLP service
- FPT Qwen 2.5 32B is better
- nlp-fpt/chat is more advanced
- Better error handling in nlp-fpt

### Why Keep simple-chat?
- Different use case (no DB, pure conversation)
- Useful for chitchat
- Lower latency (no DB queries)
- Complements main chat endpoint

### Why nlp-fpt/chat as Main?
- Most advanced features
- FPT Qwen 2.5 32B (32 billion parameters)
- Intent detection
- Context-aware
- Best error handling

---

## 📝 Next Actions

**Immediate (This Session):**
1. ✅ Created this analysis document
2. ⏭️ Archive fpt-chat/
3. ⏭️ Archive nlp/
4. ⏭️ Document in REFACTORING_SUMMARY.md

**Short Term (Next Session):**
1. Migrate nlp-fpt/chat from Prisma to Mongoose
2. Test thoroughly
3. Rename endpoints
4. Update frontend

---

**Created:** 29 November 2025  
**Status:** ✅ Analysis Complete, Ready for Execution  
**Priority:** 🟡 Medium (After Python refactor complete)
