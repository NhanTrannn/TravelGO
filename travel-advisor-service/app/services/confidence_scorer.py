"""
Confidence Scoring System - Đánh giá độ tin cậy của kết quả từ database

Quyết định khi nào cần fallback sang web search
"""

import logging
from typing import List, Dict, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class ConfidenceLevel(Enum):
    """Mức độ tin cậy của kết quả"""
    HIGH = "high"           # 0.8 - 1.0: Rất tin cậy, không cần web search
    MEDIUM = "medium"       # 0.5 - 0.8: Tương đối tin cậy, có thể bổ sung web search
    LOW = "low"             # 0.3 - 0.5: Ít tin cậy, nên dùng web search
    VERY_LOW = "very_low"   # 0.0 - 0.3: Rất ít tin cậy, bắt buộc web search


class ConfidenceScorer:
    """Calculate confidence score for database results"""
    
    def __init__(self):
        self.min_expected_results = {
            'spots': 5,      # Ít nhất 5 địa điểm
            'hotels': 3,     # Ít nhất 3 khách sạn
            'food': 3,       # Ít nhất 3 nhà hàng
            'transport': 2   # Ít nhất 2 phương tiện
        }
        
        self.threshold_high = 0.8
        self.threshold_medium = 0.5
        self.threshold_low = 0.3
    
    def calculate_confidence(self,
                           results: List[Any],
                           data_type: str,
                           query: str,
                           province: Optional[str] = None,
                           theme: Optional[str] = None) -> Dict[str, Any]:
        """
        Tính confidence score dựa trên nhiều yếu tố
        
        Args:
            results: Kết quả từ database
            data_type: Loại dữ liệu (spots, hotels, food, transport)
            query: Query gốc của user
            province: Tỉnh/thành phố
            theme: Theme/chủ đề (biển, núi, lịch sử, etc.)
            
        Returns:
            Dict with:
                - score: float (0.0 - 1.0)
                - level: ConfidenceLevel
                - should_use_web_search: bool
                - reason: str (lý do)
        """
        try:
            score = 0.0
            reasons = []
            
            # Factor 1: Số lượng kết quả (40 điểm)
            result_count = len(results)
            min_expected = self.min_expected_results.get(data_type, 3)
            
            if result_count == 0:
                score += 0.0
                reasons.append(f"❌ Không có kết quả nào (cần {min_expected})")
            elif result_count < min_expected:
                score += 0.2
                reasons.append(f"⚠️ Quá ít kết quả ({result_count}/{min_expected})")
            elif result_count >= min_expected * 2:
                score += 0.4
                reasons.append(f"✅ Nhiều kết quả ({result_count} items)")
            else:
                score += 0.3
                reasons.append(f"✓ Đủ kết quả ({result_count} items)")
            
            # Factor 2: Chất lượng dữ liệu (30 điểm)
            data_quality = self._assess_data_quality(results, data_type)
            score += data_quality * 0.3
            
            if data_quality > 0.8:
                reasons.append("✅ Dữ liệu chất lượng cao")
            elif data_quality > 0.5:
                reasons.append("✓ Dữ liệu chấp nhận được")
            else:
                reasons.append("⚠️ Dữ liệu thiếu thông tin")
            
            # Factor 3: Relevance với query (20 điểm)
            relevance = self._assess_relevance(results, query, theme)
            score += relevance * 0.2
            
            if relevance > 0.7:
                reasons.append("✅ Rất liên quan đến query")
            elif relevance > 0.4:
                reasons.append("✓ Liên quan đến query")
            else:
                reasons.append("⚠️ Ít liên quan đến query")
            
            # Factor 4: Completeness (10 điểm)
            if province and theme:
                score += 0.1
                reasons.append("✓ Có đầy đủ context")
            elif province or theme:
                score += 0.05
            
            # Determine confidence level
            if score >= self.threshold_high:
                level = ConfidenceLevel.HIGH
                should_search = False
            elif score >= self.threshold_medium:
                level = ConfidenceLevel.MEDIUM
                should_search = False  # Optional, có thể bổ sung
            elif score >= self.threshold_low:
                level = ConfidenceLevel.LOW
                should_search = True
            else:
                level = ConfidenceLevel.VERY_LOW
                should_search = True
            
            return {
                'score': round(score, 2),
                'level': level.value,
                'should_use_web_search': should_search,
                'reason': ' | '.join(reasons),
                'result_count': result_count,
                'min_expected': min_expected
            }
            
        except Exception as e:
            logger.error(f"Error calculating confidence: {e}")
            return {
                'score': 0.0,
                'level': ConfidenceLevel.VERY_LOW.value,
                'should_use_web_search': True,
                'reason': f"Error: {str(e)}"
            }
    
    def _assess_data_quality(self, results: List[Any], data_type: str) -> float:
        """Đánh giá chất lượng dữ liệu"""
        if not results:
            return 0.0
        
        quality_score = 0.0
        count = 0
        
        for result in results[:10]:  # Check first 10 results
            score = 0.0
            
            if data_type == 'spots':
                # Check required fields for spots
                if hasattr(result, 'name') and result.name:
                    score += 0.3
                if hasattr(result, 'description') and result.description and len(result.description) > 50:
                    score += 0.3
                if hasattr(result, 'location') and result.location:
                    score += 0.2
                if hasattr(result, 'tags') and result.tags:
                    score += 0.2
            
            elif data_type == 'hotels':
                # Check required fields for hotels
                if hasattr(result, 'name') and result.name:
                    score += 0.3
                if hasattr(result, 'price') and result.price:
                    score += 0.2
                if hasattr(result, 'address') and result.address:
                    score += 0.2
                if hasattr(result, 'rating') and result.rating:
                    score += 0.3
            
            elif data_type == 'food':
                # Check required fields for food
                if hasattr(result, 'name') and result.name:
                    score += 0.3
                if hasattr(result, 'type') and result.type:
                    score += 0.3
                if hasattr(result, 'description') and result.description:
                    score += 0.2
                if hasattr(result, 'price_range') and result.price_range:
                    score += 0.2
            
            quality_score += score
            count += 1
        
        return quality_score / count if count > 0 else 0.0
    
    def _assess_relevance(self, results: List[Any], query: str, theme: Optional[str]) -> float:
        """Đánh giá độ liên quan với query"""
        if not results:
            return 0.0
        
        query_lower = query.lower()
        theme_lower = theme.lower() if theme else ""
        
        # Extract keywords from query
        keywords = [word for word in query_lower.split() if len(word) > 2]
        
        relevance_score = 0.0
        count = 0
        
        for result in results[:10]:
            score = 0.0
            
            # Get searchable text from result
            text = ""
            if hasattr(result, 'name'):
                text += f" {result.name} "
            if hasattr(result, 'description'):
                text += f" {result.description} "
            if hasattr(result, 'tags'):
                text += f" {' '.join(result.tags)} " if isinstance(result.tags, list) else f" {result.tags} "
            
            text = text.lower()
            
            # Check keyword matches
            matches = sum(1 for keyword in keywords if keyword in text)
            score += min(matches / len(keywords), 1.0) * 0.6 if keywords else 0.3
            
            # Check theme match
            if theme_lower and theme_lower in text:
                score += 0.4
            
            relevance_score += score
            count += 1
        
        return relevance_score / count if count > 0 else 0.0


# Global instance
confidence_scorer = ConfidenceScorer()


def should_use_web_search(results: List[Any],
                         data_type: str,
                         query: str,
                         province: Optional[str] = None,
                         theme: Optional[str] = None) -> tuple[bool, Dict[str, Any]]:
    """
    Convenience function to check if web search is needed
    
    Returns:
        (should_search: bool, confidence_info: dict)
    
    Usage:
        should_search, info = should_use_web_search(
            results=spots,
            data_type='spots',
            query="địa điểm lịch sử ở Huế",
            province="Thừa Thiên Huế",
            theme="lịch sử"
        )
        
        if should_search:
            print(f"Need web search: {info['reason']}")
            web_results = web_search_agent.search(...)
    """
    confidence = confidence_scorer.calculate_confidence(
        results=results,
        data_type=data_type,
        query=query,
        province=province,
        theme=theme
    )
    
    return confidence['should_use_web_search'], confidence
