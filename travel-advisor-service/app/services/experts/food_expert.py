"""
Food Expert - Retrieves food recommendations and restaurants
"""

import time
from typing import Dict, Any, List
from .base_expert import BaseExpert, ExpertResult
from app.core import logger


class FoodExpert(BaseExpert):
    """
    Expert for finding food and restaurants
    Uses keyword matching on spots with food-related content
    """
    
    # Food keywords for filtering
    FOOD_KEYWORDS = [
        "quán", "nhà hàng", "restaurant", "ăn", "món", 
        "bún", "phở", "cơm", "bánh", "chả", "nem",
        "hải sản", "seafood", "cafe", "cà phê", "coffee",
        "bia", "bar", "pub", "đặc sản", "ẩm thực"
    ]
    
    # Regional specialties mapping
    REGIONAL_FOODS = {
        "thua-thien-hue": ["bún bò huế", "cơm hến", "bánh bèo", "bánh nậm", "nem lụi"],
        "da-nang": ["mì quảng", "bánh tráng cuốn thịt heo", "bún chả cá"],
        "ha-noi": ["phở", "bún chả", "chả cá lã vọng", "bánh cuốn", "bún thang"],
        "ho-chi-minh": ["hủ tiếu", "bánh mì", "cơm tấm", "phở"],
        "kien-giang": ["bún quậy", "bún kèn", "hải sản phú quốc"],
        "khanh-hoa": ["bánh căn", "bún cá", "nem nướng ninh hòa"],
        "lam-dong": ["bánh tráng nướng đà lạt", "atiso", "dâu tây"],
        "quang-nam": ["cao lầu", "mì quảng", "cơm gà hội an"]
    }
    
    @property
    def expert_type(self) -> str:
        return "food_expert"
    
    def execute(self, query: str, parameters: Dict[str, Any]) -> ExpertResult:
        """
        Find food/restaurants
        
        Parameters:
            - location: Province/city name
            - keywords: Specific food keywords (e.g., "bún bò")
            - budget_level: tiết kiệm/trung bình/sang trọng
            - limit: Max results (default 5)
        """
        start_time = time.time()
        
        try:
            location = parameters.get("location")
            keywords = parameters.get("keywords", [])
            budget_level = parameters.get("budget_level")
            limit = parameters.get("limit", 5)
            
            # Normalize location
            province_id = self._normalize_location(location)
            
            logger.info(f"🔍 FoodExpert: province={province_id}, keywords={keywords}")
            
            # Build search keywords
            search_keywords = self._build_search_keywords(query, keywords, province_id)
            
            # Search in spots collection (food-related spots)
            mongo_results = self._search_mongo(province_id, search_keywords, limit)
            
            # Filter: Only use MongoDB results if they are legitimate restaurants
            # Otherwise, use LLM-based recommendations only
            results = []
            
            if mongo_results and len(mongo_results) > 0:
                # Validate that results are actually food-related
                valid_results = [r for r in mongo_results if self._is_valid_restaurant(r)]
                if len(valid_results) >= 2:  # At least 2 valid restaurants
                    results = valid_results[:limit]
            
            # If no good MongoDB data, use regional specialties + LLM recommendations
            if len(results) == 0 and province_id:
                specialties = self._get_regional_specialties(province_id)
                if specialties:
                    # Return food recommendations instead of fake restaurants
                    results.append({
                        "id": f"specialty-{province_id}",
                        "name": f"Đặc sản {location or province_id}",
                        "type": "recommendation",
                        "description": f"Các món nên thử khi đến {location}",
                        "dishes": specialties,
                        "source": "local_knowledge"
                    })
                    
                # Could add LLM-generated restaurant list here in the future
                if self.llm and len(results) == 1:
                    logger.info("⚠️  No real restaurant data, using recommendations only")
            
            execution_time = int((time.time() - start_time) * 1000)
            
            # Generate summary
            summary = self._generate_summary(results, location, keywords)
            
            return ExpertResult(
                expert_type=self.expert_type,
                success=True,
                data=results,
                summary=summary,
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            logger.error(f"❌ FoodExpert error: {e}")
            return ExpertResult(
                expert_type=self.expert_type,
                success=False,
                data=[],
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000)
            )
    
    def _build_search_keywords(self, query: str, keywords: List[str], province_id: str) -> List[str]:
        """Build search keywords including regional foods"""
        all_keywords = set(keywords)
        
        # Extract food keywords from query
        query_lower = query.lower()
        for food_kw in self.FOOD_KEYWORDS:
            if food_kw in query_lower:
                all_keywords.add(food_kw)
        
        # Add regional specialties
        if province_id and province_id in self.REGIONAL_FOODS:
            for specialty in self.REGIONAL_FOODS[province_id]:
                if specialty.lower() in query_lower:
                    all_keywords.add(specialty)
        
        # If no specific keywords, add general food keywords
        if not all_keywords:
            all_keywords.update(["quán", "ăn", "nhà hàng"])
        
        return list(all_keywords)
    
    def _search_mongo(self, province_id: str, keywords: List[str], limit: int) -> List[Dict]:
        """Search food-related spots in MongoDB"""
        
        if self.mongo is None:
            return []
        
        try:
            collection = self.mongo.get_collection("spots_detailed")
            if collection is None:
                return []
            
            # Build query for food-related spots
            mongo_query = {}
            
            if province_id:
                mongo_query["province_id"] = province_id
            
            # Search in name and description for food keywords
            or_conditions = []
            for kw in keywords:
                or_conditions.extend([
                    {"name": {"$regex": kw, "$options": "i"}},
                    {"description_short": {"$regex": kw, "$options": "i"}},
                    {"description_full": {"$regex": kw, "$options": "i"}}
                ])
            
            if or_conditions:
                mongo_query["$or"] = or_conditions
            
            # Execute query
            cursor = collection.find(mongo_query).sort("rating", -1).limit(limit * 5)  # Get more to filter
            
            results = []
            for doc in cursor:
                # STRICT FILTER: Check if it's actually food-related
                name = doc.get("name", "").lower()
                desc_short = doc.get("description_short", "").lower()
                desc_full = doc.get("description_full", "").lower()
                
                # Must contain at least one strong food keyword
                strong_food_keywords = [
                    "nhà hàng", "restaurant", "quán ăn", "quán", "ăn", "món",
                    "bún", "phở", "cơm", "bánh", "chả", "nem",
                    "hải sản", "seafood", "cafe", "cà phê", "buffet"
                ]
                
                is_food = any(
                    kw in name or kw in desc_short or kw in desc_full
                    for kw in strong_food_keywords
                )
                
                # Skip non-food spots (landmarks, markets, bridges, etc.)
                non_food_keywords = [
                    "bảo tàng", "museum", "nhà thờ", "church", "chùa", "temple",
                    "cung", "palace", "di tích", "monument", "công viên", "park",
                    "cầu", "bridge", "chợ", "market", "đỉnh", "núi", "mountain",
                    "bãi biển", "beach", "vịnh", "bay", "hồ", "lake", "suối", "stream"
                ]
                
                is_non_food = any(
                    kw in name.lower()
                    for kw in non_food_keywords
                )
                
                if is_food and not is_non_food and len(results) < limit:
                    results.append({
                        "id": doc.get("id"),
                        "name": doc.get("name"),
                        "type": "restaurant",
                        "province_id": doc.get("province_id"),
                        "description": doc.get("description_short", "")[:200],
                        "image": doc.get("image"),
                        "rating": doc.get("rating", 0),
                        "address": doc.get("address", ""),
                        "cost": doc.get("cost", ""),
                        "source": "mongodb"
                    })
                
                if len(results) >= limit:
                    break
            
            return results
            
        except Exception as e:
            logger.error(f"❌ MongoDB search error: {e}")
            return []
    
    def _is_valid_restaurant(self, result: Dict) -> bool:
        """Validate if result is actually a restaurant/food spot"""
        name = result.get("name", "").lower()
        desc = result.get("description", "").lower()
        
        # Strong indicators it's a restaurant
        restaurant_indicators = [
            "nhà hàng", "restaurant", "quán", "ăn",
            "buffet", "cafe", "bar", "pub"
        ]
        
        has_restaurant_indicator = any(ind in name or ind in desc for ind in restaurant_indicators)
        
        # Strong indicators it's NOT a restaurant
        non_restaurant_keywords = [
            "bảo tàng", "museum", "nhà thờ", "church", "chùa", "temple",
            "cầu", "bridge", "chợ", "market", "đỉnh", "núi", "bãi biển",
            "vịnh", "cung", "di tích"
        ]
        
        is_non_restaurant = any(kw in name for kw in non_restaurant_keywords)
        
        return has_restaurant_indicator and not is_non_restaurant
    
    def _get_regional_specialties(self, province_id: str) -> List[str]:
        """Get regional specialty dishes"""
        return self.REGIONAL_FOODS.get(province_id, [])
    
    def _generate_summary(self, results: List[Dict], location: str, keywords: List[str]) -> str:
        """Generate a brief summary of found food spots"""
        if not results:
            return f"Không tìm thấy quán ăn phù hợp ở {location or 'khu vực này'}"
        
        food_spots = [r for r in results if r.get("type") != "recommendation"]
        keywords_str = f" ({', '.join(keywords)})" if keywords else ""
        
        if food_spots:
            top_places = [r.get("name", "?") for r in food_spots[:2]]
            return f"Tìm thấy {len(food_spots)} địa điểm ăn uống{keywords_str} tại {location or 'Việt Nam'}. Gợi ý: {', '.join(top_places)}"
        
        return f"Gợi ý ẩm thực cho {location or 'khu vực này'}"
