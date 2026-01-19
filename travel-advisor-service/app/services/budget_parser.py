"""
Budget Parser - Converts natural language budget to MongoDB filters
Phase 1.2 from Plan-RAG Roadmap
"""

import re
from typing import Dict, Any, Optional, Tuple
from openai import OpenAI
from app.core import settings, logger


class BudgetParser:
    """Parse Vietnamese budget expressions"""
    
    # Budget level ranges (VNĐ per night)
    BUDGET_RANGES = {
        "tiết kiệm": (0, 500_000),
        "bình dân": (500_000, 1_000_000),
        "trung bình": (1_000_000, 2_000_000),
        "cao cấp": (2_000_000, 5_000_000),
        "sang trọng": (5_000_000, float('inf'))
    }
    
    def __init__(self):
        self.llm_client = OpenAI(
            api_key=settings.FPT_API_KEY,
            base_url=settings.FPT_BASE_URL
        )
    
    def parse(self, query: str, budget_level: Optional[str] = None) -> Dict[str, Any]:
        """
        Parse budget from query
        
        Args:
            query: User message
            budget_level: TripState.budget_level
        
        Returns:
            MongoDB filter dict: {"price": {"$gte": X, "$lte": Y}}
        """
        logger.info(f"🔍 Parsing budget from: '{query}'")
        
        # Try pattern-based parsing first (fast)
        filters = self._parse_patterns(query)
        
        if filters:
            logger.info(f"✅ Pattern match: {filters}")
            return filters
        
        # Try budget_level from state
        if budget_level and budget_level in self.BUDGET_RANGES:
            min_price, max_price = self.BUDGET_RANGES[budget_level]
            filters = {"price": {"$gte": min_price, "$lte": max_price}}
            logger.info(f"✅ From budget_level '{budget_level}': {filters}")
            return filters
        
        # Fall back to LLM for complex cases
        filters = self._parse_with_llm(query)
        logger.info(f"✅ LLM parsed: {filters}")
        return filters
    
    def _parse_patterns(self, query: str) -> Optional[Dict[str, Any]]:
        """Pattern-based parsing (fast path)"""
        
        # Normalize (keep decimal points, only remove thousands separators)
        q = query.lower().replace(",", "")
        
        # Pattern 1: "dưới X triệu" / "không quá X triệu"
        match = re.search(r"(?:dưới|không quá|tối đa)\s+([\d.]+)\s*(?:triệu|tr)", q)
        if match:
            max_price = int(float(match.group(1)) * 1_000_000)
            return {"price": {"$lte": max_price}}
        
        # Pattern 2: "trên X triệu" / "từ X triệu"
        match = re.search(r"(?:trên|từ|tối thiểu)\s+([\d.]+)\s*(?:triệu|tr)", q)
        if match:
            min_price = int(float(match.group(1)) * 1_000_000)
            return {"price": {"$gte": min_price}}
        
        # Pattern 3: "khoảng X triệu" / "tầm X triệu" (soft buffer ±10%)
        match = re.search(r"(?:khoảng|tầm|tầm khoảng|xấp xỉ)\s+([\d.]+)\s*(?:triệu|tr)", q)
        if match:
            center = float(match.group(1)) * 1_000_000
            buffer = center * 0.1
            return {
                "price": {
                    "$gte": int(center - buffer),
                    "$lte": int(center + buffer)
                }
            }
        
        # Pattern 4: "từ X đến Y triệu"
        match = re.search(r"từ\s+([\d.]+)\s*(?:đến|-)\s*([\d.]+)\s*(?:triệu|tr)", q)
        if match:
            min_price = int(float(match.group(1)) * 1_000_000)
            max_price = int(float(match.group(2)) * 1_000_000)
            return {
                "price": {
                    "$gte": min_price,
                    "$lte": max_price
                }
            }
        
        # Pattern 5: Budget levels
        for level, (min_p, max_p) in self.BUDGET_RANGES.items():
            if level in q:
                return {"price": {"$gte": min_p, "$lte": max_p}}
        
        return None
    
    def _parse_with_llm(self, query: str) -> Dict[str, Any]:
        """LLM-based parsing for complex cases"""
        
        prompt = f"""Phân tích yêu cầu về giá khách sạn từ câu sau:

"{query}"

Trả về JSON với format:
{{
    "min_price": <số VNĐ hoặc null>,
    "max_price": <số VNĐ hoặc null>
}}

Ví dụ:
- "dưới 2 triệu" → {{"min_price": null, "max_price": 2000000}}
- "tầm 1.5 triệu" → {{"min_price": 1350000, "max_price": 1650000}} (±10%)
- "từ 1 đến 3 triệu" → {{"min_price": 1000000, "max_price": 3000000}}
- "khách sạn giá rẻ" → {{"min_price": null, "max_price": 500000}}

Chỉ trả về JSON, không giải thích."""

        try:
            response = self.llm_client.chat.completions.create(
                model=settings.FPT_MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            
            result = response.choices[0].message.content.strip()
            
            # Parse JSON
            import json
            data = json.loads(result)
            
            # Build filter
            filters = {"price": {}}
            if data.get("min_price"):
                filters["price"]["$gte"] = data["min_price"]
            if data.get("max_price"):
                filters["price"]["$lte"] = data["max_price"]
            
            return filters if filters["price"] else {}
            
        except Exception as e:
            logger.error(f"LLM parsing failed: {e}")
            return {}


# Global instance
budget_parser = BudgetParser()
