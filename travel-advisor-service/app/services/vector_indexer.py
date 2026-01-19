"""
Vector Indexer - Build FAISS index for Spots & Hotels
Using Parent Document Retrieval strategy for tourism data
"""

import os
import json
import pickle
import numpy as np
from typing import List, Dict, Any, Tuple
from sentence_transformers import SentenceTransformer
import faiss
from app.db.mongo import MongoDBManager
from app.core import logger


class VectorIndexer:
    """
    Build and manage FAISS index for semantic search
    Strategy: Parent Document Retrieval
    - Each spot/hotel is embedded as a complete "representation document"
    - Format: "Tên: [Name]. Loại: [Category]. Mô tả: [Description]. Địa chỉ: [Address]"
    """
    
    def __init__(
        self,
        model_name: str = "keepitreal/vietnamese-sbert",
        index_dir: str = "data/faiss_indexes"
    ):
        self.model_name = model_name
        self.index_dir = index_dir
        
        # Create index directory
        os.makedirs(index_dir, exist_ok=True)
        
        # Load embedding model
        logger.info(f"📦 Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        logger.info(f"   ✅ Model loaded - Embedding dimension: {self.embedding_dim}")
        
        # MongoDB connection
        self.mongo = MongoDBManager()
        self.mongo.connect()
    
    def _create_representation_document(
        self,
        doc: Dict[str, Any],
        doc_type: str = "spot"
    ) -> str:
        """
        Create representation document for embedding
        
        Strategy: Concatenate key fields with labels for semantic understanding
        
        Args:
            doc: MongoDB document (spot or hotel)
            doc_type: "spot" or "hotel"
        
        Returns:
            Formatted string for embedding
        """
        if doc_type == "spot":
            # For tourist spots
            name = doc.get('name', '')
            category = doc.get('category') or 'Địa điểm du lịch'
            desc_short = doc.get('description_short', '')
            desc_full = doc.get('description_full', '')
            address = doc.get('address', '')
            cost = doc.get('cost', '')
            
            # Use short description if available, else use first 200 chars of full
            description = desc_short if desc_short else (desc_full[:200] if desc_full else '')
            
            # Build representation
            parts = [
                f"Tên địa điểm: {name}",
                f"Loại hình: {category}",
                f"Mô tả: {description}",
            ]
            
            if address:
                parts.append(f"Địa chỉ: {address}")
            if cost and cost not in ['None', 'none', '']:
                parts.append(f"Chi phí: {cost}")
            
            return ". ".join(parts)
        
        elif doc_type == "hotel":
            # For hotels
            name = doc.get('name', '')
            address = doc.get('address', '')
            facilities = doc.get('facilities', '')
            rating = doc.get('rating', '')
            price = doc.get('price', '')
            
            parts = [
                f"Tên khách sạn: {name}",
            ]
            
            if address:
                parts.append(f"Địa chỉ: {address}")
            if facilities:
                parts.append(f"Tiện nghi: {facilities[:150]}")  # Limit facilities text
            if rating:
                parts.append(f"Đánh giá: {rating}/10")
            if price:
                parts.append(f"Giá: {price} VNĐ/đêm")
            
            return ". ".join(parts)
        
        return ""
    
    def build_spots_index(
        self,
        province_id: str = None,
        batch_size: int = 32,
        force_rebuild: bool = False
    ) -> Tuple[faiss.Index, List[Dict[str, Any]]]:
        """
        Build FAISS index for tourist spots
        
        Args:
            province_id: Filter by province (e.g., "da-nang"). None = all provinces
            batch_size: Batch size for encoding
            force_rebuild: Force rebuild even if index exists
        
        Returns:
            (faiss_index, metadata_list)
        """
        index_name = f"spots_{province_id if province_id else 'all'}"
        index_path = os.path.join(self.index_dir, f"{index_name}.faiss")
        metadata_path = os.path.join(self.index_dir, f"{index_name}_metadata.pkl")
        
        # Check if index exists
        if not force_rebuild and os.path.exists(index_path) and os.path.exists(metadata_path):
            logger.info(f"📂 Loading existing index: {index_name}")
            index = faiss.read_index(index_path)
            with open(metadata_path, 'rb') as f:
                metadata = pickle.load(f)
            logger.info(f"   ✅ Loaded {index.ntotal} spots from cache")
            return index, metadata
        
        logger.info(f"🔨 Building FAISS index for spots: {index_name}")
        
        # Query MongoDB
        query = {}
        if province_id:
            query["province_id"] = province_id
        
        # Get spots with valid latitude/longitude
        query["latitude"] = {"$exists": True, "$ne": None, "$ne": "None"}
        query["longitude"] = {"$exists": True, "$ne": None, "$ne": "None"}
        
        spots_col = self.mongo.get_collection("spots_detailed")
        spots = list(spots_col.find(query))
        
        logger.info(f"   📊 Found {len(spots)} spots in database")
        
        if len(spots) == 0:
            logger.warning("   ⚠️ No spots found!")
            return None, []
        
        # Create representation documents
        logger.info("   📝 Creating representation documents...")
        documents = []
        metadata = []
        
        for spot in spots:
            doc_text = self._create_representation_document(spot, "spot")
            if doc_text:
                documents.append(doc_text)
                
                # Store metadata for retrieval
                metadata.append({
                    "id": spot.get('id', str(spot['_id'])),
                    "name": spot.get('name', ''),
                    "category": spot.get('category'),
                    "rating": spot.get('rating'),
                    "latitude": float(spot.get('latitude')) if spot.get('latitude') else None,
                    "longitude": float(spot.get('longitude')) if spot.get('longitude') else None,
                    "address": spot.get('address', ''),
                    "description_short": spot.get('description_short', ''),
                    "image": spot.get('image', ''),
                    "url": spot.get('url', ''),
                    "cost": spot.get('cost', ''),
                    "province_id": spot.get('province_id', ''),
                    "reviews_count": spot.get('reviews_count', 0)
                })
        
        logger.info(f"   ✅ Created {len(documents)} documents")
        
        # Encode documents in batches
        logger.info(f"   🧠 Encoding with {self.model_name}...")
        embeddings = self.model.encode(
            documents,
            batch_size=batch_size,
            show_progress_bar=True,
            convert_to_numpy=True
        )
        
        logger.info(f"   ✅ Encoded {len(embeddings)} embeddings (dim={embeddings.shape[1]})")
        
        # Build FAISS index
        logger.info("   🔧 Building FAISS index...")
        
        # Use IndexFlatIP for cosine similarity (inner product after normalization)
        faiss.normalize_L2(embeddings)
        index = faiss.IndexFlatIP(self.embedding_dim)
        index.add(embeddings)
        
        logger.info(f"   ✅ FAISS index built with {index.ntotal} vectors")
        
        # Save index and metadata
        faiss.write_index(index, index_path)
        with open(metadata_path, 'wb') as f:
            pickle.dump(metadata, f)
        
        logger.info(f"   💾 Saved index to {index_path}")
        logger.info(f"   💾 Saved metadata to {metadata_path}")
        
        return index, metadata
    
    def build_hotels_index(
        self,
        province_id: str = None,
        batch_size: int = 32,
        force_rebuild: bool = False
    ) -> Tuple[faiss.Index, List[Dict[str, Any]]]:
        """
        Build FAISS index for hotels
        
        Args:
            province_id: Filter by province (e.g., "da-nang"). None = all provinces
            batch_size: Batch size for encoding
            force_rebuild: Force rebuild even if index exists
        
        Returns:
            (faiss_index, metadata_list)
        """
        index_name = f"hotels_{province_id if province_id else 'all'}"
        index_path = os.path.join(self.index_dir, f"{index_name}.faiss")
        metadata_path = os.path.join(self.index_dir, f"{index_name}_metadata.pkl")
        
        # Check if index exists
        if not force_rebuild and os.path.exists(index_path) and os.path.exists(metadata_path):
            logger.info(f"📂 Loading existing index: {index_name}")
            index = faiss.read_index(index_path)
            with open(metadata_path, 'rb') as f:
                metadata = pickle.load(f)
            logger.info(f"   ✅ Loaded {index.ntotal} hotels from cache")
            return index, metadata
        
        logger.info(f"🔨 Building FAISS index for hotels: {index_name}")
        
        # Query MongoDB
        query = {}
        if province_id:
            query["province_id"] = province_id
        
        # Get hotels with valid latitude/longitude
        query["latitude"] = {"$exists": True, "$ne": None, "$ne": "None"}
        query["longitude"] = {"$exists": True, "$ne": None, "$ne": "None"}
        
        hotels_col = self.mongo.get_collection("hotels")
        hotels = list(hotels_col.find(query))
        
        logger.info(f"   📊 Found {len(hotels)} hotels in database")
        
        if len(hotels) == 0:
            logger.warning("   ⚠️ No hotels found!")
            return None, []
        
        # Create representation documents
        logger.info("   📝 Creating representation documents...")
        documents = []
        metadata = []
        
        for hotel in hotels:
            doc_text = self._create_representation_document(hotel, "hotel")
            if doc_text:
                documents.append(doc_text)
                
                # Store metadata for retrieval
                metadata.append({
                    "id": str(hotel['_id']),
                    "name": hotel.get('name', ''),
                    "price": hotel.get('price'),
                    "rating": hotel.get('rating'),
                    "latitude": float(hotel.get('latitude')) if hotel.get('latitude') else None,
                    "longitude": float(hotel.get('longitude')) if hotel.get('longitude') else None,
                    "address": hotel.get('address', ''),
                    "facilities": hotel.get('facilities', ''),
                    "image_url": hotel.get('image_url', ''),
                    "url": hotel.get('url', ''),
                    "province_id": hotel.get('province_id', '')
                })
        
        logger.info(f"   ✅ Created {len(documents)} documents")
        
        # Encode documents in batches
        logger.info(f"   🧠 Encoding with {self.model_name}...")
        embeddings = self.model.encode(
            documents,
            batch_size=batch_size,
            show_progress_bar=True,
            convert_to_numpy=True
        )
        
        logger.info(f"   ✅ Encoded {len(embeddings)} embeddings (dim={embeddings.shape[1]})")
        
        # Build FAISS index
        logger.info("   🔧 Building FAISS index...")
        
        # Use IndexFlatIP for cosine similarity
        faiss.normalize_L2(embeddings)
        index = faiss.IndexFlatIP(self.embedding_dim)
        index.add(embeddings)
        
        logger.info(f"   ✅ FAISS index built with {index.ntotal} vectors")
        
        # Save index and metadata
        faiss.write_index(index, index_path)
        with open(metadata_path, 'wb') as f:
            pickle.dump(metadata, f)
        
        logger.info(f"   💾 Saved index to {index_path}")
        logger.info(f"   💾 Saved metadata to {metadata_path}")
        
        return index, metadata
    
    def build_all_indexes(self, provinces: List[str] = None):
        """
        Build indexes for all provinces or specified list
        
        Args:
            provinces: List of province_ids (e.g., ["da-nang", "ha-noi"])
                      None = build for all provinces + one global index
        """
        logger.info("🚀 Building all FAISS indexes...")
        
        if provinces is None:
            # Build one global index for all data
            logger.info("\n📍 Building global indexes...")
            self.build_spots_index(province_id=None)
            self.build_hotels_index(province_id=None)
        else:
            # Build per-province indexes
            for province_id in provinces:
                logger.info(f"\n📍 Building indexes for: {province_id}")
                self.build_spots_index(province_id=province_id)
                self.build_hotels_index(province_id=province_id)
        
        logger.info("\n✅ All indexes built successfully!")
    
    def close(self):
        """Close MongoDB connection"""
        self.mongo.close()


# Build script
if __name__ == "__main__":
    indexer = VectorIndexer()
    
    # Auto-detect all provinces with actual data
    logger.info("🔍 Detecting provinces with data...")
    
    # Get unique province_ids from hotels collection
    hotel_provinces = indexer.mongo.hotels.distinct("province_id")
    
    # Get unique province_ids from spots collection
    spot_provinces = indexer.mongo.spots_detailed.distinct("province_id")
    
    # Combine and filter out None/empty values
    all_provinces = set(hotel_provinces + spot_provinces)
    all_provinces = sorted([p for p in all_provinces if p and p.strip()])
    
    logger.info(f"   ✅ Found {len(all_provinces)} provinces with data:")
    for province in all_provinces:
        hotel_count = indexer.mongo.hotels.count_documents({"province_id": province})
        spot_count = indexer.mongo.spots_detailed.count_documents({"province_id": province})
        logger.info(f"      - {province}: {hotel_count} hotels, {spot_count} spots")
    
    # Build indexes for all provinces with data
    indexer.build_all_indexes(provinces=all_provinces)
    indexer.close()
