<div align="center">
	<h1>🌐 Smart Travel Ecosystem – Next.js + Prisma + FastAPI NLP + Crawler</h1>
	<p><strong>Dự án học tập & thực hành xây dựng hệ sinh thái du lịch thông minh:</strong><br/>Listings (Khách sạn), Đặt phòng (Bookings), Điểm đến (Destinations), Địa điểm (Places), Tour, Lịch trình (Itineraries) + NLP (Ollama) + Crawler (Selenium) + Pipeline làm sạch tiếng Việt.</p>
</div>

---

## 1. Tổng quan
Hệ thống gồm nhiều phần tích hợp:

| Thành phần | Mô tả |
|------------|------|
| `my-travel-app` | Frontend + API (Next.js App Router, TypeScript, Tailwind) |
| Prisma + SQL Server | Lớp truy vấn & schema (models: User, Listing, Booking, Destination, Place, Tour, Itinerary, ItineraryItem, StagingListing) |
| `python_service` | FastAPI NLP (Ollama), Crawler Selenium, Data Processor, Reprocess text |
| Crawler Pipeline | Crawl → Staging (raw) → Làm sạch → Đưa vào Listing/Place |
| NLP | Endpoint phân tích và hội thoại: `/analyze`, `/chat` (song ngữ Việt/Anh + heuristics fallback) |

### Mục tiêu chính
1. Cho phép người dùng duyệt và đặt chỗ (Listing + Booking + Checkout + Trips).
2. Quản lý dữ liệu du lịch đa lớp: Destination / Place / Tour / Itinerary.
3. Tạo & xử lý dữ liệu thô từ web (crawler) → staging → chuẩn hoá → hiển thị.
4. Tích hợp AI: phân tích câu truy vấn, gợi ý tìm kiếm và hội thoại.
5. Làm sạch lỗi encoding tiếng Việt (mojibake) tự động.

---
## 2. Kiến trúc (mô tả dạng chữ)
```
[User Browser]
		│
		├── (Next.js App Router) ── UI Pages / Components
		│         │               └── Calls internal API routes (/api/*)
		│         ├── /api/nlp/* → Proxy sang FastAPI NLP service
		│         ├── /api/listings, /api/bookings → Prisma SQL Server
		│         └── Hiển thị dữ liệu đã xử lý (Listing, Destination, Place …)
		│
		├── [Python FastAPI NLP] ─ /analyze /chat → Ollama (LLM) / heuristics
		│
		├── [Crawler Engine] (Selenium) → Crawl Vntrip → raw JSON → StagingListing
		│                   └── Data Processor (Pydantic) → Listing (chuẩn hoá)
		│                   └── Reprocess Script → Fix tiếng Việt, update DB
		│
		└── [SQL Server] Prisma schema (User, Listing, Booking, StagingListing…)
```

### 2.1 Cây thư mục chi tiết (Tour_with_NLP_Minimal)

