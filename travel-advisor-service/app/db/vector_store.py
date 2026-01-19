"""
Vector store manager with fallback support
Supports ChromaDB (if available) or in-memory cosine similarity
"""

import os
import numpy as np
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
from app.core import settings, logger

# Try to import ChromaDB (optional)
CHROMADB_AVAILABLE = False
try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    # Test if chromadb actually works with current pydantic
    _ = chromadb.PersistentClient  # This will fail if incompatible
    CHROMADB_AVAILABLE = True
    logger.info("ChromaDB is available")
except ImportError:
    logger.warning("ChromaDB not installed, using embedding-only mode")
except Exception as e:
    logger.warning(f"ChromaDB not compatible: {e}, using embedding-only mode")


class VectorStoreManager:
    """Vector store manager with fallback support"""
    
    def __init__(self):
        self.client = None
        self.embedding_model = None
        self.collection = None
        self._connected = False
        self._use_chromadb = CHROMADB_AVAILABLE
    
    def connect(self):
        """Connect and load embedding model"""
        if self._connected:
            return
            
        try:
            # Load embedding model first (always needed)
            logger.info(f"🔌 Loading embedding model: {settings.EMBEDDING_MODEL}")
            self.embedding_model = SentenceTransformer(
                settings.EMBEDDING_MODEL,
                device=settings.EMBEDDING_DEVICE
            )
            logger.info("✅ Embedding model ready!")
            
            # Try ChromaDB if available
            if self._use_chromadb:
                try:
                    if settings.CHROMA_HOST == "localhost":
                        # Ensure directory exists
                        os.makedirs(settings.CHROMA_PERSIST_DIR, exist_ok=True)
                        self.client = chromadb.PersistentClient(
                            path=settings.CHROMA_PERSIST_DIR
                        )
                    else:
                        self.client = chromadb.HttpClient(
                            host=settings.CHROMA_HOST,
                            port=settings.CHROMA_PORT
                        )
                    
                    # Get or create collection
                    self.collection = self.client.get_or_create_collection(
                        name="travel_documents",
                        metadata={"description": "Travel spots and hotels"}
                    )
                    
                    doc_count = self.collection.count()
                    logger.info(f"✅ ChromaDB connected: {doc_count} docs")
                    
                except Exception as e:
                    logger.warning(f"ChromaDB failed: {e}, using embedding-only mode")
                    self._use_chromadb = False
                    self.client = None
                    self.collection = None
            
            self._connected = True
            
        except Exception as e:
            logger.error(f"❌ Vector store init failed: {e}")
            raise
    
    def embed_text(self, text: str) -> List[float]:
        """Embed text using sentence transformer"""
        if not self.embedding_model:
            self.connect()
        return self.embedding_model.encode(text).tolist()
    
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple texts"""
        if not self.embedding_model:
            self.connect()
        embeddings = self.embedding_model.encode(texts)
        return [e.tolist() for e in embeddings]
    
    def search(self, query: str, k: int = 5, filters: dict = None) -> Dict[str, Any]:
        """Search vector store"""
        if not self._connected:
            self.connect()
        
        # Embed query
        query_embedding = self.embed_text(query)
        
        # If ChromaDB available, use it
        if self._use_chromadb and self.collection:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=k,
                where=filters if filters else None
            )
            return results
        
        # Otherwise return empty (will use MongoDB search instead)
        return {
            "ids": [[]],
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]]
        }
    
    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        a = np.array(vec1)
        b = np.array(vec2)
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))
    
    def rank_by_similarity(
        self, 
        query: str, 
        documents: List[Dict[str, Any]], 
        text_field: str = "content",
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Rank documents by semantic similarity to query"""
        if not documents:
            return []
        
        if not self._connected:
            self.connect()
        
        # Get query embedding
        query_embedding = self.embed_text(query)
        
        # Get document texts
        doc_texts = []
        for doc in documents:
            text = doc.get(text_field, "") or doc.get("name", "") or str(doc)
            doc_texts.append(text)
        
        # Embed all documents
        doc_embeddings = self.embed_texts(doc_texts)
        
        # Calculate similarities
        scored_docs = []
        for i, doc in enumerate(documents):
            similarity = self.cosine_similarity(query_embedding, doc_embeddings[i])
            scored_docs.append({
                **doc,
                "_similarity": similarity
            })
        
        # Sort by similarity descending
        scored_docs.sort(key=lambda x: x["_similarity"], reverse=True)
        
        return scored_docs[:top_k]
    
    def health_check(self) -> bool:
        """Check if vector store is healthy"""
        try:
            if not self._connected:
                return False
            if self._use_chromadb and self.client:
                self.client.heartbeat()
            return True
        except Exception:
            return False


# Singleton instance
vector_store = VectorStoreManager()


def get_vector_store() -> VectorStoreManager:
    """Get vector store instance"""
    return vector_store
