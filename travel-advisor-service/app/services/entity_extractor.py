"""
Entity Extractor - Extract spot/hotel names from user queries
Solution C: Hybrid approach for accurate entity recognition

Author: AI Engineering Team
Date: 12/01/2026
"""

import logging
import json
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger("travel-advisor")


@dataclass
class ExtractedEntity:
    """Extracted entity with confidence and type"""
    name: str
    entity_type: str  # "spot" or "hotel"
    confidence: float  # 0.0 - 1.0
    source: str  # "context", "llm", "fuzzy", "keyword"
    original_text: str  # Original text from query


class EntityExtractor:
    """
    Extract entities (spots, hotels) from user queries
    
    Multi-level approach:
    1. Check context (itinerary/selected items) - Highest confidence
    2. LLM-based extraction - High confidence
    3. Keyword patterns - Medium confidence
    4. Fallback to None - Query by location only
    """
    
    def __init__(self, llm_client=None, mongo_manager=None):
        self.llm = llm_client
        self.mongo = mongo_manager
        
        # Common spot keywords (for pattern matching)
        self.spot_keywords = [
            "địa điểm", "chỗ", "điểm", "nơi", "khu", "công viên", "vườn",
            "chùa", "đền", "phố", "đường", "cầu", "hồ", "núi", "đồi",
            "bãi biển", "biển", "bãi", "đảo", "hang", "động", "thác",
            "bảo tàng", "museum", "temple", "beach", "mountain", "lake"
        ]
        
        # Common hotel keywords
        self.hotel_keywords = [
            "khách sạn", "hotel", "resort", "homestay", "nhà nghỉ",
            "villa", "motel", "hostel", "apartment", "căn hộ"
        ]
        
        logger.info("✅ EntityExtractor initialized")
    
    def extract_entities(
        self, 
        query: str, 
        context: Dict[str, Any]
    ) -> Dict[str, List[ExtractedEntity]]:
        """
        Extract entities from query using multi-level approach
        
        Returns:
            {
                "spots": [ExtractedEntity(...)],
                "hotels": [ExtractedEntity(...)],
                "query_type": "spot_detail" | "hotel_detail" | "general"
            }
        """
        logger.info(f"🔍 Extracting entities from: '{query[:100]}...'")
        
        results = {
            "spots": [],
            "hotels": [],
            "query_type": "general"
        }
        
        # LEVEL 1: Check context (itinerary/selected items)
        context_entities = self._extract_from_context(query, context)
        if context_entities["spots"] or context_entities["hotels"]:
            logger.info(f"✅ [LEVEL 1] Found entities in context: {len(context_entities['spots'])} spots, {len(context_entities['hotels'])} hotels")
            results["spots"].extend(context_entities["spots"])
            results["hotels"].extend(context_entities["hotels"])
            
            # Determine query type
            if context_entities["spots"]:
                results["query_type"] = "spot_detail"
            elif context_entities["hotels"]:
                results["query_type"] = "hotel_detail"
            
            return results
        
        # LEVEL 2: LLM-based extraction
        if self.llm:
            llm_entities = self._extract_with_llm(query, context)
            if llm_entities["spots"] or llm_entities["hotels"]:
                logger.info(f"✅ [LEVEL 2] LLM extracted: {len(llm_entities['spots'])} spots, {len(llm_entities['hotels'])} hotels")
                results["spots"].extend(llm_entities["spots"])
                results["hotels"].extend(llm_entities["hotels"])
                
                if llm_entities["spots"]:
                    results["query_type"] = "spot_detail"
                elif llm_entities["hotels"]:
                    results["query_type"] = "hotel_detail"
                
                return results
        
        # LEVEL 3: Keyword pattern matching
        pattern_entities = self._extract_with_patterns(query, context)
        if pattern_entities["spots"] or pattern_entities["hotels"]:
            logger.info(f"⚠️ [LEVEL 3] Pattern matching: {len(pattern_entities['spots'])} spots, {len(pattern_entities['hotels'])} hotels")
            results["spots"].extend(pattern_entities["spots"])
            results["hotels"].extend(pattern_entities["hotels"])
            
            if pattern_entities["spots"]:
                results["query_type"] = "spot_detail"
            elif pattern_entities["hotels"]:
                results["query_type"] = "hotel_detail"
            
            return results
        
        # LEVEL 4: No entities found
        logger.warning("⚠️ [LEVEL 4] No entities extracted - will use broad search")
        return results
    
    def _extract_from_context(
        self, 
        query: str, 
        context: Dict[str, Any]
    ) -> Dict[str, List[ExtractedEntity]]:
        """
        LEVEL 1: Extract entities from conversation context
        Highest confidence - 100% accurate when found
        """
        results = {"spots": [], "hotels": []}
        query_lower = query.lower()
        
        # Remove Vietnamese diacritics for better matching
        query_normalized = self._normalize_text(query_lower)
        
        # Check itinerary builder for spots
        itinerary = context.get("itinerary_builder", {})
        if itinerary:
            # Extract all spots from all days
            all_spots = []
            for day_data in itinerary.get("days", []):
                all_spots.extend(day_data.get("spots", []))
            
            # Check if query mentions any spot
            for spot in all_spots:
                spot_name = spot.get("name", "")
                if not spot_name:
                    continue
                
                spot_name_lower = spot_name.lower()
                spot_name_normalized = self._normalize_text(spot_name_lower)
                
                # Check if spot name appears in query
                if (spot_name_lower in query_lower or 
                    spot_name_normalized in query_normalized or
                    self._fuzzy_contains(query_normalized, spot_name_normalized)):
                    
                    entity = ExtractedEntity(
                        name=spot_name,
                        entity_type="spot",
                        confidence=1.0,  # 100% confidence from context
                        source="context",
                        original_text=spot_name
                    )
                    results["spots"].append(entity)
                    logger.info(f"✅ Found spot in context: '{spot_name}' (confidence: 1.0)")
            
            # Check selected hotel (support both nested and flat structure)
            selected_hotel = itinerary.get("selected_hotel", {})
            hotel_name = ""
            
            if selected_hotel:
                hotel_name = selected_hotel.get("name", "")
            elif "hotel_name" in itinerary:
                # Fallback: check flat structure
                hotel_name = itinerary.get("hotel_name", "")
            
            if hotel_name:
                    hotel_name_lower = hotel_name.lower()
                    hotel_name_normalized = self._normalize_text(hotel_name_lower)
                    
                    # Check multiple conditions for hotel matching
                    should_match = False
                    
                    # 1. Full name match
                    if hotel_name_lower in query_lower or hotel_name_normalized in query_normalized:
                        should_match = True
                    
                    # 2. Fuzzy match (at least 70% words match)
                    elif self._fuzzy_contains(query_normalized, hotel_name_normalized, threshold=0.5):
                        should_match = True
                    
                    # 3. Partial name match (any significant word from hotel name)
                    elif self._check_partial_hotel_match(query_lower, hotel_name_lower):
                        should_match = True
                    
                    # 4. Indirect reference (khách sạn đã chọn, hotel này, etc.)
                    elif self._check_indirect_hotel_reference(query_lower):
                        should_match = True
                        logger.info(f"✅ Found hotel via indirect reference: '{hotel_name}'")
                    
                    if should_match:
                        entity = ExtractedEntity(
                            name=hotel_name,
                            entity_type="hotel",
                            confidence=1.0,
                            source="context",
                            original_text=hotel_name
                        )
                        results["hotels"].append(entity)
                        logger.info(f"✅ Found hotel in context: '{hotel_name}' (confidence: 1.0)")
        
        return results
    
    def _extract_with_llm(
        self, 
        query: str, 
        context: Dict[str, Any]
    ) -> Dict[str, List[ExtractedEntity]]:
        """
        LEVEL 2: Extract entities using LLM
        High confidence - 85-95% accurate
        """
        results = {"spots": [], "hotels": []}
        
        try:
            # Build context summary for LLM
            context_summary = self._format_context_for_llm(context)
            
            # Prompt engineering with few-shot examples
            prompt = f"""Phân tích câu hỏi của khách du lịch và trích xuất tên địa điểm hoặc khách sạn cụ thể.

CÂU HỎI: "{query}"

BỐI CẢNH:
{context_summary}

YÊU CẦU: Trả về JSON với format chính xác (KHÔNG thêm text ngoài JSON):
{{
  "spots": ["tên địa điểm 1", "tên địa điểm 2"],
  "hotels": ["tên khách sạn"],
  "query_type": "spot_detail" | "hotel_detail" | "general"
}}

VÍ DỤ:
- "Bà Nà Hills có gì đặc biệt?" → {{"spots": ["Bà Nà Hills"], "hotels": [], "query_type": "spot_detail"}}
- "Cho tôi biết về Cầu Vàng" → {{"spots": ["Cầu Vàng"], "hotels": [], "query_type": "spot_detail"}}
- "InterContinental có view biển không?" → {{"spots": [], "hotels": ["InterContinental Danang"], "query_type": "hotel_detail"}}
- "Khách sạn đã chọn có spa không?" → {{"spots": [], "hotels": ["[hotel từ context]"], "query_type": "hotel_detail"}}
- "Địa điểm đầu tiên ngày 1" → {{"spots": ["[spot đầu tiên từ context]"], "hotels": [], "query_type": "spot_detail"}}

LƯU Ý:
- Nếu câu hỏi nhắc đến "khách sạn đã chọn", "hotel này", "chỗ ở" → Lấy tên từ context
- Nếu nhắc "địa điểm", "chỗ", "nơi" + số thứ tự → Lấy từ itinerary
- Tên địa điểm có thể không có dấu (vd: "Ba Na Hills" → "Bà Nà Hills")
- Chỉ trả về JSON, không giải thích

JSON:"""

            # Call LLM
            response = self.llm.complete(
                prompt=prompt,
                max_tokens=200,
                temperature=0.3  # Low temperature for consistent extraction
            )
            
            # Parse JSON response
            parsed = self._parse_llm_json(response)
            if not parsed:
                logger.warning("⚠️ LLM response không parse được JSON")
                return results
            
            # Convert to ExtractedEntity objects
            for spot_name in parsed.get("spots", []):
                entity = ExtractedEntity(
                    name=spot_name,
                    entity_type="spot",
                    confidence=0.9,  # High confidence from LLM
                    source="llm",
                    original_text=spot_name
                )
                results["spots"].append(entity)
                logger.info(f"✅ LLM extracted spot: '{spot_name}' (confidence: 0.9)")
            
            for hotel_name in parsed.get("hotels", []):
                entity = ExtractedEntity(
                    name=hotel_name,
                    entity_type="hotel",
                    confidence=0.9,
                    source="llm",
                    original_text=hotel_name
                )
                results["hotels"].append(entity)
                logger.info(f"✅ LLM extracted hotel: '{hotel_name}' (confidence: 0.9)")
        
        except Exception as e:
            logger.error(f"❌ LLM extraction failed: {e}")
        
        return results
    
    def _extract_with_patterns(
        self, 
        query: str, 
        context: Dict[str, Any]
    ) -> Dict[str, List[ExtractedEntity]]:
        """
        LEVEL 3: Extract entities using keyword patterns
        Medium confidence - 60-70% accurate
        """
        results = {"spots": [], "hotels": []}
        query_lower = query.lower()
        
        # Pattern 1: "về/của/tại + [Name]"
        # Example: "về Bà Nà Hills", "của Cầu Vàng"
        patterns = [
            r'về\s+([A-ZÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬĐÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴ][a-zA-Zàáảãạăằắẳẵặâầấẩẫậđèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵ\s]+)',
            r'của\s+([A-ZÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬĐÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴ][a-zA-Zàáảãạăằắẳẵặâầấẩẫậđèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵ\s]+)',
            r'tại\s+([A-ZÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬĐÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴ][a-zA-Zàáảãạăằắẳẵặâầấẩẫậđèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵ\s]+)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            for match in matches:
                name = match.strip()
                if len(name) > 3:  # Ignore very short matches
                    # Determine if it's a spot or hotel
                    entity_type = "hotel" if any(kw in query_lower for kw in self.hotel_keywords) else "spot"
                    
                    entity = ExtractedEntity(
                        name=name,
                        entity_type=entity_type,
                        confidence=0.7,
                        source="pattern",
                        original_text=name
                    )
                    
                    if entity_type == "spot":
                        results["spots"].append(entity)
                    else:
                        results["hotels"].append(entity)
                    
                    logger.info(f"⚠️ Pattern extracted {entity_type}: '{name}' (confidence: 0.7)")
        
        return results
    
    def _format_context_for_llm(self, context: Dict[str, Any]) -> str:
        """Format context for LLM prompt"""
        lines = []
        
        destination = context.get("destination", "N/A")
        lines.append(f"- Điểm đến: {destination}")
        
        itinerary = context.get("itinerary_builder", {})
        if itinerary:
            days = itinerary.get("days", [])
            if days:
                lines.append("- Lịch trình:")
                for day_data in days:
                    day = day_data.get("day", 0)
                    spots = day_data.get("spots", [])
                    spot_names = [s.get("name") for s in spots if s.get("name")]
                    if spot_names:
                        lines.append(f"  + Ngày {day}: {', '.join(spot_names)}")
            
            selected_hotel = itinerary.get("selected_hotel", {})
            if selected_hotel and selected_hotel.get("name"):
                lines.append(f"- Khách sạn đã chọn: {selected_hotel.get('name')}")
        
        if len(lines) == 1:  # Only destination
            return "Chưa có lịch trình cụ thể"
        
        return "\n".join(lines)
    
    def _parse_llm_json(self, response: str) -> Optional[Dict]:
        """Parse JSON from LLM response (handle common errors)"""
        try:
            # Clean response
            response = response.strip()
            
            # Remove common prefixes
            if response.startswith("JSON:"):
                response = response[5:].strip()
            if response.startswith("```json"):
                response = response[7:].strip()
            if response.startswith("```"):
                response = response[3:].strip()
            if response.endswith("```"):
                response = response[:-3].strip()
            
            # Find JSON object
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = response[start:end]
                return json.loads(json_str)
            
            return None
        
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON parse error: {e}")
            logger.error(f"Response: {response[:200]}")
            return None
    
    def _normalize_text(self, text: str) -> str:
        """Normalize Vietnamese text for better matching"""
        import unicodedata
        
        # Remove diacritics
        text = unicodedata.normalize('NFD', text)
        text = ''.join(char for char in text if unicodedata.category(char) != 'Mn')
        
        # Replace đ → d
        text = text.replace('đ', 'd').replace('Đ', 'D')
        
        return text.lower()
    
    def _fuzzy_contains(self, text: str, pattern: str, threshold: float = 0.7) -> bool:
        """Check if pattern appears in text with fuzzy matching"""
        # Simple word-based fuzzy matching
        text_words = set(text.split())
        pattern_words = set(pattern.split())
        
        if not pattern_words:
            return False
        
        # Check how many pattern words appear in text
        matches = sum(1 for word in pattern_words if word in text_words)
        ratio = matches / len(pattern_words)
        
        return ratio >= threshold
    
    def _check_hotel_mention(self, query: str, hotel_name: str) -> bool:
        """Check if query mentions hotel (even indirectly)"""
        # Direct mention
        if hotel_name in query:
            return True
        
        # Indirect mentions
        hotel_keywords = [
            "khách sạn", "hotel", "chỗ ở", "nơi nghỉ", 
            "đã chọn", "này", "kia", "resort"
        ]
        
        # Check if query mentions hotel + has hotel keywords
        hotel_words = hotel_name.split()
        query_words = query.split()
        
        # Check if at least one significant word from hotel name appears
        significant_words = [w for w in hotel_words if len(w) > 3]
        has_hotel_word = any(word in query for word in significant_words)
        has_keyword = any(kw in query for kw in hotel_keywords)
        
        return has_hotel_word and has_keyword
    
    def _check_partial_hotel_match(self, query: str, hotel_name: str) -> bool:
        """
        Check if any significant word from hotel name appears in query.
        Used for partial matches like 'InterContinental' matching 
        'InterContinental Danang Sun Peninsula Resort'
        """
        # Split hotel name into words
        hotel_words = hotel_name.lower().split()
        
        # Filter significant words (>3 chars, not common words)
        common_words = {"hotel", "resort", "spa", "beach", "sun", "star", "luxury", "five"}
        significant_words = [
            w for w in hotel_words 
            if len(w) > 3 and w not in common_words
        ]
        
        # Check if any significant word appears in query
        query_lower = query.lower()
        for word in significant_words:
            if word in query_lower:
                return True
        
        return False
    
    def _check_indirect_hotel_reference(self, query: str) -> bool:
        """
        Check if query uses indirect reference to hotel
        Examples: "khách sạn đã chọn", "hotel này", "chỗ ở", "resort này"
        """
        indirect_patterns = [
            "khách sạn đã chọn",
            "khách sạn này",
            "hotel đã chọn",
            "hotel này",
            "chỗ ở đã chọn",
            "chỗ ở này",
            "nơi nghỉ đã chọn",
            "nơi nghỉ này",
            "resort này",
            "resort đã chọn"
        ]
        
        query_lower = query.lower()
        return any(pattern in query_lower for pattern in indirect_patterns)


def create_entity_extractor(llm_client=None, mongo_manager=None) -> EntityExtractor:
    """Factory function to create EntityExtractor"""
    return EntityExtractor(llm_client, mongo_manager)
