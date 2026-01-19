"""
Simple RAG Service - Baseline before Plan-RAG
"""

from typing import Dict, Any, List
from app.db import mongodb_manager, vector_store
from app.services.budget_parser import budget_parser
from app.core import logger


class SimpleRAGService:
    """Simple RAG without query decomposition"""
    
    # Synonym mapping for keyword expansion
    SYNONYM_MAP = {
        "biển": ["biển", "bãi biển", "beach", "bờ biển", "bãi tắm"],
        "núi": ["núi", "đồi", "mountain", "hill"],
        "chùa": ["chùa", "temple", "pagoda", "tự", "đền"],
        "thác": ["thác", "thác nước", "waterfall"],
        "phố cổ": ["phố cổ", "old town", "old quarter", "phố"],
        "bảo tàng": ["bảo tàng", "museum"],
        "công viên": ["công viên", "park", "vườn"],
        "suối": ["suối", "stream", "spring"],
        "hồ": ["hồ", "lake", "reservoir"],
        "rừng": ["rừng", "forest", "jungle"]
    }
    
    # Common stop words to exclude from keyword extraction
    STOP_WORDS = {
        "khách sạn", "hotel", "tìm", "ở", "đâu", "gần", "có", "không",
        "địa điểm", "du lịch", "tham quan", "đi", "xem", "nào",
        "cho", "tôi", "mình", "em", "anh", "chị", "với", "và", "hoặc"
    }
    
    def __init__(self):
        self.mongo = mongodb_manager
        self.vector = vector_store
        self.budget_parser = budget_parser
    
    def _extract_keywords(self, query: str) -> List[str]:
        """Extract meaningful keywords from query (exclude stop words)"""
        words = query.lower().split()
        keywords = []
        
        for word in words:
            # Skip stop words and short words
            if word not in self.STOP_WORDS and len(word) > 2:
                # Skip numbers and budget-related words
                if not word.isdigit() and word not in ["triệu", "tr", "nghìn", "đồng", "vnđ"]:
                    keywords.append(word)
        
        return keywords
    
    def _expand_keywords(self, query: str) -> List[str]:
        """Expand query with synonyms"""
        query_lower = query.lower()
        expanded = []
        
        # Check for known synonyms
        for key, synonyms in self.SYNONYM_MAP.items():
            if key in query_lower:
                expanded.extend(synonyms)
        
        # Add original keywords
        original_keywords = self._extract_keywords(query)
        expanded.extend(original_keywords)
        
        # Remove duplicates while preserving order
        seen = set()
        result = []
        for keyword in expanded:
            if keyword not in seen:
                seen.add(keyword)
                result.append(keyword)
        
        return result if result else [query]  # Fallback to original query
    
    def search_hotels(
        self,
        query: str,
        province: str = None,
        budget_level: str = None,
        k: int = 10,  # Increased from 5 to give more options
        min_rating: float = 8.0  # Filter low-rated hotels
    ) -> List[Dict[str, Any]]:
        """Search hotels with improved filters and text search"""
        
        logger.info(f"🔍 Hotel search: query='{query}', province={province}")
        
        # Build MongoDB filters
        mongo_filters = {}
        
        if province:
            # Match by province_id (e.g., "ha-noi", "da-nang")
            from utils.normalization import normalize_vietnamese_slug
            province_id = normalize_vietnamese_slug(province)
            mongo_filters["province_id"] = province_id
        
        # Parse budget
        budget_filters = self.budget_parser.parse(query, budget_level)
        mongo_filters.update(budget_filters)
        
        # IMPROVEMENT #1: Add text search for keywords
        # Extract keywords from query (exclude common words)
        keywords = self._extract_keywords(query)
        if keywords:
            or_conditions = []
            for keyword in keywords:
                or_conditions.extend([
                    {"name": {"$regex": keyword, "$options": "i"}},
                    {"address": {"$regex": keyword, "$options": "i"}},
                    {"facilities": {"$regex": keyword, "$options": "i"}}
                ])
            
            if or_conditions:
                # Combine with existing filters
                if "$or" in mongo_filters:
                    mongo_filters["$and"] = [
                        {"$or": mongo_filters.pop("$or")},
                        {"$or": or_conditions}
                    ]
                else:
                    mongo_filters["$or"] = or_conditions
        
        # IMPROVEMENT #2: Filter by minimum rating
        mongo_filters["rating"] = {"$gte": min_rating}
        
        logger.info(f"   MongoDB filters: {mongo_filters}")
        
        # Get hotels from MongoDB
        hotels_collection = self.mongo.get_collection("hotels")
        
        # IMPROVEMENT #3: Better sorting - rating DESC, then price ASC
        cursor = hotels_collection.find(
            mongo_filters,
            limit=k
        ).sort([("rating", -1), ("price", 1)])
        
        results = []
        for hotel in cursor:
            results.append({
                "id": str(hotel["_id"]),
                "name": hotel["name"],
                "rating": hotel.get("rating", 0.0),
                "price": hotel.get("price", 0),
                "priceRange": f"{hotel.get('price', 0):,} VNĐ/đêm",
                "address": hotel.get("address", ""),
                "province_id": hotel.get("province_id", ""),
                "url": hotel.get("url", ""),
                "image": hotel.get("image_url", ""),
                "facilities": hotel.get("facilities", ""),
                "latitude": hotel.get("latitude"),
                "longitude": hotel.get("longitude")
            })
        
        logger.info(f"✅ Found {len(results)} hotels")
        return results
    
    def search_spots(
        self,
        query: str,
        province: str = None,
        k: int = 10,  # Increased from 5
        min_reviews: int = 10,  # Filter unpopular spots
        free_only: bool = False  # Option to filter free spots
    ) -> List[Dict[str, Any]]:
        """Search spots with improved text search and filters"""
        
        logger.info(f"🔍 Spot search: query='{query}', province={province}")
        
        # For now, use MongoDB direct query (vector search can be added later)
        mongo_filters = {}
        
        if province:
            from utils.normalization import normalize_vietnamese_slug
            province_id = normalize_vietnamese_slug(province)
            mongo_filters["province_id"] = province_id
        
        # IMPROVEMENT #1: Filter by minimum reviews
        mongo_filters["reviews_count"] = {"$gte": min_reviews}
        
        # IMPROVEMENT #2: Filter by cost if requested
        if free_only:
            mongo_filters["cost"] = {"$in": ["Miễn phí", "miễn phí", "không", "None"]}
        
        spots_collection = self.mongo.get_collection("spots_detailed")
        
        # IMPROVEMENT #3: Expand query with synonyms
        expanded_keywords = self._expand_keywords(query)
        
        # Search by name or description (prioritize name and description_short over description_full)
        if expanded_keywords:
            or_conditions = []
            for keyword in expanded_keywords:
                or_conditions.extend([
                    {"name": {"$regex": keyword, "$options": "i"}},
                    {"description_short": {"$regex": keyword, "$options": "i"}},
                    # description_full is slower, use only if specific
                    {"description_full": {"$regex": keyword, "$options": "i"}}
                ])
            mongo_filters["$or"] = or_conditions
        
        logger.info(f"   MongoDB filters (spots): {mongo_filters}")
        
        # IMPROVEMENT #4: Better sorting - rating DESC, reviews_count DESC
        cursor = spots_collection.find(
            mongo_filters, 
            limit=k
        ).sort([("rating", -1), ("reviews_count", -1)])
        
        results = []
        for spot in cursor:
            results.append({
                "id": spot.get("id", str(spot["_id"])),
                "name": spot["name"],
                "province_id": spot.get("province_id", ""),
                "description": spot.get("description_short", ""),
                "description_full": spot.get("description_full", ""),
                "rating": spot.get("rating", 0.0),
                "reviews_count": spot.get("reviews_count", 0),
                "image": spot.get("image", ""),
                "url": spot.get("url", ""),
                "address": spot.get("address", ""),
                "cost": spot.get("cost", "miễn phí")
            })
        
        logger.info(f"✅ Found {len(results)} spots")
        return results
    
    def _detect_intent(self, message: str) -> Dict[str, Any]:
        """
        Improved intent detection using keyword analysis
        Returns: {"intent": str, "confidence": float, "entities": dict}
        """
        message_lower = message.lower()
        
        # Priority-based intent detection (more specific first)
        
        # 1. Itinerary planning (highest priority for multi-day queries)
        if any(word in message_lower for word in ["lịch trình", "itinerary", "kế hoạch"]):
            return {
                "intent": "itinerary",
                "confidence": 0.9,
                "entities": {}
            }
        
        # 2. Hotel search (check for explicit hotel keywords)
        hotel_keywords = ["khách sạn", "hotel", "nghỉ", "ở", "chỗ ở", "booking"]
        hotel_count = sum(1 for word in hotel_keywords if word in message_lower)
        
        # 3. Spot search (check for location/attraction keywords)
        spot_keywords = ["địa điểm", "đi đâu", "tham quan", "du lịch", "xem", "thăm", "ghé", "bãi biển", "núi", "chùa"]
        spot_count = sum(1 for word in spot_keywords if word in message_lower)
        
        # Determine primary intent based on keyword frequency
        if hotel_count > spot_count:
            return {
                "intent": "hotel",
                "confidence": 0.7 + (hotel_count * 0.1),
                "entities": {}
            }
        elif spot_count > 0:
            return {
                "intent": "spot",
                "confidence": 0.7 + (spot_count * 0.1),
                "entities": {}
            }
        
        # 4. Ambiguous queries - check for question patterns
        if "?" in message or any(word in message_lower for word in ["nào", "gì", "sao", "như thế nào"]):
            # If asking about location/place → spot
            if any(word in message_lower for word in ["biển", "núi", "chùa", "đền", "hồ", "thác"]):
                return {
                    "intent": "spot",
                    "confidence": 0.6,
                    "entities": {}
                }
        
        # Default: generic
        return {
            "intent": "generic",
            "confidence": 0.3,
            "entities": {}
        }
    
    def chat(
        self,
        message: str,
        trip_state: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Improved chat endpoint with better intent detection"""
        
        logger.info(f"💬 Chat: {message}")
        
        # Extract context
        destination = trip_state.get("destination") if trip_state else None
        budget_level = trip_state.get("budget_level") if trip_state else None
        
        # IMPROVEMENT: Use better intent detection
        intent_result = self._detect_intent(message)
        intent = intent_result["intent"]
        confidence = intent_result["confidence"]
        
        logger.info(f"   Detected intent: {intent} (confidence: {confidence:.2f})")
        
        if intent == "hotel":
            # Hotel search
            hotels = self.search_hotels(
                query=message,
                province=destination,
                budget_level=budget_level
            )
            
            return {
                "response": f"Tìm thấy {len(hotels)} khách sạn phù hợp với yêu cầu của bạn!",
                "results": {"hotels": hotels},
                "confidence": confidence,
                "plan": [],
                "sources": [],
                "intent": intent
            }
        
        elif intent == "spot":
            # Spot search
            spots = self.search_spots(
                query=message,
                province=destination
            )
            
            return {
                "response": f"Gợi ý {len(spots)} địa điểm tham quan thú vị!",
                "results": {"spots": spots},
                "confidence": confidence,
                "plan": [],
                "sources": [],
                "intent": intent
            }
        
        elif intent == "itinerary":
            # TODO: Implement itinerary planning
            return {
                "response": "Tính năng lập lịch trình đang được phát triển. Vui lòng tìm khách sạn hoặc địa điểm riêng lẻ.",
                "results": {},
                "confidence": confidence,
                "plan": [],
                "sources": [],
                "intent": intent
            }
        
        else:
            # Generic response with helpful suggestions
            return {
                "response": "Tôi có thể giúp bạn:\n- Tìm khách sạn phù hợp với budget\n- Gợi ý địa điểm tham quan\n- Lập lịch trình du lịch\n\nBạn cần tìm gì?",
                "results": {},
                "confidence": confidence,
                "plan": [],
                "sources": [],
                "intent": intent
            }


# Global instance
rag_service = SimpleRAGService()
