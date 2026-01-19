"""
Planner Agent - Query Decomposition using Plan-RAG
Breaks down complex queries into sub-tasks (DAG)
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from app.core import logger


class TaskType(str, Enum):
    """Types of sub-tasks"""
    FIND_SPOTS = "find_spots"
    FIND_HOTELS = "find_hotels"
    FIND_FOOD = "find_food"
    CREATE_ITINERARY = "create_itinerary"
    CALCULATE_COST = "calculate_cost"
    GENERAL_INFO = "general_info"


@dataclass
class SubTask:
    """A sub-task in the execution plan"""
    task_id: str
    task_type: TaskType
    query: str  # Reformulated query for this task
    parameters: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)  # Task IDs this depends on
    priority: int = 1  # Lower = higher priority
    optional: bool = False


@dataclass
class ExecutionPlan:
    """Complete execution plan with sub-tasks"""
    original_query: str
    intent: str
    location: Optional[str]
    tasks: List[SubTask] = field(default_factory=list)
    execution_order: List[str] = field(default_factory=list)  # Topologically sorted task IDs
    
    def get_parallel_tasks(self) -> List[List[SubTask]]:
        """Get tasks grouped by execution level (parallel execution)"""
        if not self.tasks:
            return []
        
        # Group by priority
        levels = {}
        for task in self.tasks:
            priority = task.priority
            if priority not in levels:
                levels[priority] = []
            levels[priority].append(task)
        
        return [levels[p] for p in sorted(levels.keys())]


class PlannerAgent:
    """
    Planner Agent using Plan-RAG methodology
    Decomposes complex queries into executable sub-tasks
    """
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        logger.info("✅ PlannerAgent initialized")
    
    def plan(self, extracted_intent) -> ExecutionPlan:
        """
        Create execution plan from extracted intent
        
        Args:
            extracted_intent: ExtractedIntent from IntentExtractor
            
        Returns:
            ExecutionPlan with sub-tasks
        """
        intent = extracted_intent.intent
        location = extracted_intent.location
        
        # Create base plan
        plan = ExecutionPlan(
            original_query="",  # Will be set later
            intent=intent,
            location=location
        )
        
        # Route to appropriate planning strategy
        if intent == "plan_trip":
            plan = self._plan_trip(extracted_intent, plan)
        elif intent == "find_hotel":
            plan = self._plan_hotel_search(extracted_intent, plan)
        elif intent == "find_food":
            plan = self._plan_food_search(extracted_intent, plan)
        elif intent == "find_spot":
            plan = self._plan_spot_search(extracted_intent, plan)
        else:
            plan = self._plan_general_qa(extracted_intent, plan)
        
        # Compute execution order
        plan.execution_order = self._topological_sort(plan.tasks)
        
        logger.info(f"📋 Created plan with {len(plan.tasks)} tasks: {[t.task_type.value for t in plan.tasks]}")
        
        return plan
    
    def _plan_trip(self, intent, plan: ExecutionPlan) -> ExecutionPlan:
        """Plan for trip planning (most complex)"""
        
        tasks = []
        location = intent.location or "Việt Nam"
        duration = intent.duration or 2
        
        # Task 1: Find spots (parallel)
        tasks.append(SubTask(
            task_id="spots_1",
            task_type=TaskType.FIND_SPOTS,
            query=f"Địa điểm du lịch nổi tiếng ở {location}",
            parameters={
                "location": location,
                "interests": intent.interests,
                "limit": 10
            },
            priority=1
        ))
        
        # Task 2: Find food (parallel)
        tasks.append(SubTask(
            task_id="food_1",
            task_type=TaskType.FIND_FOOD,
            query=f"Quán ăn ngon, món đặc sản ở {location}",
            parameters={
                "location": location,
                "budget_level": intent.budget_level,
                "limit": 5
            },
            priority=1
        ))
        
        # Task 3: Find hotels (parallel, optional if accommodation=none)
        if intent.accommodation != "none":
            tasks.append(SubTask(
                task_id="hotel_1",
                task_type=TaskType.FIND_HOTELS,
                query=f"Khách sạn {intent.budget_level or 'tốt'} ở {location}",
                parameters={
                    "location": location,
                    "budget": intent.budget,
                    "budget_level": intent.budget_level,
                    "nights": duration - 1 if duration > 1 else 1
                },
                priority=1,
                optional=intent.accommodation == "optional"
            ))
        
        # Task 4: Create itinerary (depends on spots, food, hotel)
        depends = ["spots_1", "food_1"]
        if intent.accommodation != "none":
            depends.append("hotel_1")
        
        tasks.append(SubTask(
            task_id="itinerary_1",
            task_type=TaskType.CREATE_ITINERARY,
            query=f"Lịch trình {duration} ngày ở {location}",
            parameters={
                "location": location,
                "duration": duration,
                "people_count": intent.people_count,
                "budget": intent.budget,
                "interests": intent.interests
            },
            depends_on=depends,
            priority=2
        ))
        
        # Task 5: Calculate cost (depends on itinerary)
        if intent.budget:
            tasks.append(SubTask(
                task_id="cost_1",
                task_type=TaskType.CALCULATE_COST,
                query=f"Tính chi phí chuyến đi {location}",
                parameters={
                    "budget": intent.budget,
                    "duration": duration,
                    "people_count": intent.people_count
                },
                depends_on=["itinerary_1"],
                priority=3
            ))
        
        plan.tasks = tasks
        return plan
    
    def _plan_hotel_search(self, intent, plan: ExecutionPlan) -> ExecutionPlan:
        """Plan for hotel search"""
        
        location = intent.location or "Việt Nam"
        
        plan.tasks = [
            SubTask(
                task_id="hotel_1",
                task_type=TaskType.FIND_HOTELS,
                query=f"Khách sạn {intent.budget_level or ''} ở {location}",
                parameters={
                    "location": location,
                    "budget": intent.budget,
                    "budget_level": intent.budget_level,
                    "keywords": intent.keywords
                },
                priority=1
            )
        ]
        
        return plan
    
    def _plan_food_search(self, intent, plan: ExecutionPlan) -> ExecutionPlan:
        """Plan for food search"""
        
        location = intent.location or "Việt Nam"
        
        plan.tasks = [
            SubTask(
                task_id="food_1",
                task_type=TaskType.FIND_FOOD,
                query=f"Quán ăn {' '.join(intent.keywords) if intent.keywords else 'ngon'} ở {location}",
                parameters={
                    "location": location,
                    "keywords": intent.keywords,
                    "budget_level": intent.budget_level
                },
                priority=1
            )
        ]
        
        return plan
    
    def _plan_spot_search(self, intent, plan: ExecutionPlan) -> ExecutionPlan:
        """Plan for spot/attraction search"""
        
        location = intent.location or "Việt Nam"
        
        plan.tasks = [
            SubTask(
                task_id="spots_1",
                task_type=TaskType.FIND_SPOTS,
                query=f"Địa điểm {' '.join(intent.interests) if intent.interests else 'du lịch'} ở {location}",
                parameters={
                    "location": location,
                    "interests": intent.interests,
                    "keywords": intent.keywords
                },
                priority=1
            )
        ]
        
        return plan
    
    def _plan_general_qa(self, intent, plan: ExecutionPlan) -> ExecutionPlan:
        """Plan for general questions"""
        
        plan.tasks = [
            SubTask(
                task_id="info_1",
                task_type=TaskType.GENERAL_INFO,
                query=intent.keywords[0] if intent.keywords else "thông tin du lịch",
                parameters={
                    "location": intent.location,
                    "keywords": intent.keywords
                },
                priority=1
            )
        ]
        
        return plan
    
    def _topological_sort(self, tasks: List[SubTask]) -> List[str]:
        """Topological sort of tasks based on dependencies"""
        
        # Build dependency graph
        in_degree = {t.task_id: 0 for t in tasks}
        graph = {t.task_id: [] for t in tasks}
        
        for task in tasks:
            for dep in task.depends_on:
                if dep in graph:
                    graph[dep].append(task.task_id)
                    in_degree[task.task_id] += 1
        
        # Kahn's algorithm
        queue = [tid for tid, degree in in_degree.items() if degree == 0]
        result = []
        
        while queue:
            # Sort by priority within same level
            queue.sort(key=lambda tid: next((t.priority for t in tasks if t.task_id == tid), 999))
            current = queue.pop(0)
            result.append(current)
            
            for neighbor in graph[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        return result


# Factory function
def create_planner_agent(llm_client=None) -> PlannerAgent:
    """Create PlannerAgent with optional LLM client"""
    return PlannerAgent(llm_client)
