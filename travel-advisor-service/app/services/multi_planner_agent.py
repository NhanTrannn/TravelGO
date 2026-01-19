"""
Multi-Planner Agent - Enhanced planning for multi-intent queries
Creates execution plans with multiple parallel/sequential tasks
"""

from typing import List
from app.core import logger
from app.services.planner_agent import (
    PlannerAgent, ExecutionPlan, SubTask, TaskType
)
from app.services.multi_intent_extractor import MultiIntent


class MultiPlannerAgent:
    """
    Enhanced Planner Agent for multi-intent queries
    
    Handles queries like: "khách sạn + địa điểm + quán ăn ở Đà Nẵng"
    Creates parallel tasks: [find_hotels, find_spots, find_food]
    """
    
    def __init__(self, base_planner: PlannerAgent):
        self.base_planner = base_planner
        logger.info("✅ MultiPlannerAgent initialized")
    
    def plan(self, multi_intent: MultiIntent) -> ExecutionPlan:
        """
        Create execution plan from multi-intent
        
        Args:
            multi_intent: MultiIntent from MultiIntentExtractor
            
        Returns:
            ExecutionPlan with parallel/sequential tasks
        """
        
        # Get all intents (primary + sub)
        all_intents = [multi_intent.primary_intent] + multi_intent.sub_intents
        
        if len(all_intents) == 1:
            # Single intent - use base planner
            return self.base_planner.plan(multi_intent.to_extracted_intent())
        
        logger.info(f"📋 Planning for multi-intent: {all_intents}")
        
        # Create plan
        plan = ExecutionPlan(
            original_query="",
            intent=multi_intent.primary_intent,
            location=multi_intent.location
        )
        
        # Add tasks for each intent
        tasks = []
        
        for i, intent in enumerate(all_intents, 1):
            intent_tasks = self._create_tasks_for_intent(
                intent=intent,
                multi_intent=multi_intent,
                task_index=i
            )
            tasks.extend(intent_tasks)
        
        plan.tasks = tasks
        
        # Topological sort
        plan.execution_order = self._topological_sort(tasks)
        
        logger.info(f"✅ Created plan with {len(tasks)} tasks: {plan.execution_order}")
        
        return plan
    
    def _create_tasks_for_intent(
        self,
        intent: str,
        multi_intent: MultiIntent,
        task_index: int
    ) -> List[SubTask]:
        """Create tasks for a single intent"""
        
        location = multi_intent.location or "Việt Nam"
        tasks = []
        
        # Get intent-specific parameters
        intent_param = multi_intent.intent_params.get(intent, {})
        sub_query = intent_param.get("query", "")
        keywords = intent_param.get("keywords", multi_intent.keywords)
        interests = intent_param.get("interests", multi_intent.interests)
        
        if intent == "find_hotel":
            tasks.append(SubTask(
                task_id=f"hotel_{task_index}",
                task_type=TaskType.FIND_HOTELS,
                query=sub_query or f"Khách sạn ở {location}",
                parameters={
                    "location": location,
                    "budget": multi_intent.budget,
                    "budget_level": multi_intent.budget_level,
                    "keywords": keywords,
                    "limit": 5
                },
                priority=1,  # Parallel
                depends_on=[]
            ))
        
        elif intent == "find_spot":
            tasks.append(SubTask(
                task_id=f"spots_{task_index}",
                task_type=TaskType.FIND_SPOTS,
                query=sub_query or f"Địa điểm du lịch ở {location}",
                parameters={
                    "location": location,
                    "interests": interests,
                    "keywords": keywords,
                    "limit": 6
                },
                priority=1,  # Parallel
                depends_on=[]
            ))
        
        elif intent == "find_food":
            tasks.append(SubTask(
                task_id=f"food_{task_index}",
                task_type=TaskType.FIND_FOOD,
                query=sub_query or f"Quán ăn ngon ở {location}",
                parameters={
                    "location": location,
                    "keywords": keywords,
                    "budget_level": multi_intent.budget_level,
                    "limit": 5
                },
                priority=1,  # Parallel
                depends_on=[]
            ))
        
        elif intent == "plan_trip":
            # Plan trip requires spots + hotels + food first
            tasks.extend([
                SubTask(
                    task_id=f"spots_{task_index}",
                    task_type=TaskType.FIND_SPOTS,
                    query=f"Địa điểm du lịch ở {location}",
                    parameters={
                        "location": location,
                        "interests": interests,
                        "limit": 10
                    },
                    priority=1,
                    depends_on=[]
                ),
                SubTask(
                    task_id=f"hotel_{task_index}",
                    task_type=TaskType.FIND_HOTELS,
                    query=f"Khách sạn ở {location}",
                    parameters={
                        "location": location,
                        "budget": multi_intent.budget,
                        "budget_level": multi_intent.budget_level,
                        "duration": multi_intent.duration,
                        "people_count": multi_intent.people_count,
                        "limit": 5
                    },
                    priority=1,
                    depends_on=[]
                ),
                SubTask(
                    task_id=f"food_{task_index}",
                    task_type=TaskType.FIND_FOOD,
                    query=f"Quán ăn ở {location}",
                    parameters={
                        "location": location,
                        "budget_level": multi_intent.budget_level,
                        "limit": 5
                    },
                    priority=1,
                    depends_on=[]
                ),
                SubTask(
                    task_id=f"itinerary_{task_index}",
                    task_type=TaskType.CREATE_ITINERARY,
                    query=f"Tạo lịch trình {multi_intent.duration or 3} ngày ở {location}",
                    parameters={
                        "location": location,
                        "duration": multi_intent.duration or 3,
                        "people_count": multi_intent.people_count
                    },
                    priority=2,  # Sequential - depends on above
                    depends_on=[f"spots_{task_index}", f"hotel_{task_index}", f"food_{task_index}"]
                ),
                SubTask(
                    task_id=f"cost_{task_index}",
                    task_type=TaskType.CALCULATE_COST,
                    query="Ước tính chi phí",
                    parameters={
                        "duration": multi_intent.duration or 3,
                        "people_count": multi_intent.people_count,
                        "budget_level": multi_intent.budget_level
                    },
                    priority=3,  # Sequential - depends on itinerary
                    depends_on=[f"itinerary_{task_index}"]
                )
            ])
        
        return tasks
    
    def _topological_sort(self, tasks: List[SubTask]) -> List[str]:
        """Topological sort - reuse from base planner"""
        return self.base_planner._topological_sort(tasks)


def create_multi_planner_agent(base_planner: PlannerAgent) -> MultiPlannerAgent:
    """Factory function"""
    return MultiPlannerAgent(base_planner)
