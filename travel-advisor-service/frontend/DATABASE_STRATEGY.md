# ⚠️ DATABASE STRATEGY DECISION NEEDED

## Current Situation

Dự án hiện đang sử dụng **HYBRID DATABASE APPROACH** với cả Prisma và Mongoose:

### ✅ Mongoose (Active - MongoDB)
**Models đang hoạt động:**
- `src/models/User.ts` - User authentication
- `src/models/Booking.ts` - Booking management
- `src/models/Listing.ts` - Hotel listings
- `src/models/StagingListing.ts` - Crawler staging data

**Connection:**
- `src/lib/db.ts` - MongoDB connection manager

**Database:**
- MongoDB Atlas/Local
- Environment: `MONGODB_URI` in `.env`

---

### ⚠️ Prisma (Legacy - SQL Server)
**Files vẫn import Prisma:**
- `src/lib/prisma.ts` - PrismaClient definition
- `src/app/trips/page.tsx`
- `src/app/places/[id]/page.tsx`
- `src/app/api/bookings/route.ts`
- `src/app/api/bookings/[bookingId]/route.ts`
- `src/app/api/listings/route.ts`
- `src/app/api/nlp/chat/route.ts`
- `src/app/api/nlp-fpt/chat/route.ts`
- `src/app/api/b2b/competitors/route.ts`
- `src/app/api/b2b/competitors/[id]/prices/route.ts`
- `src/app/api/auth/[...nextauth]/route.ts` (PrismaAdapter)

**Schema:**
- `prisma/schema.prisma` - SQL Server schema
- `prisma/seed.js`, `prisma/seed.ts` - Seeding scripts

**Database:**
- SQL Server (legacy)
- Connection string: May not be configured

---

## 🎯 Migration Status

### Phase 1: Models Migration (✅ COMPLETED)
- User model migrated to Mongoose
- Booking model migrated to Mongoose
- Listing model migrated to Mongoose

### Phase 2: API Routes Migration (⚠️ IN PROGRESS)
**Migrated:**
- Some routes already use Mongoose models

