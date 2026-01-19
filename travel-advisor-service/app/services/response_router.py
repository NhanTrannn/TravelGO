"""
Response Router - Smart routing between structured and natural responses
Decides when to use UI cards vs natural language vs hybrid
"""

from enum import Enum
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from app.core import logger


class ResponseMode(str, Enum):
    """Response modes for different situations"""
    STRUCTURED = "structured"  # UI cards only (hotels, spots, itinerary)
    NATURAL = "natural"        # LLM-generated text only (follow-up, clarification)
    HYBRID = "hybrid"          # UI cards + natural explanation
    CONVERSATIONAL = "conversational"  # Pure chat (greeting, thanks, chitchat)


class QueryType(str, Enum):
    """Types of user queries"""
    # Primary intents (need structured data)
    SEARCH_HOTEL = "search_hotel"
    SEARCH_SPOT = "search_spot"
    SEARCH_FOOD = "search_food"
    CREATE_ITINERARY = "create_itinerary"
    CALCULATE_COST = "calculate_cost"
    
    # Detail/follow-up intents (need natural + maybe structured)
    GET_DETAIL = "get_detail"           # "Chi tiết về Bãi Sao"
    COMPARE = "compare"                  # "So sánh 2 khách sạn này"
    EXPLAIN = "explain"                  # "Tại sao chọn khách sạn này?"
    BREAKDOWN = "breakdown"              # "Chi phí mỗi ngày"
    MORE_OPTIONS = "more_options"        # "Còn khách sạn nào khác không?"
    FILTER = "filter"                    # "Chỉ xem khách sạn dưới 1 triệu"
    
    # Conversational (natural only)
    GREETING = "greeting"
    THANKS = "thanks"
    FAREWELL = "farewell"
    CHITCHAT = "chitchat"
    CLARIFICATION = "clarification"      # Bot hỏi user
    
    # Region-based
    REGION_SEARCH = "region_search"      # "Du lịch miền nam"
    
    # Booking
    BOOK_HOTEL = "book_hotel"
    
    # Unknown
    UNKNOWN = "unknown"


@dataclass
class RoutingDecision:
    """Decision from the router"""
    mode: ResponseMode
    query_type: QueryType
    requires_data: bool = True
    requires_llm: bool = False
    data_sources: List[str] = field(default_factory=list)  # ["hotels", "spots", "foods"]
    reference_entity: Optional[str] = None  # Entity being referenced (e.g., "Bãi Sao")
    context_needed: List[str] = field(default_factory=list)  # ["last_spots", "last_hotels"]
    prompt_template: Optional[str] = None


