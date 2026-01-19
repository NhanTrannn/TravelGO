"""
Query-driven Data Collector
Automatically collects missing data when queries fail, then populates database
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from app.core import logger
from app.db import mongodb_manager


class DataCollectionRequest:
    """Represents a data collection request based on failed query"""
    
    def __init__(self, query: str, province: str, data_type: str, keywords: List[str]):
        self.query = query
        self.province = province
        self.data_type = data_type  # 'spots', 'hotels', 'food', 'transport'
        self.keywords = keywords
        self.timestamp = datetime.now()
        self.priority = self._calculate_priority()
    
    def _calculate_priority(self) -> int:
        """Calculate priority based on data type and keywords"""
        base_priority = {
            'spots': 10,
            'hotels': 8,
            'food': 7,
            'transport': 6
        }.get(self.data_type, 5)
        
        # Boost priority for specific themes
        theme_boost = 0
        important_themes = ['biển', 'beach', 'lịch sử', 'history', 'ẩm thực', 'food', 
                          'miễn phí', 'free', 'tiết kiệm', 'budget']
        for theme in important_themes:
            if any(theme in kw.lower() for kw in self.keywords):
                theme_boost += 2
        
        return base_priority + theme_boost
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for storage"""
        return {
            'query': self.query,
            'province': self.province,
            'data_type': self.data_type,
            'keywords': self.keywords,
            'timestamp': self.timestamp,
            'priority': self.priority,
            'status': 'pending'
        }


