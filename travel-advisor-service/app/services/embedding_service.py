"""
Embedding Service - Handles text chunking, embedding, and semantic search
Uses vietnamese-sbert for Vietnamese text embedding
"""

import numpy as np
from typing import List, Dict, Any, Tuple
from sentence_transformers import SentenceTransformer
from app.core import logger


class EmbeddingService:
    """
    Service for embedding Vietnamese text and semantic search
    
    Features:
    - Text chunking with overlap
    - Vietnamese SBERT embeddings (768-dim)
    - Cosine similarity search
    - Re-ranking with confidence scores
    """
    
    def __init__(self, model_name: str = "keepitreal/vietnamese-sbert"):
        """
        Initialize embedding model
        
        Args:
            model_name: HuggingFace model name (default: vietnamese-sbert)
        """
        try:
            logger.info(f"📦 Loading embedding model: {model_name}")
            self.model = SentenceTransformer(model_name)
            self.embedding_dim = 768
            logger.info(f"✅ Embedding model loaded (dim={self.embedding_dim})")
        except Exception as e:
            logger.error(f"❌ Failed to load embedding model: {e}")
            self.model = None
            self.embedding_dim = 0
    
    def chunk_text(
        self,
        text: str,
        chunk_size: int = 200,
        overlap: int = 50
    ) -> List[str]:
        """
        Chunk text into smaller pieces with overlap
        
        Args:
            text: Input text
            chunk_size: Max characters per chunk
            overlap: Overlap between chunks
            
        Returns:
            List of text chunks
        """
        if not text or len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # Try to break at sentence boundary
            if end < len(text):
                for delimiter in ['. ', '.\n', '! ', '?\n']:
                    last_delim = text[start:end].rfind(delimiter)
                    if last_delim != -1:
                        end = start + last_delim + len(delimiter)
                        break
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - overlap
        
        return chunks
    
    def embed_text(self, text: str) -> np.ndarray:
        """
        Embed single text into vector
        
        Args:
            text: Input text
            
        Returns:
            Embedding vector (768-dim)
        """
        if self.model is None:
            return np.zeros(self.embedding_dim)
        
        try:
            embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding
        except Exception as e:
            logger.error(f"❌ Embedding error: {e}")
            return np.zeros(self.embedding_dim)
    
    def embed_batch(self, texts: List[str], batch_size: int = 8) -> np.ndarray:
        """
        Embed multiple texts in batches (optimized batch_size=8 for speed)
        
        Args:
            texts: List of texts
            batch_size: Batch size for encoding (default 8 for faster processing)
            
        Returns:
            Numpy array of embeddings (n x 768)
        """
        if self.model is None or not texts:
            return np.zeros((len(texts), self.embedding_dim))
        
        try:
            logger.info(f"⏳ Encoding {len(texts)} texts in batches of {batch_size}...")
            embeddings = self.model.encode(
                texts,
                batch_size=batch_size,
                convert_to_numpy=True,
                show_progress_bar=True  # Show progress for long operations
            )
            logger.info(f"✅ Encoded {len(texts)} texts")
            return embeddings
        except Exception as e:
            logger.error(f"❌ Batch embedding error: {e}")
            return np.zeros((len(texts), self.embedding_dim))
    
    def cosine_similarity(
        self,
        query_embedding: np.ndarray,
        doc_embeddings: np.ndarray
    ) -> np.ndarray:
        """
        Compute cosine similarity between query and documents
        
        Args:
            query_embedding: Query vector (768,)
            doc_embeddings: Document vectors (n x 768)
            
        Returns:
            Similarity scores (n,)
        """
        # Normalize vectors
        query_norm = query_embedding / (np.linalg.norm(query_embedding) + 1e-8)
        docs_norm = doc_embeddings / (np.linalg.norm(doc_embeddings, axis=1, keepdims=True) + 1e-8)
        
        # Compute cosine similarity
        similarities = np.dot(docs_norm, query_norm)
        
        return similarities
    
    def chunk_and_embed_spots(
        self,
        spots: List[Dict[str, Any]],
        chunk_size: int = 400,  # Increased to reduce number of chunks
        max_chunks_per_spot: int = 3  # Limit chunks per spot
    ) -> List[Dict[str, Any]]:
        """
        Chunk and embed spot descriptions (optimized for speed)
        
        Args:
            spots: List of spot documents
            chunk_size: Max characters per chunk (increased for fewer chunks)
            max_chunks_per_spot: Max chunks per spot (default 3)
            
        Returns:
            List of enriched spots with embeddings
        """
        if self.model is None:
            return spots
        
        enriched_spots = []
        all_chunks = []
        chunk_to_spot_idx = []  # Track which spot each chunk belongs to
        
        # First pass: Create all chunks
        for spot_idx, spot in enumerate(spots):
            spot_id = spot.get("id", "")
            name = spot.get("name", "")
            desc_short = spot.get("description_short", "")
            desc_full = spot.get("description_full", "")
            tags = spot.get("tags", [])
            
            # Combine text for embedding (limit length)
            combined_text = f"{name}. {desc_short}".strip()
            
            # Add tags context
            if tags:
                tags_text = ", ".join(tags[:5]) if isinstance(tags, list) else str(tags)
                combined_text += f" Tags: {tags_text}"
            
            # Chunk long descriptions (limit chunks)
            chunks = self.chunk_text(combined_text, chunk_size=chunk_size)[:max_chunks_per_spot]
            
            # Store chunks
            for chunk in chunks:
                all_chunks.append(chunk)
                chunk_to_spot_idx.append(spot_idx)
        
        logger.info(f"📦 Chunking complete: {len(all_chunks)} chunks from {len(spots)} spots")
        
        # Second pass: Batch embed all chunks at once (FAST)
        if all_chunks:
            all_embeddings = self.embed_batch(all_chunks, batch_size=8)
            
            # Third pass: Group embeddings by spot
            current_chunk_idx = 0
            for spot_idx, spot in enumerate(spots):
                # Get chunks for this spot
                spot_chunks = []
                spot_chunk_embeddings = []
                
                while current_chunk_idx < len(chunk_to_spot_idx) and chunk_to_spot_idx[current_chunk_idx] == spot_idx:
                    spot_chunks.append(all_chunks[current_chunk_idx])
                    spot_chunk_embeddings.append(all_embeddings[current_chunk_idx])
                    current_chunk_idx += 1
                
                # Compute main embedding (average)
                if spot_chunk_embeddings:
                    main_embedding = np.mean(spot_chunk_embeddings, axis=0)
                else:
                    main_embedding = np.zeros(self.embedding_dim)
                
                enriched_spot = dict(spot)
                enriched_spot["embedding"] = main_embedding
                enriched_spot["chunks"] = spot_chunks
                enriched_spot["chunk_count"] = len(spot_chunks)
                
                enriched_spots.append(enriched_spot)
        
        logger.info(f"✅ Embedded {len(enriched_spots)} spots ({len(all_chunks)} total chunks)")
        return enriched_spots
    
    def semantic_search(
        self,
        query: str,
        spots: List[Dict[str, Any]],
        top_k: int = 10,
        threshold: float = 0.3
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Semantic search for spots based on query
        
        Args:
            query: Search query
            spots: List of spots with embeddings
            top_k: Number of results to return
            threshold: Minimum confidence threshold
            
        Returns:
            List of (spot, confidence_score) tuples
        """
        if self.model is None or not spots:
            return []
        
        # Embed query
        query_embedding = self.embed_text(query)
        
        # Extract spot embeddings
        spot_embeddings = np.array([s.get("embedding", np.zeros(self.embedding_dim)) for s in spots])
        
        # Compute similarities
        similarities = self.cosine_similarity(query_embedding, spot_embeddings)
        
        # Filter by threshold and sort
        results = []
        for idx, sim in enumerate(similarities):
            if sim >= threshold:
                results.append((spots[idx], float(sim)))
        
        # Sort by similarity (descending)
        results.sort(key=lambda x: x[1], reverse=True)
        
        # Log top results for debugging
        if results:
            top_3 = [(r[0].get('name', 'Unknown'), round(r[1], 3)) for r in results[:3]]
            logger.info(f"🔍 Top semantic matches: {top_3}")
        
        return results[:top_k]
    
    def rerank_spots(
        self,
        keyword_results: List[Dict[str, Any]],
        semantic_results: List[Tuple[Dict[str, Any], float]],
        keyword_weight: float = 0.4,
        semantic_weight: float = 0.6
    ) -> List[Dict[str, Any]]:
        """
        Re-rank spots by combining keyword and semantic scores
        
        Args:
            keyword_results: Results from keyword search
            semantic_results: Results from semantic search with scores
            keyword_weight: Weight for keyword score (default 0.4)
            semantic_weight: Weight for semantic score (default 0.6)
            
        Returns:
            Re-ranked list of spots
        """
        # Build score dict
        scores = {}
        
        # Keyword scores (normalized by position)
        for idx, spot in enumerate(keyword_results):
            spot_id = spot.get("id")
            if spot_id:
                # Position-based score: 1.0 for first, 0.5 for last
                position_score = 1.0 - (idx / max(len(keyword_results), 1))
                scores[spot_id] = {
                    "keyword_score": position_score,
                    "semantic_score": 0.0,
                    "spot": spot
                }
        
        # Semantic scores
        for spot, sim_score in semantic_results:
            spot_id = spot.get("id")
            if spot_id:
                if spot_id in scores:
                    scores[spot_id]["semantic_score"] = sim_score
                else:
                    scores[spot_id] = {
                        "keyword_score": 0.0,
                        "semantic_score": sim_score,
                        "spot": spot
                    }
        
        # Compute combined scores
        ranked_spots = []
        for spot_id, data in scores.items():
            combined_score = (
                keyword_weight * data["keyword_score"] +
                semantic_weight * data["semantic_score"]
            )
            spot = data["spot"]
            spot["confidence"] = round(combined_score, 3)
            ranked_spots.append(spot)
        
        # Sort by combined score
        ranked_spots.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        
        # Apply MMR for diversity
        ranked_spots = self._apply_mmr_diversity(ranked_spots)
        
        logger.info(f"📊 Re-ranked {len(ranked_spots)} spots (keyword_w={keyword_weight}, semantic_w={semantic_weight})")
        
        return ranked_spots
    
    def _apply_mmr_diversity(
        self, 
        spots: List[Dict[str, Any]], 
        lambda_param: float = 0.7,
        max_same_category: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Apply Maximum Marginal Relevance (MMR) to diversify results.
        Ensures variety in categories while maintaining relevance.
        
        Args:
            spots: Ranked list of spots
            lambda_param: Balance between relevance (1.0) and diversity (0.0)
            max_same_category: Maximum spots from same category
        
        Returns:
            Diversified list of spots
        """
        if len(spots) <= 3:
            return spots
        
        # Track category counts for diversity
        category_counts = {}
        diversified = []
        remaining = spots.copy()
        
        # First spot is always the most relevant
        if remaining:
            diversified.append(remaining.pop(0))
            cat = diversified[0].get("category", "other")
            category_counts[cat] = 1
        
        while remaining and len(diversified) < len(spots):
            best_score = -1
            best_idx = 0
            
            for idx, spot in enumerate(remaining):
                relevance = spot.get("confidence", 0)
                cat = spot.get("category", "other")
                
                # Diversity penalty if category is already saturated
                category_penalty = 0
                cat_count = category_counts.get(cat, 0)
                if cat_count >= max_same_category:
                    category_penalty = 0.3  # Significant penalty for over-represented categories
                elif cat_count >= 2:
                    category_penalty = 0.1  # Small penalty
                
                # MMR score = λ * relevance - (1-λ) * max_similarity_to_selected
                # Simplified: we use category as proxy for similarity
                mmr_score = lambda_param * relevance - (1 - lambda_param) * category_penalty
                
                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = idx
            
            # Add best spot
            selected = remaining.pop(best_idx)
            diversified.append(selected)
            cat = selected.get("category", "other")
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        return diversified


def create_embedding_service() -> EmbeddingService:
    """Factory function to create embedding service"""
    return EmbeddingService()
