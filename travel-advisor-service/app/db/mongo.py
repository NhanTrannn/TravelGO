"""
MongoDB connection manager
"""

from pymongo import MongoClient
from pymongo.database import Database
from app.core import settings, logger


class MongoDBManager:
    """MongoDB connection manager"""
    
    def __init__(self):
        self.client: MongoClient = None
        self.db: Database = None
    
    def connect(self):
        """Connect to MongoDB"""
        try:
            self.client = MongoClient(settings.SPOTS_MONGODB_URI)
            self.db = self.client[settings.SPOTS_DB_NAME]
            
            # Test connection
            self.client.server_info()
            
            logger.info(f"✅ Connected to MongoDB: {settings.SPOTS_DB_NAME}")
            logger.info(f"   - spots_detailed: {self.db['spots_detailed'].count_documents({})} docs")
            logger.info(f"   - hotels: {self.db['hotels'].count_documents({})} docs")
            logger.info(f"   - provinces_info: {self.db['provinces_info'].count_documents({})} docs")
            
        except Exception as e:
            logger.error(f"❌ MongoDB connection failed: {e}")
            raise
    
    def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("🔒 MongoDB connection closed")
    
    def get_collection(self, collection_name: str):
        """Get a collection by name"""
        if self.db is None:
            raise RuntimeError("MongoDB not connected. Call connect() first.")
        return self.db[collection_name]
    
    def health_check(self) -> bool:
        """Check if MongoDB is healthy"""
        try:
            if self.client is None:
                return False
            self.client.server_info()
            return True
        except:
            return False


# Global instance
mongodb_manager = MongoDBManager()


def get_mongodb() -> MongoDBManager:
    """Dependency for FastAPI"""
    return mongodb_manager
