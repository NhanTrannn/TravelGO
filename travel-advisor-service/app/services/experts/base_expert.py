"""
Base Expert - Abstract class for all expert executors
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from app.core import logger


@dataclass
class ExpertResult:
    """Result from an expert execution"""
    expert_type: str
    success: bool
    data: List[Dict[str, Any]]
    summary: str = ""
    error: Optional[str] = None
    execution_time_ms: int = 0
    metadata: Optional[Dict[str, Any]] = None  # For additional info (confidence, web_search, etc.)


class BaseExpert(ABC):
    """
    Base class for all Expert Executors
    Each expert specializes in one type of retrieval/generation
    """
    
    def __init__(self, mongo_manager=None, vector_store=None, llm_client=None):
        self.mongo = mongo_manager
        self.vector = vector_store
        self.llm = llm_client
    
    @property
    @abstractmethod
    def expert_type(self) -> str:
        """Return expert type identifier"""
        pass
    
    @abstractmethod
    def execute(self, query: str, parameters: Dict[str, Any]) -> ExpertResult:
        """
        Execute the expert's task
        
        Args:
            query: The reformulated query for this task
            parameters: Task-specific parameters
            
        Returns:
            ExpertResult with retrieved data
        """
        pass
    
    # Province aliases mapping to database province_id
    # IMPORTANT: Map to actual province_id values in MongoDB hotels collection
    PROVINCE_ALIASES = {
        # Alias -> database province_id (based on actual data)
        "sa-pa": "lao-cai",      # Sapa is in Lao Cai province (115 hotels)
        "sapa": "lao-cai",       # Alternative spelling
        "sa pa": "lao-cai",
        "phu-quoc": "kien-giang", # Phu Quoc is in Kien Giang
        "hue": "thua-thien-hue",  # Hue city -> Thua Thien Hue province (113 hotels)
        "nha-trang": "khanh-hoa", # Nha Trang is in Khanh Hoa
        "da-lat": "lam-dong",     # Da Lat is in Lam Dong
        "dalat": "lam-dong",      # Alternative spelling
        "hoi-an": "quang-nam",    # Hoi An is in Quang Nam province (306 hotels)
        "hoian": "quang-nam",     # Alternative spelling
        "phan-thiet": "binh-thuan", # Phan Thiet is in Binh Thuan
        "vung-tau": "ba-ria-vung-tau",
        "ha-long": "quang-ninh",   # Ha Long bay is in Quang Ninh
        "halong": "quang-ninh",
        "mui-ne": "binh-thuan",    # Mui Ne is in Binh Thuan
        "cat-ba": "hai-phong",     # Cat Ba island is in Hai Phong
    }
    
    # Known location coordinates for geo-search fallback
    LOCATION_COORDS = {
        "hoi-an": (15.8794, 108.3350),
        "hue": (16.4637, 107.5909),
        "da-nang": (16.0544, 108.2022),
        "nha-trang": (12.2388, 109.1967),
        "da-lat": (11.9404, 108.4583),
        "phu-quoc": (10.2276, 103.9632),
        "sa-pa": (22.3364, 103.8438),
        "ha-long": (20.9511, 107.0807),
        "phan-thiet": (10.9289, 108.1028),
        "vung-tau": (10.3460, 107.0843),
        "ha-noi": (21.0285, 105.8542),
        "ho-chi-minh": (10.8231, 106.6297),
    }
    
    def _normalize_location(self, location: str) -> str:
        """Normalize location to province_id format (slug)"""
        if not location:
            return None
        
        # Simple normalization
        import re
        
        # Remove common suffixes
        location = re.sub(r"\s*(tỉnh|thành phố|tp\.?)\s*", "", location, flags=re.IGNORECASE)
        
        # Convert to slug
        slug = location.lower().strip()
        
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
        
        # Replace spaces with dashes
        slug = re.sub(r'\s+', '-', slug)
        
        # Remove non-alphanumeric characters except dashes
        slug = re.sub(r'[^a-z0-9-]', '', slug)
        
        # Apply alias mapping
        if slug in self.PROVINCE_ALIASES:
            slug = self.PROVINCE_ALIASES[slug]
        
        return slug