```text
Tour_with_NLP_Minimal/
│
├── 📁 my-travel-app/                           # 🎨 FRONTEND - Next.js App (Port 3000)
│   ├── 📁 src/
│   │   ├── 📁 app/                             # Next.js App Router (Pages & API Routes)
│   │   │   ├── 📁 api/                         # ⚡ Backend API Routes
│   │   │   │   ├── auth/[...nextauth]/route.ts     # NextAuth.js authentication
│   │   │   │   ├── destinations/route.ts           # Destinations API (provinces + spots mix)
│   │   │   │   ├── spots/[id]/route.ts             # Spot detail by slug
│   │   │   │   ├── listings/route.ts               # Hotels/Listings CRUD
│   │   │   │   ├── bookings/                       # Bookings management
│   │   │   │   │   ├── route.ts                    # List/Create bookings
│   │   │   │   │   └── [bookingId]/route.ts        # Update/Delete booking
│   │   │   │   ├── fpt-planner/route.ts            # Trip planner with FPT AI
│   │   │   │   ├── fpt-chat/route.ts               # FPT chat endpoint
│   │   │   │   ├── simple-chat/route.ts            # Simple chat interface
│   │   │   │   ├── trip-planner/route.ts           # Trip planning logic
│   │   │   │   ├── nlp/                            # NLP proxy endpoints
│   │   │   │   │   ├── chat/route.ts               # Chat with NLP
│   │   │   │   │   └── search/route.ts             # NLP-powered search
│   │   │   │   ├── nlp-fpt/chat/route.ts           # FPT NLP chat
│   │   │   │   ├── register/route.ts               # User registration
│   │   │   │   └── b2b/competitors/                # B2B competitor pricing
│   │   │   │       ├── route.ts
│   │   │   │       └── [id]/prices/
│   │   │   │
│   │   │   ├── 📁 destinations/                # 🗺️ Destinations Pages
│   │   │   │   ├── page.tsx                        # List all (provinces + spots with filters)
│   │   │   │   └── [slug]/page.tsx                 # Province detail (⭐ Adapter Pattern)
│   │   │   │
│   │   │   ├── 📁 spots/                       # 📍 Spots Detail Pages
│   │   │   │   └── [slug]/page.tsx                 # Spot detail (⭐ Adapter Pattern)
│   │   │   │
│   │   │   ├── 📁 listings/                    # 🏨 Listings (Hotels) Pages
│   │   │   │   └── [id]/
│   │   │   │       ├── page.tsx                    # Hotel detail page
│   │   │   │       └── ListingClient.tsx           # Client-side hotel component
│   │   │   │
│   │   │   ├── 📁 chat/                        # 💬 AI Chat Interface
│   │   │   │   └── page.tsx                        # Chatbot with Generative UI
│   │   │   │
│   │   │   ├── 📁 checkout/                    # 💳 Booking Checkout
│   │   │   │   └── [bookingId]/page.tsx            # Checkout flow
│   │   │   │
│   │   │   ├── 📁 trips/                       # ✈️ User's Trips
│   │   │   │   └── page.tsx                        # Booked trips list
│   │   │   │
│   │   │   ├── 📁 trip-planner/                # 🗓️ Trip Planning
│   │   │   │   └── page.tsx                        # Interactive trip planner
│   │   │   │
│   │   │   ├── 📁 trip-result/                 # 📋 Trip Results
│   │   │   │   └── page.tsx                        # Generated itinerary display
│   │   │   │
│   │   │   ├── 📁 search/                      # 🔍 Search Results
│   │   │   │   └── page.tsx                        # Search results page
│   │   │   │
│   │   │   ├── 📁 places/                      # 🏞️ Places Detail
│   │   │   │   └── [id]/page.tsx                   # Place detail page
│   │   │   │
│   │   │   ├── 📁 simple-chat/                 # 💭 Simple Chat
│   │   │   │   └── page.tsx                        # Basic chat interface
│   │   │   │
│   │   │   ├── page.tsx                            # 🏠 Homepage (⭐ uses Adapter Pattern)
│   │   │   ├── layout.tsx                          # Root layout with providers
│   │   │   ├── globals.css                         # Tailwind global styles
│   │   │   ├── SessionProvider.tsx                 # Auth session wrapper
│   │   │   └── favicon.ico                         # Site favicon
│   │   │
│   │   ├── 📁 components/                      # 🧩 React Components
│   │   │   ├── 📁 features/                        # Feature-specific components
│   │   │   │   ├── FeaturedDestinations.tsx        # ⭐ Unified card display (Adapter)
│   │   │   │   ├── FeaturedDestination.tsx         # Single destination card
│   │   │   │   ├── HeroSection.tsx                 # Homepage hero banner
│   │   │   │   ├── NlpSearchBox.tsx                # NLP-powered search input
│   │   │   │   ├── CallToAction.tsx                # CTA section
│   │   │   │   ├── HowItWorks.tsx                  # How it works section
│   │   │   │   ├── DestinationTabs.tsx             # Destination category tabs
│   │   │   │   ├── TripPlannerChat.tsx             # Trip planning chat UI
│   │   │   │   ├── chatbot/
│   │   │   │   │   ├── ChatWidget.tsx              # Main chatbot widget
│   │   │   │   │   └── ChatWidget.backup.tsx       # Backup version
│   │   │   │   ├── auth/
│   │   │   │   │   ├── LoginModal.tsx              # Login modal
│   │   │   │   │   └── RegisterModal.tsx           # Registration modal
│   │   │   │   └── listings/
│   │   │   │       └── CreateListingModal.tsx      # Create hotel listing modal
│   │   │   │
│   │   │   ├── 📁 shared/                          # Shared layout components
│   │   │   │   ├── Navbar.tsx                      # Navigation bar
│   │   │   │   └── Footer.tsx                      # Footer
│   │   │   │
│   │   │   └── 📁 ui/                              # Reusable UI components (shadcn/ui)
│   │   │       ├── Button.tsx                      # Button component
│   │   │       ├── Card.tsx                        # Card component
│   │   │       ├── Input.tsx                       # Form input
│   │   │       ├── Modal.tsx                       # Modal dialog
│   │   │       ├── ImageUpload.tsx                 # Image upload widget
│   │   │       └── Map.tsx                         # Map component
│   │   │
│   │   ├── 📁 lib/                             # 📚 Libraries & Utilities
│   │   │   ├── 📁 adapters/                        # ⭐ ADAPTER PATTERN (NEW)
│   │   │   │   └── destinationAdapter.ts           # Transform DB → UI CardItem
│   │   │   │       • mapProvinceToCard()           # Province → CardItem
│   │   │   │       • mapSpotToCard()               # Spot → CardItem
│   │   │   │       • normalizeImageUrl()           # Image URL helper
│   │   │   ├── db.ts                               # MongoDB connection (Mongoose)
│   │   │   ├── csvdb.ts                            # CSV database handler
│   │   │   ├── prisma.ts                           # Prisma client (legacy)
│   │   │   ├── nlp-config.ts                       # NLP configuration
│   │   │   ├── utils.ts                            # General utilities
│   │   │   ├── seed-csv.ts                         # CSV seeding utilities
│   │   │   └── providers/
│   │   │       ├── ModalProvider.tsx               # Modal context provider
│   │   │       └── ToasterProvider.tsx             # Toast notifications provider
│   │   │
│   │   ├── 📁 models/                          # 🗄️ Mongoose Models (MongoDB)
│   │   │   ├── User.ts                             # User schema
│   │   │   ├── Booking.ts                          # Booking schema
│   │   │   ├── Listing.ts                          # Listing (hotels) schema
│   │   │   └── StagingListing.ts                   # Staging data from crawlers
│   │   │
│   │   ├── 📁 types/                           # 📝 TypeScript Type Definitions (⭐ NEW)
│   │   │   ├── raw.ts                              # Database raw types (ProvinceRaw, SpotRaw)
│   │   │   └── ui.ts                               # UI interface types (CardItem, Props)
│   │   │
│   │   └── 📁 hooks/                           # 🎣 Custom React Hooks
│   │       ├── useAuth.ts                          # Authentication hook
│   │       ├── useLoginModal.ts                    # Login modal state
│   │       ├── useRegisterModal.ts                 # Register modal state
│   │       └── useListingModal.ts                  # Listing modal state
│   │
│   ├── 📁 prisma/                              # 🗃️ Prisma Schema (Legacy SQL Server)
│   │   ├── schema.prisma                           # Database schema definition
│   │   ├── seed.js                                 # Database seeding script
│   │   └── seed.ts                                 # TypeScript seeding script
│   │
│   ├── 📁 public/                              # 🖼️ Static Assets
│   │   ├── next.svg                                # Next.js logo
│   │   ├── vercel.svg                              # Vercel logo
│   │   └── *.svg                                   # Other SVG icons
│   │
│   ├── 📁 scripts/                             # 🛠️ Utility Scripts
│   │   ├── backfill-normalization.js               # Fix data normalization
│   │   └── fix_csv_images.py                       # Fix CSV image URLs
│   │
│   ├── 📁 data/                                # 💾 CSV Database Files
│   │   ├── hotels.csv                              # Hotels data
│   │   ├── bookings.csv                            # Bookings data
│   │   ├── users.csv                               # Users data
│   │   └── hotels.bak_images                       # Image backup
│   │
│   ├── package.json                                # Frontend dependencies
│   ├── tsconfig.json                               # TypeScript configuration
│   ├── next.config.ts                              # Next.js configuration
│   ├── eslint.config.mjs                           # ESLint configuration
│   ├── postcss.config.mjs                          # PostCSS configuration
│   ├── .env.local                                  # Environment variables (MongoDB URI, etc.)
│   ├── .env.example                                # Environment template
│   ├── README.md                                   # ⭐ THIS FILE
│   ├── seed-csv.js                                 # Seed CSV database
│   ├── seed-hotels.js                              # Seed hotels data
│   ├── setup-csv.ps1                               # CSV setup script
│   ├── create_database.ps1                         # Database creation script
│   ├── test-*.js                                   # Test scripts
│   └── AUTH_SETUP_COMPLETE.md                      # Auth setup documentation
│
└── 📁 python_service_fpt/                      # 🐍 PYTHON BACKEND - FastAPI NLP (Port 8001)
    ├── 📁 core/                                    # Core business logic
    │   ├── mongo_manager.py                        # MongoDB listings manager
    │   └── spots_mongo_manager.py                  # ⭐ Spots & provinces manager
    │       • get_all_provinces()                   # Query provinces_info collection
    │       • search_spots_by_province()            # Query spots_detailed collection
    │       • get_spot_detail()                     # Get single spot by slug
    │
    ├── 📁 routes/                                  # ⚡ FastAPI API Routes (⭐ Adapter Backend)
    │   ├── __init__.py                             # Routes package initialization
    │   ├── provinces.py                            # ⭐ Provinces API
    │   │   • GET /api/provinces/featured           # Featured provinces (limit=N)
    │   │   • GET /api/provinces/all                # All provinces with metadata
    │   │   • GET /api/provinces/{slug}/info        # Province detail by slug
    │   ├── spots.py                                # ⭐ Spots API
    │   │   • GET /api/spots/featured               # Top-rated spots (rating >= 4.0)
    │   │   • GET /api/spots/{spot_id}              # Spot detail by slug
    │   │   • GET /api/spots/by-province            # Spots by province (paginated)
    │   └── spots_semantic.py                       # Vector search (embeddings) - future
    │
    ├── 📁 utils/                                   # 🔧 Utility Functions
    │   ├── json_utils.py                           # JSON parsing helpers
    │   ├── normalization.py                        # Vietnamese text normalization
    │   ├── reality_check.py                        # Destination validation heuristics
    │   ├── embedding_utils.py                      # Text embedding utilities
    │   └── vector_search.py                        # Vector search utilities
    │
    ├── 📁 scripts/                                 # 🆕 Data Processing Scripts (Refactored)
    │   ├── 📁 crawling/
    │   │   └── crawl_provinces_info.py             # Crawl provinces metadata from web
    │   ├── 📁 migration/
    │   │   ├── import_provinces_from_csv.py        # Import provinces from CSV
    │   │   ├── import_spots_csv.py                 # Import spots from CSV
    │   │   └── migrate_csv_to_mongo.py             # Migrate CSV data to MongoDB
    │   ├── � seeding/
    │   │   └── seed_spots.py                       # Seed spots data to MongoDB
    │   ├── 📁 processing/
    │   │   ├── data_processor.py                   # Process staging → clean listings
    │   │   ├── embed_spots.py                      # Generate embeddings for vector search
    │   │   ├── provinces_enrich_from_csv.py        # Enrich provinces with additional data
    │   │   └── build_knowledge_base.py             # Build vector knowledge base
    │   ├── 📁 export/
    │   │   └── export_spots_to_csv.py              # Export spots data to CSV
    │   ├── 📁 maintenance/
    │   │   └── drop_listings.py                    # Drop listings collection (cleanup)
    │   └── 📁 powershell/
    │       ├── compare_api_tests.ps1               # Compare API test results
    │       ├── monitor_api_recovery.ps1            # Monitor API health recovery
    │       ├── setup_ollama_fallback.ps1           # Setup Ollama as AI fallback
    │       └── switch_ai_backend.ps1               # Switch between FPT/Ollama backends
    │
    ├── � tests/                                   # 🆕 Testing & Debugging (Refactored)
    │   ├── 📁 unit/
    │   │   ├── test_mongodb_connection.py          # Test MongoDB connection
    │   │   └── test_mongodb_ssl_workaround.py      # Test SSL certificate workaround
    │   ├── 📁 integration/
    │   │   ├── test_full_data_flow.py              # Test complete data pipeline
    │   │   └── test_spots_response.py              # Test spots API response format
    │   ├── 📁 api/
    │   │   ├── quick_test_api.py                   # Quick API endpoint test
    │   │   ├── benchmark_fpt.py                    # FPT AI API performance benchmark
    │   │   └── quick_test_region.py                # Test region-based queries
    │   ├── 📁 database/
    │   │   ├── quick_test_db.py                    # Quick database connectivity test
    │   │   ├── check_database_complete.py          # Verify database completeness
    │   │   └── check_db_connections.py             # Check all DB connection pools
    │   ├── 📁 debug/
    │   │   ├── debug_frontend_backend.py           # Debug frontend-backend integration
    │   │   ├── debug_spots_images.py               # Debug spots image URLs
    │   │   ├── debug_vector_search.py              # Debug vector search functionality
    │   │   ├── diagnose_api.py                     # API diagnostics tool
    │   │   └── main_alternative.py                 # Alternative main.py version (backup)
    │   └── 📁 analysis/
    │       ├── analyze_mongo_listings.py           # Analyze MongoDB listings data
    │       └── inspect_mongo_mapping.py            # Inspect MongoDB field mappings
    │
    ├── main.py                                     # ⭐ FastAPI Main Application (ACTIVE)
    │   • Mounts routes from routes/ package
    │   • /chat endpoint - FPT AI conversation
    │   • /health - Health check
    │   • CORS middleware for frontend
    │
    ├── requirements.txt                            # Python dependencies
    │   • fastapi, uvicorn                          # Web framework
    │   • openai                                    # FPT AI SDK
    │   • pymongo                                   # MongoDB driver
    │   • python-dotenv                             # Environment variables
    │
    ├── .env                                        # Environment variables
    │   • FPT_API_KEY                               # FPT AI API key
    │   • MONGODB_URI                               # MongoDB connection string
    │   • SPOTS_MONGODB_URI                         # Spots database URI
    │
    ├── .env.example                                # Environment template
    ├── .env.ollama_fallback                        # Ollama fallback config
    │
    └── 📄 Documentation:
        ├── README_FPT.md                           # Python service documentation
        ├── API_TESTING_GUIDE.md                    # API testing guide
        ├── API_ISSUE_DIAGNOSIS.md                  # API troubleshooting
        └── PYTHON_3_14_SSL_ISSUE.md                # Python 3.14 SSL fix
│   │   │   │   ├── 📁 listings/           # Listings (Hotels) CRUD
│   │   │   │   ├── 📁 bookings/           # Bookings management
│   │   │   │   └── 📁 fpt-planner/        # Trip planner với FPT AI
│   │   │   │       └── route.ts           # POST chat for itinerary generation
│   │   │   ├── 📁 destinations/           # Destinations Browse & Detail Pages
│   │   │   │   ├── page.tsx               # List all destinations (provinces + spots)
│   │   │   │   └── [slug]/page.tsx        # Province detail page (NEW - Adapter Pattern)
│   │   │   ├── 📁 spots/                  # Spots Detail Pages
│   │   │   │   └── [slug]/page.tsx        # Spot detail page (NEW - Adapter Pattern)
│   │   │   ├── 📁 chat/                   # AI Chat Interface
│   │   │   │   └── page.tsx               # Chatbot with Generative UI
│   │   │   ├── 📁 search/                 # Search Results Page
│   │   │   ├── 📁 listings/               # Listings Pages
│   │   │   ├── 📁 checkout/               # Booking Checkout Flow
│   │   │   ├── 📁 trips/                  # User's Booked Trips
│   │   │   ├── page.tsx                   # Homepage (uses Adapter Pattern)
│   │   │   ├── layout.tsx                 # Root layout with SessionProvider
│   │   │   └── globals.css                # Tailwind global styles
│   │   │
│   │   ├── 📁 components/                 # React Components
│   │   │   ├── 📁 features/               # Feature-specific components
│   │   │   │   ├── FeaturedDestinations.tsx  # ⭐ Unified Card Display (Adapter Pattern)
│   │   │   │   ├── HeroSection.tsx        # Homepage hero banner
│   │   │   │   ├── NlpSearchBox.tsx       # NLP-powered search input
│   │   │   │   └── chatbot/               # Chatbot components with Generative UI
│   │   │   ├── 📁 ui/                     # Reusable UI components (shadcn/ui)
│   │   │   │   ├── Button.tsx             # Button component
│   │   │   │   ├── Card.tsx               # Card component
│   │   │   │   └── Input.tsx              # Form inputs
│   │   │   └── 📁 shared/                 # Shared utilities components
│   │   │
│   │   ├── 📁 lib/                        # Libraries & Utilities
│   │   │   ├── 📁 adapters/               # ⭐ ADAPTER PATTERN (NEW)
│   │   │   │   └── destinationAdapter.ts  # Transform DB data → UI CardItem
│   │   │   │       • mapProvinceToCard()  # Province → CardItem
│   │   │   │       • mapSpotToCard()      # Spot → CardItem
│   │   │   │       • normalizeImageUrl()  # Image URL helper
│   │   │   ├── db.ts                      # MongoDB connection (Mongoose)
│   │   │   └── utils.ts                   # General utility functions
│   │   │
│   │   ├── 📁 types/                      # ⭐ TypeScript Type Definitions (NEW)
│   │   │   ├── raw.ts                     # Database raw types (ProvinceRaw, SpotRaw)
│   │   │   └── ui.ts                      # UI interface types (CardItem, Props)
│   │   │
│   │   ├── 📁 models/                     # Mongoose Models (MongoDB)
│   │   │   ├── User.ts                    # User schema
│   │   │   ├── Booking.ts                 # Booking schema
│   │   │   ├── Listing.ts                 # Listing (hotels) schema
│   │   │   └── StagingListing.ts          # Staging data from crawlers
│   │   │
│   │   └── 📁 hooks/                      # Custom React Hooks
│   │       └── useAuth.ts                 # Authentication hook
│   │
│   ├── 📁 public/                         # Static assets (images, icons)
│   ├── 📁 prisma/                         # Prisma schema (legacy SQL Server)
│   ├── package.json                       # Frontend dependencies
│   ├── tsconfig.json                      # TypeScript config
│   ├── next.config.ts                     # Next.js configuration
│   ├── .env.local                         # Environment variables (MongoDB URI, API keys)
│   └── README.md                          # Frontend documentation
│
├── 📁 python_service_fpt/                 # 🐍 PYTHON BACKEND - FastAPI NLP Service (Port 8001)
│   ├── 📁 core/                           # Core business logic
│   │   ├── mongo_manager.py               # MongoDB listings manager
│   │   └── spots_mongo_manager.py         # ⭐ MongoDB spots & provinces manager
│   │       • get_all_provinces()          # Query provinces_info collection
│   │       • search_spots_by_province()   # Query spots_detailed collection
│   │       • get_spot_detail()            # Get single spot by slug
│   │
│   ├── 📁 routes/                         # ⭐ FastAPI API Routes (NEW - Adapter Pattern Backend)
│   │   ├── __init__.py                    # Routes package init
│   │   ├── provinces.py                   # Provinces API endpoints
│   │   │   • GET /api/provinces/featured  # Get featured provinces (limit=N)
│   │   │   • GET /api/provinces/all       # Get all provinces with metadata
│   │   │   • GET /api/provinces/{slug}/info  # Get province detail by slug
│   │   ├── spots.py                       # Spots API endpoints
│   │   │   • GET /api/spots/featured      # Get top-rated spots (rating >= 4.0)
│   │   │   • GET /api/spots/{spot_id}     # Get spot detail by slug
│   │   │   • GET /api/spots/by-province   # List spots by province with pagination
│   │   └── spots_semantic.py              # Vector search (embeddings) - placeholder
│   │
│   ├── 📁 utils/                          # Utility functions
│   │   ├── json_utils.py                  # JSON parsing helpers
│   │   ├── normalization.py               # Vietnamese text normalization
│   │   ├── reality_check.py               # Destination validation heuristics
│   │   └── embedding_utils.py             # Text embedding utilities (for semantic search)
│   │
│   ├── main.py                            # ⭐ FastAPI main application (ACTIVE)
│   │   • Mounts routes from routes/ package
│   │   • /chat endpoint - FPT AI conversation
│   │   • /health - Health check
│   │   • CORS middleware for frontend communication
│   │
│   ├── main1.py                           # Alternative main (testing purposes)
│   ├── seed_spots.py                      # Seed spots data to MongoDB
│   ├── crawl_provinces_info.py            # Crawl provinces metadata
│   ├── data_processor.py                  # Process staging → clean listings
│   ├── embed_spots.py                     # Generate embeddings for vector search
│   ├── requirements.txt                   # Python dependencies
│   │   • fastapi, uvicorn                 # Web framework
│   │   • openai                           # FPT AI SDK
│   │   • pymongo                          # MongoDB driver
│   │   • python-dotenv                    # Environment variables
│   ├── .env                               # Environment variables
│   │   • FPT_API_KEY                      # FPT AI API key
│   │   • MONGODB_URI                      # MongoDB connection string
│   │   • SPOTS_MONGODB_URI                # Spots database URI
│   └── README_FPT.md                      # Python service documentation
│
├── 📁 MyDataCrawler/                      # 🕷️ WEB CRAWLER - Selenium-based data collection
│   ├── crawler_selenium.py                # Main crawler for hotels (VnTrip)
│   ├── crawl_provinces_gody.py            # Crawl provinces from Gody.vn
│   ├── requirements.txt                   # Crawler dependencies (selenium, pandas)
│   └── run_hotels_selenium.bat            # Batch script to run crawler
│
├── 📁 python_service/                     # 🐍 LEGACY Python Service (Ollama - Port 8000)
│   └── ...                                # (Not actively used, kept for reference)
│
├── 📄 Documentation Files:                # 📚 PROJECT DOCUMENTATION
│   ├── ADAPTER_PATTERN_GUIDE.md           # ⭐ Complete Adapter Pattern implementation guide
│   ├── ADAPTER_IMPLEMENTATION_SUMMARY.md  # Executive summary of adapter pattern
│   ├── ADAPTER_TESTING_CHECKLIST.md       # Testing procedures for adapter pattern
│   ├── ADAPTER_QUICK_REFERENCE.md         # Quick reference cheat sheet
│   ├── ADAPTER_COMPLETION.md              # Implementation completion report
│   ├── ADAPTER_VISUAL_ARCHITECTURE.md     # Architecture diagrams & visual guides
│   ├── MONGODB_MIGRATION_GUIDE.md         # MongoDB setup & migration guide
│   ├── DATABASE_IMAGES_FIXED.md           # Database image display fixes
│   ├── SETUP_QUICK.md                     # Quick setup guide (< 5 minutes)
│   ├── START_GUIDE.md                     # Detailed startup guide
│   ├── README_QUICKSTART.md               # Quickstart documentation
│   ├── dev_readme.md                      # Developer guide overview
│   └── DOCS_INDEX.md                      # Documentation index
│
├── 📄 Scripts:                            # 🛠️ AUTOMATION SCRIPTS
│   ├── start_servers.ps1                  # Start both backend + frontend servers
│   ├── check_environment.ps1              # Verify Python, Node.js, MongoDB installation
│   ├── install_mongodb.ps1                # MongoDB installation helper
│   └── create_minimal_version.ps1         # Create minimal version of project
│
├── .gitignore                             # Git ignore rules
├── .gitattributes                         # Git attributes
└── README.md                              # ⭐ THIS FILE - Main project documentation
├─ .vscode/                    # Cấu hình VSCode (debug, settings)
│  ├─ launch.json             # Debug cấu hình
│  ├─ c_cpp_properties.json   # Cấu hình C/C++ (không trọng tâm dự án này)
│  └─ settings.json           # Workspace settings
├─ Backend/                    # Thư mục backend cũ / cấu hình DB
│  ├─ package.json            # Scripts/deps cho backend tách rời (nếu dùng)
│  ├─ package-lock.json
│  ├─ README_CONNECTION.md    # Hướng dẫn kết nối DB
│  ├─ SETUP_SQLITE.md         # Hướng dẫn SQLite (dev thử nghiệm)
│  ├─ SETUP_SQLSERVER.md      # Hướng dẫn SQL Server
│  ├─ enable-mixed-mode.ps1   # Script bật mixed-mode auth SQL Server
│  ├─ prisma.config.ts.bak    # Backup cấu hình prisma
│  └─ prisma/
│     └─ schema.prisma        # Schema Prisma (models đầy đủ ở phiên bản backend)
├─ my-travel-app/              # Frontend Next.js + API routes (App Router)
│  ├─ package.json            # Scripts: dev/build/start + deps (next, tailwind...)
│  ├─ package-lock.json
│  ├─ README.md               # (File hiện tại) Tài liệu dự án
│  ├─ AUTH_SETUP_COMPLETE.md  # Ghi chú setup xác thực
│  ├─ tsconfig.json           # TypeScript config
│  ├─ next.config.ts          # Cấu hình Next (images, experimental...)
│  ├─ postcss.config.mjs      # Cấu hình PostCSS/Tailwind
│  ├─ eslint.config.mjs       # Cấu hình ESLint
│  ├─ .gitignore
│  ├─ prisma/
│  │  ├─ schema.prisma        # Schema Prisma dùng ở phần frontend dev
│  │  ├─ seed.ts              # Seed dữ liệu demo (TypeScript)
│  │  └─ seed.js              # Seed JS (fallback)
│  ├─ public/                 # Static assets (svg, favicon...)
│  │  ├─ globe.svg
│  │  ├─ next.svg
│  │  ├─ vercel.svg
│  │  ├─ file.svg
│  │  ├─ window.svg
│  │  └─ favicon.ico
│  └─ src/
│     ├─ app/                 # App Router pages + API routes
│     │  ├─ layout.tsx        # Root layout (Navbar/Footer/Providers)
│     │  ├─ page.tsx          # Trang chủ (Hero + Search + Featured)
│     │  ├─ globals.css       # Global styles (Tailwind base)
│     │  ├─ SessionProvider.tsx # Provider cho phiên next-auth
│     │  ├─ favicon.ico
│     │  ├─ destinations/
│     │  │  ├─ page.tsx       # Danh sách Destinations
│     │  │  └─ [id]/page.tsx  # Chi tiết Destination (tabs Places/Tours/Itineraries)
│     │  ├─ places/
│     │  │  └─ [id]/page.tsx  # Chi tiết Place (HOTEL/ATTRACTION...)
│     │  ├─ listings/
│     │  │  ├─ [id]/page.tsx  # Server component fetch Listing theo id
│     │  │  └─ [id]/ListingClient.tsx # Client UI (badge Crawled, booking)
│     │  ├─ search/page.tsx   # Trang search (hiển thị kết quả)
│     │  ├─ trips/page.tsx    # Trang trips (danh sách bookings của user)
│     │  ├─ checkout/[bookingId]/page.tsx # Trang checkout thanh toán demo
│     │  └─ api/              # Route handlers (serverless)
│     │     ├─ auth/[...nextauth]/route.ts      # Auth provider NextAuth
│     │     ├─ register/route.ts                # Đăng ký user
│     │     ├─ listings/route.ts                # CRUD Listings
│     │     ├─ bookings/route.ts                # Tạo booking
│     │     ├─ bookings/[bookingId]/route.ts    # Patch/GET booking
│     │     ├─ nlp/search/route.ts              # Proxy NLP search
│     │     └─ nlp/chat/route.ts                # Proxy NLP chat
│     ├─ components/
│     │  ├─ shared/            # Thành phần dùng chung layout
│     │  │  ├─ Navbar.tsx      # Điều hướng, triggers login/register
│     │  │  └─ Footer.tsx      # Footer
│     │  ├─ ui/                # Atomic UI components
│     │  │  ├─ Button.tsx
│     │  │  ├─ Card.tsx
│     │  │  ├─ Input.tsx
│     │  │  ├─ ImageUpload.tsx # Upload ảnh (Cloud/Local)
│     │  │  ├─ Map.tsx         # Google Maps hiển thị marker
│     │  │  └─ Modal.tsx       # Modal base
│     │  ├─ features/          # Khối tính năng cao cấp
│     │  │  ├─ HeroSection.tsx
│     │  │  ├─ NlpSearchBox.tsx    # Gửi câu hỏi NLP
│     │  │  ├─ FeaturedDestinations.tsx # Danh sách Listing/Destination hiển thị
│     │  │  ├─ FeaturedDestination.tsx  # Card đơn lẻ
│     │  │  ├─ DestinationTabs.tsx      # Tabs trong trang Destination
│     │  │  ├─ HowItWorks.tsx
│     │  │  ├─ CallToAction.tsx
│     │  │  ├─ chatbot/ChatWidget.tsx   # Widget chat realtime
│     │  │  ├─ auth/LoginModal.tsx      # Modal đăng nhập
│     │  │  ├─ auth/RegisterModal.tsx   # Modal đăng ký
│     │  │  └─ listings/CreateListingModal.tsx # Tạo Listing mới
│     ├─ hooks/               # Custom hooks (UI state)
│     │  ├─ useLoginModal.ts
│     │  ├─ useRegisterModal.ts
│     │  └─ useListingModal.ts
│     ├─ lib/
│     │  ├─ prisma.ts         # Prisma client singleton (SSR/API)
│     │  ├─ utils.ts          # Helper (format giá, ngày...)
│     │  └─ providers/
│     │     ├─ ModalProvider.tsx  # Context/modal root
│     │     └─ ToasterProvider.tsx# Toast notifications
├─ python_service/             # Dịch vụ Python: NLP + crawler + xử lý dữ liệu
│  ├─ requirements.txt        # Danh sách dependencies Python
│  ├─ README_MODELS.md        # Ghi chú models Ollama cần pull
│  ├─ main.py                 # FastAPI app (endpoints NLP / health)
│  ├─ nlp_utils.py            # Hỗ trợ prompt, intent parsing
│  ├─ text_utils.py           # Làm sạch tiếng Việt (ftfy + heuristics)
│  ├─ crawler_main.py         # Entry chạy crawler Selenium
│  ├─ data_processor.py       # Xử lý staging → Listing
│  ├─ reprocess_text.py       # Sửa lại text đã lưu (retroactive fix)
│  ├─ test_simple.py          # Test đơn giản cho utils
│  ├─ test_db_manager.py      # Kiểm tra logic DB staging merge
│  ├─ configs/
│  │  └─ targets.json         # Khai báo targets crawl (selectors, category)
│  └─ core/
│     ├─ __init__.py
│     ├─ crawler_engine.py    # Logic selenium scroll, extract, build record
│     └─ db_manager.py        # MERGE / upsert vào StagingListing
└─ (Caches & __pycache__)      # Các file biên dịch Python (bỏ qua)
```

