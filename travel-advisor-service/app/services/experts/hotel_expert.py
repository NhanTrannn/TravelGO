"""
Hotel Expert - Retrieves hotels and accommodations
"""

import time
from math import radians, sin, cos, sqrt, atan2
from typing import Dict, Any, List
from .base_expert import BaseExpert, ExpertResult
from app.core import logger


class HotelExpert(BaseExpert):
    """
    Expert for finding hotels and accommodations
    Uses price filters, rating filters, and location matching
    """
    
    # [NEW] Hybrid Search Service
    _hybrid_search = None
    
    # Budget level to price range mapping (VND per night)
    BUDGET_RANGES = {
        "tiết kiệm": (0, 800_000),
        "trung bình": (500_000, 2_500_000),
        "sang trọng": (2_000_000, 50_000_000)
    }
    
    # Keywords for hotel types
    HOTEL_TYPES = {
        "resort": ["resort", "khu nghỉ dưỡng"],
        "homestay": ["homestay", "nhà nghỉ", "phòng trọ"],
        "hotel": ["hotel", "khách sạn"],
        "villa": ["villa", "biệt thự"]
    }
    
    @property
    def expert_type(self) -> str:
        return "hotel_expert"
    
    def __init__(self, mongo_client=None, vector_client=None, llm_client=None):
        """Initialize HotelExpert"""
        super().__init__(mongo_client, vector_client, llm_client)
        
        # [NEW] Initialize Hybrid Search
        if HotelExpert._hybrid_search is None:
            try:
                from app.services.hybrid_search import hybrid_search_service
                HotelExpert._hybrid_search = hybrid_search_service
                logger.info("✅ HotelExpert: Hybrid Search initialized")
            except Exception as e:
                logger.error(f"❌ HotelExpert failed to init Hybrid Search: {e}")
                HotelExpert._hybrid_search = False  # Mark as attempted but failed
    
    def execute(self, query: str, parameters: Dict[str, Any]) -> ExpertResult:
        """
        Find hotels
        
        Parameters:
            - location: Province/city name
            - budget: Max budget in VND
            - budget_level: tiết kiệm/trung bình/sang trọng
            - keywords: Additional search keywords (e.g., "view biển")
            - nights: Number of nights
            - limit: Max results (default 10)
        """
        start_time = time.time()
        
        try:
            location = parameters.get("location")
            budget = parameters.get("budget")
            budget_level = parameters.get("budget_level")
            keywords = parameters.get("keywords", [])
            limit = parameters.get("limit", 5)
            original_query = parameters.get("original_query", query)
            
            # Normalize location
            province_id = self._normalize_location(location)
            
            # Determine price range
            min_price, max_price = self._get_price_range(budget, budget_level)
            
            logger.info(f"🔍 HotelExpert: province={province_id}, price={min_price}-{max_price}")
            
            # [NEW] Try Hybrid Search first if available
            if HotelExpert._hybrid_search and HotelExpert._hybrid_search is not False:
                logger.info("   🚀 Using Hybrid Search for hotels...")
                try:
                    hotels = HotelExpert._hybrid_search.search_hotels(
                        query=original_query,  # Use original query for semantic search
                        province_id=province_id,
                        limit=limit,
                        threshold=0.3,  # Moderate threshold
                        max_price=max_price if max_price else None,
                        min_price=min_price if min_price else None
                    )
                    
                    if hotels:
                        elapsed = time.time() - start_time
                        logger.info(f"   ✅ Hybrid Search returned {len(hotels)} hotels ({elapsed:.2f}s)")
                        
                        return ExpertResult(
                            expert_type=self.expert_type,
                            success=True,
                            data=hotels,
                            metadata={
                                "count": len(hotels),
                                "source": "hybrid_search",
                                "elapsed": elapsed
                            }
                        )
                except Exception as e:
                    logger.error(f"   ❌ Hybrid Search failed: {e}")
                    # Fall through to legacy search
            
            # [FALLBACK] Legacy search if Hybrid not available
            logger.info("   ⚙️ Using legacy keyword search...")
            
            # Search in MongoDB by province_id
            results = self._search_mongo(
                province_id=province_id,
                min_price=min_price,
                max_price=max_price,
                keywords=keywords,
                query=query,
                limit=limit
            )
            
            # Fallback: geo-search if no results and location has known coords
            if not results and location:
                location_slug = self._make_slug(location)
                if location_slug in self.LOCATION_COORDS:
                    lat, lng = self.LOCATION_COORDS[location_slug]
                    logger.info(f"🗺️ HotelExpert: Fallback geo-search near {location} ({lat}, {lng})")
                    results = self._search_by_geo(
                        lat=lat,
                        lng=lng,
                        radius_km=30,  # Search within 30km
                        min_price=min_price,
                        max_price=max_price,
                        limit=limit
                    )
            
            execution_time = int((time.time() - start_time) * 1000)
            
            # Generate summary
            summary = self._generate_summary(results, location, budget_level)
            
            return ExpertResult(
                expert_type=self.expert_type,
                success=True,
                data=results,
                summary=summary,
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            logger.error(f"❌ HotelExpert error: {e}")
            return ExpertResult(
                expert_type=self.expert_type,
                success=False,
                data=[],
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000)
            )
    
    def _get_price_range(self, budget: int = None, budget_level: str = None) -> tuple:
        """Get min/max price based on budget parameters"""
        
        if budget_level and budget_level.lower() in self.BUDGET_RANGES:
            return self.BUDGET_RANGES[budget_level.lower()]
        
        if budget:
            # Estimate per-night budget as 30% of total
            per_night = budget * 0.3
            return (0, int(per_night))
        
        # Default: all price ranges
        return (0, 50_000_000)
    
    def _search_mongo(
        self,
        province_id: str,
        min_price: int,
        max_price: int,
        keywords: List[str],
        query: str,
        limit: int
    ) -> List[Dict]:
        """Search hotels in MongoDB"""
        
        if self.mongo is None:
            return []
        
        try:
            collection = self.mongo.get_collection("hotels")
            if collection is None:
                return []
            
            # Build query
            mongo_query = {}
            
            if province_id:
                mongo_query["province_id"] = province_id
            
            # Price filter
            mongo_query["price"] = {"$gte": min_price, "$lte": max_price}
            
            # Keyword search in name, facilities, address
            if keywords:
                or_conditions = []
                for kw in keywords:
                    or_conditions.extend([
                        {"name": {"$regex": kw, "$options": "i"}},
                        {"facilities": {"$regex": kw, "$options": "i"}},
                        {"address": {"$regex": kw, "$options": "i"}}
                    ])
                if or_conditions:
                    mongo_query["$or"] = or_conditions
            else:
                # Search using query text
                query_words = query.lower().split()
                important_words = [w for w in query_words if len(w) > 2 and w not in ["khách", "sạn", "hotel", "tìm", "ở", "đâu"]]
                
                if important_words:
                    or_conditions = []
                    for word in important_words:
                        or_conditions.extend([
                            {"name": {"$regex": word, "$options": "i"}},
                            {"facilities": {"$regex": word, "$options": "i"}}
                        ])
                    if or_conditions:
                        mongo_query["$or"] = or_conditions
            
            # Execute query - sort by rating desc, then price asc
            cursor = collection.find(mongo_query).sort([
                ("rating", -1),
                ("price", 1)
            ]).limit(limit * 2)
            
            results = []
            for doc in cursor:
                results.append({
                    "id": str(doc.get("_id")),
                    "name": doc.get("name"),
                    "province_id": doc.get("province_id"),
                    "address": doc.get("address", ""),
                    "price": doc.get("price", 0),
                    "price_formatted": f"{doc.get('price', 0):,.0f} VNĐ/đêm",
                    "rating": doc.get("rating", 0),
                    "facilities": doc.get("facilities", ""),
                    "image": doc.get("image_url") or doc.get("image", ""),
                    "latitude": doc.get("latitude"),
                    "longitude": doc.get("longitude"),
                    "source": "mongodb"
                })
            
            return results[:limit]
            
        except Exception as e:
            logger.error(f"❌ MongoDB hotel search error: {e}")
            return []
    
    def _generate_summary(self, results: List[Dict], location: str, budget_level: str) -> str:
        """Generate a brief summary of found hotels"""
        if not results:
            return f"Không tìm thấy khách sạn phù hợp ở {location or 'khu vực này'}"
        
        avg_price = sum(r.get("price", 0) for r in results) / len(results)
        top_hotels = [r.get("name", "?") for r in results[:2]]
        
        budget_text = f" ({budget_level})" if budget_level else ""
        
        return f"Tìm thấy {len(results)} khách sạn{budget_text} tại {location or 'Việt Nam'}. Giá trung bình: {avg_price:,.0f} VNĐ/đêm. Gợi ý: {', '.join(top_hotels)}"
    
    def _make_slug(self, text: str) -> str:
        """Convert text to slug format for lookup"""
        import re
        if not text:
            return ""
        
        slug = text.lower().strip()
        
        # Vietnamese character mapping
        char_map = {
            'à': 'a', 'á': 'a', 'ả': 'a', 'ã': 'a', 'ạ': 'a',
            'ă': 'a', 'ằ': 'a', 'ắ': 'a', 'ẳ': 'a', 'ẵ': 'a', 'ặ': 'a',
            'â': 'a', 'ầ': 'a', 'ấ': 'a', 'ẩ': 'a', 'ẫ': 'a', 'ậ': 'a',
            'đ': 'd',
            'è': 'e', 'é': 'e', 'ẻ': 'e', 'ẽ': 'e', 'ẹ': 'e',
            'ê': 'e', 'ề': 'e', 'ế': 'e', 'ể': 'e', 'ễ': 'e', 'ệ': 'e',
            'ì': 'i', 'í': 'i', 'ỉ': 'i', 'ĩ': 'i', 'ị': 'i',
            'ò': 'o', 'ó': 'o', 'ỏ': 'o', 'õ': 'o', 'ọ': 'o',
            'ô': 'o', 'ồ': 'o', 'ố': 'o', 'ổ': 'o', 'ỗ': 'o', 'ộ': 'o',
            'ơ': 'o', 'ờ': 'o', 'ớ': 'o', 'ở': 'o', 'ỡ': 'o', 'ợ': 'o',
            'ù': 'u', 'ú': 'u', 'ủ': 'u', 'ũ': 'u', 'ụ': 'u',
            'ư': 'u', 'ừ': 'u', 'ứ': 'u', 'ử': 'u', 'ữ': 'u', 'ự': 'u',
            'ỳ': 'y', 'ý': 'y', 'ỷ': 'y', 'ỹ': 'y', 'ỵ': 'y',
        }
        
        for vn_char, ascii_char in char_map.items():
            slug = slug.replace(vn_char, ascii_char)
        
        slug = re.sub(r'\s+', '-', slug)
        slug = re.sub(r'[^a-z0-9-]', '', slug)
        
        return slug
    
    def _search_by_geo(
        self,
        lat: float,
        lng: float,
        radius_km: float,
        min_price: int,
        max_price: int,
        limit: int
    ) -> List[Dict]:
        """
        Search hotels by geographic proximity using Haversine formula approximation.
        MongoDB doesn't have built-in geo index, so we filter in Python.
        """
        if self.mongo is None:
            return []
        
        try:
            collection = self.mongo.get_collection("hotels")
            if collection is None:
                return []
            
            # Approximate bounding box (1 degree ≈ 111 km)
            lat_delta = radius_km / 111.0
            lng_delta = radius_km / (111.0 * abs(cos(radians(lat))))
            
            # Query with bounding box for efficiency
            mongo_query = {
                "latitude": {"$gte": lat - lat_delta, "$lte": lat + lat_delta},
                "longitude": {"$gte": lng - lng_delta, "$lte": lng + lng_delta},
                "price": {"$gte": min_price, "$lte": max_price}
            }
            
            cursor = collection.find(mongo_query).limit(limit * 3)  # Get extra for distance filtering
            
            results = []
            for doc in cursor:
                doc_lat = doc.get("latitude")
                doc_lng = doc.get("longitude")
                
                if doc_lat and doc_lng:
                    # Calculate actual distance
                    distance = self._haversine(lat, lng, doc_lat, doc_lng)
                    
                    if distance <= radius_km:
                        results.append({
                            "id": str(doc.get("_id")),
                            "name": doc.get("name"),
                            "province_id": doc.get("province_id"),
                            "address": doc.get("address", ""),
                            "price": doc.get("price", 0),
                            "price_formatted": f"{doc.get('price', 0):,.0f} VNĐ/đêm",
                            "rating": doc.get("rating", 0),
                            "facilities": doc.get("facilities", ""),
                            "image": doc.get("image_url") or doc.get("image", ""),
                            "latitude": doc_lat,
                            "longitude": doc_lng,
                            "distance_km": round(distance, 1),
                            "source": "mongodb_geo"
                        })
            
            # Sort by distance, then rating
            results.sort(key=lambda x: (x.get("distance_km", 999), -x.get("rating", 0)))
            
            logger.info(f"🗺️ Geo-search found {len(results)} hotels within {radius_km}km")
            
            return results[:limit]
            
        except Exception as e:
            logger.error(f"❌ Geo-search error: {e}")
            return []
    
    def _haversine(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calculate distance between two points in km using Haversine formula"""
        R = 6371  # Earth's radius in km
        
        lat1_rad = radians(lat1)
        lat2_rad = radians(lat2)
        delta_lat = radians(lat2 - lat1)
        delta_lng = radians(lng2 - lng1)
        
        a = sin(delta_lat/2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lng/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        
        return R * c
