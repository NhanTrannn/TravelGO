"""
Hybrid Search Service - Combines MongoDB filtering + FAISS semantic search
Strategy: Filter first (MongoDB) → Semantic search (FAISS) → Rank & return
"""

import os
import pickle
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
from difflib import SequenceMatcher

from app.core import logger
from app.db import mongodb_manager


class HybridSearchService:
    """
    Hybrid Search: MongoDB metadata filtering + FAISS semantic search
    
    Workflow:
    1. User query → Extract filters (province, budget, etc.)
    2. MongoDB: Filter by metadata (province_id, price range, rating)
    3. FAISS: Semantic search on filtered results
    4. Post-ranking: Combine semantic score + popularity (rating, reviews)
    """
    
    def __init__(
        self,
        model_name: str = "keepitreal/vietnamese-sbert",
        index_dir: Optional[str] = None
    ):
        self.model_name = model_name
        
        # Use absolute path to avoid issues with working directory
        if index_dir is None:
            # Get project root (travel-advisor-service/)
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            index_dir = os.path.join(project_root, "data", "faiss_indexes")
        
        self.index_dir = index_dir
        
        # Load embedding model
        logger.info(f"📦 Loading embedding model for search: {model_name}")
        self.model = SentenceTransformer(model_name)
        # Cache for loaded indexes
        self._index_cache: Dict[str, Tuple[faiss.Index, List[Dict]]] = {}
        
        # Location to province_slug mapping (for FAISS index lookup)
        self.location_to_province = {
            "phú quốc": "kien-giang",
            "phu quoc": "kien-giang",
            "nha trang": "khanh-hoa",
            "đà lạt": "lam-dong",
            "da lat": "lam-dong",
            "hội an": "quang-nam",
            "hoi an": "quang-nam",
            "sapa": "lao-cai",
            "sa pa": "lao-cai",
            "vũng tàu": "ba-ria-vung-tau",
            "vung tau": "ba-ria-vung-tau",
            "đà nẵng": "da-nang",
            "da nang": "da-nang",
            "hà nội": "ha-noi",
            "ha noi": "ha-noi",
            "hồ chí minh": "ho-chi-minh",
            "ho chi minh": "ho-chi-minh",
            "sài gòn": "ho-chi-minh",
            "saigon": "ho-chi-minh",
        }
    
    def _resolve_province_slug(self, location: str) -> Optional[str]:
        """
        Resolve location name to province_slug for FAISS index lookup
        
        Args:
            location: Location name (e.g., "Phú Quốc", "Nha Trang")
        
        Returns:
            Province slug (e.g., "kien-giang", "khanh-hoa") or None
        """
        if not location:
            return None
        
        # Normalize
        location_lower = location.lower().strip()
        
        # Direct match
        if location_lower in self.location_to_province:
            return self.location_to_province[location_lower]
        
        # Fuzzy match (in case user types "phu quốc" instead of "phú quốc")
        import unicodedata
        def normalize(s):
            s = s.lower().strip().replace('đ', 'd')
            return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
        
        location_norm = normalize(location_lower)
        for key, slug in self.location_to_province.items():
            if normalize(key) == location_norm:
                return slug
        
        return None
    
    def _fuzzy_match_score(self, query: str, text: str) -> float:
        """
        Calculate fuzzy matching score between query and text
        Helps when user types without diacritics (e.g., "Nha Tho" vs "Nhà Thờ")
        
        Returns:
            Score between 0 and 1
        """
        import unicodedata
        
        # Normalize both strings (remove diacritics, lowercase, strip)
        def normalize(s):
            s = s.lower().strip()
            # Manual Vietnamese character replacements
            s = s.replace('đ', 'd')
            # Remove diacritics
            s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
            return s
        
        query_norm = normalize(query)
        text_norm = normalize(text)
        
        # Exact match after normalization
        if query_norm == text_norm:
            return 1.0
        
        # Contains match
        if query_norm in text_norm or text_norm in query_norm:
            return 0.95
        
        # Word-level matching (split by space)
        query_words = set(query_norm.split())
        text_words = set(text_norm.split())
        
        if query_words and text_words:
            # Jaccard similarity on words
            intersection = len(query_words & text_words)
            union = len(query_words | text_words)
            word_score = intersection / union if union > 0 else 0
            
            # If >50% words match, boost
            if word_score > 0.5:
                return 0.7 + (word_score * 0.3)
        
        # Sequence matching (character-level)
        return SequenceMatcher(None, query_norm, text_norm).ratio()
    
    def _load_index(
        self,
        doc_type: str,
        province_id: str = None
    ) -> Tuple[Optional[faiss.Index], Optional[List[Dict]]]:
        """
        Load FAISS index and metadata from disk
        
        Args:
            doc_type: "spots" or "hotels"
            province_id: Province ID (e.g., "da-nang") or None for global
        
        Returns:
            (faiss_index, metadata_list) or (None, None) if not found
        """
        cache_key = f"{doc_type}_{province_id if province_id else 'all'}"
        
        # Check cache
        if cache_key in self._index_cache:
            return self._index_cache[cache_key]
        
        # Load from disk
        index_path = os.path.join(self.index_dir, f"{cache_key}.faiss")
        metadata_path = os.path.join(self.index_dir, f"{cache_key}_metadata.pkl")
        
        # Debug: Check file existence
        logger.info(f"   📁 Index path: {index_path}")
        logger.info(f"   📁 Exists: {os.path.exists(index_path)}")
        
        if not os.path.exists(index_path) or not os.path.exists(metadata_path):
            logger.warning(f"⚠️ Index not found: {cache_key}")
            logger.info(f"   Run: python -m app.services.vector_indexer to build indexes")
            return None, None
        
        # Load index with workaround for Windows paths with spaces/Unicode
        # FAISS on Windows has issues with paths containing spaces or Unicode characters
        # Solution: Change working directory temporarily
        index_path_normalized = os.path.normpath(index_path)
        original_cwd = os.getcwd()
        try:
            # Use relative path from index directory
            os.chdir(self.index_dir)
            index = faiss.read_index(f"{cache_key}.faiss")
        finally:
            os.chdir(original_cwd)
        with open(metadata_path, 'rb') as f:
            metadata = pickle.load(f)
        
        logger.info(f"📂 Loaded index: {cache_key} ({index.ntotal} vectors)")
        
        # Cache it
        self._index_cache[cache_key] = (index, metadata)
        
        return index, metadata
    
    def _filter_by_metadata(
        self,
        metadata_list: List[Dict[str, Any]],
        filters: Dict[str, Any]
    ) -> List[int]:
        """
        Filter metadata by criteria and return valid indices
        
        Args:
            metadata_list: List of metadata dicts
            filters: Dict with filter criteria
                - min_rating: float
                - max_price: int
                - min_price: int
                - min_reviews: int (for spots)
                - free_only: bool (for spots)
        
        Returns:
            List of valid indices in metadata_list
        """
        valid_indices = []
        
        for idx, meta in enumerate(metadata_list):
            # Rating filter
            if 'min_rating' in filters:
                rating = meta.get('rating')
                if rating is None or rating == 'None':
                    rating = 0.0
                else:
                    try:
                        rating = float(rating)
                    except:
                        rating = 0.0
                
                if rating < filters['min_rating']:
                    continue
            
            # Price filters (for hotels)
            if 'max_price' in filters:
                price = meta.get('price')
                if price and price > filters['max_price']:
                    continue
            
            if 'min_price' in filters:
                price = meta.get('price')
                if price and price < filters['min_price']:
                    continue
            
            # Reviews filter (for spots)
            if 'min_reviews' in filters:
                reviews = meta.get('reviews_count', 0)
                if reviews < filters['min_reviews']:
                    continue
            
            # Free only filter (for spots)
            if filters.get('free_only', False):
                cost = meta.get('cost', '').lower()
                if 'miễn phí' not in cost and 'free' not in cost:
                    continue
            
            valid_indices.append(idx)
        
        return valid_indices
    
    def _mongodb_fallback_hotels(
        self,
        query: str,
        province_id: Optional[str] = None,
        limit: int = 10,
        min_rating: Optional[float] = None,
        max_price: Optional[float] = None,
        min_price: Optional[float] = None
    ) -> List[Dict]:
        """
        Fallback to MongoDB search when FAISS index not available
        Uses text search + filters
        """
        logger.info("   🔄 MongoDB fallback: Searching hotels directly...")
        
        # Build MongoDB query
        mongo_query = {}
        
        if province_id:
            mongo_query['province_id'] = province_id
        
        if min_rating is not None:
            mongo_query['rating'] = {'$gte': min_rating}
        
        if max_price is not None or min_price is not None:
            price_query = {}
            if max_price:
                price_query['$lte'] = max_price
            if min_price:
                price_query['$gte'] = min_price
            mongo_query['price'] = price_query
        
        # Text search on name and description
        if query and len(query.strip()) > 0:
            mongo_query['$or'] = [
                {'name': {'$regex': query, '$options': 'i'}},
                {'description': {'$regex': query, '$options': 'i'}},
                {'location': {'$regex': query, '$options': 'i'}}
            ]
        
        # Query MongoDB
        hotels = list(mongodb_manager.db.hotels.find(
            mongo_query,
            {'_id': 0}  # Exclude MongoDB _id
        ).limit(limit))
        
        logger.info(f"   ✅ Found {len(hotels)} hotels via MongoDB fallback")
        
        # Add dummy scores for compatibility
        for hotel in hotels:
            hotel['score'] = hotel.get('rating', 5.0) / 10.0
            hotel['match_type'] = 'mongodb_fallback'
        
        return hotels
    
    def _mongodb_fallback_spots(
        self,
        query: str,
        province_id: Optional[str] = None,
        limit: int = 10,
        category: Optional[str] = None
    ) -> List[Dict]:
        """
        Fallback to MongoDB search when FAISS index not available
        """
        logger.info("   🔄 MongoDB fallback: Searching spots directly...")
        
        # Build MongoDB query
        mongo_query = {}
        
        if province_id:
            mongo_query['province_id'] = province_id
        
        if category:
            mongo_query['category'] = category
        
        # Text search
        if query and len(query.strip()) > 0:
            mongo_query['$or'] = [
                {'name': {'$regex': query, '$options': 'i'}},
                {'description': {'$regex': query, '$options': 'i'}},
                {'category': {'$regex': query, '$options': 'i'}}
            ]
        
        # Query MongoDB
        spots = list(mongodb_manager.db.spots_detailed.find(
            mongo_query,
            {'_id': 0}
        ).limit(limit))
        
        logger.info(f"   ✅ Found {len(spots)} spots via MongoDB fallback")
        
        # Add dummy scores
        for spot in spots:
            spot['score'] = spot.get('rating', 8.0) / 10.0
            spot['match_type'] = 'mongodb_fallback'
        
        return spots
    
    def search_spots(
        self,
        query: str,
        province_id: str = None,
        k: int = 10,
        limit: int = None,  # Alias for k
        threshold: float = None,  # Minimum semantic score filter
        min_rating: float = None,
        min_reviews: int = None,
        free_only: bool = False,
        alpha: float = 0.7  # Weight for semantic score (1-alpha for popularity)
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search for tourist spots
        
        Args:
            query: User query (semantic search)
            province_id: Filter by province (e.g., "da-nang")
            k: Number of results to return (default 10)
            limit: Alias for k (for compatibility)
            threshold: Minimum semantic_score (0-1) to include result
            min_rating: Minimum rating filter
            min_reviews: Minimum reviews count filter
            free_only: Only return free spots
            alpha: Weight for semantic similarity (0-1)
        
        Returns:
            List of spots with metadata + scores
        """
        # Resolve limit/k
        result_limit = limit if limit is not None else k
        
        # Auto-resolve province_slug from query if not provided
        province_slug = province_id
        if not province_slug:
            province_slug = self._resolve_province_slug(query)
            if province_slug:
                logger.info(f"   📍 Auto-resolved '{query}' → province_slug='{province_slug}'")
        
        logger.info(f"🔍 Hybrid search (spots): query='{query}', province={province_slug}")
        
        # Load index with resolved province_slug
        index, metadata = self._load_index("spots", province_slug)
        
        if index is None or metadata is None:
            logger.warning("   ⚠️ FAISS index not available, fallback to MongoDB")
            return self._mongodb_fallback_spots(
                query=query,
                province_id=province_slug,
                limit=result_limit,
                category=category
            )
        
        # Apply metadata filters
        filters = {}
        if min_rating is not None:
            filters['min_rating'] = min_rating
        if min_reviews is not None:
            filters['min_reviews'] = min_reviews
        if free_only:
            filters['free_only'] = True
        
        valid_indices = self._filter_by_metadata(metadata, filters)
        
        if len(valid_indices) == 0:
            logger.info("   ⚠️ No spots match metadata filters")
            return []
        
        logger.info(f"   📊 After metadata filtering: {len(valid_indices)}/{len(metadata)} spots")
        
        # ========================================================================
        # STRATEGY: Hybrid Semantic + Fuzzy Search
        # ========================================================================
        # 1. Semantic search (FAISS): Good for descriptive queries, natural language
        # 2. Fuzzy search (normalize): Good for exact names, place names without diacritics
        # 3. Merge and re-rank by best score
        
        # STEP 1: Semantic Search via FAISS
        query_embedding = self.model.encode([query], convert_to_numpy=True)
        faiss.normalize_L2(query_embedding)
        
        search_k = min(result_limit * 10, len(valid_indices))  # Get 10x candidates
        distances, indices = index.search(query_embedding, search_k)
        
        # STEP 2: Pure Fuzzy Search (scan all valid spots)
        # Only do this if query looks like a specific name (short query)
        fuzzy_candidates = []
        query_word_count = len(query.split())
        if query_word_count <= 8:  # Allow longer queries for place names with city
            for idx in valid_indices:
                meta = metadata[idx]
                fuzzy_score = self._fuzzy_match_score(query, meta.get('name', ''))
                if fuzzy_score > 0.6:  # Strong match
                    fuzzy_candidates.append((idx, fuzzy_score))
            
            # Sort by fuzzy score
            fuzzy_candidates.sort(key=lambda x: x[1], reverse=True)
        
        # STEP 3: Merge results from both search paths
        seen_indices = set()
        results = []
        
        # First add fuzzy matches (prioritize exact name matches)
        for idx, fuzzy_score in fuzzy_candidates[:result_limit * 2]:  # Get more fuzzy candidates
            if idx in seen_indices:
                continue
            seen_indices.add(idx)
            
            meta = metadata[idx]
            # Use fuzzy score as semantic score (high priority)
            semantic_score = fuzzy_score * 0.95  # Slightly reduce to allow semantic override
            
            # Calculate popularity score
            rating = meta.get('rating')
            if rating is None or rating == 'None':
                rating = 0.0
            else:
                try:
                    rating = float(rating)
                except:
                    rating = 0.0
            
            reviews = meta.get('reviews_count', 0)
            popularity_score = (rating / 10.0) * 0.7 + min(np.log1p(reviews) / 10.0, 0.3)
            
            # Combined score
            final_score = alpha * semantic_score + (1 - alpha) * popularity_score
            
            results.append({
                **meta,
                'semantic_score': semantic_score,
                'popularity_score': popularity_score,
                'final_score': final_score,
                'score': final_score,
                'match_type': 'fuzzy'
            })
        
        # Then add semantic matches
        for dist, idx in zip(distances[0], indices[0]):
            if idx not in valid_indices or idx in seen_indices:
                continue
            seen_indices.add(idx)
            
            meta = metadata[idx]
            
            # Calculate combined score
            semantic_score = float(dist)  # Cosine similarity (0-1)
            
            # Check fuzzy score (may boost semantic)
            fuzzy_score = self._fuzzy_match_score(query, meta.get('name', ''))
            if fuzzy_score > 0.6:
                semantic_score = max(semantic_score, fuzzy_score * 0.9)
            
            # Calculate popularity score
            rating = meta.get('rating')
            if rating is None or rating == 'None':
                rating = 0.0
            else:
                try:
                    rating = float(rating)
                except:
                    rating = 0.0
            
            reviews = meta.get('reviews_count', 0)
            popularity_score = (rating / 10.0) * 0.7 + min(np.log1p(reviews) / 10.0, 0.3)
            
            # Combined score
            final_score = alpha * semantic_score + (1 - alpha) * popularity_score
            
            # Apply threshold filter if specified
            if threshold is not None and semantic_score < threshold:
                continue
            
            results.append({
                **meta,
                'semantic_score': semantic_score,
                'popularity_score': popularity_score,
                'final_score': final_score,
                'score': final_score,
                'match_type': 'semantic'
            })
        
        # Sort by final score
        results.sort(key=lambda x: x['final_score'], reverse=True)
        
        logger.info(f"   ✅ Hybrid search returned {len(results)} spots")
        
        return results[:result_limit]
    
    def search_hotels(
        self,
        query: str,
        province_id: str = None,
        k: int = 10,
        limit: int = None,  # Alias for k
        threshold: float = None,  # Minimum semantic score filter
        min_rating: float = None,
        max_price: int = None,
        min_price: int = None,
        alpha: float = 0.6  # Lower alpha for hotels (price matters more)
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search for hotels
        
        Args:
            query: User query (semantic search)
            province_id: Filter by province (e.g., "da-nang")
            k: Number of results to return (default 10)
            limit: Alias for k (for compatibility)
            threshold: Minimum semantic_score (0-1) to include result
            min_rating: Minimum rating filter
            max_price: Maximum price filter (VNĐ)
            min_price: Minimum price filter (VNĐ)
            alpha: Weight for semantic similarity (0-1)
        
        Returns:
            List of hotels with metadata + scores
        """
        # Resolve limit/k
        result_limit = limit if limit is not None else k
        
        # Auto-resolve province_slug from query if not provided
        # e.g., "Phú Quốc" → "kien-giang"
        province_slug = province_id
        if not province_slug:
            province_slug = self._resolve_province_slug(query)
            if province_slug:
                logger.info(f"   📍 Auto-resolved '{query}' → province_slug='{province_slug}'")
        
        logger.info(f"🔍 Hybrid search (hotels): query='{query}', province={province_slug}")
        
        # Load index with resolved province_slug
        index, metadata = self._load_index("hotels", province_slug)
        
        if index is None or metadata is None:
            logger.warning("   ⚠️ FAISS index not available, fallback to MongoDB search")
            return self._mongodb_fallback_hotels(
                query=query,
                province_id=province_slug,
                limit=result_limit,
                min_rating=min_rating,
                max_price=max_price,
                min_price=min_price
            )
        
        # Apply metadata filters
        filters = {}
        if min_rating is not None:
            filters['min_rating'] = min_rating
        if max_price is not None:
            filters['max_price'] = max_price
        if min_price is not None:
            filters['min_price'] = min_price
        
        valid_indices = self._filter_by_metadata(metadata, filters)
        
        if len(valid_indices) == 0:
            logger.info("   ⚠️ No hotels match metadata filters")
            return []
        
        logger.info(f"   📊 After metadata filtering: {len(valid_indices)}/{len(metadata)} hotels")
        
        # ========================================================================
        # STRATEGY: Hybrid Semantic + Fuzzy Search (same as spots)
        # ========================================================================
        # 1. Semantic search (FAISS): Good for descriptive queries
        # 2. Fuzzy search (normalize): Good for exact hotel names without diacritics
        # 3. Merge and re-rank by best score
        
        # STEP 1: Semantic Search via FAISS
        query_embedding = self.model.encode([query], convert_to_numpy=True)
        faiss.normalize_L2(query_embedding)
        
        search_k = min(result_limit * 10, len(valid_indices))  # Get 10x candidates
        distances, indices = index.search(query_embedding, search_k)
        
        # STEP 2: Pure Fuzzy Search (scan all valid hotels)
        fuzzy_candidates = []
        query_word_count = len(query.split())
        if query_word_count <= 8:  # Allow hotel names with location
            for idx in valid_indices:
                meta = metadata[idx]
                fuzzy_score = self._fuzzy_match_score(query, meta.get('name', ''))
                if fuzzy_score > 0.6:  # Strong match
                    fuzzy_candidates.append((idx, fuzzy_score))
            
            # Sort by fuzzy score
            fuzzy_candidates.sort(key=lambda x: x[1], reverse=True)
        
        # STEP 3: Merge results from both search paths
        seen_indices = set()
        results = []
        
        # First add fuzzy matches (prioritize exact name matches)
        for idx, fuzzy_score in fuzzy_candidates[:result_limit * 2]:
            if idx in seen_indices:
                continue
            seen_indices.add(idx)
            
            meta = metadata[idx]
            # Use fuzzy score as semantic score (high priority)
            semantic_score = fuzzy_score * 0.95
            
            # Calculate price score
            price = meta.get('price')
            if price is None or price == 'None':
                price_score = 0.0
            else:
                try:
                    price = float(price)
                    # Normalize price (lower is better for hotels)
                    price_score = max(0, 1.0 - (price / 10000000))  # 10M VND as max
                except:
                    price_score = 0.0
            
            # Combined score
            final_score = alpha * semantic_score + (1 - alpha) * price_score
            
            results.append({
                **meta,
                'semantic_score': semantic_score,
                'price_score': price_score,
                'final_score': final_score,
                'score': final_score,
                'match_type': 'fuzzy'
            })
        
        # Then add semantic matches
        for dist, idx in zip(distances[0], indices[0]):
            if idx not in valid_indices or idx in seen_indices:
                continue
            seen_indices.add(idx)
        # Then add semantic matches
        for dist, idx in zip(distances[0], indices[0]):
            if idx not in valid_indices or idx in seen_indices:
                continue
            seen_indices.add(idx)
            
            meta = metadata[idx]
            
            # Calculate combined score
            semantic_score = float(dist)
            
            # Check fuzzy score (may boost semantic)
            fuzzy_score = self._fuzzy_match_score(query, meta.get('name', ''))
            if fuzzy_score > 0.6:
                semantic_score = max(semantic_score, fuzzy_score * 0.9)
            
            # Calculate price score
            price = meta.get('price')
            if price is None or price == 'None':
                price_score = 0.0
            else:
                try:
                    price = float(price)
                    price_score = max(0, 1.0 - (price / 10000000))
                except:
                    price_score = 0.0
            
            # Combined score
            final_score = alpha * semantic_score + (1 - alpha) * price_score
            
            # Apply threshold filter if specified
            if threshold is not None and semantic_score < threshold:
                continue
            
            results.append({
                **meta,
                'semantic_score': semantic_score,
                'price_score': price_score,
                'final_score': final_score,
                'score': final_score,
                'match_type': 'semantic'
            })
        
        # Sort by final score
        results.sort(key=lambda x: x['final_score'], reverse=True)
        
        logger.info(f"   ✅ Hybrid search returned {len(results)} hotels")
        
        return results[:result_limit]


# Global instance
hybrid_search_service = HybridSearchService()