Ghi chú: Cấu trúc trên phản ánh vai trò từng phần trong pipeline tổng thể; nếu tái cấu trúc, nên giữ phân tách: `my-travel-app` (UI+API) và `python_service` (crawl + NLP) để dễ triển khai/horizontally scale.


---
## 3. Công nghệ sử dụng
- **Next.js 16 / App Router** – SSR + file-based routing
- **TypeScript** – type safety
- **TailwindCSS 4** – styling nhanh
- **Prisma 6.19 (SQL Server provider)** – ORM + schema
- **FastAPI** – dịch vụ NLP & xử lý AI
- **Ollama (llama3 / vinallama)** – LLM cục bộ
- **Selenium + webdriver-manager** – crawl trang Vntrip
- **SQLAlchemy + pyodbc** – kết nối SQL Server trong Python
- **charset-normalizer + ftfy** – sửa lỗi encoding, mojibake
- **Google Maps (@react-google-maps/api)** – hiển thị bản đồ
- **NextAuth** – xác thực email/password (demo)

---
## 4. Prisma Schema – Các Model chính
| Model | Vai trò |
|-------|---------|
| `User` | Người dùng (đăng nhập / sở hữu listing) |
| `Listing` | Khách sạn / điểm lưu trú (giá, vị trí, lat/lng, sourceUrl) |
| `Booking` | Đặt phòng (startDate, endDate, status: PENDING/PAID) |
| `Destination` | Thành phố / vùng du lịch |
| `Place` | Địa điểm cụ thể: HOTEL / RESTAURANT / ATTRACTION |
| `Tour` | Tour trọn gói theo Destination |
| `Itinerary` | Lịch trình (nhiều ngày) |
| `ItineraryItem` | Mục chi tiết trong lịch trình (day/time/place) |
| `StagingListing` | Bảng staging dữ liệu thô crawl (rawJson, category, status) |

