# -*- coding: utf-8 -*-
"""
Intent Extractor - NLU component using FPT AI
Extracts intent, entities, and constraints from user queries
"""

import re
from typing import Dict, Any, Optional
from dataclasses import dataclass, field, asdict
from app.core import logger


@dataclass
class ExtractedIntent:
    """Structured extraction result"""

    intent: str  # plan_trip, find_spot, find_hotel, find_food, general_qa
    mode: str = "traveler"  # traveler, business
    location: Optional[str] = None
    duration: Optional[int] = None  # days
    budget: Optional[int] = None  # VND
    budget_level: Optional[str] = None  # tiết kiệm, trung bình, sang trọng
    people_count: int = 1
    companion_type: Optional[str] = None  # solo, couple, family, friends, business
    accommodation: str = "required"  # required, optional, none
    interests: list = field(default_factory=list)
    keywords: list = field(default_factory=list)
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class IntentExtractor:
    """
    Intent Extractor using FPT AI (Saola 3.1)
    Fallback to regex-based extraction if LLM fails
    """

    # Common Vietnamese cities/provinces
    KNOWN_LOCATIONS = [
        "Hà Nội",
        "Hồ Chí Minh",
        "Đà Nẵng",
        "Huế",
        "Nha Trang",
        "Đà Lạt",
        "Hội An",
        "Phú Quốc",
        "Sapa",
        "Hạ Long",
        "Vũng Tàu",
        "Phan Thiết",
        "Mũi Né",
        "Cần Thơ",
        "Ninh Bình",
        "Quy Nhơn",
        "Bình Định",
        "Quảng Ninh",
        "Lào Cai",
        "Kiên Giang",
        "Thừa Thiên Huế",
        "Khánh Hòa",
        "Lâm Đồng",
        "Bà Rịa Vũng Tàu",
    ]

    # Intent keywords - CRITICAL: Separate "show" from "plan" to avoid conflict
    # FIX #1: BOOKING MUST BE CHECKED BEFORE SEARCH to avoid "khách sạn" false match
    INTENT_PATTERNS = {
        # HIGHEST PRIORITY: Read-only intents (viewing existing data)
        "show_itinerary": [
            "xem lại",
            "xem lai",
            "hiển thị lịch trình",
            "hien thi lich trinh",
            "lịch trình của tôi",
            "lich trinh cua toi",
            "lịch trình đã tạo",
            "lich trinh da tao",
            "cho tôi xem",
            "cho toi xem",
            "lịch trình hiện có",
            "lich trinh hien co",
            # FIX 2026-01-18: Add patterns for asking about selected spots
            "địa điểm sẽ đến",
            "dia diem se den",
            "địa điểm đã chọn",
            "dia diem da chon",
            "các địa điểm",
            "cac dia diem",
            "những điểm đến",
            "nhung diem den",
            "thông tin địa điểm",
            "thong tin dia diem",
            "cho tôi thông tin",
            "cho toi thong tin",
        ],
        "calculate_cost": [
            "tính tiền",
            "tinh tien",
            "chi phí",
            "chi phi",
            "bao nhiêu tiền",
            "bao nhieu tien",
            "số tiền",
            "so tien",
            "giá bao nhiêu",
            "gia bao nhieu",
            "tổng cộng",
            "tong cong",
            "ước tính chi phí",
            "uoc tinh chi phi",
            "estimate",
            "lập budget",
            "lap budget",
            "lập chi phí",
            "lap chi phi",
            "budget",
        ],
        # FIX A: Update people count intent - MUST BE BEFORE calculate_cost patterns
        # Triggers recalculation when user changes number of people in COST_ESTIMATION state
        "update_people_count": [
            "người thì sao",
            "nguoi thi sao",
            "nếu có",
            "neu co",
            "tính cho",
            "tinh cho",
            "đổi số người",
            "doi so nguoi",
            "thay đổi số người",
            "thay doi so nguoi",
            "với số người",
            "voi so nguoi",
            "người đi",
            "nguoi di",
            "thành viên",
            "thanh vien",
            "người tham gia",
            "nguoi tham gia",
        ],
        # FIX C: Place details intent - MUST BE BEFORE tips/general_info
        # Returns detailed info about a specific place (vs tips which returns advice)
        "get_place_details": [
            "chi tiết về",
            "chi tiet ve",
            "giới thiệu về",
            "gioi thieu ve",
            "thông tin về",
            "thong tin ve",
            "cho tôi biết về",
            "cho toi biet ve",
            "kể về",
            "ke ve",
            "mô tả",
            "mo ta",
            "nói về",
            "noi ve",
            "địa điểm này",
            "dia diem nay",
            "chỗ này",
            "cho nay",
        ],
        # FIX #2: Tips/advice intent (must be checked before general_info)
        "get_location_tips": [
            "lưu ý",
            "luu y",
            "kinh nghiệm",
            "kinh nghiem",
            "tips",
            "có gì cần biết",
            "co gi can biet",
            "nên biết",
            "nen biet",
            "chú ý",
            "chu y",
            "khuyến cáo",
            "khuyen cao",
            "mẹo",
            "meo",
            "điều cần lưu ý",
            "dieu can luu y",
        ],
        # CRITICAL: Booking intents BEFORE search intents (FIX #1)
        "book_hotel": [
            "đặt phòng",
            "dat phong",
            "book",
            "đặt chỗ",
            "dat cho",
            "thuê phòng",
            "thue phong",
            "reserve",
            "booking",
        ],
        # MEDIUM PRIORITY: Action intents (creating/modifying data)
        "plan_trip": [
            "lên lịch trình",
            "len lich trinh",
            "lập lịch trình",
            "lap lich trinh",
            "tạo lịch trình",
            "tao lich trinh",
            "kế hoạch mới",
            "ke hoach moi",
            "tạo tour",
            "tao tour",
            "bắt đầu lên kế hoạch",
            "bat dau len ke hoach",
        ],
        "find_hotel": [
            "khách sạn",
            "khach san",
            "hotel",
            "resort",
            "homestay",
            "chỗ ở",
            "cho o",
            "nghỉ",
            "nghi",
            "lưu trú",
            "luu tru",
            "tìm khách sạn",
            "tim khach san",
        ],
        "find_food": [
            "ăn",
            "an",
            "quán",
            "quan",
            "nhà hàng",
            "nha hang",
            "món",
            "mon",
            "bún",
            "bun",
            "phở",
            "pho",
            "cơm",
            "com",
            "bánh",
            "banh",
            "hải sản",
            "hai san",
            "ẩm thực",
            "am thuc",
            "đặc sản",
            "dac san",
        ],
        "find_spot": [
            "địa điểm",
            "dia diem",
            "chỗ nào",
            "cho nao",
            "ở đâu",
            "o dau",
            "tham quan",
            "check-in",
            "chụp ảnh",
            "chup anh",
            "cảnh đẹp",
            "canh dep",
            "đi chơi",
            "di choi",
        ],
        # LOW PRIORITY: Social intents
        "greeting": ["xin chào", "hello", "hi", "chào", "hey"],
        "farewell": ["tạm biệt", "bye", "goodbye", "hẹn gặp lại"],
        "thanks": ["cảm ơn", "thank", "thanks"],
        "chitchat": [],  # Catch-all for non-travel queries
        # MORE requests
        "more_spots": [
            "còn địa điểm",
            "thêm địa điểm",
            "địa điểm khác",
            "chỗ khác",
            "điểm khác",
            "gợi ý thêm địa điểm",
            "còn chỗ nào",
            "con dia diem",
            "them dia diem",
            "cho khac",
        ],
        "more_hotels": [
            "còn khách sạn",
            "thêm khách sạn",
            "khách sạn khác",
            "hotel khác",
            "chỗ nghỉ khác",
            "gợi ý thêm khách sạn",
            "con khach san",
            "them khach san",
        ],
        "more_food": [
            "còn quán",
            "thêm quán",
            "quán khác",
            "nhà hàng khác",
            "món khác",
            "ăn gì khác",
            "gợi ý thêm quán",
            "con quan",
            "them quan",
        ],
    }

    # Patterns to detect generic "more" requests that need context mapping
    MORE_PATTERNS = [
        r"còn.*(?:gì|nào).*không",  # "còn gì khác không", "còn chỗ nào không"
        r"con.*(?:gi|nao).*khong",  # non-accent version
        r"thêm.*(?:không|đi|nữa)",  # "thêm nữa không", "thêm đi"
        r"them.*(?:khong|di|nua)",  # non-accent version
        r"gợi ý thêm",  # "gợi ý thêm"
        r"goi y them",  # non-accent
        r"(?:có|còn).*khác.*không",  # "có gì khác không"
        r"(?:co|con).*khac.*khong",  # non-accent
    ]

    # Off-topic/rude patterns to detect chitchat
    OFFTOPIC_PATTERNS = [
        r"mày",
        r"tao",
        r"biết gì",
        r"ngu",
        r"stupid",
        r"giới thiệu",
        r"bạn là ai",
        r"ai vậy",
        r"làm gì",
    ]

    # Budget patterns
    BUDGET_PATTERNS = {
        "tiết kiệm": ["tiết kiệm", "rẻ", "thấp", "bình dân", "backpacker"],
        "trung bình": ["trung bình", "vừa", "hợp lý"],
        "sang trọng": ["sang", "cao cấp", "luxury", "5 sao", "resort"],
    }

    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        logger.info("✅ IntentExtractor initialized")

    def _is_booking_request(self, query_lower: str) -> bool:
        """
        FIX #1: Compound detection for booking requests
        Detects booking intent when BOTH booking phrases AND hotel references exist
        Example: "đặt phòng tại Khách sạn Dragon Sea"
        """
        booking_phrases = [
            "đặt phòng",
            "dat phong",
            "book",
            "đặt chỗ",
            "dat cho",
            "thuê phòng",
            "thue phong",
            "reserve",
            "booking",
        ]
        hotel_words = [
            "khách sạn",
            "khach san",
            "hotel",
            "resort",
            "homestay",
            "khu nghỉ dưỡng",
            "khu nghi duong",
        ]

        has_booking = any(phrase in query_lower for phrase in booking_phrases)
        has_hotel = any(word in query_lower for word in hotel_words)

        if has_booking and has_hotel:
            logger.info(
                f"[FIX #1] 🎯 Compound booking detected: booking_phrase=True + hotel_reference=True"
            )
            return True
        return False

    def _is_budget_calculation_request(self, query_lower: str) -> bool:
        """
        FIX #3: Compound detection for budget/cost calculation
        Detects when user asks about budget/cost, NOT creating new plan
        Example: "lập budget hiện tại" should be calculate_cost, NOT plan_trip
        """
        # Strong indicators of cost calculation (not planning)
        budget_phrases = [
            "lập budget",
            "lap budget",
            "lập chi phí",
            "lap chi phi",
            "tính budget",
            "tinh budget",
        ]
        cost_phrases = [
            "tính tiền",
            "tinh tien",
            "chi phí",
            "chi phi",
            "bao nhiêu tiền",
            "bao nhieu tien",
        ]

        # Check for budget calculation phrases
        has_budget = any(phrase in query_lower for phrase in budget_phrases)
        has_cost = any(phrase in query_lower for phrase in cost_phrases)

        if has_budget or has_cost:
            # Make sure it's NOT about creating new plan (these would be plan_trip)
            plan_creation_phrases = [
                "lập lịch trình",
                "lap lich trinh",
                "tạo lịch trình",
                "tao lich trinh",
                "lên kế hoạch",
                "len ke hoach",
            ]
            is_creating_plan = any(
                phrase in query_lower for phrase in plan_creation_phrases
            )

            if not is_creating_plan:
                logger.info(
                    f"[FIX #3] 🎯 Budget/cost calculation detected (NOT plan creation)"
                )
                return True

        return False

    def extract(self, query: str, context: Dict[str, Any] = None) -> ExtractedIntent:
        """
        Extract intent and entities from user query

        Args:
            query: User's natural language query
            context: Optional conversation context

        Returns:
            ExtractedIntent with all extracted information
        """
        context = context or {}
        query_lower = query.lower()

        # === PRE-LLM CHECKS: High-confidence pattern detection ===
        # These patterns are checked BEFORE LLM to avoid LLM misinterpretation

        # FIX #1: Check compound booking pattern first
        if self._is_booking_request(query_lower):
            hotel_name = self._extract_hotel_name(query, context)
            return ExtractedIntent(
                intent="book_hotel",
                location=context.get("destination"),
                keywords=[hotel_name] if hotel_name else [],
                confidence=0.95,
            )

        # FIX #3: Check budget/cost calculation pattern (avoid "lập" confusion)
        if self._is_budget_calculation_request(query_lower):
            return ExtractedIntent(
                intent="calculate_cost",
                location=context.get("destination"),
                duration=context.get("duration"),
                budget=context.get("budget"),
                confidence=0.95,
            )

        # === LLM EXTRACTION (after high-confidence checks) ===
        # Try LLM extraction for ambiguous cases
        if self.llm_client:
            try:
                return self._extract_with_llm(query, context)
            except Exception as e:
                logger.warning(f"⚠️ LLM extraction failed, using regex: {e}")

        # Fallback to regex extraction
        return self._extract_with_regex(query, context)

    def _extract_with_llm(self, query: str, context: Dict[str, Any]) -> ExtractedIntent:
        """Extract using LLM with smart inference"""

        system_prompt = """Bạn là chuyên gia NLU (Natural Language Understanding) cho hệ thống du lịch Việt Nam.
Nhiệm vụ: Phân tích câu hỏi người dùng và trích xuất thông tin có cấu trúc một cách THÔNG MINH.

QUAN TRỌNG - Suy luận thông minh:
- "cùng bạn gái/bạn trai" = 2 người (couple)
- "cùng gia đình" = 4 người (default family size)
- "cùng bạn bè" = 4 người (default group)
- "một mình" / "solo" = 1 người
- "3 ngày 2 đêm" = 3 ngày
- "cuối tuần" = 2 ngày
- "1 tuần" = 7 ngày

Trả về JSON với format:
{
    "intent": "show_itinerary" | "plan_trip" | "find_spot" | "find_hotel" | "find_food" | "book_hotel" | "calculate_cost" | "greeting" | "chitchat" | "thanks" | "farewell" | "more_spots" | "more_hotels" | "general_qa",
    "mode": "traveler" | "business",
    "location": "tên tỉnh/thành phố (chuẩn hóa)" | null,
    "duration": số ngày (int) | null,
    "budget": tổng ngân sách VNĐ (int) | null,
    "budget_level": "tiết kiệm" | "trung bình" | "sang trọng" | null,
    "people_count": số người (int, suy luận từ context),
    "companion_type": "solo" | "couple" | "family" | "friends" | "business" | null,
    "accommodation": "required" | "optional" | "none",
    "interests": ["biển", "núi", "ẩm thực", "văn hóa", "nghỉ dưỡng", ...],
    "keywords": ["từ khóa quan trọng"],
    "confidence": 0.0-1.0
}

INTENT RULES - CRITICAL DISTINCTIONS:
★★★ QUAN TRỌNG: Phân biệt READ vs WRITE operations ★★★

READ Operations (xem dữ liệu đã có):
- show_itinerary: "xem lại lịch trình", "lịch trình của tôi", "lịch trình đã tạo", "cho tôi xem lịch trình", "hiển thị lịch trình"
- calculate_cost: "tính tiền", "chi phí là bao nhiêu", "ước tính chi phí", "lập budget", "lập chi phí", "budget hiện tại" (đặc biệt khi context đã có lịch trình)

WRITE Operations (tạo mới):
- plan_trip: "lên lịch trình", "tạo lịch trình", "lập kế hoạch", "bắt đầu lên kế hoạch" (CÓ duration HOẶC từ khóa tạo mới)

★★★ FIX #3: "lập budget" / "lập chi phí" = calculate_cost (KHÔNG PHẢI plan_trip!) ★★★

★★★ VÍ DỤ QUAN TRỌNG ★★★
- "xem lại lịch trình và tính tiền" → show_itinerary (KHÔNG phải plan_trip!)
- "tính tiền lịch trình này" → calculate_cost (KHÔNG phải plan_trip!)
- "cho tôi xem lịch trình đã tạo" → show_itinerary (KHÔNG phải plan_trip!)
- "lên lịch trình 3 ngày Đà Nẵng" → plan_trip (tạo mới)
- "tạo tour 5 ngày Phú Quốc" → plan_trip (tạo mới)

Other intents:
- greeting: Lời chào đơn giản
- chitchat: Không liên quan du lịch
- thanks/farewell: Cảm ơn/Tạm biệt
- more_spots/more_hotels: Muốn xem thêm (còn ... khác không, thêm ...)
- book_hotel: Đặt phòng cụ thể
- find_spot: Tìm địa điểm (có "địa điểm", "tham quan", "chỗ nào", "đi chơi", "chỗ đẹp")
- find_hotel: Tìm khách sạn (có "khách sạn", "hotel", "resort", "homestay", "chỗ ở")
- find_food: Tìm ẩm thực (có "món ăn", "quán", "nhà hàng", "đặc sản", "ẩm thực")

QUAN TRỌNG - Ưu tiên cụ thể hơn chung chung:
- "Địa điểm du lịch X" → find_spot (có "địa điểm" → ưu tiên find_spot)
- "Khách sạn X" → find_hotel
- "Du lịch X 3 ngày" → plan_trip (có duration)
- "Du lịch X" (không có duration) → general_qa hoặc find_spot nếu hỏi về địa điểm

VÍ DỤ SUY LUẬN:
Query: "3 ngày 2 đêm cùng bạn gái" → {"duration": 3, "people_count": 2, "companion_type": "couple", "interests": ["lãng mạn", "nghỉ dưỡng"]}
Query: "đi biển với gia đình" → {"people_count": 4, "companion_type": "family", "interests": ["biển", "gia đình"]}
Query: "du lịch tiết kiệm" → {"budget_level": "tiết kiệm", "budget": 3000000}
Query: "nghỉ dưỡng cao cấp" → {"budget_level": "sang trọng", "interests": ["nghỉ dưỡng", "spa"]}

CHỈ trả về JSON, không giải thích."""

        # Add context if available
        context_str = ""
        if context:
            ctx_parts = []
            if context.get("destination"):
                ctx_parts.append(f"Điểm đến: {context['destination']}")
            if context.get("duration"):
                ctx_parts.append(f"Thời gian: {context['duration']} ngày")
            if context.get("people_count"):
                ctx_parts.append(f"Số người: {context['people_count']}")
            if context.get("companion_type"):
                ctx_parts.append(f"Loại nhóm: {context['companion_type']}")
            if context.get("budget"):
                ctx_parts.append(f"Ngân sách: {context['budget']}")
            if ctx_parts:
                context_str = f"\nContext hiện tại: {', '.join(ctx_parts)}"

        prompt = f'Query: "{query}"{context_str}'

        result = self.llm_client.extract_json(prompt, system_prompt)

        # Merge with existing context (don't override if LLM returns null)
        location = result.get("location") or context.get("destination")
        duration = result.get("duration") or context.get("duration")
        budget = result.get("budget") or context.get("budget")
        people_count = result.get("people_count") or context.get("people_count") or 1
        companion_type = result.get("companion_type") or context.get("companion_type")

        # Convert to ExtractedIntent
        return ExtractedIntent(
            intent=result.get("intent", "general_qa"),
            mode=result.get("mode", "traveler"),
            location=location,
            duration=duration,
            budget=budget,
            budget_level=result.get("budget_level"),
            people_count=people_count,
            companion_type=companion_type,
            accommodation=result.get("accommodation", "required"),
            interests=result.get("interests", []),
            keywords=result.get("keywords", []),
            confidence=result.get("confidence", 0.8),
        )

    def _extract_with_regex(
        self, query: str, context: Dict[str, Any]
    ) -> ExtractedIntent:
        """Fallback regex-based extraction with smart intent detection"""

        query_lower = query.lower()

        # === FIX #1: CHECK COMPOUND BOOKING FIRST (before pattern matching) ===
        if self._is_booking_request(query_lower):
            hotel_name = self._extract_hotel_name(query, context)
            return ExtractedIntent(
                intent="book_hotel",
                location=context.get("destination"),
                keywords=[hotel_name] if hotel_name else [],
                confidence=0.95,  # High confidence for compound detection
            )

        # === SPECIAL INTENTS (check first, higher priority) ===

        # Check for greeting patterns FIRST
        # Use word boundaries to avoid false matches like "chi tiết" matching "hi "
        greeting_patterns = [
            r"\bxin chào\b",
            r"\bhello\b",
            r"^hi$",
            r"^hi\s",
            r"\bchào bạn\b",
            r"\bhey\b",
            r"\bchào nhé\b",
        ]
        import re as re_mod

        if any(re_mod.search(pattern, query_lower) for pattern in greeting_patterns):
            return ExtractedIntent(intent="greeting", confidence=0.95)

        # Check for thanks
        thanks_patterns = ["cảm ơn", "thank", "thanks", "tks"]
        if any(pattern in query_lower for pattern in thanks_patterns):
            return ExtractedIntent(intent="thanks", confidence=0.95)

        # Check for farewell
        farewell_patterns = ["tạm biệt", "bye", "goodbye", "hẹn gặp lại"]
        if any(pattern in query_lower for pattern in farewell_patterns):
            return ExtractedIntent(intent="farewell", confidence=0.95)

        # Check for off-topic/chitchat
        if self._is_offtopic(query_lower):
            return ExtractedIntent(intent="chitchat", confidence=0.9)

        # Check for booking intent (higher priority than find_hotel)
        booking_patterns = ["đặt phòng", "book", "đặt chỗ", "thuê phòng"]
        if any(pattern in query_lower for pattern in booking_patterns):
            # Try to extract hotel name
            hotel_name = self._extract_hotel_name(query, context)
            return ExtractedIntent(
                intent="book_hotel",
                location=context.get("destination"),
                keywords=[hotel_name] if hotel_name else [],
                confidence=0.85,
            )

        # FIX #3: Check for cost/budget calculation BEFORE plan_trip (to avoid "lập" false match)
        cost_patterns = [
            "tính tiền",
            "chi phí",
            "bao nhiêu tiền",
            "số tiền",
            "ngân sách",
            "ước tính",
            "lập budget",
            "lap budget",
            "budget",
        ]
        if any(pattern in query_lower for pattern in cost_patterns):
            return ExtractedIntent(
                intent="calculate_cost",
                location=context.get("destination"),
                duration=context.get("duration"),
                budget=context.get("budget"),
                confidence=0.85,
            )

        # === CHECK FOR "MORE" REQUESTS (needs context to determine what type) ===
        # Check specific "more" patterns first
        more_spots_patterns = self.INTENT_PATTERNS.get("more_spots", [])
        more_hotels_patterns = self.INTENT_PATTERNS.get("more_hotels", [])
        more_food_patterns = self.INTENT_PATTERNS.get("more_food", [])

        if any(kw in query_lower for kw in more_spots_patterns):
            return ExtractedIntent(
                intent="find_spot",
                location=context.get("destination"),
                keywords=["more"],  # Signal that user wants more spots
                confidence=0.85,
            )

        if any(kw in query_lower for kw in more_hotels_patterns):
            return ExtractedIntent(
                intent="find_hotel",
                location=context.get("destination"),
                keywords=["more"],
                confidence=0.85,
            )

        if any(kw in query_lower for kw in more_food_patterns):
            return ExtractedIntent(
                intent="find_food",
                location=context.get("destination"),
                keywords=["more"],
                confidence=0.85,
            )

        # Check generic "more" patterns (rely on context to determine type)
        for pattern in self.MORE_PATTERNS:
            if re.search(pattern, query_lower):
                # Map to intent based on context's last_intent
                last_intent = context.get("last_intent", "")
                if last_intent == "find_spot" or last_intent == "explore_destination":
                    return ExtractedIntent(
                        intent="find_spot",
                        location=context.get("destination"),
                        keywords=["more"],
                        confidence=0.8,
                    )
                elif last_intent == "find_hotel":
                    return ExtractedIntent(
                        intent="find_hotel",
                        location=context.get("destination"),
                        keywords=["more"],
                        confidence=0.8,
                    )
                elif last_intent == "find_food":
                    return ExtractedIntent(
                        intent="find_food",
                        location=context.get("destination"),
                        keywords=["more"],
                        confidence=0.8,
                    )
                # Default to find_spot if no clear context
                return ExtractedIntent(
                    intent="find_spot",
                    location=context.get("destination"),
                    keywords=["more"],
                    confidence=0.7,
                )

        # === TRAVEL INTENTS ===

        # CRITICAL: Check for "show_itinerary" BEFORE "plan_trip" to avoid conflict
        # "xem lại lịch trình" should be show_itinerary, not plan_trip
        show_patterns = self.INTENT_PATTERNS.get("show_itinerary", [])
        if any(kw in query_lower for kw in show_patterns):
            return ExtractedIntent(
                intent="show_itinerary",
                location=context.get("destination"),
                duration=context.get("duration"),
                confidence=0.9,
            )

        # Extract intent from keywords (now multi-intent aware)
        found_intents = []

        # Priority order for intent detection
        # IMPORTANT: Specific intents (find_spot, find_hotel, find_food) should be checked
        # BEFORE generic "plan_trip" because "du lịch" is too generic
        # E.g., "Địa điểm du lịch Phú Quốc" should be find_spot, not plan_trip
        intent_priority = [
            "calculate_cost",
            "find_hotel",
            "find_spot",
            "find_food",
            "plan_trip",
        ]

        # CRITICAL: Collect ALL matching intents (NO break statement)
        for intent_name in intent_priority:
            keywords = self.INTENT_PATTERNS.get(intent_name, [])
            if any(kw in query_lower for kw in keywords):
                found_intents.append(intent_name)
                logger.debug(f"  ✓ Regex detected intent: {intent_name}")

        # Smart conflict resolution:
        # If both "calculate_cost" and "plan_trip" detected, check context
        # FIX #3: Also check for itinerary_builder (interactive mode)
        if "calculate_cost" in found_intents and "plan_trip" in found_intents:
            # If user has existing itinerary or is in builder mode, prioritize calculate_cost
            if (
                context.get("last_itinerary")
                or context.get("itinerary_data")
                or context.get("itinerary_builder")
            ):
                found_intents.remove("plan_trip")
                logger.info(
                    "🎯 [FIX #3] Removed plan_trip conflict: User wants to calculate cost, not create new plan"
                )

        # Primary intent: first detected (highest priority)
        intent = found_intents[0] if found_intents else "general_qa"
        confidence = 0.7 if found_intents else 0.5

        logger.info(f"🎯 Final intent selection: {intent} (from {found_intents})")

        # Extract location
        location = None
        for loc in self.KNOWN_LOCATIONS:
            if loc.lower() in query_lower:
                location = loc
                break

        # Use context location if not found
        if not location and context.get("destination"):
            location = context["destination"]

        # Extract duration
        duration = None
        duration_match = re.search(r"(\d+)\s*(?:ngày|day)", query_lower)
        if duration_match:
            duration = int(duration_match.group(1))

        # Extract budget
        budget = None
        budget_match = re.search(
            r"(\d+(?:[.,]\d+)?)\s*(?:triệu|tr|million)", query_lower
        )
        if budget_match:
            budget = int(float(budget_match.group(1).replace(",", ".")) * 1_000_000)

        # Extract budget level
        budget_level = None
        for level, keywords in self.BUDGET_PATTERNS.items():
            if any(kw in query_lower for kw in keywords):
                budget_level = level
                break

        # Extract people count - support natural language
        people_count = 1
        explicit_people_count = None  # If user explicitly says "5 người"

        # Pattern 1: Explicit number "2 người", "4 person" - this has highest priority
        people_match = re.search(r"(\d+)\s*(?:người|person|nguoi)", query_lower)
        if people_match:
            explicit_people_count = int(people_match.group(1))
            people_count = explicit_people_count

        # Pattern 2: "cùng" phrases implying 2 people (couple)
        companion_type = None
        couple_patterns = [
            r"cùng\s*(?:bạn\s*gái|bạn\s*trai|người\s*yêu|vợ|chồng|bạn|em|anh)",
            r"với\s*(?:bạn\s*gái|bạn\s*trai|người\s*yêu|vợ|chồng|bạn|em|anh)",
            r"đi\s*(?:cặp|đôi|hai)",
            r"cho\s*(?:cặp|đôi|hai)",
            r"hai\s*(?:vợ\s*chồng|đứa|người)",
            r"2\s*(?:vợ\s*chồng|đứa)",
        ]
        for pattern in couple_patterns:
            if re.search(pattern, query_lower):
                if (
                    explicit_people_count is None
                ):  # Only set if not explicitly specified
                    people_count = 2
                companion_type = "couple"
                break

        # Pattern 3: Solo travel
        solo_patterns = [
            r"một\s*mình",
            r"đi\s*một\s*mình",
            r"solo",
            r"tự\s*đi",
            r"1\s*người",
        ]
        for pattern in solo_patterns:
            if re.search(pattern, query_lower):
                if (
                    explicit_people_count is None
                ):  # Only set if not explicitly specified
                    people_count = 1
                companion_type = "solo"
                break

        # Pattern 4: Family/group (don't override explicit people_count)
        family_patterns = [
            (r"(?:cả\s*)?gia\s*đình", 4, "family"),
            (r"nhóm\s*bạn|với\s*bạn\s*bè|cùng\s*bạn\s*bè", 4, "friends"),
            (r"nhóm\s*(\d+)", None, "friends"),  # Extract from "nhóm 5 người"
            (r"(\d+)\s*(?:bạn|friend)", None, "friends"),
            (r"cùng\s*(?:con|bé|trẻ)", 3, "family"),  # Parent + child typically 3+
            (r"công\s*ty|team|đồng\s*nghiệp", 5, "business"),
        ]
        for pattern, count, ctype in family_patterns:
            match = re.search(pattern, query_lower)
            if match:
                companion_type = ctype
                # Only set people_count if not explicitly specified
                if explicit_people_count is None:
                    if count:
                        people_count = count
                    elif match.groups():
                        try:
                            people_count = int(match.group(1))
                        except:
                            pass
                break

        # Check accommodation constraint
        accommodation = "required"
        if any(
            kw in query_lower
            for kw in ["không thuê", "không cần", "không ở", "tiết kiệm"]
        ):
            accommodation = "optional"
        if any(
            kw in query_lower for kw in ["không khách sạn", "không hotel", "no hotel"]
        ):
            accommodation = "none"

        # Extract interests/keywords
        interests = []
        keywords = []

        if any(kw in query_lower for kw in ["biển", "beach"]):
            interests.append("beach")
            keywords.append("biển")
        if any(kw in query_lower for kw in ["núi", "mountain", "trekking"]):
            interests.append("mountain")
            keywords.append("núi")
        if any(kw in query_lower for kw in ["ăn", "món", "quán", "nhà hàng"]):
            interests.append("food")
        if any(kw in query_lower for kw in ["văn hóa", "lịch sử", "đền", "chùa"]):
            interests.append("culture")

        return ExtractedIntent(
            intent=intent,
            mode="traveler",
            location=location,
            duration=duration,
            budget=budget,
            budget_level=budget_level,
            people_count=people_count,
            companion_type=companion_type,
            accommodation=accommodation,
            interests=interests,
            keywords=keywords,
            confidence=confidence,
        )

    def _is_offtopic(self, query_lower: str) -> bool:
        """Detect off-topic or rude queries"""
        for pattern in self.OFFTOPIC_PATTERNS:
            if re.search(pattern, query_lower):
                return True

        # Very short queries with no travel keywords
        if len(query_lower.split()) <= 2:
            travel_keywords = ["đi", "đến", "ở", "ăn", "nghỉ", "khách sạn", "địa điểm"]
            if not any(kw in query_lower for kw in travel_keywords):
                return True

        return False

    def _extract_hotel_name(self, query: str, context: Dict[str, Any]) -> Optional[str]:
        """Extract hotel name from query or context"""
        # Pattern 1: "đặt phòng tại/ở <hotel name>"
        match = re.search(r"(?:tại|ở)\s+(.+?)(?:\s*$|[,.])", query, re.IGNORECASE)
        if match:
            return match.group(1).strip()

        # Pattern 2: "đặt phòng <hotel name>" (without tại/ở)
        match2 = re.search(
            r"đặt\s+(?:phòng\s+)?(.+?)(?:\s*$|[,.])", query, re.IGNORECASE
        )
        if match2:
            hotel_name = match2.group(1).strip()
            # Filter out common non-hotel words
            skip_words = ["khách sạn", "ở", "tại", "cho", "tôi"]
            for word in skip_words:
                if hotel_name.lower().startswith(word):
                    hotel_name = hotel_name[len(word) :].strip()
            if hotel_name and len(hotel_name) > 2:
                return hotel_name

        # Pattern 3: Look for "Khách sạn <name>" or "<name> Hotel"
        match3 = re.search(
            r"(?:khách sạn|hotel|resort)\s+(.+?)(?:\s*$|[,.])", query, re.IGNORECASE
        )
        if match3:
            return match3.group(1).strip()

        # Pattern 4: Extract text after booking keywords
        for keyword in ["đặt phòng", "book", "đặt chỗ"]:
            if keyword in query.lower():
                parts = query.lower().split(keyword)
                if len(parts) > 1 and parts[1].strip():
                    remaining = parts[1].strip()
                    # Clean up
                    remaining = re.sub(r"^(tại|ở|cho)\s+", "", remaining)
                    if remaining and len(remaining) > 3:
                        # Find the hotel name in original query (preserve case)
                        idx = query.lower().find(remaining[:10])
                        if idx >= 0:
                            return query[idx:].strip()
                        return remaining

        # Check context for selected hotel
        if context.get("selected_hotel"):
            return context["selected_hotel"]

        return None


# Factory function
def create_intent_extractor(llm_client=None) -> IntentExtractor:
    """Create IntentExtractor with optional LLM client"""
    return IntentExtractor(llm_client)