class DataCollector:
    """Collects missing data and populates database"""
    
    def __init__(self):
        self.db = mongodb_manager
        self._ensure_collections()
    
    def _check_db_connection(self) -> bool:
        """Check if MongoDB is connected"""
        if self.db is None or self.db.db is None:
            logger.warning("MongoDB not connected - data collection disabled")
            return False
        return True
    
    def _ensure_collections(self):
        """Ensure data collection tracking collections exist"""
        try:
            if self.db is None or self.db.db is None:
                logger.warning("MongoDB not connected, skipping collection creation")
                return
            
            # Collection for tracking data gaps
            if 'data_gaps' not in self.db.db.list_collection_names():
                self.db.db.create_collection('data_gaps')
                logger.info("✅ Created data_gaps collection")
            
            # Collection for pending collection tasks
            if 'collection_queue' not in self.db.db.list_collection_names():
                self.db.db.create_collection('collection_queue')
                logger.info("✅ Created collection_queue collection")
        except Exception as e:
            logger.error(f"Error ensuring collections: {e}")
    
    def record_data_gap(self, 
                       query: str, 
                       province: str, 
                       data_type: str, 
                       keywords: List[str],
                       result_count: int = 0) -> None:
        """
        Record a data gap when query returns insufficient results
        
        Args:
            query: Original user query
            province: Province/location queried
            data_type: Type of data (spots, hotels, food, etc.)
            keywords: Search keywords used
            result_count: Number of results found (0 = complete miss)
        """
        try:
            if not self._check_db_connection():
                return
            
            request = DataCollectionRequest(query, province, data_type, keywords)
            
            # Check if similar gap already recorded recently (within 24h)
            existing = self.db.get_collection('data_gaps').find_one({
                'province': province,
                'data_type': data_type,
                'timestamp': {'$gte': datetime.now().replace(hour=0, minute=0, second=0)}
            })
            
            if existing:
                # Update frequency counter
                self.db.get_collection('data_gaps').update_one(
                    {'_id': existing['_id']},
                    {'$inc': {'frequency': 1}, '$set': {'last_query': query}}
                )
                logger.info(f"📊 Updated data gap frequency: {province}/{data_type}")
            else:
                # Record new gap
                gap_doc = request.to_dict()
                gap_doc['result_count'] = result_count
                gap_doc['frequency'] = 1
                gap_doc['last_query'] = query
                
                self.db.get_collection('data_gaps').insert_one(gap_doc)
                logger.info(f"🔍 Recorded new data gap: {province}/{data_type} (priority: {request.priority})")
            
            # Add to collection queue if priority is high
            if request.priority >= 8 and result_count == 0:
                self._add_to_collection_queue(request)
        
        except Exception as e:
            logger.error(f"Error recording data gap: {e}")
    
    def _add_to_collection_queue(self, request: DataCollectionRequest) -> None:
        """Add high-priority gap to collection queue"""
        try:
            # Check if already queued
            existing = self.db.get_collection('collection_queue').find_one({
                'province': request.province,
                'data_type': request.data_type,
                'status': {'$in': ['pending', 'in_progress']}
            })
            
            if not existing:
                queue_doc = request.to_dict()
                queue_doc['created_at'] = datetime.now()
                queue_doc['attempts'] = 0
                
                self.db.get_collection('collection_queue').insert_one(queue_doc)
                logger.info(f"📥 Added to collection queue: {request.province}/{request.data_type}")
        
        except Exception as e:
            logger.error(f"Error adding to queue: {e}")
    
    def get_collection_suggestions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get prioritized suggestions for what data to collect
        
        Returns list of suggestions sorted by priority and frequency
        """
        try:
            if not self._check_db_connection():
                return []
            
            # Aggregate data gaps by province and type
            pipeline = [
                {
                    '$group': {
                        '_id': {
                            'province': '$province',
                            'data_type': '$data_type'
                        },
                        'total_queries': {'$sum': '$frequency'},
                        'avg_priority': {'$avg': '$priority'},
                        'sample_keywords': {'$first': '$keywords'},
                        'last_query': {'$first': '$last_query'},
                        'last_timestamp': {'$max': '$timestamp'}
                    }
                },
                {
                    '$project': {
                        'province': '$_id.province',
                        'data_type': '$_id.data_type',
                        'total_queries': 1,
                        'avg_priority': 1,
                        'sample_keywords': 1,
                        'last_query': 1,
                        'last_timestamp': 1,
                        'score': {
                            '$add': [
                                {'$multiply': ['$avg_priority', 2]},
                                '$total_queries'
                            ]
                        }
                    }
                },
                {'$sort': {'score': -1}},
                {'$limit': limit}
            ]
            
            results = list(self.db.get_collection('data_gaps').aggregate(pipeline))
            
            logger.info(f"📋 Generated {len(results)} collection suggestions")
            return results
        
        except Exception as e:
            logger.error(f"Error getting suggestions: {e}")
            return []
    
    def get_pending_collection_tasks(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get pending tasks from collection queue"""
        try:
            if not self._check_db_connection():
                return []
            
            tasks = list(self.db.get_collection('collection_queue').find(
                {'status': 'pending'},
                sort=[('priority', -1), ('created_at', 1)],
                limit=limit
            ))
            return tasks
        except Exception as e:
            logger.error(f"Error getting tasks: {e}")
            return []
    
    def mark_task_completed(self, task_id, data_collected: int) -> None:
        """Mark a collection task as completed"""
        try:
            if not self._check_db_connection():
                return
            
            self.db.get_collection('collection_queue').update_one(
                {'_id': task_id},
                {
                    '$set': {
                        'status': 'completed',
                        'completed_at': datetime.now(),
                        'data_collected': data_collected
                    }
                }
            )
            logger.info(f"✅ Task completed: {task_id} ({data_collected} items)")
        except Exception as e:
            logger.error(f"Error marking task completed: {e}")
    
    def generate_collection_report(self) -> Dict[str, Any]:
        """Generate comprehensive report of data collection needs"""
        try:
            if not self._check_db_connection():
                return {}
            
            # Most needed provinces
            province_needs = list(self.db.get_collection('data_gaps').aggregate([
                {'$group': {
                    '_id': '$province',
                    'total_gaps': {'$sum': 1},
                    'total_queries': {'$sum': '$frequency'}
                }},
                {'$sort': {'total_queries': -1}},
                {'$limit': 10}
            ]))
            
            # Most needed data types
            type_needs = list(self.db.get_collection('data_gaps').aggregate([
                {'$group': {
                    '_id': '$data_type',
                    'total_gaps': {'$sum': 1},
                    'total_queries': {'$sum': '$frequency'}
                }},
                {'$sort': {'total_queries': -1}}
            ]))
            
            # Recent high-priority gaps
            recent_gaps = list(self.db.get_collection('data_gaps').find(
                {'priority': {'$gte': 8}},
                sort=[('timestamp', -1)],
                limit=20
            ))
            
            # Queue statistics
            queue_stats = {
                'pending': self.db.get_collection('collection_queue').count_documents({'status': 'pending'}),
                'in_progress': self.db.get_collection('collection_queue').count_documents({'status': 'in_progress'}),
                'completed': self.db.get_collection('collection_queue').count_documents({'status': 'completed'})
            }
            
            return {
                'province_needs': province_needs,
                'type_needs': type_needs,
                'recent_gaps': recent_gaps,
                'queue_stats': queue_stats,
                'total_gaps': self.db.get_collection('data_gaps').count_documents({}),
                'generated_at': datetime.now()
            }
        
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            return {}


# Singleton instance
data_collector = DataCollector()


def record_search_failure(query: str, province: str, data_type: str, 
                         keywords: List[str], result_count: int = 0) -> None:
    """
    Convenience function to record search failures
    Should be called from experts when searches return insufficient results
    """
    data_collector.record_data_gap(query, province, data_type, keywords, result_count)