`sourceUrl` trong `Listing` (nullable) giúp tránh trùng dữ liệu crawl; khi đã sạch có thể thêm UNIQUE sau.

---
## 5. Tính năng Frontend chính
### 5.1 Trang chủ
- HeroSection, NLP Search Box, Featured Destinations (hiển thị Listings mới nhất – badge "Crawled" nếu có `sourceUrl`).

### 5.2 Chi tiết Listing
- Hiển thị ảnh, mô tả, bản đồ, tính tổng giá theo ngày chọn.
- Tạo Booking → chuyển sang trang Checkout.

### 5.3 Checkout & Trips
- Checkout tạo mã giả lập / QR (demo) → PATCH Booking status → chuyển `PAID`.
- Trang `Trips` liệt kê các đặt phòng của user.

### 5.4 Destinations / Places / Tours / Itineraries
- Trang danh sách Destinations.
- Trang chi tiết Destination với tab Place (HOTEL/RESTAURANT/ATTRACTION), Tours, Itineraries.
- Trang chi tiết Place.

### 5.5 NLP Search / Chat
- Search Box gọi `/api/nlp/search`/`/api/nlp/chat` proxy → Python NLP.
- Phân loại intent: chat vs search, trích xuất location/price/keywords.

---
## 6. NLP Service (FastAPI + Ollama)
### Endpoints
| Endpoint | Mô tả |
|----------|-------|
| `POST /analyze` | Trích xuất `location`, `price_max`, `keywords` từ câu người dùng |
| `POST /chat` | Phân loại intent + trả về câu trả lời hoặc search_params |
| `GET /healthz` | Kiểm tra kết nối Ollama |
| `GET /models` | Liệt kê models Ollama |