**Not Migrated (Still using Prisma import):**
- trips/page.tsx
- places/[id]/page.tsx
- api/bookings/* (imports prisma but may use Mongoose models?)
- api/listings/* (imports prisma but may use Mongoose models?)
- api/nlp/* chat routes
- api/b2b/* routes
- api/auth (NextAuth with PrismaAdapter)

### Phase 3: NextAuth Migration (❓ PENDING)
Currently using `@next-auth/prisma-adapter` in:
- `src/app/api/auth/[...nextauth]/route.ts`

**Options:**
1. Keep PrismaAdapter if Prisma is still needed for auth
2. Migrate to `@auth/mongodb-adapter` for full MongoDB

---

## 📊 Decision Matrix

### Option A: Complete MongoDB Migration (Recommended)
**Pros:**
- Single database solution
- Simpler architecture
- Better for Mongoose expertise
- Easier maintenance

**Cons:**
- Need to refactor all Prisma imports
- Need to migrate NextAuth adapter
- Need to test thoroughly

**Effort:** 4-6 hours

---

### Option B: Keep Hybrid (Not Recommended)
**Pros:**
- No immediate work needed
- Existing code continues to work

**Cons:**
- Complex architecture
- Two database connections
- Confusing for developers
- Hard to maintain

**Risk:** High technical debt

---

### Option C: Rollback to Prisma (Not Recommended)
**Pros:**
- Prisma has great TypeScript support
- Prisma Studio for GUI

**Cons:**
- Need to rollback all Mongoose models
- Lose MongoDB flexibility
- More work than Option A

**Effort:** 6-8 hours

---

## 🚀 Recommended Action Plan

### ✅ Choose Option A: Complete MongoDB Migration

#### Step 1: Verify Current State
```bash
# Check which APIs actually use Prisma queries
grep -r "prisma\." src/app/api/
```

#### Step 2: Refactor API Routes
Replace all `prisma` imports with Mongoose models:
```typescript
// Before:
import prisma from "@/lib/prisma"
const bookings = await prisma.booking.findMany()

// After:
import Booking from "@/models/Booking"
import dbConnect from "@/lib/db"
await dbConnect()
const bookings = await Booking.find()
```

#### Step 3: Migrate NextAuth
```bash
npm install @auth/mongodb-adapter
```

Update `api/auth/[...nextauth]/route.ts`:
```typescript
// Before:
import { PrismaAdapter } from "@next-auth/prisma-adapter"
adapter: PrismaAdapter(prisma)

// After:
import { MongoDBAdapter } from "@auth/mongodb-adapter"
import clientPromise from "@/lib/mongodb" // Create this
adapter: MongoDBAdapter(clientPromise)
```

#### Step 4: Remove Prisma Dependencies
```bash
npm uninstall @prisma/client prisma @next-auth/prisma-adapter
```

Update `package.json`:
- Remove `prisma:generate` script
- Remove prisma dependencies

#### Step 5: Archive Prisma Files
```bash
mv prisma/ archive/prisma_legacy/
mv src/lib/prisma.ts archive/
```

---

## ⏰ Timeline Estimate

| Task | Effort | Priority |
|------|--------|----------|
| Verify Prisma usage | 30 min | High |
| Refactor API routes | 2-3 hours | High |
| Migrate NextAuth | 1 hour | High |
| Testing | 1 hour | Critical |
| Remove dependencies | 15 min | Medium |
| Archive legacy code | 15 min | Low |
| **TOTAL** | **4-6 hours** | - |

---

## 🧪 Testing Checklist

After migration, test:
- [ ] User authentication (login/logout/register)
- [ ] Booking creation and retrieval
- [ ] Listing CRUD operations
- [ ] Trip management
- [ ] Chat functionality (if it stores data)
- [ ] B2B competitor pricing

---

## 🔍 Current Risk Assessment

### High Risk: NextAuth Migration
- PrismaAdapter → MongoDBAdapter may break sessions
- **Mitigation:** Test login flow thoroughly
- **Rollback plan:** Keep backup of auth route

### Medium Risk: Query Syntax Differences
- Prisma: `prisma.booking.findMany()`
- Mongoose: `Booking.find()`
- **Mitigation:** Update all query patterns

### Low Risk: Data Loss
- Both Prisma and Mongoose point to same MongoDB?
- **Verification needed:** Check if Prisma schema.prisma points to MongoDB or SQL Server

---

## 📝 Questions to Answer

1. ❓ Does Prisma currently connect to SQL Server or MongoDB?
   - Check `prisma/schema.prisma` → `datasource db { provider = ? }`

2. ❓ Are there any Prisma-specific features being used?
   - Migrations?
   - Prisma Studio?
   - Complex relations?

3. ❓ Is there production data in SQL Server that needs migration?
   - If yes, need data migration plan
   - If no, can proceed with Option A

4. ❓ Does NextAuth work with current setup?
   - Test login/logout
   - Check session storage

---

## 📞 Next Steps

**Immediate (This Session):**
1. ✅ Created this document
2. ⏭️ Decision: Archive Prisma for now, plan full migration later
3. ⏭️ Create `PRISMA_TO_MONGOOSE_MIGRATION_GUIDE.md` with detailed steps

**Short Term (Next Sprint):**
1. Verify which APIs actually use Prisma queries
2. Refactor one API route as proof of concept
3. Test thoroughly
4. Plan full migration

**Long Term (Future):**
1. Complete full migration to MongoDB/Mongoose
2. Remove Prisma dependencies
3. Update team documentation

---

## 📄 Related Documentation

- [Mongoose Models](../src/models/)
- [Database Connection](../src/lib/db.ts)
- [Prisma Schema](../prisma/schema.prisma) (Legacy)
- [Migration Guide](PRISMA_TO_MONGOOSE_MIGRATION_GUIDE.md) (To be created)

---

**Created:** 29 November 2025  
**Status:** ⚠️ Decision Pending  
**Priority:** 🔴 High (Affects architecture)