class ResponseRouter:
    """
    Smart router that decides how to respond to user queries
    """
    
    # Keywords for each query type
    QUERY_PATTERNS = {
        # Detail queries - user asking about specific item
        QueryType.GET_DETAIL: [
            "chi tiết", "thông tin", "cho biết về", "kể về", "nói về",
            "tôi quan tâm", "muốn biết thêm", "giới thiệu về",
            "thế nào", "ra sao", "như thế nào"
        ],
        
        # Breakdown queries
        QueryType.BREAKDOWN: [
            "mỗi ngày", "từng ngày", "chi tiết chi phí", "phân tích",
            "chia ra", "breakdown", "cụ thể từng"
        ],
        
        # Comparison queries
        QueryType.COMPARE: [
            "so sánh", "khác gì", "tốt hơn", "nên chọn",
            "giữa", "hay là"
        ],
        
        # Explanation queries
        QueryType.EXPLAIN: [
            "tại sao", "vì sao", "lý do", "giải thích",
            "tại vì", "do đâu"
        ],
        
        # More options
        QueryType.MORE_OPTIONS: [
            "còn gì", "thêm", "khác không", "nữa không",
            "gợi ý thêm", "xem thêm", "còn chỗ nào"
        ],
        
        # Filter
        QueryType.FILTER: [
            "chỉ xem", "dưới", "trên", "trong khoảng",
            "lọc", "filter", "giá từ", "rating từ"
        ],
        
        # Region search
        QueryType.REGION_SEARCH: [
            "miền nam", "miền bắc", "miền trung", "miền tây",
            "phía nam", "phía bắc", "vùng"
        ],
        
        # Booking
        QueryType.BOOK_HOTEL: [
            "đặt phòng", "book", "đặt chỗ", "thuê phòng",
            "đăng ký", "reserve"
        ],
        
        # Conversational
        QueryType.GREETING: ["xin chào", "hello", "hi", "chào", "hey"],
        QueryType.THANKS: ["cảm ơn", "thank", "thanks"],
        QueryType.FAREWELL: ["tạm biệt", "bye", "goodbye"],
    }
    
    # Region to provinces mapping
    REGION_PROVINCES = {
        "miền nam": ["Phú Quốc", "Cần Thơ", "Vũng Tàu", "TP.HCM", "Bến Tre", "An Giang"],
        "miền bắc": ["Hà Nội", "Sapa", "Hạ Long", "Ninh Bình", "Hà Giang", "Cao Bằng"],
        "miền trung": ["Đà Nẵng", "Huế", "Hội An", "Nha Trang", "Quy Nhơn", "Đà Lạt"],
        "miền tây": ["Cần Thơ", "Bến Tre", "An Giang", "Cà Mau", "Sóc Trăng"],
        "tây nguyên": ["Đà Lạt", "Buôn Ma Thuột", "Pleiku", "Kon Tum"],
    }
    
    def __init__(self, llm_client=None):
        self.llm = llm_client
        logger.info("✅ ResponseRouter initialized")
    
    def route(self, query: str, intent: str, context: Dict[str, Any]) -> RoutingDecision:
        """
        Determine how to respond to a query
        
        Args:
            query: User's message
            intent: Extracted intent from IntentExtractor
            context: Current conversation context
            
        Returns:
            RoutingDecision with mode, type, and requirements
        """
        query_lower = query.lower()
        
        # === Check for conversational intents first ===
        if intent in ["greeting", "thanks", "farewell", "chitchat"]:
            return RoutingDecision(
                mode=ResponseMode.CONVERSATIONAL,
                query_type=QueryType[intent.upper()],
                requires_data=False,
                requires_llm=False
            )
        
        # === Check for follow-up/detail queries ===
        # These require context from previous response
        
        # Detail query - user asking about specific entity
        if self._matches_patterns(query_lower, QueryType.GET_DETAIL):
            entity = self._extract_referenced_entity(query, context)
            return RoutingDecision(
                mode=ResponseMode.HYBRID,
                query_type=QueryType.GET_DETAIL,
                requires_data=True,
                requires_llm=True,
                reference_entity=entity,
                context_needed=["last_spots", "last_hotels", "last_foods"],
                prompt_template="get_detail"
            )
        
        # Breakdown query - user wants detailed breakdown
        if self._matches_patterns(query_lower, QueryType.BREAKDOWN):
            return RoutingDecision(
                mode=ResponseMode.HYBRID,
                query_type=QueryType.BREAKDOWN,
                requires_data=True,
                requires_llm=True,
                context_needed=["last_cost", "last_itinerary"],
                prompt_template="breakdown"
            )
        
        # Compare query
        if self._matches_patterns(query_lower, QueryType.COMPARE):
            return RoutingDecision(
                mode=ResponseMode.NATURAL,
                query_type=QueryType.COMPARE,
                requires_data=True,
                requires_llm=True,
                context_needed=["last_hotels", "last_spots"],
                prompt_template="compare"
            )
        
        # Explain query
        if self._matches_patterns(query_lower, QueryType.EXPLAIN):
            return RoutingDecision(
                mode=ResponseMode.NATURAL,
                query_type=QueryType.EXPLAIN,
                requires_data=False,
                requires_llm=True,
                context_needed=["last_response", "last_recommendations"],
                prompt_template="explain"
            )
        
        # More options
        if self._matches_patterns(query_lower, QueryType.MORE_OPTIONS):
            # Determine what type based on context
            last_intent = context.get("last_intent", "")
            data_source = self._get_data_source_from_intent(last_intent)
            return RoutingDecision(
                mode=ResponseMode.STRUCTURED,
                query_type=QueryType.MORE_OPTIONS,
                requires_data=True,
                requires_llm=False,
                data_sources=[data_source] if data_source else ["spots"],
                context_needed=[f"shown_{data_source}_count"]
            )
        
        # Region search - "miền nam", "miền bắc", etc.
        if self._matches_patterns(query_lower, QueryType.REGION_SEARCH):
            region = self._extract_region(query_lower)
            return RoutingDecision(
                mode=ResponseMode.STRUCTURED,
                query_type=QueryType.REGION_SEARCH,
                requires_data=True,
                requires_llm=False,
                data_sources=["provinces"],
                reference_entity=region
            )
        
        # Booking
        if self._matches_patterns(query_lower, QueryType.BOOK_HOTEL):
            hotel_name = self._extract_hotel_name(query, context)
            return RoutingDecision(
                mode=ResponseMode.HYBRID,
                query_type=QueryType.BOOK_HOTEL,
                requires_data=True,
                requires_llm=True,
                reference_entity=hotel_name,
                context_needed=["last_hotels"],
                prompt_template="book_hotel"
            )
        
        # === Primary search intents - use structured response ===
        if intent == "find_hotel":
            return RoutingDecision(
                mode=ResponseMode.STRUCTURED,
                query_type=QueryType.SEARCH_HOTEL,
                requires_data=True,
                requires_llm=False,
                data_sources=["hotels"]
            )
        
        if intent == "find_spot":
            return RoutingDecision(
                mode=ResponseMode.STRUCTURED,
                query_type=QueryType.SEARCH_SPOT,
                requires_data=True,
                requires_llm=False,
                data_sources=["spots"]
            )
        
        if intent == "find_food":
            return RoutingDecision(
                mode=ResponseMode.STRUCTURED,
                query_type=QueryType.SEARCH_FOOD,
                requires_data=True,
                requires_llm=False,
                data_sources=["foods"]
            )
        
        if intent == "plan_trip":
            return RoutingDecision(
                mode=ResponseMode.HYBRID,
                query_type=QueryType.CREATE_ITINERARY,
                requires_data=True,
                requires_llm=True,
                data_sources=["spots", "hotels", "foods"],
                prompt_template="create_itinerary"
            )
        
        if intent == "calculate_cost":
            return RoutingDecision(
                mode=ResponseMode.STRUCTURED,
                query_type=QueryType.CALCULATE_COST,
                requires_data=True,
                requires_llm=False,
                data_sources=["costs"]
            )
        
        # === Default: Unknown - try to understand with LLM ===
        return RoutingDecision(
            mode=ResponseMode.NATURAL,
            query_type=QueryType.UNKNOWN,
            requires_data=False,
            requires_llm=True,
            prompt_template="fallback"
        )
    
    def _matches_patterns(self, query: str, query_type: QueryType) -> bool:
        """Check if query matches patterns for a query type"""
        patterns = self.QUERY_PATTERNS.get(query_type, [])
        return any(p in query for p in patterns)
    
    def _extract_referenced_entity(self, query: str, context: Dict) -> Optional[str]:
        """Extract entity name being referenced in query"""
        # Check if query contains a known entity from context
        last_spots = context.get("last_spots", [])
        last_hotels = context.get("last_hotels", [])
        
        query_lower = query.lower()
        
        # Check spots
        for spot in last_spots:
            name = spot.get("name", "").lower()
            if name and name in query_lower:
                return spot.get("name")
        
        # Check hotels
        for hotel in last_hotels:
            name = hotel.get("name", "").lower()
            if name and name in query_lower:
                return hotel.get("name")
        
        return None
    
    def _extract_region(self, query: str) -> Optional[str]:
        """Extract region name from query"""
        for region in self.REGION_PROVINCES.keys():
            if region in query:
                return region
        return None
    
    def _extract_hotel_name(self, query: str, context: Dict) -> Optional[str]:
        """Extract hotel name from query or context"""
        # Check if query mentions a specific hotel
        last_hotels = context.get("last_hotels", [])
        query_lower = query.lower()
        
        for hotel in last_hotels:
            name = hotel.get("name", "").lower()
            if name and name in query_lower:
                return hotel.get("name")
        
        return None
    
    def _get_data_source_from_intent(self, intent: str) -> str:
        """Map intent to data source"""
        mapping = {
            "find_hotel": "hotels",
            "find_spot": "spots",
            "find_food": "foods",
            "plan_trip": "itinerary",
            "calculate_cost": "costs"
        }
        return mapping.get(intent, "spots")
    
    def get_region_provinces(self, region: str) -> List[str]:
        """Get provinces for a region"""
        return self.REGION_PROVINCES.get(region, [])


def create_response_router(llm_client=None) -> ResponseRouter:
    """Factory function"""
    return ResponseRouter(llm_client)