### Ví dụ `POST /chat`
```jsonc
{
	"message": "tìm ks da lat duoi 2tr view dep"
}
// →
{
	"type": "search",
	"reply": "Mình sẽ tìm một số lựa chọn phù hợp.",
	"search_params": {
		"location": "Đà Lạt",
		"price_max": 2000000,
		"keywords": "view đẹp"
	}
}
```
Fallback heuristic hoạt động nếu Ollama chưa cài hoặc offline.

---
## 7. Crawler & Pipeline
### Files chính (`python_service`)
| File | Vai trò |
|------|---------|
| `configs/targets.json` | Định nghĩa target crawl (selector, category) |
| `core/crawler_engine.py` | Selenium lấy dữ liệu theo selectors |
| `core/db_manager.py` | Lưu batch vào bảng `StagingListing` (MERGE) |
| `crawler_main.py` | Entry chạy crawler |
| `data_processor.py` | Chuyển từ Staging (PENDING) → Listing (PROCESSED) |
| `text_utils.py` | Làm sạch tiếng Việt (encoding + ftfy + heuristic) |
| `reprocess_text.py` | Sửa dữ liệu cũ (Listing + StagingListing) |

### Dòng chảy
1. `python crawler_main.py` → thêm các bản ghi vào `StagingListing`.
2. `python data_processor.py` → chuẩn hoá title/location/price → chèn vào `Listing`.
3. `python reprocess_text.py` (tuỳ chọn) → sửa lỗi font, mojibake.

### StagingListing.status
- `PENDING`: chờ xử lý.
- `PROCESSED`: đã chuyển sang Listing.
- `ERROR`: lỗi parse / dữ liệu thiếu.

---
## 8. Làm sạch tiếng Việt
Sử dụng:
- `charset-normalizer` phát hiện encoding.
- `ftfy.fix_text` sửa mojibake.
- `html.unescape` giải mã entity.
- `unicodedata.normalize("NFC")` chuẩn hoá Unicode.
- Heuristic map sửa mẫu: `Khách s?n` → `Khách sạn`, `Bi?n` → `Biển`...

Muốn mở rộng: chỉnh `HEURISTIC_MAP` trong `text_utils.py` rồi chạy lại `reprocess_text.py`.

---
## 9. Cài đặt & Chạy (Windows PowerShell)
### 9.1 Frontend & API (Next.js)
```powershell
cd C:\Users\ASUS\SinhVienCNhan\Tour_with_NLP\Tour_with_NLP\my-travel-app
npm install
npx -y prisma@6.19.0 generate
npm run dev   # http://localhost:3000
```

### 9.2 Python NLP Service
```powershell
cd C:\Users\ASUS\SinhVienCNhan\Tour_with_NLP\Tour_with_NLP\python_service
python -m venv .venv
./.venv/Scripts/Activate.ps1
pip install -r requirements.txt
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
# Kiểm tra
Invoke-RestMethod http://127.0.0.1:8000/healthz -UseBasicParsing | ConvertTo-Json -Depth 5
```

### 9.3 Ollama (đã cài)
```powershell
ollama --version
ollama pull llama3:8b
Invoke-RestMethod http://127.0.0.1:11434/api/tags -UseBasicParsing | ConvertTo-Json -Depth 5
```

### 9.4 Crawler
```powershell
cd C:\Users\ASUS\SinhVienCNhan\Tour_with_NLP\Tour_with_NLP\python_service
python crawler_main.py
python data_processor.py
python reprocess_text.py  # tùy chọn làm sạch lại
```

### 9.5 Seed dữ liệu demo (Listings ban đầu)
```powershell
cd C:\Users\ASUS\SinhVienCNhan\Tour_with_NLP\Tour_with_NLP\my-travel-app
node prisma/seed.js
```

### 9.6 Query nhanh kiểm tra
```sql
SELECT TOP 5 title, price, sourceUrl FROM Listing ORDER BY createdAt DESC;
SELECT status, COUNT(*) FROM StagingListing GROUP BY status;
```

---
## 10. Biến môi trường quan trọng
| File | Biến |
|------|------|
| `.env.local` (Next.js) | `DATABASE_URL`, `NEXTAUTH_SECRET`, `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` |
| `python_service/.env` (tuỳ chọn) | `OLLAMA_BASE_URL`, `OLLAMA_MODEL` |

`DATABASE_URL` dùng SQL Server Express: ví dụ:
```
sqlserver://localhost:1433;database=nlp_travel_db;instanceName=SQLEXPRESS;encrypt=DANGER_PLAINTEXT
```

---
## 11. Xử lý ảnh từ nguồn bên ngoài
`next.config.ts` đã cấu hình `images.remotePatterns` cho:
`images.unsplash.com`, `res.cloudinary.com`, `upload.wikimedia.org`, `picsum.photos`, `placehold.co`, `source.unsplash.com`, `i.vntrip.vn`, `statics.vntrip.vn`.

Nếu thêm domain khác: bổ sung vào mảng `remotePatterns` rồi restart dev server.

---
## 12. Checkout & Booking Flow (Tóm tắt)
1. Người dùng chọn ngày tại trang Listing.
2. POST `/api/bookings` tạo bản ghi với `status=PENDING`.
3. Trang `/checkout/[bookingId]` hiển thị mã giả lập thanh toán.
4. PATCH `/api/bookings/[bookingId]` → `status=PAID`.
5. Trang `Trips` hiển thị các bookings đã thanh toán.

---
## 13. Troubleshooting
| Vấn đề | Nguyên nhân | Cách xử lý |
|--------|-------------|-----------|
| Lỗi font tiếng Việt | Sai encoding / mojibake | Dùng `clean_vietnamese_text`, chạy `reprocess_text.py` |
| `EPERM rename query_engine-windows.dll.node` | File lock do process node chạy | Dừng dev server, chạy lại `npx prisma generate` |
| 404 ảnh Vntrip | Domain chưa khai báo | Thêm `i.vntrip.vn`, `statics.vntrip.vn` vào `next.config.ts` |
| Ollama health `ollama:false` | Chưa cài / daemon chưa chạy | Cài Ollama, pull model, kiểm tra `11434/api/tags` |
| Unicode dấu hỏi `?` | Mất ký tự do nhiều lần decode | Thêm heuristic map hoặc kiểm tra meta charset trang nguồn |

---
## 14. Roadmap đề xuất
- Chuẩn hoá `Place` ingest thay vì đưa vào `Listing`.
- Thêm pipeline tự động định kỳ (scheduler).
- Gợi ý lịch trình tự động (LLM) → lưu thành `Itinerary`.
- Chuẩn hoá địa danh bằng bảng mapping (HCM → Hồ Chí Minh, HN → Hà Nội…).
- Thêm kiểm thử tự động (Jest + playwright cho crawler headless).
- Thêm phân trang & bộ lọc nâng cao (giá min/max, địa điểm).
- Tích hợp geocoding khi tạo Listing (Google Geocoding API).

---
## 15. Bảo mật & Lưu ý
- Dữ liệu crawl chỉ sử dụng học tập – không thương mại.
- LLM chạy cục bộ (Ollama) – tránh gửi dữ liệu nhạy cảm lên cloud.
- Kiểm tra license / robots.txt nếu mở rộng nhiều nguồn khác.
- Thêm rate limit cho API `/api/nlp/*` nếu public.

---
## 16. Đóng góp / Phát triển thêm
Clone, tạo branch, mở PR. Kiểm tra trước khi commit:
```powershell
npm run lint
npm run build
```
Python: chạy test thủ công hoặc thêm pytest.

---
## 17. Ví dụ kiểm thử nhanh NLP
```powershell
Invoke-RestMethod -Uri 'http://127.0.0.1:8000/analyze' -Method Post -ContentType 'application/json' -Body '{"text":"ks đà lạt 2 củ view đẹp"}'
Invoke-RestMethod -Uri 'http://127.0.0.1:8000/chat' -Method Post -ContentType 'application/json' -Body '{"message":"tìm ks da lat duoi 2tr view dep"}'
```

---
## 18. Ghi chú thêm
- Một số field (`sourceUrl`) chưa unique để tránh migration fail với dữ liệu cũ. Có thể thêm UNIQUE sau khi dọn sạch.
- Heuristics tiếng Việt nên được mở rộng dần theo log.
- Có thể refactor xử lý font sang job nền để không chặn pipeline.

---
## 19. Giấy phép
Project phục vụ học tập, không tích hợp license cụ thể. Khi dùng lại vui lòng kiểm tra license của data nguồn & models (Ollama models).

---
**Chúc bạn khám phá & mở rộng dự án thuận lợi!**
