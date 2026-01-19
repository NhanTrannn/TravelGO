# -*- coding: utf-8 -*-
"""
Master Controller - Orchestrator for Plan-RAG Architecture
Coordinates Preprocessor -> Planner -> Experts -> Generator
Enhanced with Conversation Memory for progressive disclosure

VERSION: 2.1.0-DISTANCE-FIX (2026-01-16 14:35)
- FIX #4: Distance calculation bypass for builder mode
"""

import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from app.core import logger
from app.db import mongodb_manager
from app.services.weather import WeatherService

# Log module version on import
logger.info("🔧 [MODULE] master_controller.py VERSION 2.1.0-DISTANCE-FIX loaded")


# Location highlights for GenUI responses
LOCATION_HIGHLIGHTS = {
    "đà nẵng": {
        "icon": "🏖️",
        "tagline": "thành phố biển xinh đẹp",
        "highlights": "Bãi biển Mỹ Khê, Bà Nà Hills, Cầu Rồng",
        "tags": ["biển", "nghỉ dưỡng", "ẩm thực"],
    },
    "da nang": {
        "icon": "🏖️",
        "tagline": "thành phố biển xinh đẹp",
        "highlights": "Bãi biển Mỹ Khê, Bà Nà Hills, Cầu Rồng",
        "tags": ["biển", "nghỉ dưỡng", "ẩm thực"],
    },
    "hội an": {
        "icon": "🏮",
        "tagline": "phố cổ lung linh",
        "highlights": "Phố cổ, Đêm hoa đăng, Chùa Cầu",
        "tags": ["văn hóa", "ẩm thực", "may đo"],
    },
    "hoi an": {
        "icon": "🏮",
        "tagline": "phố cổ lung linh",
        "highlights": "Phố cổ, Đêm hoa đăng, Chùa Cầu",
        "tags": ["văn hóa", "ẩm thực", "may đo"],
    },
    "nha trang": {
        "icon": "🌊",
        "tagline": "thiên đường biển",
        "highlights": "Vinpearl, Hòn Mun, Tháp Bà Ponagar",
        "tags": ["biển", "lặn biển", "hải sản"],
    },
    "phú quốc": {
        "icon": "🏝️",
        "tagline": "đảo ngọc phương Nam",
        "highlights": "Safari, Grand World, Bãi Sao",
        "tags": ["biển", "nghỉ dưỡng", "thiên nhiên"],
    },
    "phu quoc": {
        "icon": "🏝️",
        "tagline": "đảo ngọc phương Nam",
        "highlights": "Safari, Grand World, Bãi Sao",
        "tags": ["biển", "nghỉ dưỡng", "thiên nhiên"],
    },
    "sapa": {
        "icon": "⛰️",
        "tagline": "thị trấn mù sương",
        "highlights": "Fansipan, Bản Cát Cát, Ruộng bậc thang",
        "tags": ["núi", "trekking", "văn hóa"],
    },
    "sa pa": {
        "icon": "⛰️",
        "tagline": "thị trấn mù sương",
        "highlights": "Fansipan, Bản Cát Cát, Ruộng bậc thang",
        "tags": ["núi", "trekking", "văn hóa"],
    },
    "huế": {
        "icon": "🏛️",
        "tagline": "cố đô triều Nguyễn",
        "highlights": "Đại Nội, Chùa Thiên Mụ, Lăng Tự Đức",
        "tags": ["văn hóa", "lịch sử", "ẩm thực"],
    },
    "hue": {
        "icon": "🏛️",
        "tagline": "cố đô triều Nguyễn",
        "highlights": "Đại Nội, Chùa Thiên Mụ, Lăng Tự Đức",
        "tags": ["văn hóa", "lịch sử", "ẩm thực"],
    },
    "đà lạt": {
        "icon": "🌸",
        "tagline": "thành phố ngàn hoa",
        "highlights": "Hồ Xuân Hương, Đồi chè, Langbiang",
        "tags": ["núi", "thiên nhiên", "lãng mạn"],
    },
    "da lat": {
        "icon": "🌸",
        "tagline": "thành phố ngàn hoa",
        "highlights": "Hồ Xuân Hương, Đồi chè, Langbiang",
        "tags": ["núi", "thiên nhiên", "lãng mạn"],
    },
    "hà nội": {
        "icon": "🏙️",
        "tagline": "thủ đô ngàn năm văn hiến",
        "highlights": "Phố cổ, Hồ Gươm, Văn Miếu",
        "tags": ["văn hóa", "lịch sử", "ẩm thực"],
    },
    "ha noi": {
        "icon": "🏙️",
        "tagline": "thủ đô ngàn năm văn hiến",
        "highlights": "Phố cổ, Hồ Gươm, Văn Miếu",
        "tags": ["văn hóa", "lịch sử", "ẩm thực"],
    },
    "hồ chí minh": {
        "icon": "🌆",
        "tagline": "thành phố không ngủ",
        "highlights": "Dinh Độc Lập, Bến Nhà Rồng, Phố đi bộ",
        "tags": ["đô thị", "ẩm thực", "mua sắm"],
    },
    "default": {
        "icon": "🌟",
        "tagline": "điểm đến hấp dẫn",
        "highlights": "Nhiều địa điểm tham quan thú vị",
        "tags": ["khám phá", "nghỉ dưỡng"],
    },
}


# Keep legacy ConversationContext for backward compatibility
@dataclass
class ConversationContext:
    """Tracks conversation state (legacy)"""

    destination: Optional[str] = None
    duration: Optional[int] = None
    start_date: Optional[str] = None  # YYYY-MM-DD format
    budget: Optional[int] = None
    budget_level: Optional[str] = None
    people_count: int = 1
    interests: List[str] = field(default_factory=list)
    last_intent: Optional[str] = None
    selected_hotel: Optional[str] = None
    selected_hotel_price: Optional[int] = None
    selected_spots: List[Dict] = field(
        default_factory=list
    )  # NEW: Permanently store selected spots
    itinerary: List[Dict] = field(default_factory=list)
    itinerary_builder: Optional[Dict] = None  # For interactive itinerary building
    # FIX 2026-01-18: Add missing fields for recall functionality
    last_itinerary: Optional[Dict] = None  # Finalized itinerary for recall
    workflow_state: Optional[str] = None  # Current workflow state

    def update_from_intent(self, intent):
        """Update context from ExtractedIntent"""
        if intent.location:
            self.destination = intent.location
        if intent.duration:
            self.duration = intent.duration
        if intent.budget:
            self.budget = intent.budget
        if intent.budget_level:
            self.budget_level = intent.budget_level
        if intent.people_count and intent.people_count > 0:
            self.people_count = intent.people_count
        if intent.interests:
            self.interests = intent.interests
        self.last_intent = intent.intent

    def to_dict(self) -> Dict[str, Any]:
        return {
            "destination": self.destination,
            "duration": self.duration,
            "start_date": self.start_date,
            "budget": self.budget,
            "budget_level": self.budget_level,
            "people_count": self.people_count,
            "interests": self.interests,
            "last_intent": self.last_intent,
            "selected_hotel": self.selected_hotel,
            "selected_hotel_price": self.selected_hotel_price,
            "selected_spots": self.selected_spots,
            "itinerary_builder": self.itinerary_builder,
            # FIX 2026-01-18: Include last_itinerary for recall functionality
            "last_itinerary": self.last_itinerary,
            "workflow_state": self.workflow_state,
        }


def _clean_mongo_doc(doc: dict) -> dict:
    """Clean MongoDB document for JSON serialization

    Converts ObjectId and datetime to strings
    """
    if not doc:
        return doc

    from datetime import datetime
    from bson import ObjectId

    cleaned = {}
    for key, value in doc.items():
        if isinstance(value, ObjectId):
            cleaned[key] = str(value)
        elif isinstance(value, datetime):
            cleaned[key] = value.isoformat()
        elif isinstance(value, dict):
            cleaned[key] = _clean_mongo_doc(value)
        elif isinstance(value, list):
            cleaned[key] = [
                (
                    _clean_mongo_doc(item)
                    if isinstance(item, dict)
                    else str(item) if isinstance(item, (ObjectId, datetime)) else item
                )
                for item in value
            ]
        else:
            cleaned[key] = value
    return cleaned


def _get_context_value(context, key: str, default=None):
    """
    Get value from context, handling both object attributes and dict keys

    Args:
        context: Can be ConversationContext object or dict
        key: Field name to retrieve
        default: Default value if not found

    Returns:
        Value from context or default
    """
    if hasattr(context, key):
        return getattr(context, key, default)
    elif isinstance(context, dict):
        return context.get(key, default)
    return default


class MasterController:
    """
    Master Controller for Plan-RAG Architecture

    Flow:
    1. Preprocess: Extract intent, entities, constraints
    2. Plan: Decompose into sub-tasks
    3. Execute: Run expert executors in parallel/sequence
    4. Aggregate: Combine results
    5. Generate: Create final response
    """

    def __init__(self):
        self.weather = WeatherService(mongodb_manager)

        # Ensure MongoDB is connected
        if mongodb_manager.db is None:
            mongodb_manager.connect()

        # Store MongoDB manager reference for booking etc.
        self.mongo_manager = mongodb_manager

        # Initialize LLM client
        try:
            from app.services.llm_client import llm_client

            self.llm = llm_client
        except Exception as e:
            logger.warning(f"⚠️ LLM client not available: {e}")
            self.llm = None

        # Initialize base intent extractor
        from app.services.intent_extractor import create_intent_extractor

        base_intent_extractor = create_intent_extractor(self.llm)

        # Initialize multi-intent extractor (wraps base extractor)
        from app.services.multi_intent_extractor import create_multi_intent_extractor

        self.multi_intent_extractor = create_multi_intent_extractor(
            base_intent_extractor
        )
        self.intent_extractor = base_intent_extractor  # Backward compatibility

        # Initialize base planner
        from app.services.planner_agent import create_planner_agent

        base_planner = create_planner_agent(self.llm)

        # Initialize multi-planner (wraps base planner)
        from app.services.multi_planner_agent import create_multi_planner_agent

        self.multi_planner = create_multi_planner_agent(base_planner)
        self.planner = base_planner  # Backward compatibility

        # Initialize response aggregator
        from app.services.response_aggregator import create_response_aggregator

        self.response_aggregator = create_response_aggregator(self.llm)

        # Initialize conversation memory manager
        from app.services.conversation_memory import (
            create_conversation_memory_manager,
            EnhancedConversationContext,
        )

        self.memory_manager = create_conversation_memory_manager(self.llm)
        self.EnhancedConversationContext = EnhancedConversationContext

        # Initialize embedding service for semantic search
        try:
            from app.services.embedding_service import create_embedding_service

            self.embedding_service = create_embedding_service()
            logger.info("✅ Embedding service initialized")
        except Exception as e:
            logger.warning(f"⚠️  Embedding service not available: {e}")
            self.embedding_service = None

        # [NEW] Initialize Hybrid Search Service
        try:
            from app.services.hybrid_search import hybrid_search_service

            self.hybrid_search = hybrid_search_service
            logger.info("✅ Hybrid Search Service initialized in MasterController")
        except Exception as e:
            logger.error(f"❌ Failed to init Hybrid Search: {e}")
            self.hybrid_search = None

        # Initialize experts
        from app.services.experts import (
            SpotExpert,
            HotelExpert,
            FoodExpert,
            ItineraryExpert,
            CostCalculatorExpert,
            GeneralInfoExpert,
            ItineraryVerifier,
            create_itinerary_verifier,
        )

        self.experts = {
            "find_spots": SpotExpert(
                mongodb_manager, None, self.llm, self.embedding_service
            ),
            "find_hotels": HotelExpert(mongodb_manager, None, self.llm),
            "find_food": FoodExpert(mongodb_manager, None, self.llm),
            "create_itinerary": ItineraryExpert(mongodb_manager, None, self.llm),
            "calculate_cost": CostCalculatorExpert(mongodb_manager, None, self.llm),
            "general_info": GeneralInfoExpert(mongodb_manager, self.llm),
        }

        # [NEW] Initialize Itinerary Verifier (Rule-based + LLM-as-critic)
        try:
            self.itinerary_verifier = create_itinerary_verifier(
                self.llm, mongodb_manager
            )
            logger.info("✅ ItineraryVerifier initialized")
        except Exception as e:
            logger.warning(f"⚠️ ItineraryVerifier not available: {e}")
            self.itinerary_verifier = None

        # [NEW] Initialize Spot Selector Handler
        try:
            from app.services.spot_selector_handler import create_spot_selector_handler

            self.spot_selector = create_spot_selector_handler(mongodb_manager, self.llm)
            logger.info("✅ SpotSelectorHandler initialized")
        except Exception as e:
            logger.warning(f"⚠️ SpotSelectorHandler not available: {e}")
            self.spot_selector = None

        # ============================================================
        # STATE MACHINE: Intent Dependencies (StateGuard Matrix)
        # Chặn đứng các Intent "nhảy bước" để duy trì luồng tuyến tính
        # ============================================================
        self.INTENT_DEPENDENCIES = {
            "calculate_cost": {
                "required_states": ["CHOOSING_HOTEL", "READY_TO_FINALIZE"],
                "required_fields": ["selected_hotel"],
                "error_action": "prompt_hotel",
                "error_msg": "🏨 Bạn ơi, mình cần chốt khách sạn trước thì mới tính tổng chi phí chính xác được ạ!\n\n💡 Gõ **'tìm khách sạn'** để xem danh sách.",
            },
            "find_hotel": {
                "required_states": ["CHOOSING_HOTEL", "CHOOSING_SPOTS", "INITIAL"],
                "required_fields": ["destination"],
                "error_action": "prompt_destination",
                "error_msg": "📍 Bạn muốn tìm khách sạn ở đâu? Cho mình biết điểm đến nhé!",
            },
            "find_food": {
                "required_states": [
                    "CHOOSING_HOTEL",
                    "CHOOSING_SPOTS",
                    "INITIAL",
                    "READY_TO_FINALIZE",
                ],
                "required_fields": ["destination"],
                "error_action": "prompt_destination",
                "error_msg": "📍 Bạn muốn tìm quán ăn ở đâu? Cho mình biết địa điểm nhé!",
            },
        }

        # Priority order for task execution (Pipeline tuyến tính)
        self.TASK_PRIORITY_ORDER = ["spots", "hotels", "food", "itinerary", "cost"]

        logger.info(
            "✅ MasterController initialized with enhanced multi-intent Plan-RAG + Conversation Memory + Semantic Search"
        )

    # ============================================================
    # FIX B: METADATA HELPER FUNCTIONS
    # Add metadata envelope to ALL responses for evaluation metrics
    # ============================================================
    def _build_response_metadata(
        self, multi_intent, context, intent_override: str = None
    ) -> Dict[str, Any]:
        """
        Build metadata envelope for response.
        Used for evaluation metrics (Intent accuracy, Entity extraction).
        """
        return {
            "intent": intent_override
            or getattr(multi_intent, "primary_intent", "unknown"),
            "sub_intents": getattr(multi_intent, "sub_intents", []),
            "entities": {
                "destination": getattr(multi_intent, "location", None),
                "duration": getattr(multi_intent, "duration", None),
                "people_count": getattr(multi_intent, "people_count", 1),
                "budget": getattr(multi_intent, "budget", None),
                "budget_level": getattr(multi_intent, "budget_level", None),
                "interests": getattr(multi_intent, "interests", []),
                "companion_type": getattr(multi_intent, "companion_type", None),
            },
            "confidence": getattr(multi_intent, "confidence", 0.0),
            "workflow_state": getattr(context, "workflow_state", "INITIAL"),
            "flow_action": getattr(multi_intent, "flow_action", None),
            "context_relation": getattr(multi_intent, "context_relation", "new_topic"),
        }

    def _add_metadata_to_response(
        self,
        response: Dict[str, Any],
        multi_intent,
        context,
        intent_override: str = None,
    ) -> Dict[str, Any]:
        """
        Add metadata envelope to any response dict.
        """
        if response:
            response["metadata"] = self._build_response_metadata(
                multi_intent, context, intent_override
            )
        return response

    def process_request(
        self, messages: List[Dict[str, str]], context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Process user request through Plan-RAG pipeline with progressive disclosure

        Args:
            messages: List of {"role": "user"|"assistant", "content": "..."}
            context: Optional conversation context

        Returns:
            Response dict with reply, ui_type, ui_data, context
        """
        start_time = time.time()

        try:
            # Get last user message
            user_message = self._get_last_user_message(messages)
            if not user_message:
                return self._error_response("Không nhận được tin nhắn")

            # Initialize/restore enhanced context
            enhanced_context = self._restore_enhanced_context(context)

            # Add user message to history
            enhanced_context.add_message("user", user_message)

            logger.info(f"📥 Processing: {user_message[:50]}...")

            # === PHASE 1: PREPROCESS - Multi-Intent Extraction ===
            multi_intent = self.multi_intent_extractor.extract(
                user_message, enhanced_context.to_dict()
            )

            all_intents = [multi_intent.primary_intent] + multi_intent.sub_intents
            logger.info(
                f"🎯 Intents detected: {all_intents} | Location: {multi_intent.location}"
            )

            # Update context from primary intent
            extracted_intent = multi_intent.to_extracted_intent()
            enhanced_context.update_from_intent(extracted_intent)

            # === PHASE 1.5: FLOW CONTROL - Chặn Greedy Execution ===
            # NGUYÊN TẮC: State-First, Intent-Second
            state = enhanced_context.workflow_state
            logger.info(
                f"🔄 Flow Control Check: State={state}, Primary Intent={multi_intent.primary_intent}"
            )

            # RULE 1: Nếu đang trong Interactive Itinerary Builder → KHÓA vào luồng này
            if enhanced_context.itinerary_builder or state in [
                "CHOOSING_SPOTS",
                "GATHERING_INFO",
            ]:
                # Chặn các intent làm nhiễu (find_hotel, find_food tự động)
                if multi_intent.primary_intent in [
                    "find_spot",
                    "plan_trip",
                    "general_qa",
                ]:
                    logger.info(f"🔒 Flow locked to itinerary builder")
                    special_response = self._handle_special_intent_sync(
                        multi_intent, enhanced_context, user_message
                    )
                    if special_response:
                        execution_time = int((time.time() - start_time) * 1000)
                        special_response["execution_time_ms"] = execution_time
                        special_response["context"] = enhanced_context.to_dict()
                        return special_response

            # RULE 2: Nếu primary_intent = plan_trip và state = INITIAL → CHỈ chạy builder
            # TUYỆT ĐỐI KHÔNG cho phép find_hotel hay find_food chạy đồng thời
            if multi_intent.primary_intent == "plan_trip" and state == "INITIAL":
                # Loại bỏ tất cả sub_intents hotel/food tự động
                original_sub_intents = multi_intent.sub_intents.copy()
                multi_intent.sub_intents = [
                    intent
                    for intent in multi_intent.sub_intents
                    if intent not in ["find_hotel", "find_food"]
                ]
                if original_sub_intents != multi_intent.sub_intents:
                    logger.warning(
                        f"🚫 Blocked greedy execution: Removed {set(original_sub_intents) - set(multi_intent.sub_intents)}"
                    )

            # RULE 3: Nếu state = CHOOSING_HOTEL → KHÔNG cho phép find_food tự động
            if state == "CHOOSING_HOTEL":
                # Chỉ cho phép find_food nếu user yêu cầu ĐÍCH DANH
                if "find_food" in multi_intent.sub_intents and not any(
                    kw in user_message.lower()
                    for kw in ["quán ăn", "món ăn", "food", "nhà hàng"]
                ):
                    multi_intent.sub_intents.remove("find_food")
                    logger.warning(f"🚫 Blocked auto find_food in CHOOSING_HOTEL state")

            # === PHASE 1.6: HANDLE SPECIAL INTENTS (sync version) ===
            special_response = self._handle_special_intent_sync(
                multi_intent, enhanced_context, user_message
            )
            if special_response:
                execution_time = int((time.time() - start_time) * 1000)
                special_response["execution_time_ms"] = execution_time
                special_response["context"] = enhanced_context.to_dict()
                # FIX B: Add metadata to special intent responses
                self._add_metadata_to_response(
                    special_response, multi_intent, enhanced_context
                )
                logger.info(f"✅ Special intent handled in {execution_time}ms")
                return special_response

            # === PHASE 2: PLAN - Multi-Intent Planning ===
            plan = self.multi_planner.plan(multi_intent)

            logger.info(
                f"📋 Execution plan: {len(plan.tasks)} tasks → {plan.execution_order}"
            )

            # === PHASE 3: EXECUTE ===
            results = self._execute_plan(plan, original_query=user_message)

            # === PHASE 4: AGGREGATE ===
            aggregated = self._aggregate_results(results)

            # Store results in context for follow-up queries
            if aggregated.get("spots"):
                enhanced_context.update_last_spots(aggregated["spots"])
            if aggregated.get("hotels"):
                enhanced_context.update_last_hotels(aggregated["hotels"])
            if aggregated.get("food"):
                enhanced_context.update_last_foods(aggregated["food"])
            if aggregated.get("itinerary"):
                enhanced_context.update_last_itinerary(
                    {"days": aggregated["itinerary"]}
                )

            # === PHASE 5: PROGRESSIVE RESPONSE GENERATION ===
            # Check what we can answer vs what we need to defer
            progressive_info = self.memory_manager.create_progressive_response(
                multi_intent, aggregated, enhanced_context
            )

            answered_sections = progressive_info["answered_sections"]
            unanswered_intents = progressive_info["unanswered_intents"]
            has_partial = progressive_info["has_partial_answer"]

            logger.info(
                f"📊 Response: {len(answered_sections)} sections answered, {len(unanswered_intents)} deferred"
            )

            # Build progressive reply
            if has_partial or len(answered_sections) > 0:
                # We have at least something to answer
                reply = self.memory_manager.build_progressive_reply(
                    answered_sections=answered_sections,
                    unanswered_intents=unanswered_intents,
                    results=aggregated,
                    location=multi_intent.location
                    or enhanced_context.destination
                    or "khu vực này",
                    context=enhanced_context,
                )

                # Determine UI type based on what we answered
                ui_type = self._determine_ui_type(answered_sections, aggregated)
                ui_data = self._build_ui_data(answered_sections, aggregated)

            else:
                # Nothing to answer - need clarification
                reply = self._generate_clarification_request(
                    multi_intent, unanswered_intents, enhanced_context
                )
                ui_type = "options"
                ui_data = self._generate_clarification_options(enhanced_context)

            # Add assistant message to history
            enhanced_context.add_message(
                "assistant", reply[:200]
            )  # Store truncated version

            # Build final response with FULL METADATA for evaluation
            response = {
                "reply": reply,
                "ui_type": ui_type,
                "ui_data": ui_data,
                "intent": multi_intent.primary_intent,
                "intents": all_intents,
                "answered_sections": answered_sections,
                "unanswered_count": len(unanswered_intents),
                # === FIX B: ADD METADATA ENVELOPE ===
                "metadata": {
                    "intent": multi_intent.primary_intent,
                    "sub_intents": multi_intent.sub_intents,
                    "entities": {
                        "destination": multi_intent.location,
                        "duration": multi_intent.duration,
                        "people_count": multi_intent.people_count,
                        "budget": multi_intent.budget,
                        "budget_level": multi_intent.budget_level,
                        "interests": multi_intent.interests,
                        "companion_type": multi_intent.companion_type,
                    },
                    "confidence": multi_intent.confidence,
                    "workflow_state": getattr(
                        enhanced_context, "workflow_state", "INITIAL"
                    ),
                    "flow_action": multi_intent.flow_action,
                    "context_relation": multi_intent.context_relation,
                },
            }

            # Add timing
            execution_time = int((time.time() - start_time) * 1000)
            response["execution_time_ms"] = execution_time
            response["context"] = enhanced_context.to_dict()

            logger.info(f"✅ Response generated in {execution_time}ms")

            return response

        except Exception as e:
            logger.error(f"❌ MasterController error: {e}")
            import traceback

            traceback.print_exc()
            return self._error_response(str(e))

    async def process_stream(
        self, messages: List[Dict[str, str]], context: Dict[str, Any] = None
    ):
        """
        Process request with streaming - yield results as they become available

        Progressive flow:
        1. Handle special intents (greeting, chitchat, booking) first
        2. Find spots → Yield immediately
        3. Find hotels → Yield next
        4. Generate itinerary → Yield next
        5. Calculate cost → Yield final

        Args:
            messages: Conversation messages
            context: Optional context

        Yields:
            Dict chunks with reply, ui_type, ui_data, status
        """
        try:
            logger.info("📡 Starting streaming process...")

            # Extract user message
            user_message = self._get_last_user_message(messages)
            if not user_message:
                yield {
                    "error": "No user message found",
                    "reply": "Bạn muốn hỏi gì?",
                    "ui_type": "none",
                }
                return

            # Phase 1: Extract intent (FAST - no streaming needed)
            logger.info(f"📥 Processing: {user_message[:50]}...")

            # Initialize/restore enhanced context
            enhanced_context = self._restore_enhanced_context(context)
            enhanced_context.add_message("user", user_message)

            # Extract multi-intent
            multi_intent = self.multi_intent_extractor.extract(
                user_message, enhanced_context.to_dict()
            )

            logger.info(
                f"🎯 Detected intent: {multi_intent.primary_intent} (confidence: {multi_intent.confidence})"
            )

            # ============================================================
            # 🔥 CRITICAL: Check SPECIAL INTENTS BEFORE workflow state logic
            # Special intents (show_itinerary, calculate_cost, book_hotel) should bypass state checks
            # ============================================================
            intent = multi_intent.primary_intent

            # FIX 2026-01-18: Override intent to book_hotel when user explicitly selects a hotel
            # LLM sometimes misdetects "Tôi chọn khách sạn: X" as "find_hotel" instead of "book_hotel"
            user_lower = user_message.lower()
            hotel_selection_patterns = [
                "tôi chọn khách sạn",
                "toi chon khach san",
                "chọn khách sạn:",
                "chon khach san:",
                "đặt phòng tại",
                "dat phong tai",
                "tôi muốn đặt phòng tại",
                "toi muon dat phong tai",
                "book hotel:",
                "select hotel:",
            ]
            if any(p in user_lower for p in hotel_selection_patterns):
                logger.info(
                    f"🏨 [FIX] Overriding intent from '{intent}' to 'book_hotel' - user is selecting a hotel"
                )
                intent = "book_hotel"
                multi_intent.primary_intent = "book_hotel"

            # FIX 2026-01-18: Override intent to show_itinerary when user asks about selected spots
            spot_info_patterns = [
                "thông tin các địa điểm",
                "thong tin cac dia diem",
                "các địa điểm sẽ đến",
                "cac dia diem se den",
                "địa điểm đã chọn",
                "dia diem da chon",
                "những địa điểm sẽ đến",
                "cho tôi thông tin các địa điểm",
                "thông tin địa điểm sẽ đến",
            ]
            if any(p in user_lower for p in spot_info_patterns):
                logger.info(
                    f"📍 [FIX] Overriding intent from '{intent}' to 'show_itinerary' - user asking about spots"
                )
                intent = "show_itinerary"
                multi_intent.primary_intent = "show_itinerary"

            # === SHOW ITINERARY: Recall from memory (HIGHEST PRIORITY) ===
            if intent == "show_itinerary" or self._is_recall_itinerary_request(
                user_message
            ):
                logger.info(
                    "🔍 [STREAMING] show_itinerary detected - recalling from memory"
                )
                recall_response = self._handle_recall_itinerary(enhanced_context)
                if recall_response:
                    yield recall_response
                    yield {
                        "reply": "",
                        "status": "complete",
                        "ui_type": "none",
                        "context": enhanced_context.to_dict(),
                    }
                    return

            # === CALCULATE COST: Estimate budget ===
            if intent == "calculate_cost":
                logger.info("💰 [STREAMING] calculate_cost detected - estimating costs")
                cost_response = self._handle_cost_calculation_sync(
                    multi_intent, enhanced_context, user_message
                )
                if cost_response:
                    yield cost_response
                    yield {
                        "reply": "",
                        "status": "complete",
                        "ui_type": "none",
                        "context": enhanced_context.to_dict(),
                    }
                    return

            # === BOOK HOTEL: Confirm booking ===
            if intent == "book_hotel":
                logger.info(
                    "🏨 [STREAMING] book_hotel detected - confirming reservation"
                )
                booking_response = self._handle_book_hotel_sync(
                    multi_intent, enhanced_context
                )
                if booking_response:
                    yield booking_response
                    yield {
                        "reply": "",
                        "status": "complete",
                        "ui_type": "none",
                        "context": enhanced_context.to_dict(),
                    }
                    return

            # === DISTANCE CALCULATION: Calculate distances (FIX #4 - EARLY CHECK) ===
            if intent in ["get_distance", "get_directions"] or self._is_distance_query(
                user_message
            ):
                logger.info(
                    "📏 [STREAMING] Distance query detected - calculating distances"
                )
                distance_response = self._handle_distance_query_sync(
                    multi_intent, enhanced_context, user_message
                )
                if distance_response:
                    yield distance_response
                    yield {
                        "reply": "",
                        "status": "complete",
                        "ui_type": "none",
                        "context": enhanced_context.to_dict(),
                    }
                    return

            # ============================================================
            # 🧠 FLOW CONTROL: State-First, Intent-Second
            # Kiểm tra workflow_state TRƯỚC KHI thực thi Intent
            # ============================================================
            current_state = getattr(enhanced_context, "workflow_state", "INITIAL")
            is_backtrack = self._is_backtrack_signal(user_message)
            logger.info(f"🔄 Current State: {current_state}")
            logger.info(f"🔄 Is backtrack signal: {is_backtrack}")
            logger.info(
                f"🔄 Context keys: {list(context.keys()) if context else 'None'}"
            )

            # CASE 0: BACKTRACK - User muốn quay lại chỉnh sửa sau khi đã finalize
            # Phải check TRƯỚC CASE A vì builder có thể đã bị xóa
            if current_state == "CHOOSING_HOTEL" and is_backtrack:
                logger.info(
                    f"🔙 BACKTRACK detected! User wants to modify spots while in CHOOSING_HOTEL"
                )

                # Nếu builder đã bị xóa (do finalize), khôi phục từ last_itinerary
                if (
                    not enhanced_context.itinerary_builder
                    and enhanced_context.last_itinerary
                ):
                    logger.info(f"🔄 Rebuilding builder from last_itinerary...")
                    enhanced_context.itinerary_builder = (
                        self._rebuild_builder_from_last(
                            enhanced_context.last_itinerary, enhanced_context
                        )
                    )

                # Chuyển state về CHOOSING_SPOTS
                enhanced_context.workflow_state = "CHOOSING_SPOTS"
                logger.info(f"✅ State changed: CHOOSING_HOTEL → CHOOSING_SPOTS")

                # Route đến builder handler
                builder_response = self._continue_interactive_itinerary_sync(
                    user_message, enhanced_context
                )
                if builder_response:
                    yield builder_response
                    yield {
                        "reply": "",
                        "status": "complete",
                        "ui_type": "none",
                        "context": enhanced_context.to_dict(),
                    }
                    return

            # CASE A: Đang trong Interactive Builder → Ưu tiên giữ user ở builder
            if self._should_stay_in_builder(
                multi_intent, enhanced_context, user_message
            ):
                logger.info(
                    f"📌 User is in builder (state={current_state}), routing to builder handler"
                )

                # Kiểm tra flow_action từ LLM (finalize, continue, back)
                flow_action = getattr(multi_intent, "flow_action", None)

                if flow_action == "finalize" or self._is_finalize_signal(user_message):
                    # User nói "xong" → Finalize current step
                    finalize_response = self._finalize_interactive_itinerary_sync(
                        enhanced_context
                    )
                    yield finalize_response
                    # NO completion signal - let frontend continue conversation
                    return
                else:
                    # Tiếp tục trong builder (chọn số, hỏi thêm địa điểm, etc.)
                    continue_result = self._continue_interactive_itinerary_sync(
                        user_message, enhanced_context
                    )

                    # Check if this is a builder initialization result
                    # (happens when user inputs start_date and builder restarts)
                    if (
                        continue_result
                        and continue_result.get("ui_type")
                        == "interactive-itinerary-spot"
                        and continue_result.get("status") == "choosing_spots"
                    ):
                        # This is builder initialization, yield result and complete signal, then RETURN
                        yield continue_result
                        yield {
                            "reply": "",
                            "status": "complete",
                            "ui_type": "none",
                            "context": enhanced_context.to_dict(),
                        }
                        return
                    else:
                        # Normal continuation, yield result and complete signal
                        yield continue_result
                        yield {
                            "reply": "",
                            "status": "complete",
                            "ui_type": "none",
                            "context": enhanced_context.to_dict(),
                        }
                        return

            # CASE B: StateGuard - Lọc Intent bị chặn do thiếu điều kiện
            valid_intents, blocked_reasons = self._validate_intent_flow(
                multi_intent, enhanced_context
            )

            if blocked_reasons and not valid_intents:
                # Tất cả intents bị chặn → Trả về hướng dẫn
                guard_response = self._generate_state_guard_response(
                    blocked_reasons, enhanced_context
                )
                if guard_response:
                    yield guard_response
                    yield {
                        "reply": "",
                        "status": "complete",
                        "ui_type": "none",
                        "context": enhanced_context.to_dict(),
                    }
                    return

            # Cập nhật intents đã lọc
            if blocked_reasons:
                logger.info(
                    f"🚫 StateGuard filtered: {[b['intent'] for b in blocked_reasons]}"
                )
                # Update MultiIntent: set primary_intent and sub_intents from valid_intents
                if valid_intents:
                    multi_intent.primary_intent = valid_intents[0]
                    multi_intent.sub_intents = valid_intents[1:]

            # CASE C: Bắt đầu Interactive Builder mới (plan_trip từ INITIAL)
            if (
                multi_intent.primary_intent == "plan_trip"
                and current_state == "INITIAL"
            ):
                if multi_intent.location and multi_intent.duration:
                    # Check if user provided FULL information → auto-generate mode
                    # Normalize budget and people types safely before comparisons
                    import re

                    # Budget normalization
                    has_budget = False
                    # Prefer multi_intent.budget, fallback to context.budget
                    budget_val = getattr(multi_intent, "budget", None)
                    if budget_val is None and getattr(enhanced_context, "budget", None):
                        budget_val = enhanced_context.budget
                        multi_intent.budget = budget_val
                    if isinstance(budget_val, (int, float)):
                        has_budget = budget_val > 0
                    elif isinstance(budget_val, str):
                        lower = budget_val.lower().replace(",", ".").strip()
                        m = re.search(
                            r"(\d+(?:\.\d+)?)\s*(triệu|tr|triệu đồng|vnd|đ)?", lower
                        )
                        if m:
                            num = float(m.group(1))
                            unit = m.group(2) or ""
                            budget_val = (
                                int(num * 1_000_000)
                                if ("triệu" in unit or "tr" in unit)
                                else int(num)
                            )
                            multi_intent.budget = budget_val
                            has_budget = budget_val > 0

                    # People normalization
                    has_multiple_people = False
                    # Prefer multi_intent.people_count, fallback to context.people_count
                    people_val = getattr(multi_intent, "people_count", None)
                    if (
                        people_val is None
                        or (
                            isinstance(people_val, (int, float))
                            and int(people_val) <= 1
                        )
                    ) and getattr(enhanced_context, "people_count", None):
                        people_val = enhanced_context.people_count
                        multi_intent.people_count = people_val
                    if isinstance(people_val, (int, float)):
                        has_multiple_people = int(people_val) > 1
                    elif isinstance(people_val, str):
                        pm = re.search(r"(\d+)", people_val)
                        if pm:
                            multi_intent.people_count = int(pm.group(1))
                            has_multiple_people = multi_intent.people_count > 1

                    # FALLBACK: If budget/people still not available, parse from user message
                    if not has_budget or not has_multiple_people:
                        logger.info(
                            f"📝 Fallback regex parsing from user_message: budget_ok={has_budget}, people_ok={has_multiple_people}"
                        )
                        msg_lower = user_message.lower()

                        # Try to extract budget: "6 triệu", "6tr", "6.5 triệu"
                        if not has_budget:
                            budget_match = re.search(
                                r"(\d+(?:[.,]\d+)?)\s*(?:triệu|tr|triệu đồng|vnd|đ)",
                                msg_lower,
                            )
                            if budget_match:
                                budget_str = budget_match.group(1).replace(",", ".")
                                multi_intent.budget = int(float(budget_str) * 1_000_000)
                                has_budget = True
                                logger.info(
                                    f"✅ Extracted budget from regex: {multi_intent.budget}"
                                )

                        # Try to extract people: "5 người", "5 people", "5 đi"
                        if not has_multiple_people:
                            people_match = re.search(
                                r"(\d+)\s*(?:người|people|đi)", msg_lower
                            )
                            if people_match:
                                multi_intent.people_count = int(people_match.group(1))
                                has_multiple_people = multi_intent.people_count > 1
                                logger.info(
                                    f"✅ Extracted people_count from regex: {multi_intent.people_count}"
                                )

                    # Trigger AUTO mode if we have budget; people_count optional
                    has_full_info = has_budget

                    logger.info(
                        f"🔍 DEBUG auto-generate check: location={multi_intent.location}, duration={multi_intent.duration}, budget={multi_intent.budget}, people={multi_intent.people_count}, has_budget={has_budget}, has_full_info={has_full_info}"
                    )

                    if has_full_info:
                        logger.info(
                            f"🤖 Budget available ({multi_intent.budget}) - enabling AUTO-GENERATE mode"
                        )
                        # Store in context for later use
                        enhanced_context.auto_generate_mode = True
                        enhanced_context.destination = multi_intent.location
                        enhanced_context.duration = multi_intent.duration
                        enhanced_context.budget = multi_intent.budget
                        enhanced_context.people_count = multi_intent.people_count
                        enhanced_context.budget_level = (
                            multi_intent.budget_level or "trung bình"
                        )
                        enhanced_context.companion_type = (
                            multi_intent.companion_type or "bạn bè"
                        )
                        logger.info(
                            f"✅ Context updated: auto_mode=True, budget={enhanced_context.budget}, people={enhanced_context.people_count}"
                        )
                    else:
                        logger.info(
                            f"📋 No budget detected - using MANUAL selection mode"
                        )
                        enhanced_context.auto_generate_mode = False

                    logger.info(
                        f"🗓️ Starting itinerary builder: {multi_intent.location} x {multi_intent.duration} days (auto_mode={enhanced_context.auto_generate_mode})"
                    )
                    result = self._start_interactive_itinerary_sync(
                        multi_intent.location, multi_intent.duration, enhanced_context
                    )

                    # CRITICAL: Ensure auto_generate_mode is saved in itinerary_builder for persistence
                    if result and enhanced_context.itinerary_builder:
                        enhanced_context.itinerary_builder["auto_generate_mode"] = (
                            enhanced_context.auto_generate_mode
                        )
                        logger.info(
                            f"💾 Saved auto_generate_mode={enhanced_context.auto_generate_mode} to itinerary_builder"
                        )

                    yield result
                    yield {
                        "reply": "",
                        "status": "complete",
                        "ui_type": "none",
                        "context": enhanced_context.to_dict(),
                    }
                    return

            # ============================================================
            # END FLOW CONTROL - Continue with normal processing below
            # ============================================================

            # === HANDLE "MORE" REQUESTS FIRST ===
            # When user asks for more spots/hotels/food, directly execute fresh search
            if multi_intent.keywords and "more" in multi_intent.keywords:
                logger.info(
                    f"🔄 Handling 'MORE' request for {multi_intent.primary_intent}"
                )
                more_response = await self._handle_more_request(
                    multi_intent, enhanced_context, user_message
                )
                if more_response:
                    yield more_response
                    yield {
                        "reply": "",
                        "status": "complete",
                        "ui_type": "none",
                        "context": enhanced_context.to_dict(),
                    }
                    return

            # === PRIORITY CHECK: Customize itinerary per day ===
            # This must be checked BEFORE regular intent handling
            day_preferences = self._parse_day_preferences(user_message)
            if day_preferences:
                logger.info(f"🗓️ Detected day preferences: {day_preferences}")
                customize_response = await self._handle_customize_itinerary(
                    day_preferences, enhanced_context, multi_intent
                )
                if customize_response:
                    yield customize_response
                    yield {
                        "reply": "",
                        "status": "complete",
                        "ui_type": "none",
                        "context": enhanced_context.to_dict(),
                    }
                    return

            # === SMART HANDLER: Check for special intents first ===
            special_response = await self._handle_special_intent(
                multi_intent, enhanced_context, user_message
            )
            if special_response:
                yield special_response
                yield {
                    "reply": "",
                    "status": "complete",
                    "ui_type": "none",
                    "context": enhanced_context.to_dict(),
                }
                return

            # === SMART CONVERSATION: Check if we need more info before planning ===
            info_gathering_response = await self._check_info_gathering_needed(
                multi_intent, enhanced_context, user_message
            )
            if info_gathering_response:
                yield info_gathering_response
                yield {
                    "reply": "",
                    "status": "complete",
                    "ui_type": "none",
                    "context": enhanced_context.to_dict(),
                }
                return

            # Update context from primary intent
            extracted_intent = multi_intent.to_extracted_intent()
            enhanced_context.update_from_intent(extracted_intent)

            # === IMPORTANT: Merge context back into multi_intent for planning ===
            # If user says "đi 3 ngày" without location, use context's destination
            if not multi_intent.location and enhanced_context.destination:
                logger.info(
                    f"📍 Using context destination: {enhanced_context.destination}"
                )
                multi_intent.location = enhanced_context.destination
            if not multi_intent.duration and enhanced_context.duration:
                logger.info(f"⏱️ Using context duration: {enhanced_context.duration}")
                multi_intent.duration = enhanced_context.duration
            if not multi_intent.budget and enhanced_context.budget:
                logger.info(f"💰 Using context budget: {enhanced_context.budget}")
                multi_intent.budget = enhanced_context.budget

            # Phase 2: Create plan
            plan = self.multi_planner.plan(multi_intent)

            # Phase 3: Execute plan WITH STREAMING
            # Group tasks by type for progressive delivery
            # PASS enhanced_context for Anti-Greedy filtering
            task_groups = self._group_tasks_for_streaming(plan.tasks, enhanced_context)
            logger.info(
                f"📊 Task groups: {list(task_groups.keys())} ({sum(len(t) for t in task_groups.values())} total tasks)"
            )

            if not task_groups:
                # No tasks created - use smart fallback
                logger.warning("⚠️ No task groups created - using smart fallback")
                fallback_response = await self._create_smart_fallback(
                    user_message, multi_intent, enhanced_context
                )
                yield fallback_response
                yield {
                    "reply": "",
                    "status": "complete",
                    "ui_type": "none",
                    "context": enhanced_context.to_dict(),
                }
                return

            aggregated_all = {
                "spots": [],
                "hotels": [],
                "food": [],
                "itinerary": [],
                "costs": {},
            }

            # ============================================================
            # PRIORITY BREAK MODE: Chỉ thực thi 1 group ưu tiên
            # để tránh đổ UI ào ạt (Greedy Execution)
            # ============================================================
            priority_break_mode = current_state in [
                "INITIAL",
                "CHOOSING_SPOTS",
                "CHOOSING_HOTEL",
            ]
            executed_primary_group = False

            for group_name, tasks in task_groups.items():
                logger.info(f"🔄 Processing group: {group_name} ({len(tasks)} tasks)")

                # Execute this group - PASS AGGREGATED DATA for dependencies!
                group_results = self._execute_plan_subset(
                    tasks, user_message, aggregated_all
                )

                # Aggregate group results
                group_aggregated = self._aggregate_results(group_results)
                logger.info(
                    f"   Aggregated: {list(group_aggregated.keys())} - has data: {any(group_aggregated.values())}"
                )

                # Merge into total
                for key in aggregated_all.keys():
                    if key in group_aggregated:
                        if isinstance(group_aggregated[key], list):
                            aggregated_all[key].extend(group_aggregated[key])
                        elif isinstance(group_aggregated[key], dict):
                            aggregated_all[key].update(group_aggregated[key])

                # Store results in context for follow-up queries
                if group_aggregated.get("spots"):
                    enhanced_context.update_last_spots(group_aggregated["spots"])
                if group_aggregated.get("hotels"):
                    enhanced_context.update_last_hotels(group_aggregated["hotels"])
                if group_aggregated.get("food"):
                    enhanced_context.update_last_foods(group_aggregated["food"])
                if group_aggregated.get("itinerary"):
                    enhanced_context.update_last_itinerary(
                        {"days": group_aggregated["itinerary"]}
                    )
                if group_aggregated.get("costs"):
                    enhanced_context.update_last_cost(group_aggregated["costs"])

                # ============================================================
                # INTENT RE-RANKING: Choose best intent based on results quality
                # ============================================================
                if (
                    not executed_primary_group
                    and group_aggregated
                    and any(group_aggregated.values())
                ):
                    # Calculate result quality score for this group
                    quality_score = self._calculate_result_quality(
                        group_name, group_aggregated
                    )
                    logger.info(
                        f"   Quality score for {group_name}: {quality_score:.2f}"
                    )

                    # If this group has better results than primary intent, consider re-ranking
                    if quality_score > 0.7:  # High quality threshold
                        # Check if we should prioritize this intent over primary
                        should_rerank = self._should_rerank_intent(
                            group_name,
                            multi_intent.primary_intent,
                            quality_score,
                            aggregated_all,
                        )

                        if should_rerank:
                            logger.info(
                                f"🔄 [RE-RANK] Switching primary intent: {multi_intent.primary_intent} → {group_name}"
                            )
                            # Don't change multi_intent object, just use this group as response

                # Only yield if this group has meaningful data
                if group_aggregated and any(group_aggregated.values()):
                    # For streaming: create section-specific response, not full aggregate
                    # Determine which section to format based on group name
                    section_response = self._format_group_section(
                        group_name, group_aggregated, multi_intent, enhanced_context
                    )

                    if section_response:
                        # Add streaming metadata
                        section_response["status"] = "partial"
                        section_response["group"] = group_name
                        section_response["progress"] = f"{group_name} complete"
                        section_response["workflow_state"] = current_state

                        # Yield this chunk
                        yield section_response
                        executed_primary_group = True

                        # =====================================================
                        # 🛑 PRIORITY BREAK: Dừng sau khi gửi 1 UI Component
                        # để giữ luồng dẫn dắt, tránh đổ hotel+food+cost cùng lúc
                        # =====================================================
                        if priority_break_mode:
                            logger.info(
                                f"🛑 Priority Break: Stopping after {group_name} to guide user"
                            )
                            break

                # Don't yield empty groups to reduce overhead

            # Final summary - ALWAYS yield to signal completion
            final_response = {
                "reply": (
                    "✅ Đã hoàn tất tất cả thông tin!"
                    if not priority_break_mode
                    else ""
                ),
                "ui_type": "none",
                "status": "complete",
                "context": enhanced_context.to_dict(),
            }
            yield final_response

        except Exception as e:
            logger.error(f"❌ Streaming error: {e}", exc_info=True)
            yield {
                "error": str(e),
                "reply": "⚠️ Xin lỗi, có lỗi xảy ra.",
                "ui_type": "none",
                "status": "error",
            }

    def _group_tasks_for_streaming(
        self, tasks: List, enhanced_context=None
    ) -> Dict[str, List]:
        """
        Group tasks by type for progressive delivery.

        REFACTORED: Nhóm theo Pipeline du lịch và filter dựa trên workflow_state
        để tránh Greedy Execution (đổ UI ào ạt).

        Pipeline: discovery -> itinerary_build -> accommodation -> dining -> finance

        Returns:
            OrderedDict with tasks grouped by travel pipeline stage
        """
        from collections import OrderedDict

        # Nhóm theo giai đoạn du lịch (không chỉ theo loại kỹ thuật)
        groups = OrderedDict(
            [
                ("discovery", []),  # Tìm điểm đến, intro vùng miền
                ("spots", []),  # Các task liên quan đến chọn spot
                ("hotels", []),  # Tìm khách sạn
                ("food", []),  # Tìm quán ăn
                ("itinerary", []),  # Tạo lịch trình
                ("cost", []),  # Tính toán chi phí
            ]
        )

        for task in tasks:
            tid = task.task_id.lower()

            # Ánh xạ task vào đúng giai đoạn
            if any(x in tid for x in ["spots_", "general_info", "discover"]):
                groups["spots"].append(task)
            elif "hotel_" in tid:
                groups["hotels"].append(task)
            elif "food_" in tid:
                groups["food"].append(task)
            elif "itinerary_" in tid:
                groups["itinerary"].append(task)
            elif "cost_" in tid:
                groups["cost"].append(task)
            else:
                groups["discovery"].append(task)

        # Loại bỏ groups rỗng
        groups = OrderedDict((k, v) for k, v in groups.items() if v)

        # ============================================================
        # ANTI-GREEDY FILTER: Chỉ giữ lại group phù hợp với workflow_state
        # ============================================================
        if enhanced_context:
            current_state = getattr(enhanced_context, "workflow_state", "INITIAL")

            # Nếu đang chọn spots, chặn hotels/food/cost
            if current_state == "CHOOSING_SPOTS":
                allowed_groups = ["discovery", "spots"]
                groups = OrderedDict(
                    (k, v) for k, v in groups.items() if k in allowed_groups
                )
                logger.info(
                    f"🎯 Anti-Greedy: Filtered to {list(groups.keys())} for state {current_state}"
                )

            # Nếu đang chọn hotel, chặn cost
            elif current_state == "CHOOSING_HOTEL":
                allowed_groups = ["hotels", "discovery", "spots"]  # Cho phép backtrack
                groups = OrderedDict(
                    (k, v) for k, v in groups.items() if k in allowed_groups
                )
                logger.info(
                    f"🎯 Anti-Greedy: Filtered to {list(groups.keys())} for state {current_state}"
                )

        return groups

    def _format_group_section(
        self, group_name: str, group_data: Dict[str, Any], multi_intent, context
    ) -> Optional[Dict[str, Any]]:
        """
        Format a single group's section for streaming

        Returns ONLY the content for this specific group, not full response
        """
        location = multi_intent.location or context.destination or "khu vực này"

        # Handle each group type separately with minimal formatting
        if group_name == "spots" and group_data.get("spots"):
            spots = group_data["spots"][:6]
            return self.response_aggregator._format_spots(spots, location)

        elif group_name == "hotels" and group_data.get("hotels"):
            hotels = group_data["hotels"][:5]
            return self.response_aggregator._format_hotels(hotels, location)

        elif group_name == "food" and group_data.get("food"):
            food = group_data["food"][:5]
            return self.response_aggregator._format_food(food, location)

        elif group_name == "itinerary" and group_data.get("itinerary"):
            # For itinerary, create just the section without full page
            duration = multi_intent.duration or context.duration or 3
            itinerary_section = self.response_aggregator._create_itinerary_section(
                group_data["itinerary"], duration
            )
            return {
                "reply": itinerary_section,
                "ui_type": "itinerary",
                "ui_data": {"itinerary": group_data["itinerary"]},
            }

        elif group_name == "cost" and group_data.get("costs"):
            cost_section = self.response_aggregator._create_cost_section(
                group_data["costs"]
            )
            return {
                "reply": cost_section,
                "ui_type": "cost",
                "ui_data": {"costs": group_data["costs"]},
            }

        elif group_name == "discovery" and group_data.get("general_info"):
            # Handle general_info/discovery responses (list of info items)
            info_results = group_data["general_info"]
            if info_results:
                # Get first info item
                info_item = (
                    info_results[0] if isinstance(info_results, list) else info_results
                )

                # Extract answer text
                if isinstance(info_item, dict):
                    answer = info_item.get("answer", "")
                elif isinstance(info_item, str):
                    answer = info_item
                else:
                    answer = str(info_item)

                if answer:
                    return {
                        "reply": answer,
                        "ui_type": "text",
                        "ui_data": {},
                    }

        return None

    async def _handle_more_request(
        self, multi_intent, context, user_message: str
    ) -> Optional[Dict[str, Any]]:
        """
        Handle 'more' requests - when user wants more spots/hotels/food

        Directly executes fresh search without requiring new info gathering
        """
        intent = multi_intent.primary_intent
        location = multi_intent.location or getattr(context, "destination", None)

        if not location:
            return None  # Need location to search

        logger.info(
            f"🔄 Processing 'more' request: intent={intent}, location={location}"
        )

        try:
            # Create fresh search task based on intent
            if intent == "find_spot":
                # Get spots from MongoDB
                spots = []
                if self.mongo_manager:
                    spots_col = self.mongo_manager.get_collection("spots_detailed")
                    if spots_col is not None:
                        # Find spots using address field (spots use address instead of province)
                        query = {"address": {"$regex": location, "$options": "i"}}
                        cursor = (
                            spots_col.find(query).skip(6).limit(6)
                        )  # Skip first 6, get next 6
                        for doc in cursor:
                            spots.append(
                                {
                                    "name": doc.get("name", ""),
                                    "province": location,  # Use location from context
                                    "category": doc.get("category", ""),
                                    "description": doc.get("description_short")
                                    or doc.get("description", ""),
                                    "rating": doc.get("rating", 4.0),
                                    "image": doc.get("image")
                                    or doc.get("image_url")
                                    or "",
                                    "lat": doc.get("lat", 0),
                                    "lng": doc.get("lng", 0),
                                }
                            )

                if spots:
                    return self.response_aggregator._format_spots(spots, location)
                else:
                    return {
                        "reply": f"📍 Hiện tại tôi đã hiển thị tất cả địa điểm có trong dữ liệu về {location}.\n\n"
                        f"Bạn có muốn tìm khách sạn hoặc xem lịch trình không?",
                        "ui_type": "options",
                        "ui_data": {
                            "options": [
                                f"🏨 Tìm khách sạn {location}",
                                f"🗓️ Lên lịch trình {location}",
                            ]
                        },
                        "context": context.to_dict(),
                        "status": "partial",
                    }

            elif intent == "find_hotel":
                hotels = []
                if self.mongo_manager:
                    hotels_col = self.mongo_manager.get_collection("hotels")
                    if hotels_col is not None:
                        query = {"province": {"$regex": location, "$options": "i"}}
                        cursor = hotels_col.find(query).skip(5).limit(5)
                        for doc in cursor:
                            hotels.append(
                                {
                                    "name": doc.get("name", ""),
                                    "province": doc.get("province", location),
                                    "address": doc.get("address", ""),
                                    "rating": doc.get("rating", 4.0),
                                    "price": doc.get("price", 0),
                                    "priceRange": doc.get(
                                        "priceRange", f"{doc.get('price', 0):,} VNĐ/đêm"
                                    ),
                                    "image": (
                                        doc.get("image_url")
                                        or doc.get("images", [""])[0]
                                        if doc.get("images")
                                        else ""
                                    ),
                                    "amenities": doc.get("amenities", []),
                                }
                            )

                if hotels:
                    return self.response_aggregator._format_hotels(hotels, location)
                else:
                    return {
                        "reply": f"🏨 Đây là tất cả khách sạn có trong dữ liệu về {location}.\n\n"
                        f"Bạn có muốn xem địa điểm tham quan hoặc lên lịch trình không?",
                        "ui_type": "options",
                        "ui_data": {
                            "options": [
                                f"📍 Địa điểm tham quan {location}",
                                f"🗓️ Lên lịch trình {location}",
                            ]
                        },
                        "context": context.to_dict(),
                        "status": "partial",
                    }

            elif intent == "find_food":
                food = []
                if self.mongo_manager:
                    food_col = self.mongo_manager.get_collection("food")
                    if food_col is not None:
                        query = {"province": {"$regex": location, "$options": "i"}}
                        cursor = food_col.find(query).skip(5).limit(5)
                        for doc in cursor:
                            food.append(
                                {
                                    "name": doc.get("name", ""),
                                    "province": doc.get("province", location),
                                    "category": doc.get("category", ""),
                                    "description": doc.get("description", ""),
                                    "price": doc.get("price", ""),
                                    "image": (
                                        doc.get("image_url")
                                        or doc.get("images", [""])[0]
                                        if doc.get("images")
                                        else ""
                                    ),
                                }
                            )

                if food:
                    return self.response_aggregator._format_food(food, location)
                else:
                    return {
                        "reply": f"🍜 Đây là tất cả quán ăn có trong dữ liệu về {location}.",
                        "ui_type": "none",
                        "context": context.to_dict(),
                        "status": "partial",
                    }

        except Exception as e:
            logger.error(f"❌ Error handling more request: {e}")
            return None

        return None

    def _handle_special_intent_sync(
        self, multi_intent, context, user_message: str
    ) -> Optional[Dict[str, Any]]:
        """
        Handle special intents synchronously for process_request()

        Handles: greeting, chitchat, thanks, farewell, book_hotel, calculate_cost, show_itinerary
        Returns response dict or None if normal processing should continue
        """
        try:
            intent = multi_intent.primary_intent
            logger.info(
                f"🔧 [DEBUG] _handle_special_intent_sync called with intent={intent}, has_builder={bool(getattr(context, 'itinerary_builder', None))}"
            )
        except Exception as e:
            logger.error(f"❌ [DEBUG] Error in _handle_special_intent_sync start: {e}")
            return None

        # === HIGHEST PRIORITY: Check for show_itinerary intent FIRST ===
        # This must be checked BEFORE builder continuation logic
        if intent == "show_itinerary" or self._is_recall_itinerary_request(
            user_message
        ):
            logger.info(
                "🔍 User wants to view existing itinerary (show_itinerary intent)"
            )
            return self._handle_recall_itinerary(context)

        # === CHECK IF USER IS IN INTERACTIVE ITINERARY BUILDER MODE ===
        # FIX 2026-01-18: Skip builder mode if workflow_state is FINALIZED
        # When FINALIZED, user should be able to ask other questions without triggering builder
        itinerary_builder = getattr(context, "itinerary_builder", None)
        workflow_state = getattr(context, "workflow_state", None)
        if itinerary_builder and workflow_state != "FINALIZED":
            # User is building itinerary interactively
            lower_msg = user_message.lower().strip()

            # FIX #3: Allow calculate_cost intent even in builder mode
            # User wants to see budget, NOT continue building
            if intent == "calculate_cost":
                logger.info(
                    "[FIX #3] 🎯 calculate_cost request in builder mode - handling separately"
                )
                return self._handle_cost_calculation_sync(
                    multi_intent, context, user_message
                )

            # FIX #4: Allow distance calculation even in builder mode
            # User wants to check distances, NOT continue building
            if intent in ["get_distance", "get_directions"] or self._is_distance_query(
                user_message
            ):
                logger.info(
                    "[FIX #4] 📏 Distance query in builder mode - handling separately"
                )
                return self._handle_distance_query_sync(
                    multi_intent, context, user_message
                )

            # Check for cancel/reset commands
            cancel_patterns = [
                "hủy",
                "huy",
                "cancel",
                "bắt đầu lại",
                "bat dau lai",
                "lập lịch lại",
                "lap lich lai",
                "làm lại",
                "lam lai",
                "reset",
            ]
            if any(p in lower_msg for p in cancel_patterns):
                context.itinerary_builder = None
                return {
                    "reply": "🔄 Đã hủy lịch trình hiện tại.\n\n"
                    "Bạn có muốn lập lịch trình mới không? "
                    "Hãy cho tôi biết bạn muốn đi đâu và bao nhiêu ngày!",
                    "ui_type": "none",
                    "context": context.to_dict(),
                    "status": "partial",
                }

            # Continue building itinerary with user's input
            result = self._continue_interactive_itinerary_sync(user_message, context)
            if result:
                return result

        # === GREETING ===
        if intent == "greeting":
            # Use conversational LLM for natural greeting
            llm_response = self._handle_conversational_chat(
                user_message, context, intent_type="greeting"
            )
            if llm_response:
                return llm_response

            # Fallback template
            return {
                "reply": "Xin chào! 👋 Tôi là SaoLa AI - trợ lý du lịch AI của bạn. "
                "Tôi có thể giúp bạn:\n"
                "• 🗺️ Lên lịch trình du lịch\n"
                "• 🏨 Tìm khách sạn phù hợp\n"
                "• 📍 Gợi ý địa điểm tham quan\n"
                "• 🍜 Khám phá ẩm thực địa phương\n"
                "• 💰 Ước tính chi phí chuyến đi\n\n"
                "Bạn muốn đi đâu? 🌍",
                "ui_type": "greeting",
                "context": context.to_dict(),
                "status": "partial",
            }

        # === CHITCHAT ===
        if intent == "chitchat":
            # Use conversational LLM for natural chitchat
            llm_response = self._handle_conversational_chat(
                user_message, context, intent_type="chitchat"
            )
            if llm_response:
                return llm_response

            # Fallback template
            return {
                "reply": "Tôi là SaoLa AI - trợ lý du lịch AI! 🦌\n\n"
                "Tôi chuyên về du lịch Việt Nam và có thể giúp bạn:\n"
                "• Lên kế hoạch chuyến đi\n"
                "• Tìm khách sạn tốt nhất\n"
                "• Gợi ý điểm đến hấp dẫn\n\n"
                "Hãy cho tôi biết bạn muốn đi đâu nhé! 🗺️",
                "ui_type": "chitchat",
                "context": context.to_dict(),
                "status": "partial",
            }

        # === THANKS ===
        if intent == "thanks":
            # Use conversational LLM for natural thanks response
            llm_response = self._handle_conversational_chat(
                user_message, context, intent_type="thanks"
            )
            if llm_response:
                return llm_response

            return {
                "reply": "Không có gì ạ! 😊 Rất vui được giúp đỡ bạn. "
                "Nếu cần hỗ trợ thêm về chuyến đi, cứ hỏi tôi nhé! ✈️",
                "ui_type": "thanks",
                "context": context.to_dict(),
                "status": "partial",
            }

        # === FAREWELL ===
        if intent == "farewell":
            # Use conversational LLM for natural farewell
            llm_response = self._handle_conversational_chat(
                user_message, context, intent_type="farewell"
            )
            if llm_response:
                return llm_response

            return {
                "reply": "Tạm biệt bạn! 👋 Chúc bạn có chuyến đi thật vui vẻ! "
                "Hẹn gặp lại lần sau! 🌟",
                "ui_type": "farewell",
                "context": context.to_dict(),
                "status": "partial",
            }

        # === BOOK HOTEL ===
        if intent == "book_hotel":
            return self._handle_book_hotel_sync(multi_intent, context)

        # === FIX A: UPDATE PEOPLE COUNT (recalculate cost with new people) ===
        # Handle "2 người thì sao" when user is in COST_ESTIMATION state
        if intent == "update_people_count":
            return self._handle_update_people_count(multi_intent, context, user_message)

        # === COST CALCULATION ===
        if intent == "calculate_cost":
            return self._handle_cost_calculation_sync(
                multi_intent, context, user_message
            )

        # === GET LOCATION TIPS (tips/advice for selected spots) ===
        if intent == "get_location_tips":
            return self._handle_location_tips_sync(multi_intent, context, user_message)

        # === FIX C: GET PLACE DETAILS (detailed info about a specific place) ===
        # Different from tips - this returns description, history, features
        if intent == "get_place_details":
            return self._handle_place_details_sync(multi_intent, context, user_message)

        # === DISTANCE CALCULATION ===
        # Handle both get_distance and get_directions (LLM sometimes confuses them)
        if intent in ["get_distance", "get_directions"] or self._is_distance_query(
            user_message
        ):
            return self._handle_distance_query_sync(multi_intent, context, user_message)

        # === GET DETAIL (spot/hotel detail from context) ===
        if intent == "get_detail":

            return self._handle_detail_request_sync(multi_intent, context, user_message)

        # === SKIP special handling for planning/searching intents ===
        # These should go through PHASE 2 (plan & execute)
        skip_intents = [
            "plan_trip",
            "find_hotel",
            "find_food",
            "general_info",
            "find_spot",
        ]
        if intent in skip_intents:
            # Check if this is actually a detail request (not a search)
            lower_msg = user_message.lower()
            detail_patterns = [
                "chi tiết về",
                "thông tin về",
                "cho tôi biết về",
                "nói về",
                "giới thiệu về",
                "chi tiet ve",
                "thong tin ve",
                "cho toi biet ve",
                "noi ve",
                "gioi thieu ve",
            ]
            is_detail_request = any(p in lower_msg for p in detail_patterns)

            if is_detail_request and intent == "find_spot":
                # This is actually a detail request, not a list search
                return self._handle_detail_request_sync(
                    multi_intent, context, user_message
                )

            # === INTERACTIVE ITINERARY BUILDER ===
            # If user wants to plan a trip, start interactive mode instead of auto-generating
            if intent == "plan_trip":
                location = multi_intent.location
                duration = multi_intent.duration or getattr(context, "num_days", None)

                if location and duration:
                    # Check if user wants interactive mode or already in building mode
                    itinerary_state = getattr(context, "itinerary_builder", None)

                    if itinerary_state is None:
                        # Start interactive itinerary builder
                        return self._start_interactive_itinerary_sync(
                            location, duration, context
                        )
                    else:
                        # Continue building itinerary
                        return self._continue_interactive_itinerary_sync(
                            user_message, context
                        )

            # Otherwise, let it go to PHASE 2 for normal processing
            return None

        # Check for ordinal reference in user_message (e.g., "địa điểm đầu tiên")
        ordinal_index = self._extract_ordinal_index(user_message.lower())
        if ordinal_index is not None:
            return self._handle_detail_request_sync(multi_intent, context, user_message)

        # === RECALL ITINERARY - "Xem lại lịch trình", "Lịch trình của tôi" ===
        if self._is_recall_itinerary_request(user_message):
            return self._handle_recall_itinerary(context)

        return None

    def _handle_book_hotel_sync(
        self, multi_intent, context
    ) -> Optional[Dict[str, Any]]:
        """Handle book_hotel intent synchronously"""
        try:
            # Try to extract hotel name from keywords first
            hotel_name_from_keywords = (
                multi_intent.keywords[0] if multi_intent.keywords else None
            )
            location = getattr(context, "destination", None)

            logger.info(
                f"📍 Book hotel request: hotel_name_from_keywords={hotel_name_from_keywords}, location={location}"
            )

            # NEW: Use LLM to extract hotel name from user message for better accuracy
            user_message = getattr(multi_intent, "original_message", "") or ""
            hotel_name = None
            hotel_url = None
            hotel_price = None

            # Check if we have last_hotels in context
            last_hotels = getattr(context, "last_hotels", [])

            if last_hotels and user_message:
                # Use LLM to match user intent with hotel list
                logger.info(
                    f"🤖 [HOTEL FIX] Using LLM to extract hotel from: '{user_message}'"
                )

                hotel_list_text = "\n".join(
                    [
                        f"{i+1}. {h.get('name')} - {h.get('price', 0):,} VNĐ/đêm"
                        for i, h in enumerate(last_hotels[:10])
                    ]
                )

                llm_prompt = f"""USER nói: "{user_message}"

DANH SÁCH KHÁCH SẠN:
{hotel_list_text}

USER muốn chọn khách sạn nào?
- Nếu rõ ràng → trả về SỐ THỨ TỰ (1-{len(last_hotels)})
- Nếu không rõ → trả về "none"

CHỈ TRẢ VỀ SỐ hoặc "none", KHÔNG GIẢI THÍCH."""

                try:
                    llm_result = (
                        self.llm.complete(
                            prompt=llm_prompt, max_tokens=10, temperature=0.1
                        )
                        .strip()
                        .lower()
                    )

                    logger.info(f"🤖 [HOTEL FIX] LLM result: {llm_result}")

                    # Parse index
                    import re

                    match = re.search(r"\d+", llm_result)
                    if match:
                        hotel_index = int(match.group()) - 1  # Convert to 0-based
                        if 0 <= hotel_index < len(last_hotels):
                            selected_hotel_data = last_hotels[hotel_index]
                            hotel_name = selected_hotel_data.get("name")
                            hotel_price = selected_hotel_data.get("price")
                            hotel_url = selected_hotel_data.get("url")
                            logger.info(
                                f"✅ [HOTEL FIX] LLM selected hotel #{hotel_index + 1}: {hotel_name}"
                            )
                except Exception as llm_error:
                    logger.error(f"❌ [HOTEL FIX] LLM extraction failed: {llm_error}")

            # Fallback to keyword-based extraction
            if not hotel_name and hotel_name_from_keywords:
                hotel_name = hotel_name_from_keywords
                logger.info(
                    f"⚠️ [HOTEL FIX] Using fallback keyword extraction: {hotel_name}"
                )

                # Try to find hotel price from context.last_hotels with fuzzy matching
                if last_hotels:
                    # Use fuzzy matching
                    from difflib import SequenceMatcher

                    best_match = None
                    best_ratio = 0.0

                    for hotel in last_hotels:
                        hotel_name_in_list = hotel.get("name", "")
                        ratio = SequenceMatcher(
                            None, hotel_name.lower(), hotel_name_in_list.lower()
                        ).ratio()

                        if ratio > best_ratio:
                            best_ratio = ratio
                            best_match = hotel

                    if best_match and best_ratio > 0.6:  # 60% similarity threshold
                        hotel_name = best_match.get("name")  # Use full hotel name
                        hotel_price = best_match.get("price")
                        hotel_url = best_match.get("url")
                        logger.info(
                            f"✅ [HOTEL FIX] Fuzzy match found (ratio={best_ratio:.2f}): {hotel_name}, price: {hotel_price}"
                        )

            if hotel_name:
                # Store selected hotel in context
                context.selected_hotel = hotel_name
                logger.info(f"💾 Saved hotel to memory: {hotel_name}")

                # If not found in context, search database
                if not hotel_price and self.mongo_manager:
                    hotels_col = self.mongo_manager.get_collection("hotels")
                    if hotels_col is not None:
                        first_word = (
                            hotel_name.split()[0] if hotel_name.split() else hotel_name
                        )
                        hotel_doc = hotels_col.find_one(
                            {"name": {"$regex": first_word, "$options": "i"}}
                        )
                        if hotel_doc:
                            hotel_url = hotel_doc.get("url")
                            hotel_price = hotel_doc.get("price")
                            logger.info(
                                f"✅ Found hotel in DB: {hotel_doc.get('name')}"
                            )

                # Save price to context
                if hotel_price:
                    context.selected_hotel_price = hotel_price
                    logger.info(f"� Saved hotel price to memory: {hotel_price:,} VNĐ")

                # Build booking response
                booking_links = []
                if hotel_url:
                    booking_links.append(f"🔗 [Đặt phòng tại website gốc]({hotel_url})")

                search_name = hotel_name.replace(" ", "+")
                booking_links.extend(
                    [
                        f"🔗 [Tìm trên Booking.com](https://www.booking.com/searchresults.html?ss={search_name})",
                        f"🔗 [Tìm trên Agoda](https://www.agoda.com/search?q={search_name})",
                        f"🔗 [Tìm trên Traveloka](https://www.traveloka.com/vi-vn/hotel/search?q={search_name})",
                    ]
                )

                price_info = (
                    f"\n💰 Giá tham khảo: **{hotel_price:,} VNĐ/đêm**"
                    if hotel_price
                    else ""
                )

                return {
                    "reply": f"🏨 **Đặt phòng: {hotel_name}**{price_info}\n\n"
                    f"📱 **Cách đặt phòng:**\n"
                    f"{chr(10).join(booking_links)}\n\n"
                    f"💡 **Lưu ý khi đặt phòng:**\n"
                    f"• So sánh giá giữa các trang để tìm ưu đãi tốt nhất\n"
                    f"• Kiểm tra chính sách hủy phòng trước khi đặt\n"
                    f"• Đọc review gần đây từ khách hàng\n\n"
                    f"Bạn cần tôi ước tính chi phí toàn bộ chuyến đi không? 💰",
                    "ui_type": "booking",
                    "ui_data": {
                        "selected_hotel": hotel_name,
                        "hotel_url": hotel_url,
                        "hotel_price": hotel_price,
                        "booking_links": booking_links,
                    },
                    "status": "partial",
                    "context": context.to_dict(),
                }
            else:
                return {
                    "reply": "Bạn muốn đặt phòng khách sạn nào? 🏨\n"
                    "Hãy cho tôi biết tên khách sạn bạn quan tâm!",
                    "ui_type": "booking_prompt",
                    "context": context.to_dict(),
                    "status": "partial",
                }
        except Exception as e:
            logger.error(f"❌ Book hotel error: {e}")
            import traceback

            traceback.print_exc()
            return {
                "reply": f"🏨 Tôi ghi nhận bạn muốn đặt phòng.\n\n"
                f"Bạn có thể tìm kiếm khách sạn trên:\n"
                f"• [Booking.com](https://www.booking.com)\n"
                f"• [Agoda](https://www.agoda.com)\n"
                f"• [Traveloka](https://www.traveloka.com)\n\n"
                f"Hoặc cho tôi biết tên khách sạn cụ thể bạn muốn đặt!",
                "ui_type": "booking",
                "context": context.to_dict(),
                "status": "partial",
            }

    # ==================== INTERACTIVE ITINERARY BUILDER ====================

    def _start_interactive_itinerary_sync(
        self, location: str, duration: int, context
    ) -> Dict[str, Any]:
        """Start interactive itinerary building mode - ask user for Day 1 preferences"""
        try:
            # CRITICAL: Set duration in context immediately - used as fallback when builder missing
            context.duration = duration
            logger.info(f"✅ Set context.duration={duration}")

            # STEP 0: Ask for start_date if not provided
            if not context.start_date:
                logger.info("❓ start_date not set, prompting user...")
                # CRITICAL: Set workflow_state IMMEDIATELY so next request stays in builder
                context.workflow_state = "CHOOSING_SPOTS"
                logger.info(
                    "✅ Workflow state set to CHOOSING_SPOTS (waiting for start_date)"
                )
                # CRITICAL: Store duration in temporary builder so it's preserved when user inputs date
                context.itinerary_builder = {
                    "location": location,
                    "total_days": duration,  # Save duration here!
                    "waiting_for_start_date": True,  # Flag to indicate incomplete builder
                }
                logger.info(f"💾 Stored duration={duration} in temporary builder")
                return {
                    "reply": f'📅 **Bạn dự định đi {location} từ ngày nào?**\n\n💡 **Gợi ý:**\n• Nhập ngày cụ thể (VD: "20/1/2026" hoặc "20-1-2026")\n• Hoặc gõ: "hôm nay", "mai", "ngày kia"\n• Nếu chưa có, hãy gõ "chưa biết" để được hỗ trợ chọn ngày phù hợp',
                    "ui_type": "text",
                    "ui_data": {},
                    "context": context.to_dict(),
                    "status": "waiting_for_start_date",
                }

            logger.info(
                f"🗓️ Starting interactive itinerary builder: {location}, {duration} days from {context.start_date}"
            )

            # Get available spots for this location
            spots = self._get_spots_for_location_sync(location)

            if not spots:
                # Fallback to auto-generate if no spots found
                logger.info(
                    "⚠️ No spots found for interactive mode, falling back to auto-generate"
                )
                return None  # Let it proceed to PHASE 2

            # Initialize itinerary builder state in context
            context.itinerary_builder = {
                "location": location,
                "total_days": duration,
                "current_day": 1,
                "days_plan": {},  # {1: [spot1, spot2], 2: [...], ...}
                "available_spots": [
                    {
                        "idx": i + 1,  # Display number (1-based for UI)
                        "id": str(s.get("_id")),  # Real MongoDB ObjectId for tracking
                        "name": s.get("name"),
                        "category": (
                            s.get("category") or s.get("tags", [None])[0]
                            if s.get("tags")
                            else "Tham quan"
                        ),
                        "rating": s.get("rating"),
                        "description": s.get("description", ""),
                        "image": s.get("image")
                        or s.get("image_url")
                        or (s.get("images", [None])[0] if s.get("images") else None),
                        "image_url": s.get("image_url")
                        or s.get("image")
                        or (s.get("images", [None])[0] if s.get("images") else None),
                        "latitude": s.get("latitude"),
                        "longitude": s.get("longitude"),
                    }
                    for i, s in enumerate(spots[:20])  # Limit to 20 spots
                ],
            }

            # Debug: Verify first spot has required fields
            if context.itinerary_builder["available_spots"]:
                first_spot = context.itinerary_builder["available_spots"][0]
                logger.info(
                    f"📋 First available spot: idx={first_spot.get('idx')}, id={first_spot.get('id')[:8] if first_spot.get('id') else 'None'}..., has_coords={bool(first_spot.get('latitude') and first_spot.get('longitude'))}"
                )

            context.destination = location
            context.num_days = duration

            # CRITICAL: Set workflow state to CHOOSING_SPOTS
            context.workflow_state = "CHOOSING_SPOTS"
            logger.info("✅ Workflow state set to CHOOSING_SPOTS")

            # Get weather information for the trip
            weather_intro = ""
            if context.start_date:
                try:
                    logger.info(
                        f"🌤️ Fetching weather for {location} from {context.start_date} for {duration} days..."
                    )
                    weather_data = self.weather.get_weather(
                        location, context.start_date, duration
                    )
                    logger.info(
                        f"🌤️ Weather data received: {weather_data.keys() if weather_data else 'None'}"
                    )
                    weather_intro = self.weather.build_weather_response(weather_data)
                    logger.info(f"☀️ Weather intro length: {len(weather_intro)} chars")
                    if weather_intro:
                        logger.info(
                            f"☀️ Weather comfort level: {weather_data.get('overall', {}).get('comfort_level', 'N/A')}"
                        )
                except Exception as e:
                    logger.error(f"❌ Weather fetch error: {e}")
                    # Try to find province from database if it's an "Unknown province" error
                    if "Unknown province" in str(e):
                        logger.warning(
                            f"⚠️ Weather service doesn't recognize '{location}', trying to find province from database..."
                        )
                        try:
                            # Query database to find province using same approach as _get_spots_for_location_sync
                            if self.mongo_manager:
                                try:
                                    from unidecode import unidecode

                                    location_id = unidecode(location.lower()).replace(
                                        " ", "-"
                                    )
                                except ImportError:
                                    location_id = location.lower().replace(" ", "-")

                                logger.info(
                                    f"🔍 Querying database for location_id: {location_id}"
                                )

                                spots_col = self.mongo_manager.get_collection(
                                    "spots_detailed"
                                )
                                if spots_col is None:
                                    logger.info(
                                        "⚠️ spots_detailed not found, trying spots collection"
                                    )
                                    spots_col = self.mongo_manager.get_collection(
                                        "spots"
                                    )

                                if spots_col is None:
                                    logger.error("❌ No spots collection found")
                                else:
                                    logger.info(
                                        f"✅ Using collection: {spots_col.name}"
                                    )

                                # Try to find location with multiple patterns
                                query = {
                                    "$or": [
                                        {"province_id": location_id},
                                        {
                                            "province": {
                                                "$regex": location,
                                                "$options": "i",
                                            }
                                        },
                                        {"name": {"$regex": location, "$options": "i"}},
                                        {
                                            "address": {
                                                "$regex": location,
                                                "$options": "i",
                                            }
                                        },
                                    ]
                                }

                                logger.info(
                                    f"🔍 Query patterns: province_id={location_id}, name/address/province regex={location}"
                                )

                                spot = spots_col.find_one(query)  # Get ALL fields
                                logger.info(
                                    f"🔍 Query result keys: {list(spot.keys()) if spot else 'None'}"
                                )
                                if spot:
                                    logger.info(f"🔍 Full spot: {spot}")

                                # Extract province name from location field (format: "Name, Tỉnh ProvinceVietnamese, Country")
                                province = None
                                if spot and "location" in spot:
                                    location_text = spot.get("location", "")
                                    # Extract province name between "Tỉnh" and ","
                                    if "Tỉnh" in location_text:
                                        parts = location_text.split("Tỉnh")
                                        if len(parts) > 1:
                                            province = parts[1].split(",")[0].strip()
                                            logger.info(
                                                f"✅ Extracted province from location: {province}"
                                            )

                                if province:
                                    logger.info(f"✅ Using province: {province}")
                                    weather_data = self.weather.get_weather(
                                        province, context.start_date, duration
                                    )
                                    weather_intro = self.weather.build_weather_response(
                                        weather_data
                                    )
                                    logger.info(
                                        f"☀️ Weather fetched using province: {province}"
                                    )
                                else:
                                    logger.warning(
                                        f"⚠️ Could not find province for location: {location}"
                                    )
                        except Exception as db_error:
                            logger.error(f"❌ Database query error: {db_error}")
            else:
                logger.warning("⚠️ No start_date available for weather fetch")

            # Format spots list for display
            def get_category(s):
                cat = s.get("category")
                # Check for None, empty, or string "None"
                if cat and cat != "None" and cat != "null":
                    return cat
                tags = s.get("tags", [])
                if tags and len(tags) > 0 and tags[0]:
                    return tags[0]
                return "Điểm tham quan"

            spots_list = "\n".join(
                [f"  {i+1}. **{s.get('name')}**" for i, s in enumerate(spots[:10])]
            )

            reply = f"""🗓️ **Lập lịch trình {duration} ngày tại {location}**

{weather_intro}

Tôi sẽ giúp bạn lên kế hoạch chi tiết cho từng ngày!

📍 **NGÀY 1** - Bạn muốn đi những địa điểm nào?

Dưới đây là các địa điểm phổ biến tại {location}:

💡 **Hướng dẫn:**
• Nhập số thứ tự địa điểm (VD: "1, 3, 5" hoặc "1 3 5")
• Hoặc gõ tên địa điểm bạn muốn đi
• Gõ **"xem thêm"** để xem thêm địa điểm khác
• Gõ **"bỏ qua"** nếu muốn tôi tự động lên lịch cho ngày này
• Gõ **"tự động"** để tôi tự tạo toàn bộ lịch trình"""

            # CRITICAL: Store selected spot IDs to avoid duplication in later days
            context.selected_spot_ids = []  # Initialize empty list for tracking

            # Format spots for UI with idx
            spots_for_ui = [
                {
                    "idx": i + 1,
                    "id": (
                        str(s.get("_id"))
                        if s.get("_id")
                        else (s.get("id") or f"spot_{i+1}")
                    ),
                    "name": s.get("name"),
                    "category": get_category(s),  # Use fallback function
                    "rating": s.get("rating"),
                    "description": (
                        (
                            s.get("description_short")
                            or s.get("description")
                            or s.get("description_full", "")
                        )[:100]
                    ),
                    "image": s.get("image")
                    or s.get("image_url")
                    or (s.get("images", [None])[0] if s.get("images") else None),
                }
                for i, s in enumerate(
                    spots[:10]
                )  # Show first 10 spots in UI (light for system)
            ]

            return {
                "reply": reply,
                "ui_type": "itinerary_builder",
                "ui_data": {
                    "spots": spots_for_ui,
                    "all_spots": context.itinerary_builder.get("available_spots", []),
                    "current_day": 1,
                    "total_days": duration,
                    "destination": location,
                    "has_more_spots": len(spots) > 10,  # Flag if more spots available
                    "total_available_spots": len(spots),  # Total count for "see more"
                    "show_load_more_button": True,  # Show "Xem thêm" button at bottom
                    "load_more_text": f"Xem thêm ({len(spots) - 10} điểm khác)",  # Button text with count
                },
                "context": context.to_dict(),
                "status": "partial",
            }

        except Exception as e:
            logger.error(f"❌ Start interactive itinerary error: {e}")
            import traceback

            traceback.print_exc()
            return None  # Fallback to auto-generate

    def _rebuild_builder_from_last(self, last_itinerary: Dict, context) -> Dict:
        """
        Khôi phục itinerary_builder từ last_itinerary đã chốt.
        Dùng khi user muốn BACKTRACK (quay lại sửa lịch trình).

        Args:
            last_itinerary: Lịch trình đã finalize trước đó
            context: Enhanced context để lấy thông tin bổ sung

        Returns:
            Dict builder state có thể dùng tiếp
        """
        if not last_itinerary:
            return None

        # Extract data from last_itinerary
        location = last_itinerary.get("location") or getattr(context, "destination", "")
        duration = last_itinerary.get("duration") or getattr(context, "duration", 3)
        days_data = last_itinerary.get("days", [])

        # Rebuild days_plan từ itinerary days
        days_plan = {}
        for day_info in days_data:
            day_num = day_info.get("day", 1)
            spots = day_info.get("spots", [])
            # Convert spots to proper format - preserve all fields if dict, otherwise create minimal
            days_plan[str(day_num)] = [
                (
                    s
                    if isinstance(s, dict) and s.get("id")
                    else {"name": s if isinstance(s, str) else s.get("name", "")}
                )
                for s in spots
            ]

        builder = {
            "location": location,
            "total_days": duration,
            "current_day": 1,  # Reset về ngày 1 để user chọn thêm
            "days_plan": days_plan,
            "available_spots": [],  # Sẽ được fill lại khi show options
            "is_rebuilt": True,  # Flag để biết đây là builder được khôi phục
        }

        total_spots = sum(len(spots) for spots in days_plan.values())
        logger.info(
            f"🔄 Rebuilt builder from last_itinerary: {location}, {duration} days, {total_spots} spots preserved"
        )

        return builder

    def _generate_auto_itinerary_sync(
        self, location: str, duration: int, context
    ) -> Dict[str, Any]:
        """
        Auto-generate itinerary using LLM with constraints:
        - 3 spots per session (breakfast/lunch/dinner or morning/afternoon/evening)
        - Budget constraint from user requirements
        - People count consideration
        """
        try:
            # Normalize budget to a numeric value to avoid formatting errors
            budget_num = 0
            try:
                b = getattr(context, "budget", None)
                if isinstance(b, (int, float)):
                    budget_num = int(b)
                elif isinstance(b, str):
                    import re

                    bl = b.lower().replace(",", ".").strip()
                    m = re.search(
                        r"(\d+(?:[.,]\d+)?)\s*(triệu|tr|triệu đồng|vnd|đ)?", bl
                    )
                    if m:
                        num = float(m.group(1))
                        unit = m.group(2) or ""
                        budget_num = (
                            int(num * 1_000_000)
                            if ("triệu" in unit or "tr" in unit)
                            else int(num)
                        )
            except Exception as _:
                budget_num = 0

            logger.info(
                f"🤖 AUTO-GENERATING itinerary: {location} x {duration} days, budget={budget_num}, people={getattr(context, 'people_count', None)}"
            )

            # Get available spots for this location
            spots = self._get_spots_for_location_sync(location)
            if not spots:
                logger.error(f"❌ No spots found for {location}")
                return {
                    "reply": f"Xin lỗi, tôi không tìm thấy địa điểm nào ở {location}. Bạn có thể thử điểm đến khác không?",
                    "ui_type": "text",
                    "ui_data": {},
                    "context": context.to_dict(),
                }

            # Prepare prompt for LLM to select spots
            budget_per_day = budget_num / duration if budget_num else None
            people = context.people_count or 1

            prompt = f"""Bạn là chuyên gia lập kế hoạch du lịch. Hãy tạo lịch trình {duration} ngày ở {location} với các ràng buộc:

**Yêu cầu:**
# Số người: {people}
# Ngân sách tổng: {budget_num:,.0f} VNĐ ({budget_per_day:,.0f} VNĐ/ngày nếu phân bổ đều)
- Phong cách: {context.budget_level}
- Đối tượng đi cùng: {context.companion_type}

**Ràng buộc:**
1. Mỗi ngày phải có ĐÚNG 3 địa điểm (3 buổi: sáng/trưa/tối hoặc breakfast/lunch/dinner)
2. Tổng chi phí ước tính phải ≤ {context.budget:,.0f} VNĐ
3. Chọn địa điểm từ danh sách dưới đây (bắt buộc)
4. Ưu tiên địa điểm phù hợp với {context.companion_type} và mức giá {context.budget_level}

**Danh sách địa điểm khả dụng:**
{chr(10).join([f"{i+1}. {s.get('name')} - {s.get('category', 'Tham quan')} - Rating: {s.get('rating', 'N/A')}" for i, s in enumerate(spots[:30])])}

**Trả về JSON theo format:**
{{
    "days": [
        {{
            "day": 1,
            "spots": [
                {{"name": "Tên địa điểm 1", "session": "morning"}},
                {{"name": "Tên địa điểm 2", "session": "afternoon"}},
                {{"name": "Tên địa điểm 3", "session": "evening"}}
            ]
        }}
    ],
    "total_estimated_cost": 5500000,
    "reasoning": "Giải thích ngắn gọn về lựa chọn"
}}"""

            # Call LLM via shared client
            from app.services.llm_client import llm_client

            llm_response = llm_client.chat(
                messages=[
                    {
                        "role": "system",
                        "content": "Bạn là chuyên gia du lịch. Trả về ĐÚNG JSON format được yêu cầu, không thêm chú thích.",
                    },
                    {"role": "user", "content": prompt},
                ],
                json_mode=False,
            )

            logger.info(f"📤 LLM response: {llm_response[:400]}...")

            # Parse JSON response with multiple fallbacks
            import json
            import re

            def _try_parse_candidates(raw: str) -> Dict[str, Any]:
                candidates = []

                # 1) Markdown code block ```json ... ```
                m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
                if m:
                    candidates.append(m.group(1))

                # 2) First/last brace slice
                first, last = raw.find("{"), raw.rfind("}")
                if first != -1 and last != -1 and last > first:
                    candidates.append(raw[first : last + 1])

                # 3) All balanced-brace like blocks (shallow regex)
                for block in re.findall(r"\{[^{}]*\}", raw, re.DOTALL):
                    candidates.append(block)

                # 4) Whole response as-is (last resort)
                candidates.append(raw)

                for idx, cand in enumerate(candidates):
                    try:
                        return json.loads(cand)
                    except Exception as parse_err:
                        logger.warning(f"⚠️ JSON candidate {idx} failed: {parse_err}")
                raise ValueError("No valid JSON found in LLM response")

            plan_data = _try_parse_candidates(llm_response)
            days_plan = plan_data.get("days", [])
            total_cost = plan_data.get("total_estimated_cost", 0)
            reasoning = plan_data.get("reasoning", "")

            logger.info(
                f"✅ LLM generated {len(days_plan)} days, estimated cost: {total_cost:,.0f} VNĐ"
            )

            # Map spot names to actual spot objects
            spot_name_map = {s.get("name").lower(): s for s in spots}
            finalized_days = []

            for day_info in days_plan:
                day_num = day_info.get("day")
                day_spots = []

                for spot_ref in day_info.get("spots", []):
                    spot_name_raw = spot_ref.get("name", "")
                    spot_name = spot_name_raw.lower()
                    session = spot_ref.get("session", "morning")

                    # Find matching spot
                    matched_spot = None
                    for name_key, spot_obj in spot_name_map.items():
                        if spot_name in name_key or name_key in spot_name:
                            matched_spot = spot_obj
                            break

                    if matched_spot:
                        day_spots.append(
                            {
                                "id": str(matched_spot.get("_id"))
                                or matched_spot.get("id")
                                or spot_name_raw,
                                "name": matched_spot.get("name"),
                                "category": matched_spot.get("category")
                                or (
                                    matched_spot.get("tags", [None])[0]
                                    if matched_spot.get("tags")
                                    else "Tham quan"
                                ),
                                "rating": matched_spot.get("rating"),
                                "image": matched_spot.get("image")
                                or matched_spot.get("image_url"),
                                "latitude": matched_spot.get("latitude"),
                                "longitude": matched_spot.get("longitude"),
                                "session": session,
                            }
                        )
                    else:
                        # If LLM proposes a spot not in DB, still show it as fallback entry
                        day_spots.append(
                            {
                                "id": spot_name_raw or f"spot_{session}",
                                "name": spot_name_raw or "Địa điểm đề xuất",
                                "category": "Đề xuất",
                                "rating": None,
                                "image": None,
                                "latitude": None,
                                "longitude": None,
                                "session": session,
                            }
                        )

                finalized_days.append({"day": day_num, "spots": day_spots})

            # Fetch hotels for the destination (hybrid search + fallback to last_hotels)
            hotels = []
            try:
                hotels_raw = self.hybrid_search.search_hotels(
                    query=location,
                    province_id=None,
                    limit=5,
                    threshold=0.25,
                )
                if not hotels_raw:
                    # Fallback: try with "khách sạn {location}" to bias search
                    hotels_raw = self.hybrid_search.search_hotels(
                        query=f"khách sạn {location}",
                        province_id=None,
                        limit=5,
                        threshold=0.25,
                    )

                for h in hotels_raw or []:
                    hotels.append(
                        {
                            "id": str(h.get("_id")) if h.get("_id") else h.get("id"),
                            "name": h.get("name"),
                            "rating": h.get("rating"),
                            "price": h.get("price")
                            or h.get("price_display")
                            or h.get("price_formatted"),
                            "address": h.get("address") or h.get("location"),
                            "image": h.get("image")
                            or h.get("image_url")
                            or (
                                h.get("images", [None])[0] if h.get("images") else None
                            ),
                        }
                    )

                # If still empty, fallback to last_hotels in context
                if not hotels and getattr(context, "last_hotels", None):
                    logger.info("🏨 Using last_hotels from context as fallback")
                    hotels = context.last_hotels[:5]

                if hotels:
                    context.last_hotels = hotels
                    logger.info(
                        f"🏨 Attached {len(hotels)} hotels to itinerary_display"
                    )
                    # Auto-select a budget-friendly hotel for cost calculation
                    try:
                        if not getattr(context, "selected_hotel", None):
                            # Calculate max hotel price to fit within budget
                            nights = max(duration - 1, 1)

                            # Baseline per-day costs for food/transport/activities
                            from app.services.experts.itinerary_expert import (
                                CostCalculatorExpert,
                            )

                            estimates = CostCalculatorExpert.COST_ESTIMATES
                            people_count = people or 1
                            budget_level = (
                                getattr(context, "budget_level", "trung bình")
                                or "trung bình"
                            )

                            # Scale multiplier based on budget_level
                            scale_multiplier = {
                                "rẻ": 0.5,
                                "re": 0.5,
                                "trung bình": 1.0,
                                "trung binh": 1.0,
                                "đắt": 1.5,
                                "dat": 1.5,
                            }.get(budget_level.lower().strip(), 1.0)

                            food = (
                                estimates["food_per_day"]["trung bình"]
                                * duration
                                * people_count
                                * scale_multiplier
                            )
                            transport = (
                                estimates["transport_per_day"]["trung bình"]
                                * duration
                                * scale_multiplier
                            )
                            activities = (
                                estimates["activities_per_day"]["trung bình"]
                                * duration
                                * people_count
                                * scale_multiplier
                            )
                            other_costs = food + transport + activities

                            # If the baseline other costs already exceed the user's budget,
                            # scale them down to keep at least ~30% of budget for hotels.
                            if budget_num and other_costs > budget_num * 0.7:
                                reduction_factor = (budget_num * 0.7) / other_costs
                                food *= reduction_factor
                                transport *= reduction_factor
                                activities *= reduction_factor
                                other_costs = food + transport + activities
                                logger.info(
                                    f"💰 Scaled other costs by {reduction_factor:.2f} to fit budget: other_costs={int(other_costs)}"
                                )

                            # Max accommodation budget = total_budget - other_costs
                            max_accommodation = (
                                budget_num - other_costs if budget_num else float("inf")
                            )
                            max_hotel_price_per_night = (
                                max_accommodation / nights
                                if nights > 0
                                else float("inf")
                            )

                            logger.info(
                                f"💰 Budget allocation (budget_level={budget_level}): total={budget_num}, other_costs={int(other_costs)}, max_hotel/night={int(max_hotel_price_per_night)}"
                            )

                            # Find best hotel within budget, sorted by price (cheapest first)
                            affordable_hotels = []
                            for h in hotels:
                                h_price = h.get("price")
                                try:
                                    h_price_int = (
                                        int(h_price) if h_price else float("inf")
                                    )
                                except Exception:
                                    h_price_int = float("inf")

                                if h_price_int <= max_hotel_price_per_night:
                                    affordable_hotels.append((h_price_int, h))

                            # Sort by price (ascending) to pick cheapest within budget
                            if affordable_hotels:
                                affordable_hotels.sort(key=lambda x: x[0])
                                selected_hotel = affordable_hotels[0][1]
                                logger.info(
                                    f"✅ Selected budget-friendly hotel: {selected_hotel.get('name')} @ {affordable_hotels[0][0]} VND/đêm"
                                )
                            else:
                                # If no hotel fits budget, pick cheapest available
                                hotels_with_prices = [
                                    (
                                        (int(h.get("price", float("inf"))), h)
                                        if h.get("price")
                                        else (float("inf"), h)
                                    )
                                    for h in hotels
                                ]
                                hotels_with_prices.sort(key=lambda x: x[0])
                                selected_hotel = (
                                    hotels_with_prices[0][1]
                                    if hotels_with_prices
                                    else hotels[0]
                                )
                                logger.warning(
                                    f"⚠️ No hotel fits budget, selected cheapest: {selected_hotel.get('name')}"
                                )

                            sel_name = selected_hotel.get("name")
                            sel_price = (
                                selected_hotel.get("price")
                                or selected_hotel.get("price_display")
                                or selected_hotel.get("price_formatted")
                            )
                            if sel_name and sel_price:
                                context.selected_hotel = sel_name
                                try:
                                    context.selected_hotel_price = int(sel_price)
                                except Exception:
                                    context.selected_hotel_price = sel_price
                                context.user_selected_hotel = False
                                logger.info(
                                    f"Hotel auto-selected: {sel_name} ({context.selected_hotel_price} VND/night)"
                                )
                    except Exception as e:
                        logger.warning(f"Could not auto-select hotel for budget: {e}")
                        # Fallback to first hotel
                        try:
                            if not getattr(context, "selected_hotel", None):
                                first = hotels[0]
                                sel_name = first.get("name")
                                sel_price = (
                                    first.get("price")
                                    or first.get("price_display")
                                    or first.get("price_formatted")
                                )
                                if sel_name and sel_price:
                                    context.selected_hotel = sel_name
                                    context.selected_hotel_price = (
                                        int(sel_price)
                                        if isinstance(sel_price, (int, float))
                                        or sel_price.isdigit()
                                        else sel_price
                                    )
                                    context.user_selected_hotel = False
                        except Exception as fallback_e:
                            logger.warning(
                                f"Fallback hotel selection failed: {fallback_e}"
                            )
                else:
                    logger.info("🏨 No hotels found for itinerary_display")
            except Exception as e:
                logger.warning(f"⚠️ Failed to fetch hotels for itinerary_display: {e}")

            # Build itinerary object
            # Optionally recompute budget to include hotel costs
            recomputed_cost = None
            budget_breakdown = None
            budget_warning = None
            try:
                if hotels and (hotels[0].get("price") is not None):
                    # Use selected/first hotel's price as per-night baseline
                    selected_price = float(hotels[0]["price"]) or 0.0
                    nights = max(duration - 1, 1)

                    # Baseline per-day costs with budget_level scaling
                    from app.services.experts.itinerary_expert import (
                        CostCalculatorExpert,
                    )

                    estimates = CostCalculatorExpert.COST_ESTIMATES
                    budget_level = (
                        getattr(context, "budget_level", "trung bình") or "trung bình"
                    )

                    # Scale multiplier based on budget_level
                    scale_multiplier = {
                        "rẻ": 0.5,
                        "re": 0.5,
                        "trung bình": 1.0,
                        "trung binh": 1.0,
                        "đắt": 1.5,
                        "dat": 1.5,
                    }.get(budget_level.lower().strip(), 1.0)

                    people_count = people or 1
                    food = (
                        estimates["food_per_day"]["trung bình"]
                        * duration
                        * people_count
                        * scale_multiplier
                    )
                    transport = (
                        estimates["transport_per_day"]["trung bình"]
                        * duration
                        * scale_multiplier
                    )
                    activities = (
                        estimates["activities_per_day"]["trung bình"]
                        * duration
                        * people_count
                        * scale_multiplier
                    )

                    # If the baseline other costs already exceed the budget, scale them down
                    # so that at least ~30% of the budget is left for accommodation.
                    other_costs = food + transport + activities
                    if budget_num and other_costs > budget_num * 0.7:
                        reduction_factor = (budget_num * 0.7) / other_costs
                        food *= reduction_factor
                        transport *= reduction_factor
                        activities *= reduction_factor
                        other_costs = food + transport + activities
                        logger.info(
                            f"💰 Scaled other costs by {reduction_factor:.2f} for warning calc: other_costs={int(other_costs)}"
                        )
                    accommodation = int(selected_price * nights)

                    recomputed_cost = int(accommodation + food + transport + activities)
                    budget_breakdown = {
                        "accommodation_per_night": int(selected_price),
                        "nights": nights,
                        "accommodation": accommodation,
                        "food": int(food),
                        "transport": int(transport),
                        "activities": int(activities),
                        "total": recomputed_cost,
                    }

                    # Check if over budget and generate warning
                    if budget_num > 0 and recomputed_cost > budget_num:
                        overage = recomputed_cost - budget_num
                        max_hotel_price = (
                            max(
                                0,
                                (budget_num - (food + transport + activities)) / nights,
                            )
                            if nights > 0
                            else 0
                        )
                        budget_warning = {
                            "type": "over_budget",
                            "message": f"Chi phí ước tính ({recomputed_cost:,.0f} VND) vượt ngân sách ({budget_num:,.0f} VND) thêm {overage:,.0f} VND",
                            "overage": overage,
                            "suggestions": [
                                f"Chọn khách sạn rẻ hơn (dưới {int(max_hotel_price):,.0f} VND/đêm)",
                                "Giảm chi phí ăn uống hoặc hoạt động",
                                "Tăng ngân sách hoặc giảm số ngày",
                            ],
                        }
                        logger.warning(f"{budget_warning['message']}")
            except Exception as e:
                logger.warning(f"Budget recompute failed, keep LLM estimate: {e}")

            itinerary = {
                "location": location,
                "duration": duration,
                "start_date": context.start_date,
                "people_count": people,
                "budget": budget_num,
                "days": finalized_days,
                "estimated_cost": (
                    recomputed_cost
                    if isinstance(recomputed_cost, int) and recomputed_cost > 0
                    else total_cost
                ),
                "reasoning": reasoning,
                "hotels": hotels,
            }

            if budget_breakdown:
                itinerary["budget_breakdown"] = budget_breakdown

            if budget_warning:
                itinerary["budget_warning"] = budget_warning

            # Store in context
            context.last_itinerary = itinerary
            context.workflow_state = "FINALIZED"

            logger.info(f"Auto-generated itinerary saved to context")

            # Build reply with warning if over budget
            reply = f"Auto-generated itinerary for {duration} days in {location}!\n\n{reasoning}\n\nEstimated cost: {(recomputed_cost if isinstance(recomputed_cost, int) and recomputed_cost > 0 else total_cost):,.0f} VND (budget {budget_num:,.0f} VND)\n\nDetails below:"

            if budget_warning:
                reply += (
                    f"\n\n{budget_warning['message']}\n\nSuggestions:\n"
                    + "\n".join([f"- {s}" for s in budget_warning["suggestions"]])
                )

            return {
                "reply": reply,
                "ui_type": "itinerary_display",
                "ui_data": {"itinerary": itinerary},
                "context": context.to_dict(),
                "status": "complete",
            }

        except Exception as e:
            # Robust fallback: build a simple auto itinerary instead of switching to manual
            logger.error(f"❌ Auto-generate itinerary error: {e}")
            import traceback

            traceback.print_exc()

            try:
                # Use available spots to compose a basic plan: 3 spots/day
                spots = self._get_spots_for_location_sync(location) or []
                selected = spots[: duration * 3] if spots else []
                finalized_days = []
                idx = 0
                for day in range(1, duration + 1):
                    day_spots = []
                    for session in ["morning", "afternoon", "evening"]:
                        if idx < len(selected):
                            s = selected[idx]
                            idx += 1
                            day_spots.append(
                                {
                                    "id": (
                                        str(s.get("_id"))
                                        if s.get("_id")
                                        else s.get("id")
                                    ),
                                    "name": s.get("name"),
                                    "category": s.get("category")
                                    or (
                                        s.get("tags", [None])[0]
                                        if s.get("tags")
                                        else "Tham quan"
                                    ),
                                    "rating": s.get("rating"),
                                    "image": s.get("image")
                                    or s.get("image_url")
                                    or (
                                        s.get("images", [None])[0]
                                        if s.get("images")
                                        else None
                                    ),
                                    "latitude": s.get("latitude"),
                                    "longitude": s.get("longitude"),
                                    "session": session,
                                }
                            )
                    finalized_days.append({"day": day, "spots": day_spots})

                # Normalize budget again for safe display
                budget_num = 0
                try:
                    b = getattr(context, "budget", None)
                    if isinstance(b, (int, float)):
                        budget_num = int(b)
                    elif isinstance(b, str):
                        import re

                        bl = b.lower().replace(",", ".").strip()
                        m = re.search(
                            r"(\d+(?:[.,]\d+)?)\s*(triệu|tr|triệu đồng|vnd|đ)?", bl
                        )
                        if m:
                            num = float(m.group(1))
                            unit = m.group(2) or ""
                            budget_num = (
                                int(num * 1_000_000)
                                if ("triệu" in unit or "tr" in unit)
                                else int(num)
                            )
                except Exception:
                    budget_num = 0

                itinerary = {
                    "location": location,
                    "duration": duration,
                    "start_date": getattr(context, "start_date", None),
                    "people_count": getattr(context, "people_count", 1),
                    "budget": budget_num,
                    "days": finalized_days,
                    "estimated_cost": int(budget_num * 0.9) if budget_num else 0,
                    "reasoning": "Tạo lịch trình tự động cơ bản vì gặp lỗi định dạng từ LLM.",
                }

                context.last_itinerary = itinerary
                context.workflow_state = "FINALIZED"

                return {
                    "reply": f"🎉 **Đã tạo lịch trình tự động (fallback) cho {duration} ngày ở {location}!**\n\n💰 **Ước tính chi phí:** {itinerary['estimated_cost']:,.0f} VNĐ (ngân sách {budget_num:,.0f} VNĐ)\n\n📋 Xem chi tiết bên dưới:",
                    "ui_type": "itinerary_display",
                    "ui_data": {"itinerary": itinerary},
                    "context": context.to_dict(),
                    "status": "complete",
                }
            except Exception as fallback_error:
                logger.error(
                    f"❌ Fallback auto itinerary also failed: {fallback_error}"
                )
                # Last resort: keep previous behavior
                return self._start_interactive_itinerary_sync(
                    location, duration, context
                )

    def _continue_interactive_itinerary_sync(
        self, user_message: str, context
    ) -> Optional[Dict[str, Any]]:
        """Continue building itinerary based on user's selection with BACKTRACKING support"""
        try:
            builder = getattr(context, "itinerary_builder", None)

            # STEP 1: Check if waiting for start_date
            # Check if builder is incomplete (waiting_for_start_date flag) OR no builder at all
            if not context.start_date and (
                not builder or builder.get("waiting_for_start_date")
            ):
                # If user asks for FULL AUTO mode, persist the flag so after date input we auto-generate
                lower_msg = user_message.lower().strip()
                if any(
                    kw in lower_msg for kw in ["tự động", "tu dong", "auto", "tudong"]
                ):
                    logger.info(
                        "⚙️ User requested AUTO mode during date prompt - enabling auto_generate_mode"
                    )
                    setattr(context, "auto_generate_mode", True)
                    # Ensure builder exists and persists the flag
                    if not builder:
                        builder = {"waiting_for_start_date": True}
                        context.itinerary_builder = builder
                    builder["auto_generate_mode"] = True
                    logger.info(
                        "💾 Saved auto_generate_mode=True in builder while waiting for start_date"
                    )

                logger.info("📅 Processing start_date input...")
                from app.utils.date_normalizer import normalize_date

                # Check if user skips ("chưa biết")
                if any(
                    kw in user_message.lower()
                    for kw in ["chưa biết", "chua biet", "skip", "bỏ qua", "bo qua"]
                ):
                    # ✨ NEW: Show best months to visit instead of using today
                    logger.info(
                        "🌤️ User unsure about date, showing best months to visit..."
                    )
                    # CRITICAL: Ensure destination is set
                    if not context.destination:
                        builder = getattr(context, "itinerary_builder", None)
                        if builder:
                            context.destination = builder.get("location")
                            logger.info(
                                f"✅ Restored destination from builder: {context.destination}"
                            )
                        else:
                            logger.error("❌ No destination found in context!")
                            # Fallback to today
                            from datetime import datetime

                            context.start_date = datetime.now().strftime("%Y-%m-%d")
                            logger.info(
                                f"⏭️ Using today as fallback: {context.start_date}"
                            )
                            duration = context.duration or 3
                            builder = getattr(context, "itinerary_builder", None)
                            if builder and "total_days" in builder:
                                duration = builder["total_days"]
                                location = builder.get("location")
                            else:
                                logger.error("❌ Cannot recover from missing builder!")
                                return None
                            return self._start_interactive_itinerary_sync(
                                location, duration, context
                            )

                    location = context.destination

                    try:
                        best_time_data = self.weather.get_best_time(location)
                        logger.info(f"✅ get_best_time returned: {best_time_data}")

                        best_months = best_time_data.get("best_months", [])
                        avoid_months = best_time_data.get("avoid_months", [])
                        message = best_time_data.get("message", "")

                        logger.info(
                            f"📊 best_months type: {type(best_months)}, value: {best_months}"
                        )
                        logger.info(
                            f"📊 avoid_months type: {type(avoid_months)}, value: {avoid_months}"
                        )

                        # Format months for display (convert number to month name)
                        month_names = {
                            1: "Tháng 1",
                            2: "Tháng 2",
                            3: "Tháng 3",
                            4: "Tháng 4",
                            5: "Tháng 5",
                            6: "Tháng 6",
                            7: "Tháng 7",
                            8: "Tháng 8",
                            9: "Tháng 9",
                            10: "Tháng 10",
                            11: "Tháng 11",
                            12: "Tháng 12",
                        }

                        # CRITICAL: Handle case where best_months might already be strings
                        if best_months and isinstance(best_months[0], int):
                            best_month_names = [
                                month_names.get(m, f"Tháng {m}") for m in best_months
                            ]
                        else:
                            best_month_names = best_months if best_months else []

                        if avoid_months and isinstance(avoid_months[0], int):
                            avoid_month_names = [
                                month_names.get(m, f"Tháng {m}") for m in avoid_months
                            ]
                        else:
                            avoid_month_names = avoid_months if avoid_months else []

                        logger.info(
                            f"✅ Best months: {best_month_names}, Avoid: {avoid_month_names}"
                        )

                        # Return month selector UI instead of proceeding
                        reply = f"""📅 **Chọn ngày phù hợp cho chuyến đi**

{message}

🎯 **Tháng tốt nhất:** {', '.join(best_month_names) if best_month_names else 'Năm ngoài'}

❌ **Tháng nên tránh:** {', '.join(avoid_month_names) if avoid_month_names else 'Không có'}

💡 **Hướng dẫn:**
Nhập ngày cụ thể (VD: "15/3/2026")"""

                        context.itinerary_builder = {
                            "location": location,
                            "total_days": context.duration or 3,
                            "waiting_for_month_selection": True,  # Flag để indicate chúng ta đang chờ chọn tháng
                            "best_months": best_month_names,
                            "avoid_months": avoid_month_names,
                        }

                        # CRITICAL: Ensure destination is preserved
                        if not context.destination:
                            context.destination = location
                            logger.info(f"✅ Set context.destination: {location}")

                        return {
                            "reply": reply,
                            "ui_type": "month_selector",
                            "ui_data": {
                                "best_months": best_month_names,
                                "avoid_months": avoid_month_names,
                                "destination": location,
                            },
                            "context": context.to_dict(),
                            "status": "waiting_for_month_selection",
                        }
                    except Exception as e:
                        logger.warning(
                            f"⚠️ Failed to get best months: {e}, showing generic month selector"
                        )
                        import traceback

                        logger.error(f"🔴 DETAILED ERROR:\n{traceback.format_exc()}")

                        # Still show month selector even if weather API fails
                        # Use generic guidance instead of specific recommendations
                        all_months = [f"Tháng {i}" for i in range(1, 13)]

                        reply = f"""📅 **Chọn ngày phù hợp cho chuyến đi {location}**

Vui lòng chọn ngày bạn muốn đi:

💡 **Hướng dẫn:**
Nhập ngày cụ thể (VD: "15/3/2026")"""

                        context.itinerary_builder = {
                            "location": location,
                            "total_days": context.duration or 3,
                            "waiting_for_month_selection": True,
                            "best_months": all_months,
                            "avoid_months": [],
                        }

                        if not context.destination:
                            context.destination = location
                            logger.info(f"✅ Set context.destination: {location}")

                        return {
                            "reply": reply,
                            "ui_type": "month_selector",
                            "ui_data": {
                                "best_months": all_months,
                                "avoid_months": [],
                                "destination": location,
                            },
                            "context": context.to_dict(),
                            "status": "waiting_for_month_selection",
                        }

                else:
                    # Parse date from user input
                    try:
                        context.start_date = normalize_date(user_message)
                        logger.info(f"✅ start_date set to: {context.start_date}")
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to parse date: {e}")
                        return {
                            "reply": '❌ Xin lỗi, tôi không hiểu ngày này. Vui lòng nhập lại theo định dạng:\\n\\n• VD: "20/1/2026"\\n• Hoặc: "mai", "hôm nay"\\n• Hoặc gõ "chưa biết" để bỏ qua',
                            "ui_type": "text",
                            "ui_data": {},
                            "context": context.to_dict(),
                        }

                # After setting start_date, check if AUTO-GENERATE mode
                location = context.destination
                # CRITICAL: Use total_days from existing builder if available, otherwise fallback to context.duration
                builder = getattr(context, "itinerary_builder", None)
                if builder and "total_days" in builder:
                    duration = builder["total_days"]
                    logger.info(f"🔄 Using duration from existing builder: {duration}")
                else:
                    duration = context.duration or 3
                    logger.info(f"🔄 Using duration from context: {duration}")

                # Check if AUTO-GENERATE mode is enabled - RESTORE from builder if not in context
                auto_mode = getattr(context, "auto_generate_mode", None)
                if auto_mode is None and builder:
                    # Try to restore from builder
                    auto_mode = builder.get("auto_generate_mode", False)
                    logger.info(
                        f"🔄 Restored auto_generate_mode from builder: {auto_mode}"
                    )

                # If still not enabled, but budget exists in context → enable auto mode
                if not auto_mode and getattr(context, "budget", None):
                    try:
                        budget_ok = False
                        b = context.budget
                        if isinstance(b, (int, float)):
                            budget_ok = b > 0
                        elif isinstance(b, str):
                            import re

                            m = re.search(
                                r"(\d+(?:[.,]\d+)?)\s*(triệu|tr|triệu đồng|vnd|đ)?",
                                b.lower(),
                            )
                            if m:
                                num = float(m.group(1).replace(",", "."))
                                budget_ok = num > 0
                        if budget_ok:
                            auto_mode = True
                            setattr(context, "auto_generate_mode", True)
                            if builder:
                                builder["auto_generate_mode"] = True
                            logger.info(
                                "⚙️ Enabled auto_generate_mode because budget exists in context"
                            )
                    except Exception as e:
                        logger.warning(
                            f"⚠️ Failed to enable auto mode from context budget: {e}"
                        )

                auto_mode = bool(auto_mode)
                logger.info(
                    f"🔍 DEBUG: Checking auto_generate_mode - value={auto_mode}, builder has it={builder.get('auto_generate_mode') if builder else 'N/A'}, context.budget={getattr(context,'budget',None)}"
                )

                if auto_mode:
                    logger.info(
                        f"🤖 AUTO-GENERATE mode activated - generating itinerary with LLM"
                    )
                    return self._generate_auto_itinerary_sync(
                        location, duration, context
                    )
                else:
                    logger.info(f"📋 Manual mode - showing interactive builder")
                    return self._start_interactive_itinerary_sync(
                        location, duration, context
                    )

            if not builder:
                return None

            # 🌤️ NEW: Handle month selection when user hasn't chosen a date yet
            if builder.get("waiting_for_month_selection"):
                logger.info("📅 Processing month selection...")
                month_input = user_message.strip()

                try:
                    # Parse month input (can be "3", "tháng 3", "3-4", etc.)
                    # Convert to start date of the selected month
                    from datetime import datetime
                    from app.utils.date_normalizer import normalize_date

                    # CRITICAL: Ensure location is preserved
                    if not context.destination and builder.get("location"):
                        context.destination = builder.get("location")
                        logger.info(
                            f"✅ Restored destination from builder: {context.destination}"
                        )

                    # Try to parse as month selection
                    lower_input = month_input.lower()
                    current_year = datetime.now().year

                    # Extract month number
                    month_num = None
                    if "tháng" in lower_input:
                        # Extract number after "tháng"
                        import re

                        match = re.search(r"tháng\s*(\d+)", lower_input)
                        if match:
                            month_num = int(match.group(1))
                    else:
                        # Try to parse as number directly
                        import re

                        match = re.search(r"(\d+)", month_input)
                        if match:
                            month_num = int(match.group(1))

                    if month_num and 1 <= month_num <= 12:
                        # Set start_date to 1st day of selected month
                        context.start_date = f"{current_year}-{month_num:02d}-01"
                        logger.info(
                            f"✅ Month selected: {month_num}, start_date set to: {context.start_date}"
                        )

                        # Clear waiting flag and continue
                        builder.pop("waiting_for_month_selection", None)
                        builder.pop("best_months", None)
                        builder.pop("avoid_months", None)
                    else:
                        # Try to parse as full date
                        try:
                            context.start_date = normalize_date(month_input)
                            logger.info(f"✅ Full date parsed: {context.start_date}")
                            builder.pop("waiting_for_month_selection", None)
                            builder.pop("best_months", None)
                            builder.pop("avoid_months", None)
                        except:
                            # Invalid input
                            return {
                                "reply": "❌ Xin lỗi, tôi không hiểu lựa chọn tháng của bạn.\n\n💡 Vui lòng nhập:\n• Số tháng (VD: '3', '4')\n• Hoặc tên tháng (VD: 'tháng 3')\n• Hoặc ngày cụ thể (VD: '15/3/2026')",
                                "ui_type": "text",
                                "ui_data": {},
                                "context": context.to_dict(),
                            }

                    # After setting start_date, decide AUTO vs manual
                    location = builder.get("location", "")
                    duration = builder.get("total_days", 3)

                    auto_mode = getattr(context, "auto_generate_mode", None)
                    if auto_mode is None:
                        auto_mode = builder.get("auto_generate_mode", False)

                    # Enable auto if budget exists
                    if not auto_mode and getattr(context, "budget", None):
                        try:
                            budget_ok = False
                            b = context.budget
                            if isinstance(b, (int, float)):
                                budget_ok = b > 0
                            elif isinstance(b, str):
                                import re

                                m = re.search(
                                    r"(\d+(?:[.,]\d+)?)\s*(triệu|tr|triệu đồng|vnd|đ)?",
                                    b.lower(),
                                )
                                if m:
                                    num = float(m.group(1).replace(",", "."))
                                    budget_ok = num > 0
                            if budget_ok:
                                auto_mode = True
                                setattr(context, "auto_generate_mode", True)
                                builder["auto_generate_mode"] = True
                                logger.info(
                                    "⚙️ Enabled auto_generate_mode after month selection because budget exists"
                                )
                        except Exception as e:
                            logger.warning(
                                f"⚠️ Failed to enable auto mode from context budget (month selection): {e}"
                            )

                    if auto_mode:
                        logger.info(
                            "🤖 AUTO-GENERATE mode activated after month selection"
                        )
                        return self._generate_auto_itinerary_sync(
                            location, duration, context
                        )

                    # Otherwise continue manual builder
                    return self._start_interactive_itinerary_sync(
                        location, duration, context
                    )

                except Exception as e:
                    logger.error(f"❌ Error parsing month selection: {e}")
                    return {
                        "reply": "❌ Xin lỗi, có lỗi xảy ra khi xử lý lựa chọn tháng.",
                        "ui_type": "text",
                        "ui_data": {},
                        "context": context.to_dict(),
                    }

            current_day = builder.get("current_day", 1)
            total_days = builder.get("total_days", 3)
            location = builder.get("location", "")
            available_spots = builder.get("available_spots", [])
            days_plan = builder.get("days_plan", {})

            # 🔧 FIX: If available_spots is empty (rebuilt builder), restore from last_spots
            if (
                not available_spots
                and hasattr(context, "last_spots")
                and context.last_spots
            ):
                logger.info("🔄 Restoring available_spots from last_spots")
                available_spots = [
                    {
                        "idx": i + 1,
                        "id": str(s.get("_id")) if s.get("_id") else s.get("id"),
                        "name": s.get("name"),
                        "category": s.get("category", "Tham quan"),
                        "rating": s.get("rating"),
                        "description": s.get("description", ""),
                        "image": s.get("image") or s.get("image_url"),
                        "image_url": s.get("image_url") or s.get("image"),
                        "latitude": s.get("latitude"),
                        "longitude": s.get("longitude"),
                    }
                    for i, s in enumerate(context.last_spots[:20])
                ]
                builder["available_spots"] = available_spots

            lower_msg = user_message.lower().strip()

            # 🔄 BACKTRACKING DETECTION (PRIORITY #1)
            # Check if user wants to go back to previous step while in CHOOSING_HOTEL state
            workflow_state = getattr(context, "workflow_state", "INITIAL")

            backtrack_to_spots_keywords = [
                "thêm địa điểm",
                "them dia diem",
                "thêm spot",
                "them spot",
                "thêm điểm",
                "them diem",
                "còn thiếu",
                "con thieu",
                "thêm nữa",
                "them nua",
                "thêm một điểm",
                "them mot diem",
                "thêm check-in",
                "them check-in",
                "thêm check in",
            ]

            if workflow_state == "CHOOSING_HOTEL" and any(
                kw in lower_msg for kw in backtrack_to_spots_keywords
            ):
                logger.info(
                    f"🔄 BACKTRACK detected: User wants to add more spots while at CHOOSING_HOTEL"
                )

                # Count current spots
                total_spots = sum(len(spots) for spots in days_plan.values())

                # Transition back to CHOOSING_SPOTS
                context.workflow_state = "CHOOSING_SPOTS"
                builder["current_day"] = 1  # Reset to day 1 for adding
                context.itinerary_builder = builder

                return {
                    "reply": f"""🔄 **Được! Quay lại bổ sung địa điểm**

✅ **Tôi đã giữ nguyên:**
• {total_spots} địa điểm đã chọn cho {len(days_plan)} ngày

📍 **Giờ bạn muốn thêm địa điểm cho ngày nào?**

Gõ số ngày (ví dụ: "Ngày 1" hoặc "1") để tôi hiển thị thêm gợi ý cho ngày đó.
Hoặc gõ **"xong"** nếu không muốn thêm nữa.""",
                    "ui_type": "none",
                    "context": context.to_dict(),
                    "status": "backtrack_to_spots",
                }

            # Check for auto-generate commands
            if lower_msg in [
                "tự động",
                "tu dong",
                "auto",
                "tự động tạo",
                "tu dong tao",
            ]:
                # Clear builder state and let auto-generate
                context.itinerary_builder = None
                logger.info("🤖 User requested auto-generate itinerary")
                return None  # Proceed to PHASE 2 for auto-generation

            # Quick summary of selected spots when user asks for info
            # Broader matching: "thông tin các địa điểm", "các địa điểm sắp đến", "địa điểm nào", etc.
            import re

            if re.search(
                r"(thông tin|thong tin|gì|gi|nào|nao|sắp|sap|sẽ|se).*(địa điểm|dia diem|điểm|diem|chọn|chon)",
                lower_msg,
            ) or re.search(
                r"(các|cac).*(địa điểm|dia diem|điểm|diem).*(sẽ|se|sắp|sap|chọn|chon)",
                lower_msg,
            ):
                # FIX 2026-01-18: Also check last_itinerary if days_plan is empty
                # This handles auto-generated itineraries where data is in last_itinerary
                effective_days_plan = days_plan
                effective_total_days = total_days

                if not days_plan or not any(days_plan.values()):
                    last_itinerary = getattr(context, "last_itinerary", None)
                    if last_itinerary and last_itinerary.get("days"):
                        logger.info(
                            "📋 Using last_itinerary for spot summary (auto-generated itinerary)"
                        )
                        effective_days_plan = {}
                        effective_total_days = last_itinerary.get(
                            "duration", total_days
                        )
                        for day_info in last_itinerary.get("days", []):
                            day_num = day_info.get("day", 0)
                            spots_list = day_info.get("spots", [])
                            # Convert to format expected by summary builder
                            formatted_spots = []
                            for s in spots_list:
                                if isinstance(s, dict):
                                    formatted_spots.append(s)
                                else:
                                    # spots may be just names (strings) in auto-generated itinerary
                                    formatted_spots.append({"name": str(s)})
                            effective_days_plan[str(day_num)] = formatted_spots

                # Collect all spot names for detailed lookup
                all_spot_names = []
                summary_lines = []
                total_spots = 0

                for day_num in range(1, effective_total_days + 1):
                    day_key = str(day_num)
                    spots = effective_days_plan.get(day_key, [])
                    names = [
                        s.get("name", "?") if isinstance(s, dict) else str(s)
                        for s in spots
                    ]
                    all_spot_names.extend(names)
                    total_spots += len(names)
                    summary_lines.append(
                        f"Ngày {day_num}: "
                        + (", ".join(names) if names else "(chưa chọn)")
                    )

                logger.info(
                    f"ℹ️ User requested spot info summary: {total_spots} spots for {effective_total_days} days"
                )

                # FIX 2026-01-18: Query MongoDB for detailed spot info (like Case 2)
                spots_with_details = []
                if all_spot_names:
                    try:
                        spots_collection = self.mongo_manager.get_collection(
                            "spots_detailed"
                        )
                        for spot_name in all_spot_names[:10]:  # Limit to first 10
                            # Try exact match first
                            spot_doc = spots_collection.find_one({"name": spot_name})
                            # Fallback: fuzzy search
                            if not spot_doc:
                                spot_doc = spots_collection.find_one(
                                    {
                                        "name": {
                                            "$regex": re.escape(spot_name),
                                            "$options": "i",
                                        }
                                    }
                                )

                            if spot_doc:
                                desc = (
                                    spot_doc.get("description_short")
                                    or spot_doc.get("description")
                                    or spot_doc.get("description_full", "")[:200]
                                    or "Địa điểm du lịch nổi tiếng"
                                )
                                spots_with_details.append(
                                    {
                                        "id": str(spot_doc.get("_id", "")),
                                        "name": spot_doc.get("name", spot_name),
                                        "description": desc,
                                        "rating": spot_doc.get("rating", 4.5),
                                        "image": spot_doc.get("image_url")
                                        or spot_doc.get("image", ""),
                                        "address": spot_doc.get("address", ""),
                                    }
                                )
                            else:
                                spots_with_details.append(
                                    {
                                        "name": spot_name,
                                        "description": "Địa điểm du lịch nổi tiếng",
                                        "rating": 4.5,
                                        "image": "",
                                    }
                                )
                        logger.info(
                            f"📍 Fetched details for {len(spots_with_details)} spots"
                        )
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to fetch spot details: {e}")

                # Build rich reply with spot details
                location = getattr(context, "destination", "") or builder.get(
                    "location", ""
                )

                # Build LLM-like description
                if spots_with_details:
                    spot_intro = f"📍 **Các địa điểm tại {location}**\n\n"
                    spot_intro += f"**Các địa điểm bạn đã chọn** sẽ mang lại trải nghiệm tuyệt vời tại {location}. "

                    # Brief intro of top 3 spots
                    top_spots = spots_with_details[:3]
                    if len(top_spots) >= 1:
                        spot_intro += f"Đầu tiên là **{top_spots[0]['name']}**"
                        if top_spots[0].get("description"):
                            spot_intro += f" - {top_spots[0]['description'][:100]}..."
                    if len(top_spots) >= 2:
                        spot_intro += f" Tiếp theo là **{top_spots[1]['name']}**"
                    if len(top_spots) >= 3:
                        spot_intro += f" và **{top_spots[2]['name']}**"
                    spot_intro += ". 🏝️ 🌅 🙏\n\n"

                    spot_intro += "━━━━━━━━━━━━━━━━━━━━\n\n"
                    spot_intro += f"**Chi tiết {len(spots_with_details)} địa điểm:**\n"
                    for i, spot in enumerate(spots_with_details, 1):
                        desc_preview = (
                            spot.get("description", "")[:80] + "..."
                            if spot.get("description")
                            else ""
                        )
                        spot_intro += f"{i}. **{spot['name']}** {desc_preview}\n"

                    spot_intro += "\n━━━━━━━━━━━━━━━━━━━━\n\n"
                    spot_intro += "💬 **Bạn muốn biết thêm?**\n"
                    spot_intro += "🔍 Gõ **'chi tiết về [tên địa điểm]'** để xem thông tin đầy đủ\n"
                    spot_intro += "💡 Gõ **'lưu ý gì'** để xem tips du lịch\n"
                    spot_intro += "🏨 Gõ **'tìm khách sạn'** để chọn nơi ở"

                    reply = spot_intro
                else:
                    reply = "ℹ️ **Thông tin các địa điểm đã chọn:**\n\n"
                    reply += (
                        "\n".join(summary_lines)
                        if summary_lines
                        else "(Chưa có địa điểm nào)"
                    )
                    reply += f"\n\n📌 **Tổng cộng:** {total_spots} địa điểm cho {effective_total_days} ngày"
                    reply += "\n\n💡 Gõ 'tự động' nếu muốn tôi tự hoàn tất lịch trình từ các lựa chọn hiện có."

                return {
                    "reply": reply,
                    "ui_type": "spot_cards" if spots_with_details else "text",
                    "ui_data": (
                        {
                            "spots": spots_with_details,
                            "title": f"Các địa điểm tại {location}",
                        }
                        if spots_with_details
                        else {}
                    ),
                    "context": context.to_dict(),
                    "status": "success",
                }

            # Check for "see more" spots command
            if lower_msg in ["xem thêm", "xem them", "see more", "more"]:
                # Show all available spots from builder (already have 20 stored)
                all_spots_for_ui = available_spots  # Already formatted with all 20

                logger.info(
                    f"📖 Showing all {len(all_spots_for_ui)} available spots for {location}"
                )
                return {
                    "reply": f"""📖 **Tất cả các địa điểm tại {location}** ({len(all_spots_for_ui)} điểm)

💡 **Hướng dẫn:**
• Nhập số thứ tự địa điểm (VD: "1, 3, 5" hoặc "1 3 5")
• Hoặc gõ tên địa điểm bạn muốn đi
• Gõ **"bỏ qua"** nếu muốn tôi tự động lên lịch cho ngày này
• Gõ **"tự động"** để tôi tự tạo toàn bộ lịch trình""",
                    "ui_type": "itinerary_builder",
                    "ui_data": {
                        "spots": all_spots_for_ui,
                        "current_day": current_day,
                        "total_days": total_days,
                        "destination": location,
                        "has_more_spots": False,  # Already showing all
                        "total_available_spots": len(all_spots_for_ui),
                        "show_load_more_button": False,  # Hide button - already showing all
                    },
                    "context": context.to_dict(),
                    "status": "partial",
                }

            # Check for skip current day
            if lower_msg in ["bỏ qua", "bo qua", "skip", "tiếp", "tiep"]:
                # Skip this day (empty or auto-fill later)
                days_plan[str(current_day)] = []
                logger.info(f"⏭️ Skipping Day {current_day}")
                advance_day = True

            # COMMENTED: Removed manual "xong" check - now auto-advance after selection
            # # Check for "done" / "xong" / "tiếp tục" to advance to next day
            # # Support both exact match and contains check for more flexible input
            # elif (lower_msg in ["xong", "done", "tiếp tục", "tiep tuc", "ok", "được", "duoc", "next"] or
            #       any(keyword in lower_msg for keyword in ["xong", "done", "chốt", "chot", "finalize", "hoàn thành", "hoan thanh", "kết thúc", "ket thuc"])):
            #     # User confirms current selection, move to next day
            #     logger.info(f"✅ User confirmed Day {current_day}, advancing...")
            #     advance_day = True
            else:
                # Parse user's selection and ADD to current day (not replace)
                selected_spots = self._parse_spot_selection(
                    user_message, available_spots
                )

                # Get existing spots for current day and merge
                existing_spots = days_plan.get(str(current_day), [])
                existing_ids = {s.get("id") for s in existing_spots}

                # CRITICAL: Track all selected spot IDs globally to prevent duplication
                if not hasattr(context, "selected_spot_ids"):
                    context.selected_spot_ids = []

                # Add new spots that aren't already selected
                for spot in selected_spots:
                    spot_id = spot.get("id")
                    if spot_id not in existing_ids:
                        existing_spots.append(spot)
                        existing_ids.add(spot_id)
                        # Add to global tracking list
                        if spot_id not in context.selected_spot_ids:
                            context.selected_spot_ids.append(spot_id)
                            logger.info(
                                f"  🔒 Locked spot ID: {spot_id} ({spot.get('name')})"
                            )

                        # 🆕 SAVE TO MEMORY: Store in permanent selected_spots list with coordinates
                        if not hasattr(context, "selected_spots"):
                            context.selected_spots = []
                        # Add to permanent list if not already there
                        if not any(
                            s.get("id") == spot_id for s in context.selected_spots
                        ):
                            context.selected_spots.append(
                                {
                                    "id": spot_id,
                                    "name": spot.get("name"),
                                    "latitude": spot.get("latitude"),
                                    "longitude": spot.get("longitude"),
                                    "category": spot.get("category"),
                                    "image_url": spot.get("image_url"),
                                    "description": spot.get("description"),
                                    "day": current_day,  # Track which day it was selected for
                                }
                            )
                            logger.info(
                                f"  💾 Saved to memory: {spot.get('name')} for Day {current_day}"
                            )

                days_plan[str(current_day)] = existing_spots
                logger.info(
                    f"✅ Day {current_day} spots (merged): {[s.get('name') for s in existing_spots]}"
                )
                logger.info(
                    f"📊 Total selected spot IDs: {len(context.selected_spot_ids)}"
                )
                logger.info(
                    f"💾 Total in permanent memory: {len(context.selected_spots)} spots"
                )

                # AUTO-ADVANCE: Always move to next day after selection (removed "xong" requirement)
                # Old logic: advance_day = len(selected_spots) >= 2 or "," in user_message or " " in user_message.strip()
                advance_day = (
                    len(selected_spots) > 0
                )  # ← Always advance if any spots selected

            # Update context
            builder["days_plan"] = days_plan

            if advance_day:
                builder["current_day"] = current_day + 1
                context.itinerary_builder = builder

                # Check if we're done with all days
                if current_day >= total_days:
                    # CRITICAL: Update workflow state BEFORE finalize
                    context.workflow_state = "CHOOSING_HOTEL"
                    logger.info(f"🔄 State transition: CHOOSING_SPOTS → CHOOSING_HOTEL")

                    # Finalize itinerary selection and prompt hotel selection
                    return self._finalize_interactive_itinerary_sync(context)

                # Ask for next day
                next_day = current_day + 1

                # Show what was selected for current day
                selected_names = [
                    s.get("name") for s in days_plan.get(str(current_day), [])
                ]
                selected_text = (
                    ", ".join(selected_names) if selected_names else "Tự động lên lịch"
                )

                # CRITICAL: Filter out already selected spots from available spots
                # Use global tracking list to ensure no spot appears twice
                selected_ids = (
                    set(context.selected_spot_ids)
                    if hasattr(context, "selected_spot_ids")
                    else set()
                )

                remaining_spots = [
                    s for s in available_spots if s.get("id") not in selected_ids
                ]

                logger.info(
                    f"🔍 Filtering: {len(available_spots)} total → {len(remaining_spots)} remaining (excluded {len(selected_ids)} selected)"
                )

                # Format spots list with detailed info (same as Day 1)
                spots_list = "\n".join(
                    [
                        f"  {s.get('idx')}. **{s.get('name')}** ({s.get('category', 'Tham quan')})"
                        for s in remaining_spots[:20]  # Show up to 20 spots
                    ]
                )

                reply = f"""✅ **Ngày {current_day}:** {selected_text}

📍 **NGÀY {next_day}** - Bạn muốn đi những địa điểm nào?

Dưới đây là các địa điểm còn lại:
{ "" if spots_list else "✅ Tất cả địa điểm đã được chọn!"}

💡 **Hướng dẫn:**
• Nhập số thứ tự địa điểm (VD: "3, 5, 7")
• Hoặc gõ tên địa điểm bạn muốn đi
• Gõ **"bỏ qua"** để tôi tự động lên lịch cho ngày này"""

                # Format remaining spots for UI with full details
                def _get_cat(s):
                    cat = s.get("category")
                    if cat and cat != "None" and cat != "null":
                        return cat
                    tags = s.get("tags", [])
                    return tags[0] if tags else "Tham quan"

                spots_for_ui = [
                    {
                        "idx": s.get("idx"),  # Display number
                        "id": s.get("id"),  # Real MongoDB ObjectId
                        "name": s.get("name"),
                        "category": _get_cat(s),
                        "rating": s.get("rating"),
                        "description": (
                            (
                                s.get("description_short")
                                or s.get("description")
                                or s.get("description_full", "")
                            )[:100]
                        ),
                        "image": s.get("image")
                        or s.get("image_url")
                        or (s.get("images", [None])[0] if s.get("images") else None),
                    }
                    for s in remaining_spots[:20]  # Match available spots limit
                ]

            else:
                # User added single spot, ask if they want to add more or continue
                context.itinerary_builder = builder

                selected_names = [
                    s.get("name") for s in days_plan.get(str(current_day), [])
                ]
                selected_text = ", ".join(selected_names)

                # CRITICAL: Show remaining spots (filter out already selected)
                selected_ids = (
                    set(context.selected_spot_ids)
                    if hasattr(context, "selected_spot_ids")
                    else set()
                )
                remaining_spots = [
                    s for s in available_spots if s.get("id") not in selected_ids
                ]

                reply = f"""✅ Đã thêm vào **Ngày {current_day}**: {selected_text}

💡 Bạn có thể:
• Nhập thêm số để thêm địa điểm
• Gõ **"xong"** hoặc **"tiếp tục"** để chuyển sang ngày tiếp theo
• Gõ **"bỏ qua"** để bỏ qua ngày này"""

                def _get_cat2(s):
                    cat = s.get("category")
                    if cat and cat != "None" and cat != "null":
                        return cat
                    tags = s.get("tags", [])
                    return tags[0] if tags else "Tham quan"

                spots_for_ui = [
                    {
                        "idx": s.get("idx"),  # Display number
                        "id": s.get("id"),  # Real MongoDB ObjectId
                        "name": s.get("name"),
                        "category": _get_cat2(s),
                        "rating": s.get("rating"),
                        "description": (
                            (
                                s.get("description_short")
                                or s.get("description")
                                or s.get("description_full", "")
                            )[:100]
                        ),
                        "image": s.get("image")
                        or s.get("image_url")
                        or (s.get("images", [None])[0] if s.get("images") else None),
                    }
                    for s in remaining_spots[:12]
                ]
                next_day = current_day  # Still on same day

            return {
                "reply": reply,
                "ui_type": "itinerary_builder",
                "ui_data": {
                    "spots": spots_for_ui,
                    "current_day": next_day,
                    "total_days": total_days,
                    "destination": location,
                },
                "context": context.to_dict(),
                "status": "partial",
            }

        except Exception as e:
            logger.error(f"❌ Continue interactive itinerary error: {e}")
            import traceback

            traceback.print_exc()
            return None

    def _parse_spot_selection(self, user_message: str, available_spots: list) -> list:
        """Parse user's spot selection from message"""
        import re

        selected = []

        # Try to extract numbers (for idx matching)
        numbers = re.findall(r"\d+", user_message)
        if numbers:
            for num_str in numbers:
                num = int(num_str)
                # Match by idx field (1-based numbering for user)
                for spot in available_spots:
                    if spot.get("idx") == num:
                        if spot not in selected:
                            selected.append(spot)
                        break

        # Also try to match by name
        lower_msg = user_message.lower()
        for spot in available_spots:
            spot_name = spot.get("name", "").lower()
            # Check if any significant word from spot name is in message
            words = [w for w in spot_name.split() if len(w) > 2]
            if any(word in lower_msg for word in words):
                if spot not in selected:
                    selected.append(spot)

        return selected

    def _finalize_interactive_itinerary_sync(self, context) -> Dict[str, Any]:
        """Finalize the interactive itinerary and generate final response with VERIFICATION"""
        try:
            builder = context.itinerary_builder
            location = builder.get("location", "")
            days_plan = builder.get("days_plan", {})
            # Robust total_days: prefer builder → context.duration → non-empty days in days_plan → 3
            non_empty_days = [k for k, v in days_plan.items() if v]
            total_days = (
                builder.get("total_days")
                or getattr(context, "duration", None)
                or len(non_empty_days)
                or 3
            )

            logger.info(f"📋 Finalizing itinerary: {total_days} days at {location}")
            logger.info(f"🔍 DEBUG: days_plan keys = {list(days_plan.keys())}")
            logger.info(
                f"🔍 DEBUG: total_days = {total_days}, type = {type(total_days)}"
            )
            logger.info(f"🔍 DEBUG: builder = {builder}")

            # Convert days_plan to itinerary_days format for verification
            itinerary_days = []
            for day_num in range(1, total_days + 1):
                day_spots = days_plan.get(str(day_num), [])
                logger.info(
                    f"🔍 DEBUG: day {day_num} has {len(day_spots)} spots: {[s.get('name') for s in day_spots]}"
                )
                activities = []
                for i, spot in enumerate(day_spots):
                    activities.append(
                        {
                            "time": self._get_time_slot(i),
                            "spot_id": spot.get("id", spot.get("name", "")),
                            "spot_name": spot.get("name", ""),
                            "category": spot.get("category", ""),
                            "location": spot.get("name", ""),
                        }
                    )
                itinerary_days.append(
                    {"day": day_num, "activities": activities, "spots": day_spots}
                )

            # ==================== VERIFICATION PHASE ====================
            # Run Rule-based + LLM-as-critic verification with auto-fix
            verification_result = self._verify_and_optimize_itinerary(
                itinerary_days, context, auto_fix=True
            )
            verification_message = self._format_verification_message(
                verification_result
            )

            # Use verified/fixed itinerary if available
            if verification_result.get("itinerary"):
                itinerary_days = verification_result["itinerary"]
                # CRITICAL: Update days_plan AND rebuild with verified activities/times
                for day_data in itinerary_days:
                    day_num = day_data.get("day", 1)
                    verified_activities = day_data.get("activities", [])
                    logger.info(
                        f"🔍 DEBUG: After verification, day {day_num} has {len(verified_activities)} activities: {[a.get('spot_name') for a in verified_activities]}"
                    )

                    # Rebuild spots list with corrected order/timing from verification
                    if verified_activities:
                        verified_spots = []

                        # First pass: categorize activities into special cases and generic
                        period_activities = {"Sáng": [], "Chiều": [], "Tối": []}
                        generic_activities = (
                            []
                        )  # Activities without special time requirements
                        activity_spot_map = {}  # Map activity to spot data

                        for activity in verified_activities:
                            spot_name = activity.get("spot_name", "")
                            original_spots = days_plan.get(str(day_num), [])

                            for spot in original_spots:
                                if spot.get("name") == spot_name:
                                    spot_category = spot.get("category", "").lower()
                                    spot_name_lower = spot_name.lower()

                                    # Check for special time requirements
                                    is_special = False

                                    # Priority 1: Check for bar/nightlife in category or name (evening priority)
                                    if (
                                        "bar" in spot_category
                                        or "bar" in spot_name_lower
                                        or "night" in spot_category
                                        or "club" in spot_category
                                        or "club" in spot_name_lower
                                    ):
                                        period_activities["Tối"].append(activity)
                                        is_special = True
                                    # Priority 2: Check for sunset in category or name (afternoon)
                                    elif (
                                        "sunset" in spot_category
                                        or "sunset" in spot_name_lower
                                    ):
                                        period_activities["Chiều"].append(activity)
                                        is_special = True
                                    # Priority 3: Check for sunrise/morning
                                    elif (
                                        "sunrise" in spot_category
                                        or "morning" in spot_category
                                        or "sáng" in spot_category.lower()
                                    ):
                                        period_activities["Sáng"].append(activity)
                                        is_special = True

                                    # Generic spots - distribute evenly later
                                    if not is_special:
                                        generic_activities.append(activity)

                                    activity_spot_map[id(activity)] = spot
                                    break

                        # Distribute generic activities evenly across periods
                        if generic_activities:
                            periods = ["Sáng", "Chiều", "Tối"]
                            for idx, activity in enumerate(generic_activities):
                                period = periods[idx % 3]  # Round-robin distribution
                                period_activities[period].append(activity)

                        # Second pass: generate evenly distributed time slots for each period
                        def generate_time_slots(
                            start_hour, start_min, end_hour, end_min, count
                        ):
                            """Generate evenly distributed time slots between start and end"""
                            if count == 0:
                                return []
                            if count == 1:
                                return [f"{start_hour:02d}:{start_min:02d}"]

                            start_minutes = start_hour * 60 + start_min
                            end_minutes = end_hour * 60 + end_min
                            interval = (end_minutes - start_minutes) / (count - 1)

                            slots = []
                            for i in range(count):
                                total_minutes = int(start_minutes + interval * i)
                                hour = total_minutes // 60
                                minute = total_minutes % 60
                                slots.append(f"{hour:02d}:{minute:02d}")
                            return slots

                        # Generate time slots based on actual counts
                        time_slots_by_period = {
                            "Sáng": generate_time_slots(
                                8, 0, 11, 0, len(period_activities["Sáng"])
                            ),  # 08:00 - 11:00
                            "Chiều": generate_time_slots(
                                12, 30, 15, 30, len(period_activities["Chiều"])
                            ),  # 12:30 - 15:30
                            "Tối": generate_time_slots(
                                17, 0, 20, 30, len(period_activities["Tối"])
                            ),  # 17:00 - 20:30
                        }

                        # Third pass: assign times and rebuild spots list
                        # Create mapping of activity spot_name to activity object for updates
                        activity_by_spot_name = {
                            a.get("spot_name"): a for a in verified_activities
                        }

                        for period in ["Sáng", "Chiều", "Tối"]:
                            slots = time_slots_by_period[period]
                            for idx, activity in enumerate(period_activities[period]):
                                if idx < len(slots):
                                    new_time = slots[idx]
                                    activity["time"] = new_time

                                    # Also update the activity in verified_activities
                                    spot_name = activity.get("spot_name", "")
                                    if spot_name in activity_by_spot_name:
                                        activity_by_spot_name[spot_name][
                                            "time"
                                        ] = new_time

                                    spot = activity_spot_map.get(id(activity))
                                    if spot:
                                        verified_spots.append(spot)

                        if verified_spots:
                            days_plan[str(day_num)] = verified_spots
                            # Update itinerary_days with new times
                            day_data["activities"] = verified_activities

                            # Log detailed breakdown by period
                            logger.info(f"\n{'='*60}")
                            logger.info(f"📅 NGÀY {day_num} - PHÂN BỐ SPOTS THEO BUỔI")
                            logger.info(f"{'='*60}")

                            for period in ["Sáng", "Chiều", "Tối"]:
                                period_spots = period_activities[period]
                                count = len(period_spots)
                                spots_list = [
                                    a.get("spot_name", "") for a in period_spots
                                ]

                                if period == "Sáng":
                                    period_emoji = "🌅"
                                    period_label = "Buổi SÁNG"
                                elif period == "Chiều":
                                    period_emoji = "☀️"
                                    period_label = "Buổi CHIỀU"
                                else:
                                    period_emoji = "🌙"
                                    period_label = "Buổi TỐI"

                                logger.info(
                                    f"{period_emoji} {period_label}: {count} spot(s)"
                                )
                                for i, spot_name in enumerate(spots_list, 1):
                                    # Find the time for this spot
                                    spot_activity = next(
                                        (
                                            a
                                            for a in verified_activities
                                            if a.get("spot_name") == spot_name
                                        ),
                                        None,
                                    )
                                    time_str = (
                                        spot_activity.get("time", "??:??")
                                        if spot_activity
                                        else "??:??"
                                    )
                                    logger.info(f"   {i}. {time_str} - {spot_name}")
                            logger.info(f"{'='*60}\n")

                            logger.info(
                                f"✅ Updated day {day_num} with {len(verified_spots)} verified spots"
                            )

                            # Log period distribution
                            period_counts = {
                                "Sáng": len(period_activities["Sáng"]),
                                "Chiều": len(period_activities["Chiều"]),
                                "Tối": len(period_activities["Tối"]),
                            }
                            logger.info(f"✅ Period distribution: {period_counts}")
                    else:
                        # Keep original if no activities
                        days_plan[str(day_num)] = day_data.get(
                            "spots", days_plan.get(str(day_num), [])
                        )

            logger.info(
                f"🔍 Verification: {verification_result.get('verdict', 'pass')}, {len(verification_result.get('changes', []))} auto-fixes"
            )
            # ==================== END VERIFICATION ====================

            # Build itinerary text - Keep specific times (08:00, 11:00, etc.)
            itinerary_parts = []
            all_spots = []
            spots_details = []  # Store full spot details for frontend

            for day_num in range(1, total_days + 1):
                day_spots = days_plan.get(str(day_num), [])
                # Prefer verified activities (with actual times) if available
                day_data = next(
                    (d for d in itinerary_days if d.get("day") == day_num), None
                )
                activities = day_data.get("activities", []) if day_data else []

                if activities:
                    # Sort activities by time for correct timeline display
                    def sort_by_time(activity):
                        time_str = activity.get("time", "00:00")
                        try:
                            h, m = map(int, time_str.split(":"))
                            return h * 60 + m  # Convert to minutes for sorting
                        except:
                            return 0

                    sorted_activities = sorted(activities, key=sort_by_time)

                    # Use times directly from verified activities (already assigned by verification)
                    # Only re-distribute if multiple activities share same time
                    spots_text = "\n".join(
                        [
                            f"    • {a.get('time', self._get_time_slot(i))} - {a.get('spot_name', '')}"
                            for i, a in enumerate(sorted_activities)
                        ]
                    )

                    # Collect spot details mapped from days_plan
                    for a in sorted_activities:
                        spot_name = a.get("spot_name", "")
                        matched = next(
                            (s for s in day_spots if s.get("name") == spot_name), None
                        )
                        if matched:
                            all_spots.append(matched)
                            desc = (
                                matched.get("description_short")
                                or matched.get("description")
                                or matched.get("description_full", "")[:300]
                                or "Địa điểm du lịch nổi tiếng"
                            )
                            spots_details.append(
                                {
                                    "name": matched.get("name", ""),
                                    "description": desc,
                                    "address": matched.get("address", ""),
                                    "price_range": matched.get(
                                        "price_range", "Miễn phí"
                                    ),
                                    "image_url": matched.get("image_url")
                                    or matched.get("image", ""),
                                    "source_url": matched.get("url", ""),
                                    "tips": matched.get("tips", ""),
                                    "best_visit_time": matched.get(
                                        "best_visit_time", []
                                    ),
                                    "images": matched.get("images", []),
                                }
                            )
                        else:
                            spots_details.append({"name": spot_name, "description": ""})
                else:
                    # Fallback to index-based timeline
                    if day_spots:
                        spots_text = "\n".join(
                            [
                                f"    • {self._get_time_slot(i)} - {s.get('name')}"
                                for i, s in enumerate(day_spots)
                            ]
                        )
                        all_spots.extend(day_spots)
                        for spot in day_spots:
                            desc = (
                                spot.get("description_short")
                                or spot.get("description")
                                or spot.get("description_full", "")[:300]
                                or "Địa điểm du lịch nổi tiếng"
                            )
                            spots_details.append(
                                {
                                    "name": spot.get("name", ""),
                                    "description": desc,
                                    "address": spot.get("address", ""),
                                    "price_range": spot.get("price_range", "Miễn phí"),
                                    "image_url": spot.get("image_url")
                                    or spot.get("image", ""),
                                    "source_url": spot.get("url", ""),
                                    "tips": spot.get("tips", ""),
                                    "best_visit_time": spot.get("best_visit_time", []),
                                    "images": spot.get("images", []),
                                }
                            )
                    else:
                        spots_text = "    • Tự do khám phá hoặc nghỉ ngơi"

                itinerary_parts.append(f"📅 **Ngày {day_num}:**\n{spots_text}")

            itinerary_text = "\n\n".join(itinerary_parts)

            # Get weather information if start_date is available
            weather_summary_text = ""
            start_date = context.start_date if hasattr(context, "start_date") else None

            if start_date:
                try:
                    weather_data = self.weather.get_weather(
                        location, start_date, total_days
                    )
                    weather_summary_text = self.weather.build_weather_response(
                        weather_data
                    )
                    logger.info(
                        f"☀️ Weather info added: {weather_data['overall']['comfort_level']}"
                    )
                except Exception as e:
                    logger.warning(f"⚠️ Could not fetch weather: {e}")

            # PROACTIVE: Suggest next actions with STATE-AWARE message
            # Since we just finished CHOOSING_SPOTS, next step is CHOOSING_HOTEL
            # Include verification message if there were auto-fixes
            reply = f"""🗓️ **LỊCH TRÌNH {total_days} NGÀY TẠI {location.upper()}**

{verification_message}
{itinerary_text}
{weather_summary_text}
━━━━━━━━━━━━━━━━━━━━

✅ **Tuyệt vời! Bạn đã chọn xong địa điểm cho {total_days} ngày.**

🎯 **BƯỚC TIẾP THEO: Chọn khách sạn**

⚠️ **Lưu ý quan trọng:**
• Bạn cần chọn khách sạn trước khi tính tổng chi phí
• Tôi sẽ gợi ý các khách sạn phù hợp với ngân sách của bạn

💡 **Bạn muốn làm gì tiếp theo?**

🏨 **1. Tìm khách sạn (ƯU TIÊN)** - Gõ: "tìm khách sạn" hoặc "hotel"
📝 **2. Xem lưu ý địa điểm** - Gõ: "có lưu ý gì không"
📍 **3. Xem chi tiết địa điểm** - Gõ: "chi tiết về [tên địa điểm]"
🔄 **4. Lập lại** - Gõ: "lập lịch lại"

⏸️ **Muốn tính chi phí?** Hãy chọn khách sạn trước nhé!

💬 Hãy nói cho tôi biết bạn muốn làm gì tiếp theo?"""

            # Create itinerary data for UI - Group by VERIFIED activity times
            itinerary_items = []
            for day_num in range(1, total_days + 1):
                day_spots = days_plan.get(str(day_num), [])
                day_data = next(
                    (d for d in itinerary_days if d.get("day") == day_num), None
                )
                activities = day_data.get("activities", []) if day_data else []

                morning_spots = []
                afternoon_spots = []
                evening_spots = []

                if activities:
                    for a in activities:
                        spot_name = a.get("spot_name", "")
                        time_str = a.get("time", "")
                        period = self._classify_period_by_time(time_str or "08:00")
                        if period == "Sáng":
                            morning_spots.append(spot_name)
                        elif period == "Chiều":
                            afternoon_spots.append(spot_name)
                        else:
                            evening_spots.append(spot_name)
                else:
                    # Fallback to index-based mapping
                    for i, spot in enumerate(day_spots):
                        spot_name = spot.get("name", "")
                        time_str = self._get_time_slot(i)
                        period = self._classify_period_by_time(time_str)
                        if period == "Sáng":
                            morning_spots.append(spot_name)
                        elif period == "Chiều":
                            afternoon_spots.append(spot_name)
                        else:
                            evening_spots.append(spot_name)

                morning_text = ", ".join(morning_spots) if morning_spots else "Tự do"
                afternoon_text = (
                    ", ".join(afternoon_spots) if afternoon_spots else "Tự do"
                )
                evening_text = (
                    ", ".join(evening_spots) if evening_spots else "Nghỉ ngơi"
                )

                itinerary_items.append(
                    {
                        "day": day_num,
                        "title": (
                            f"Khám phá {location}"
                            if (morning_spots or afternoon_spots or evening_spots)
                            else "Tự do khám phá"
                        ),
                        "morning": morning_text,
                        "afternoon": afternoon_text,
                        "evening": evening_text,
                    }
                )

            # Clear builder state
            context.itinerary_builder = None
            context.last_itinerary = {
                "location": location,
                "duration": total_days,
                "days": [
                    {
                        "day": day_num,
                        "spots": [
                            s.get("name") for s in days_plan.get(str(day_num), [])
                        ],
                    }
                    for day_num in range(1, total_days + 1)
                ],
                "verification": verification_result,  # Store verification result
            }

            logger.info(f"✅ DEBUG: Finalize completed successfully")
            logger.info(
                f"📊 DEBUG: Reply length = {len(reply)} chars, ui_type = 'itinerary'"
            )

            return {
                "reply": reply,
                "ui_type": "itinerary",
                "ui_data": {
                    "items": itinerary_items,
                    "destination": location,
                    "days": total_days,
                    "total_days": total_days,
                    "spots_details": spots_details,  # NEW: Full spot details for frontend
                    # CRITICAL: Prioritize hotel selection
                    "actions": [
                        {
                            "label": "🏨 Tìm khách sạn (Ưu tiên)",
                            "action": "tìm khách sạn",
                        },
                        {"label": "� Xem lưu ý", "action": "có lưu ý gì không"},
                        {"label": "� Lập lại", "action": "lập lịch lại"},
                    ],
                    "workflow_state": "CHOOSING_HOTEL",
                    "next_step_hint": "Chọn khách sạn trước khi tính chi phí",
                },
                "context": context.to_dict(),
                "status": "success",
            }

        except Exception as e:
            logger.error(f"❌ Finalize itinerary error: {e}")
            import traceback

            traceback.print_exc()
            context.itinerary_builder = None
            return None

    def _get_time_slot(self, index: int) -> str:
        """Get time slot based on activity index"""
        time_slots = [
            "08:00",
            "09:30",
            "11:00",
            "12:30",
            "14:00",
            "15:30",
            "17:00",
            "19:00",
        ]
        return time_slots[index % len(time_slots)]

    def _classify_period_by_time(self, time_str: str) -> str:
        """Classify time period (morning/afternoon/evening) based on time string

        Args:
            time_str: Time string like "08:00", "14:00", "19:00"

        Returns:
            "Sáng" (morning: 06:00-11:00), "Chiều" (afternoon: 12:00-17:00), "Tối" (evening: 17:00+)
        """
        try:
            hour = int(time_str.split(":")[0])
            if hour < 12:
                return "Sáng"  # 00:00 - 11:59 → morning
            elif hour < 17:
                return "Chiều"  # 12:00 - 16:59 → afternoon
            else:
                return "Tối"  # 17:00+ → evening
        except:
            return "Sáng"  # Default to morning

    def _get_spots_for_location_sync(self, location: str) -> list:
        """Get spots for a location from MongoDB."""
        spots = []
        try:
            if self.mongo_manager:
                spots_col = self.mongo_manager.get_collection("spots_detailed")
                if spots_col is not None:
                    # Normalize location for search
                    location_normalized = location.lower().strip()

                    # Try multiple query approaches
                    query = {
                        "$or": [
                            {"province": {"$regex": location, "$options": "i"}},
                            {"address": {"$regex": location, "$options": "i"}},
                            {
                                "province_id": {
                                    "$regex": location_normalized.replace(" ", "-"),
                                    "$options": "i",
                                }
                            },
                        ]
                    }

                    cursor = spots_col.find(query).limit(25)
                    for doc in cursor:
                        spots.append(
                            {
                                "_id": str(
                                    doc.get("_id")
                                ),  # Convert ObjectId to string
                                "id": str(
                                    doc.get("_id", "")
                                ),  # String version for compatibility
                                "name": doc.get("name", ""),
                                "category": doc.get("category")
                                or (
                                    doc.get("tags", [])[0]
                                    if doc.get("tags")
                                    else "Tham quan"
                                ),
                                "description": (
                                    (
                                        doc.get("description_short")
                                        or doc.get("description")
                                        or doc.get("description_full", "")
                                    )[:200]
                                ),
                                "rating": doc.get("rating", 4.0),
                                "image": doc.get("image") or doc.get("image_url") or "",
                                "image_url": doc.get("image_url")
                                or doc.get("image")
                                or "",
                                "address": doc.get("address", ""),
                                "tags": doc.get("tags", []),
                                "best_visit_time": doc.get("best_visit_time", []),
                                "avg_duration_min": doc.get("avg_duration_min", 60),
                                "opening_hours": doc.get("opening_hours", ""),
                                "latitude": doc.get("latitude"),
                                "longitude": doc.get("longitude"),
                            }
                        )

                    logger.info(f"📍 Found {len(spots)} spots for {location}")
        except Exception as e:
            logger.error(f"❌ Error fetching spots: {e}")

        return spots

    # ==================== END INTERACTIVE ITINERARY BUILDER ====================

    # ==================== SPOT SELECTOR TABLE (OPTIONAL MULTI-CHOICE) ====================

    def _start_spot_selector_table(
        self, location: str, duration: int, context
    ) -> Optional[Dict[str, Any]]:
        """
        Start optional spot selection with table UI.

        This creates a spot_selector_table UI that allows users to:
        - Multi-select spots via checkboxes
        - See best_visit_time to avoid scheduling issues (e.g., night market in morning)
        - Submit, Cancel, Skip, Select All, Clear All

        Returns:
            Response dict with ui_type="spot_selector_table" or None to fallback
        """
        try:
            if not self.spot_selector:
                logger.warning(
                    "⚠️ SpotSelectorHandler not available, falling back to regular builder"
                )
                return None

            # Get spots for location
            spots = self._get_spots_for_location_sync(location)

            if not spots:
                logger.info(f"⚠️ No spots found for {location}, skipping selector table")
                return None

            # Create selector table response
            return self.spot_selector.create_selector_table(
                spots, location, duration, context
            )

        except Exception as e:
            logger.error(f"❌ Start spot selector table error: {e}")
            import traceback

            traceback.print_exc()
            return None

    def _handle_spot_selection_action(
        self, action: str, selected_ids: List[str], removed_ids: List[str], context
    ) -> Optional[Dict[str, Any]]:
        """
        Handle user's spot selection action from spot_selector_table.

        Actions: submit, cancel, skip, select_all, clear_all
        """
        try:
            if not self.spot_selector:
                return None

            return self.spot_selector.handle_selection_action(
                action, selected_ids, removed_ids, context
            )
        except Exception as e:
            logger.error(f"❌ Handle spot selection action error: {e}")
            return None

    # ==================== ITINERARY VERIFICATION ====================

    def _verify_and_optimize_itinerary(
        self, itinerary_days: List[Dict], context, auto_fix: bool = True
    ) -> Dict[str, Any]:
        """
        Verify itinerary using Rule-based + LLM-as-critic validation.

        This ensures:
        - Night markets are scheduled for evening/night
        - Sunrise spots are scheduled for early morning
        - No timing conflicts with opening hours
        - Logical travel flow (minimize backtracking)

        Args:
            itinerary_days: List of day plans with activities
            context: Enhanced context
            auto_fix: Whether to automatically fix issues

        Returns:
            Dict with verified itinerary and any issues/fixes applied
        """
        try:
            if not self.itinerary_verifier:
                logger.warning(
                    "⚠️ ItineraryVerifier not available, skipping verification"
                )
                return {
                    "verified": True,
                    "issues": [],
                    "itinerary": itinerary_days,
                    "changes": [],
                }

            # Build spots_data from context for verification
            spots_data = {}
            last_spots = getattr(context, "last_spots", [])
            for spot in last_spots:
                spot_id = spot.get("id", spot.get("name", ""))
                spots_data[spot_id] = spot

            # Run verification
            result = self.itinerary_verifier.verify(itinerary_days, spots_data)

            logger.info(
                f"🔍 Verification result: {result.verdict} ({len(result.issues)} issues)"
            )

            # Store issues in context
            context.verification_issues = [
                {
                    "type": i.type,
                    "spot_name": i.spot_name,
                    "day": i.day,
                    "reason": i.reason,
                    "severity": i.severity,
                }
                for i in result.issues
            ]

            # Auto-fix if requested and there are errors
            changes = []
            final_itinerary = itinerary_days

            if auto_fix and result.verdict == "fail":
                fixed_itinerary, applied_changes = self.itinerary_verifier.auto_fix(
                    itinerary_days, result.issues
                )
                if applied_changes:
                    final_itinerary = fixed_itinerary
                    changes = applied_changes
                    context.verified_itinerary = {"days": final_itinerary}
                    logger.info(f"✅ Auto-fixed {len(changes)} issues")

            return {
                "verified": result.verdict != "fail",
                "verdict": result.verdict,
                "issues": [
                    {
                        "spot_name": i.spot_name,
                        "day": i.day,
                        "reason": i.reason,
                        "severity": i.severity,
                        "suggested_slot": (
                            i.expected_slots[0] if i.expected_slots else None
                        ),
                    }
                    for i in result.issues
                ],
                "suggested_moves": result.suggested_moves,
                "itinerary": final_itinerary,
                "changes": changes,
            }

        except Exception as e:
            logger.error(f"❌ Verify itinerary error: {e}")
            import traceback

            traceback.print_exc()
            return {
                "verified": True,  # Don't block on verification failure
                "issues": [],
                "itinerary": itinerary_days,
                "changes": [],
            }

    def _format_verification_message(self, verification_result: Dict) -> str:
        """Format verification result as user-friendly message."""
        issues = verification_result.get("issues", [])
        changes = verification_result.get("changes", [])
        verdict = verification_result.get("verdict", "pass")

        if verdict == "pass" and not changes:
            return ""  # No message needed

        parts = []

        # Only show auto-fix message if there are actual changes
        if changes and isinstance(changes, list) and len(changes) > 0:
            parts.append("⚠️ **Tôi đã tự động điều chỉnh lịch trình:**\n")
            for change in changes:
                if isinstance(change, str):
                    parts.append(f"  • {change}")
                elif isinstance(change, dict):
                    change_desc = change.get(
                        "description", change.get("change", str(change))
                    )
                    parts.append(f"  • {change_desc}")
            parts.append("")

        # Show issues/warnings if no auto-fix was applied
        if issues and (not changes or len(changes) == 0):
            parts.append("⚠️ **Lưu ý về lịch trình:**\n")
            for issue in issues[:3]:  # Limit to 3 issues
                severity_icon = "❌" if issue.get("severity") == "error" else "⚠️"
                reason = issue.get("reason", "Vấn đề không xác định")
                parts.append(f"  {severity_icon} {reason}")
            parts.append("")

        return "\n".join(parts)

    # ==================== END ITINERARY VERIFICATION ====================

    # ==================== FIX A: UPDATE PEOPLE COUNT HANDLER ====================
    def _handle_update_people_count(
        self, multi_intent, context, user_message: str
    ) -> Optional[Dict[str, Any]]:
        """
        Handle "2 người thì sao" - update people count and recalculate cost.
        This prevents state reset when user asks for cost with different people count.

        Example triggers:
        - "Nếu có 2 người thì sao?"
        - "Tính cho 3 người đi"
        - "5 người thì hết bao nhiêu?"
        """
        try:
            import re

            # Extract people count from message
            lower_msg = user_message.lower()

            # Patterns to find number of people
            patterns = [
                r"(\d+)\s*người",  # "2 người"
                r"(\d+)\s*nguoi",  # non-accent
                r"cho\s*(\d+)\s*người",  # "cho 3 người"
                r"có\s*(\d+)\s*người",  # "có 5 người"
                r"với\s*(\d+)\s*người",  # "với 4 người"
                r"(\d+)\s*thành viên",  # "3 thành viên"
            ]

            new_people_count = None
            for pattern in patterns:
                match = re.search(pattern, lower_msg)
                if match:
                    new_people_count = int(match.group(1))
                    break

            if not new_people_count:
                # Fallback: check multi_intent
                new_people_count = getattr(multi_intent, "people_count", None)

            if not new_people_count or new_people_count < 1:
                return {
                    "reply": "Bạn muốn tính cho bao nhiêu người? 👥\n\nHãy cho tôi biết số người đi để tính lại chi phí nhé!",
                    "ui_type": "options",
                    "ui_data": {
                        "options": [
                            "1 người",
                            "2 người",
                            "3 người",
                            "4 người",
                            "5 người",
                        ]
                    },
                    "context": context.to_dict(),
                    "status": "need_info",
                }

            # Update context with new people count
            old_people_count = getattr(context, "people_count", 1)
            context.people_count = new_people_count
            multi_intent.people_count = new_people_count

            logger.info(
                f"[FIX A] 👥 Updated people count: {old_people_count} → {new_people_count}"
            )

            # Keep workflow state (DO NOT RESET!)
            # If in COST_ESTIMATION, stay in COST_ESTIMATION
            workflow_state = getattr(context, "workflow_state", "INITIAL")
            logger.info(f"[FIX A] 📊 Maintaining workflow_state: {workflow_state}")

            # Recalculate cost with new people count
            return self._handle_cost_calculation_sync(
                multi_intent, context, user_message
            )

        except Exception as e:
            logger.error(f"❌ Error in _handle_update_people_count: {e}")
            return None

    def _handle_weather_sync(
        self, multi_intent, context, user_message: str
    ) -> Optional[Dict[str, Any]]:
        """Handle weather forecast request synchronously"""
        try:
            # Extract location from context or message
            location = getattr(context, "destination", None) or multi_intent.location

            if not location:
                # Try to extract from message
                import re

                location_patterns = [
                    r"thời tiết (?:ở |tại )?([A-Za-zÀ-ỹ\s]+?)(?:\s+ngày|\s+hôm|\s+tuần|\?|$)",
                    r"([A-Za-zÀ-ỹ\s]+?)\s+thời tiết",
                ]
                for pattern in location_patterns:
                    match = re.search(pattern, user_message, re.IGNORECASE)
                    if match:
                        location = match.group(1).strip()
                        break

            if not location:
                return {
                    "reply": "🌤️ Bạn muốn xem thời tiết ở đâu?\n\n"
                    "Hãy cho tôi biết địa điểm, ví dụ: **'Thời tiết Đà Nẵng tuần này'**",
                    "ui_type": "text",
                    "context": context.to_dict(),
                    "status": "need_info",
                }

            # Determine date range
            from datetime import datetime, timedelta

            today = datetime.now()
            start_date = today.strftime("%Y-%m-%d")
            num_days = 3  # Default 3 days forecast

            # Check for specific date references in message
            lower_msg = user_message.lower()
            if "ngày mai" in lower_msg or "tomorrow" in lower_msg:
                start_date = (today + timedelta(days=1)).strftime("%Y-%m-%d")
                num_days = 1
            elif (
                "tuần này" in lower_msg
                or "tuần tới" in lower_msg
                or "this week" in lower_msg
            ):
                num_days = 7
            elif "hôm nay" in lower_msg or "today" in lower_msg:
                num_days = 1

            # Use start_date from context if available
            if hasattr(context, "start_date") and context.start_date:
                start_date = context.start_date
                num_days = getattr(context, "duration", 3) or 3

            logger.info(
                f"🌤️ Fetching weather for {location}, start={start_date}, days={num_days}"
            )

            # Get weather data
            try:
                weather_data = self.weather.get_weather(location, start_date, num_days)
                weather_response = self.weather.build_weather_response(weather_data)

                if weather_response:
                    return {
                        "reply": weather_response,
                        "ui_type": "text",
                        "context": context.to_dict(),
                        "status": "success",
                    }
                else:
                    return {
                        "reply": f"🌤️ Không có dữ liệu thời tiết cho **{location}** vào thời điểm này.\n\n"
                        "Thử lại sau hoặc chọn khoảng thời gian khác!",
                        "ui_type": "text",
                        "context": context.to_dict(),
                        "status": "success",
                    }

            except Exception as weather_error:
                logger.warning(f"⚠️ Weather API error: {weather_error}")
                return {
                    "reply": f"🌤️ Xin lỗi, tôi không thể lấy thông tin thời tiết cho **{location}** lúc này.\n\n"
                    f"Lỗi: {str(weather_error)}\n\n"
                    "Bạn có thể thử lại sau hoặc kiểm tra các trang web thời tiết như weather.com",
                    "ui_type": "text",
                    "context": context.to_dict(),
                    "status": "error",
                }

        except Exception as e:
            logger.error(f"❌ Error in _handle_weather_sync: {e}")
            return {
                "reply": "🌤️ Có lỗi xảy ra khi lấy thông tin thời tiết. Vui lòng thử lại!",
                "ui_type": "text",
                "context": context.to_dict(),
                "status": "error",
            }

    def _handle_cost_calculation_sync(
        self, multi_intent, context, user_message: str
    ) -> Optional[Dict[str, Any]]:
        """Handle cost calculation synchronously with STATE VALIDATION"""
        try:
            location = getattr(context, "destination", None) or multi_intent.location
            duration = getattr(context, "duration", None) or multi_intent.duration

            # Try to extract from message if not in context
            if not location or not duration:
                extracted = self._extract_location_and_duration_from_query(user_message)
                if extracted:
                    extracted_location, extracted_duration = extracted
                    location = location or extracted_location
                    duration = duration or extracted_duration

            if not location:
                return {
                    "reply": "Bạn muốn tính chi phí cho chuyến đi đến đâu? 🗺️\n"
                    "Hãy cho tôi biết điểm đến của bạn!",
                    "ui_type": "options",
                    "context": context.to_dict(),
                    "status": "need_info",
                }

            if not duration:
                return {
                    "reply": f"Bạn dự định đi {location} trong bao nhiêu ngày? 📅",
                    "ui_type": "options",
                    "ui_data": {"options": ["2 ngày", "3 ngày", "5 ngày", "7 ngày"]},
                    "context": context.to_dict(),
                    "status": "need_info",
                }

            # FIX 3: Auto-select hotel with LLM reasoning instead of blocking user
            workflow_state = getattr(context, "workflow_state", "INITIAL")
            selected_hotel = getattr(context, "selected_hotel", None)
            last_hotels = getattr(context, "last_hotels", [])

            # If user hasn't selected hotel, use LLM to auto-select based on budget
            if not selected_hotel and last_hotels:
                logger.info(f"🤖 [FIX 3] Auto-selecting hotel with LLM reasoning")

                try:
                    # Extract budget preference from user message or context
                    budget = getattr(context, "budget", None)
                    people_count = getattr(context, "people_count", 1)

                    # Build hotel list for LLM
                    hotel_list = []
                    for i, hotel in enumerate(last_hotels[:5], 1):
                        name = hotel.get("name", "N/A")
                        price = hotel.get("price", 0)
                        hotel_list.append(f"{i}. {name} - {price:,} VNĐ/đêm")

                    # LLM prompt for auto-selection
                    prompt = f"""Bạn là chuyên gia tư vấn du lịch.

USER muốn tính chi phí cho chuyến đi {location} ({duration} ngày, {people_count} người).

CÁC KHÁCH SẠN KHẢ DỤNG:
{chr(10).join(hotel_list)}

USER BUDGET: {budget if budget else 'Chưa rõ (giả định: trung bình)'}
USER MESSAGE: "{user_message}"

HÃY CHỌN KHÁCH SẠN PHÙ HỢP NHẤT:
- Nếu budget thấp/tiết kiệm → chọn khách sạn rẻ nhất
- Nếu budget trung bình/không đề cập → chọn khách sạn giá trung bình (vị trí 2-3)
- Nếu budget cao/sang trọng → chọn khách sạn đắt nhất

Trả về JSON:
{{"hotel_index": <số thứ tự 1-5>, "reason": "<lý do ngắn gọn>"}}"""

                    llm_response = self.llm.complete(
                        prompt, temperature=0.3, max_tokens=100
                    )

                    # Parse LLM response
                    import json
                    import re

                    json_match = re.search(r"\{.*\}", llm_response, re.DOTALL)
                    if json_match:
                        result = json.loads(json_match.group())
                        hotel_index = (
                            result.get("hotel_index", 2) - 1
                        )  # Convert to 0-based
                        reason = result.get("reason", "Phù hợp với ngân sách")

                        # Validate index
                        if 0 <= hotel_index < len(last_hotels):
                            selected_hotel_data = last_hotels[hotel_index]
                            selected_hotel = selected_hotel_data.get("name")
                            selected_hotel_price = selected_hotel_data.get("price")

                            # Update context
                            context.selected_hotel = selected_hotel
                            context.selected_hotel_price = selected_hotel_price

                            logger.info(
                                f"✅ [FIX 3] Auto-selected: {selected_hotel} - {selected_hotel_price:,} VNĐ"
                            )
                            logger.info(f"📝 Reason: {reason}")
                        else:
                            raise ValueError(f"Invalid hotel_index: {hotel_index}")
                    else:
                        raise ValueError("No JSON in LLM response")

                except Exception as llm_error:
                    logger.warning(
                        f"⚠️ [FIX 3] LLM auto-select failed: {llm_error}, using median price"
                    )
                    # Fallback: Select middle-price hotel
                    if last_hotels:
                        middle_index = len(last_hotels) // 2
                        selected_hotel_data = last_hotels[middle_index]
                        selected_hotel = selected_hotel_data.get("name")
                        selected_hotel_price = selected_hotel_data.get("price")
                        context.selected_hotel = selected_hotel
                        context.selected_hotel_price = selected_hotel_price
                        logger.info(
                            f"✅ [FIX 3] Fallback selected: {selected_hotel} - {selected_hotel_price:,} VNĐ"
                        )

            # OLD BLOCKING CODE REMOVED - Now we auto-select instead of blocking

            # Get prices based on location and context
            default_prices = self._get_location_default_prices(location)

            # Use selected hotel price if available
            selected_hotel_price = getattr(context, "selected_hotel_price", None)
            hotel_price = (
                selected_hotel_price
                if selected_hotel_price
                else default_prices["hotel"]
            )

            if selected_hotel and selected_hotel_price:
                logger.info(
                    f"💰 Using selected hotel: {selected_hotel} - {selected_hotel_price:,} VNĐ/đêm"
                )

            # Calculate per-day costs
            daily_costs = []
            total_cost = 0

            for day_num in range(1, duration + 1):
                is_last_day = day_num == duration
                is_first_day = day_num == 1

                # Accommodation (not on last day - going home)
                if is_last_day:
                    accommodation = 0
                    accommodation_note = "Về nhà"
                else:
                    accommodation = hotel_price
                    accommodation_note = (
                        selected_hotel if selected_hotel else "Khách sạn"
                    )

                # Food
                food = default_prices["food"]

                # Transport (higher on first/last day for airport)
                if is_first_day or is_last_day:
                    transport = (
                        default_prices.get("transport", 250000) + 125000
                    )  # Airport transfer
                    transport_note = "Di chuyển + sân bay"
                else:
                    transport = default_prices.get("transport", 250000)
                    transport_note = "Di chuyển nội thành"

                # Activities
                activity = default_prices.get("activity", 200000)

                day_total = accommodation + food + transport + activity
                total_cost += day_total

                daily_costs.append(
                    {
                        "day": day_num,
                        "accommodation": accommodation,
                        "accommodation_note": accommodation_note,
                        "food": food,
                        "transport": transport,
                        "transport_note": transport_note,
                        "activity": activity,
                        "total": day_total,
                    }
                )

            # FIX 3: Format response with auto-selection notice
            nights = duration - 1
            hotel_info = ""
            auto_select_notice = ""

            if selected_hotel and selected_hotel_price:
                hotel_info = f"\n🏨 Khách sạn: **{selected_hotel}** ({selected_hotel_price:,} VNĐ/đêm)"

                # Check if this was auto-selected (not manually chosen by user)
                if not getattr(context, "user_selected_hotel", False):
                    auto_select_notice = "\n\n💡 *Tôi đã tự động chọn khách sạn phù hợp với ngân sách của bạn. Bạn có thể thay đổi bằng cách chọn khách sạn khác!*"

            cost_breakdown = f"💰 **Chi phí ước tính cho {duration} ngày tại {location}**{hotel_info}{auto_select_notice}\n\n"

            for day in daily_costs:
                cost_breakdown += f"📅 **Ngày {day['day']}:**\n"
                if day["accommodation"] > 0:
                    cost_breakdown += f"  • 🏨 Lưu trú ({day['accommodation_note']}): {day['accommodation']:,} VNĐ\n"
                else:
                    cost_breakdown += f"  • 🏠 Lưu trú: {day['accommodation_note']}\n"
                cost_breakdown += f"  • 🍜 Ăn uống: {day['food']:,} VNĐ\n"
                cost_breakdown += f"  • 🚗 Di chuyển ({day['transport_note']}): {day['transport']:,} VNĐ\n"
                cost_breakdown += f"  • 🎯 Tham quan: {day['activity']:,} VNĐ\n"
                cost_breakdown += (
                    f"  💵 **Tổng ngày {day['day']}: {day['total']:,} VNĐ**\n\n"
                )

            cost_breakdown += f"━━━━━━━━━━━━━━━━━━━━\n"
            cost_breakdown += f"💵 **TỔNG CHI PHÍ: {total_cost:,} VNĐ**\n"
            cost_breakdown += f"━━━━━━━━━━━━━━━━━━━━\n\n"
            cost_breakdown += f"💡 *Chi phí trên là ước tính cho 1 người. Thực tế có thể dao động ±20% tùy vào lựa chọn dịch vụ.*"

            return {
                "reply": cost_breakdown,
                "ui_type": "cost_breakdown",
                "ui_data": {
                    "location": location,
                    "duration": duration,
                    "daily_costs": daily_costs,
                    "total_cost": total_cost,
                    "selected_hotel": selected_hotel,
                    "selected_hotel_price": selected_hotel_price,
                },
                "context": context.to_dict(),
                "status": "complete",
            }

        except Exception as e:
            logger.error(f"❌ Cost calculation error: {e}")
            import traceback

            traceback.print_exc()
            return {
                "reply": "Xin lỗi, đã có lỗi khi tính toán chi phí. Bạn có thể thử lại không? 🙏",
                "ui_type": "error",
                "context": context.to_dict(),
                "status": "error",
            }

    def _handle_location_tips_sync(
        self, multi_intent, context, user_message: str
    ) -> Optional[Dict[str, Any]]:
        """
        Handle get_location_tips intent - provide tips/advice for selected spots
        Context-aware: Uses selected_spots from itinerary_builder or last_itinerary
        """
        try:
            # SEMANTIC CHECK: Distinguish "giới thiệu/thông tin" vs "lưu ý/tips"
            # If user wants INFORMATION about spots, redirect to spot detail handler
            info_keywords = [
                "giới thiệu",
                "thông tin",
                "nói về",
                "cho tôi biết về",
                "các địa điểm",
                "địa danh",
            ]
            tips_keywords = [
                "lưu ý",
                "chuẩn bị",
                "mẹo",
                "kinh nghiệm",
                "khuyên",
                "nên làm gì",
            ]

            message_lower = user_message.lower()
            has_info_intent = any(kw in message_lower for kw in info_keywords)
            has_tips_intent = any(kw in message_lower for kw in tips_keywords)

            # If asking for INFORMATION (not tips), provide spot summaries instead
            if has_info_intent and not has_tips_intent:
                logger.info(
                    f"🔄 [TIPS] User wants spot INFO, not tips. Providing spot summaries..."
                )
                # Check if user is asking about a SPECIFIC spot
                specific_spot = self._extract_specific_spot_from_message(
                    user_message, context
                )
                if specific_spot:
                    logger.info(
                        f"🎯 [TIPS] User asking about specific spot: {specific_spot}"
                    )
                    return self._handle_single_spot_info(
                        specific_spot, context, user_message
                    )
                else:
                    return self._handle_spot_info_request_sync(context, user_message)

            # Get selected spots from context with priority order
            selected_spots = []

            # Priority 0: selected_spots memory
            selected_spots = _get_context_value(context, "selected_spots", [])
            if selected_spots:
                logger.info(
                    f"🔍 [TIPS] Found {len(selected_spots)} spots from selected_spots memory"
                )

            # Priority 1: Check itinerary builder
            if not selected_spots:
                builder = _get_context_value(context, "itinerary_builder")
                if builder:
                    days_plan = (
                        builder.get("days_plan", {})
                        if isinstance(builder, dict)
                        else {}
                    )
                    for day_spots in days_plan.values():
                        selected_spots.extend(day_spots)
                    logger.info(
                        f"🔍 [TIPS] Found {len(selected_spots)} spots from itinerary_builder"
                    )

            # Priority 2: Check last itinerary
            if not selected_spots:
                last_itinerary = _get_context_value(context, "last_itinerary")
                if last_itinerary and isinstance(last_itinerary, dict):
                    days = last_itinerary.get("days", [])
                    for day in days:
                        # Try both 'spots' and 'activities' for compatibility
                        spots_list = day.get("spots", []) or day.get("activities", [])
                        for spot in spots_list:
                            # Handle both string and dict formats
                            if isinstance(spot, str):
                                selected_spots.append({"name": spot})
                            elif isinstance(spot, dict):
                                spot_name = (
                                    spot.get("name")
                                    or spot.get("location")
                                    or spot.get("spot")
                                    or spot.get("spot_name")
                                )
                                if spot_name:
                                    selected_spots.append({"name": spot_name})
                    logger.info(
                        f"🔍 [TIPS DEBUG] Found {len(selected_spots)} spots from last_itinerary"
                    )

            logger.info(f"🔍 [TIPS DEBUG] Total selected_spots: {len(selected_spots)}")
            if not selected_spots:
                return {
                    "reply": "Bạn chưa chọn địa điểm nào cả. Hãy chọn địa điểm trước, sau đó tôi sẽ cung cấp các lưu ý hữu ích! 😊",
                    "ui_type": "text",
                    "context": context.to_dict(),
                    "status": "partial",
                }

            # Build tips response using GeneralInfoExpert for proper RAG
            spot_names = [s.get("name") for s in selected_spots[:10]]
            location = multi_intent.location or context.destination or "điểm đến"

            # Use GeneralInfoExpert to get context-aware tips with RAG
            try:
                from app.services.experts import GeneralInfoExpert

                general_expert = self.experts.get("general_info")

                if not general_expert:
                    logger.warning(
                        "⚠️ GeneralInfoExpert not found, creating instance..."
                    )
                    general_expert = GeneralInfoExpert(self.mongo_manager, self.llm)

                # Execute expert with proper RAG context gathering
                expert_result = general_expert.execute(
                    query="lưu ý khi du lịch",
                    parameters={
                        "location": location,
                        "original_query": user_message,
                        "context": {
                            "selected_spots": spot_names,
                            "itinerary": (
                                context.last_itinerary
                                if hasattr(context, "last_itinerary")
                                else None
                            ),
                        },
                    },
                )

                if expert_result.success and expert_result.summary:
                    tips_reply = f"""📝 **LƯU Ý CHO CHUYẾN ĐI {location.upper()}**

{expert_result.summary}

━━━━━━━━━━━━━━━━━━━━

💬 **Bạn muốn làm gì tiếp theo?**

🏨 **1. Tìm khách sạn** - Gõ: "tìm khách sạn"
💰 **2. Tính chi phí** - Gõ: "tính tiền"
📋 **3. Xem lại lịch trình** - Gõ: "xem lại lịch trình"
📍 **4. Chi tiết địa điểm** - Gõ: "chi tiết về [tên địa điểm]"

Cần thêm thông tin gì không? 😊"""
                    logger.info(
                        "✅ [RAG] GeneralInfoExpert provided context-aware tips"
                    )
                else:
                    raise Exception("Expert returned empty summary")

            except Exception as expert_error:
                logger.warning(f"⚠️ [RAG] Expert failed: {expert_error}, using fallback")
                # Fallback: generic tips without RAG
                tips_reply = f"""📝 **LƯU Ý CHO CHUYẾN ĐI {location.upper()}**

🎯 **Các địa điểm bạn đã chọn:**
{chr(10).join([f"  • {name}" for name in spot_names])}

💡 **Lưu ý chung:**
• ⏰ **Thời gian tốt nhất:** Khởi hành sớm (7-8h sáng) để tránh nắng và đông đúc
• 🧴 **Chuẩn bị:** Kem chống nắng, nón, nước uống, giày thoải mái
• 💰 **Tiền mặt:** Mang theo tiền lẻ cho vé vào cửa và mua nước
• 📸 **Chụp ảnh:** Giờ vàng (6-7h sáng hoặc 5-6h chiều) cho ánh sáng đẹp nhất

🎫 **Vé tham quan:**
• Nhiều địa điểm có giá vé combo tiết kiệm hơn
• Sinh viên nhớ mang thẻ để được giảm giá 50%

🚗 **Di chuyển:**
• Grab/Taxi: Tiện lợi nhất cho nhóm 2-4 người
• Thuê xe máy: Linh hoạt, khoảng 100-150k/ngày
• Xe bus: Tiết kiệm nhất, có app Danang Fantasticity

🍜 **Ẩm thực:**
• Ăn tại quán địa phương gần các điểm tham quan để tiết kiệm
• Nên ăn trưa từ 11h30-12h để tránh quá đói

━━━━━━━━━━━━━━━━━━━━

� **Bạn muốn làm gì tiếp theo?**

🏨 **1. Tìm khách sạn** - Gõ: "tìm khách sạn"
💰 **2. Tính chi phí** - Gõ: "tính tiền"
📋 **3. Xem lại lịch trình** - Gõ: "xem lại lịch trình"
📍 **4. Chi tiết địa điểm** - Gõ: "chi tiết về [tên địa điểm]"

Cần thêm thông tin gì không? 😊"""

            return {
                "reply": tips_reply,
                "ui_type": "tips",
                "ui_data": {
                    "selected_spots": spot_names,
                    "location": location,
                    "tips_categories": [
                        {
                            "icon": "⏰",
                            "title": "Thời gian",
                            "content": "Khởi hành sớm 7-8h",
                        },
                        {
                            "icon": "🧴",
                            "title": "Chuẩn bị",
                            "content": "Kem chống nắng, nón, nước",
                        },
                        {
                            "icon": "💰",
                            "title": "Tiền mặt",
                            "content": "Mang tiền lẻ cho vé",
                        },
                        {
                            "icon": "📸",
                            "title": "Chụp ảnh",
                            "content": "Golden hour 6-7h hoặc 5-6h",
                        },
                        {
                            "icon": "🎫",
                            "title": "Vé",
                            "content": "Vé combo tiết kiệm, SV giảm 50%",
                        },
                        {
                            "icon": "🚗",
                            "title": "Di chuyển",
                            "content": "Grab/Taxi hoặc thuê xe máy",
                        },
                        {
                            "icon": "🍜",
                            "title": "Ẩm thực",
                            "content": "Quán địa phương ngon + rẻ",
                        },
                    ],
                    # CRITICAL: Add action buttons matching frontend format
                    "actions": [
                        {"label": "🏨 Tìm khách sạn", "action": "tìm khách sạn"},
                        {"label": "💰 Tính chi phí", "action": "tính tiền"},
                        {
                            "label": "📋 Xem lại lịch trình",
                            "action": "xem lại lịch trình",
                        },
                    ],
                },
                "context": context.to_dict(),
                "status": "success",
            }

        except Exception as e:
            logger.error(f"❌ Location tips error: {e}")
            import traceback

            traceback.print_exc()
            return {
                "reply": "Xin lỗi, không thể lấy thông tin lưu ý lúc này. Bạn hãy thử lại nhé! 🙏",
                "ui_type": "error",
                "context": context.to_dict(),
                "status": "error",
            }

    # ==================== FIX C: PLACE DETAILS HANDLER ====================
    def _handle_place_details_sync(
        self, multi_intent, context, user_message: str
    ) -> Optional[Dict[str, Any]]:
        """
        Handle get_place_details intent - provide DETAILED INFO about a specific place.

        Different from get_location_tips which returns advice/tips.
        This returns: description, history, features, visiting hours, etc.

        Example triggers:
        - "Chi tiết về Bãi Biển Mỹ Khê"
        - "Giới thiệu về Cầu Rồng"
        - "Cho tôi biết về Ngũ Hành Sơn"
        """
        try:
            import re

            lower_msg = user_message.lower()

            # Extract place name from message
            place_name = None

            # Patterns to extract place name
            patterns = [
                r"chi tiết về (.+?)(?:\?|$|,|\.|!)",
                r"chi tiet ve (.+?)(?:\?|$|,|\.|!)",
                r"giới thiệu về (.+?)(?:\?|$|,|\.|!)",
                r"gioi thieu ve (.+?)(?:\?|$|,|\.|!)",
                r"thông tin về (.+?)(?:\?|$|,|\.|!)",
                r"thong tin ve (.+?)(?:\?|$|,|\.|!)",
                r"cho tôi biết về (.+?)(?:\?|$|,|\.|!)",
                r"cho toi biet ve (.+?)(?:\?|$|,|\.|!)",
                r"kể về (.+?)(?:\?|$|,|\.|!)",
                r"ke ve (.+?)(?:\?|$|,|\.|!)",
                r"mô tả (.+?)(?:\?|$|,|\.|!)",
                r"mo ta (.+?)(?:\?|$|,|\.|!)",
            ]

            for pattern in patterns:
                match = re.search(pattern, lower_msg)
                if match:
                    place_name = match.group(1).strip()
                    break

            # Clean up place name
            if place_name:
                # Remove common suffixes
                place_name = re.sub(
                    r"\s*(ở|tại|trong|ngoài|gần|đi|thăm|xem|đến).*$",
                    "",
                    place_name,
                    flags=re.IGNORECASE,
                )
                place_name = place_name.strip()

            logger.info(f"[FIX C] 📍 Extracted place name: '{place_name}'")

            if not place_name:
                # Try to get from context (last mentioned place)
                last_spots = getattr(context, "last_spots", [])
                selected_spots = getattr(context, "selected_spots", [])

                if selected_spots:
                    # Offer options from selected spots
                    spot_names = [
                        s.get("name", "") for s in selected_spots[:5] if s.get("name")
                    ]
                    return {
                        "reply": "Bạn muốn biết chi tiết về địa điểm nào? 📍\n\nHãy chọn một trong các địa điểm đã chọn:",
                        "ui_type": "options",
                        "ui_data": {"options": spot_names, "prefix": "Chi tiết về "},
                        "context": context.to_dict(),
                        "status": "need_info",
                    }
                elif last_spots:
                    spot_names = [
                        s.get("name", "") for s in last_spots[:5] if s.get("name")
                    ]
                    return {
                        "reply": "Bạn muốn biết chi tiết về địa điểm nào? 📍\n\nHãy chọn một trong các địa điểm:",
                        "ui_type": "options",
                        "ui_data": {"options": spot_names, "prefix": "Chi tiết về "},
                        "context": context.to_dict(),
                        "status": "need_info",
                    }
                else:
                    return {
                        "reply": "Bạn muốn biết chi tiết về địa điểm nào? 📍\n\nHãy cho tôi biết tên địa điểm bạn muốn tìm hiểu!",
                        "ui_type": "text",
                        "context": context.to_dict(),
                        "status": "need_info",
                    }

            # Search for the place in MongoDB
            spot_data = None

            try:
                # Use SpotExpert to search
                spot_expert = self.experts.get("spot")
                if spot_expert:
                    result = spot_expert.execute(
                        query=place_name, parameters={"limit": 1, "semantic": True}
                    )
                    if result.success and result.data:
                        spot_data = (
                            result.data[0]
                            if isinstance(result.data, list)
                            else result.data
                        )

                # Fallback: direct MongoDB search
                if not spot_data:
                    from app.services.mongodb_manager import get_mongodb_manager

                    mongo = get_mongodb_manager()
                    collection = mongo.client[mongo.db_name]["spots_detailed"]

                    spot_data = collection.find_one(
                        {"name": {"$regex": place_name, "$options": "i"}}, {"_id": 0}
                    )

            except Exception as db_error:
                logger.error(f"❌ Database search error: {db_error}")

            if not spot_data:
                return {
                    "reply": f"Xin lỗi, tôi không tìm thấy thông tin về **{place_name}** trong cơ sở dữ liệu. 😅\n\n"
                    f"Bạn có thể thử:\n"
                    f"• Kiểm tra lại tên địa điểm\n"
                    f'• Tìm địa điểm khác: "tìm địa điểm [tên tỉnh]"',
                    "ui_type": "text",
                    "context": context.to_dict(),
                    "status": "not_found",
                }

            # Build detailed response
            name = spot_data.get("name", place_name)
            category = spot_data.get("category") or (
                spot_data.get("tags", ["Điểm tham quan"])[0]
                if spot_data.get("tags")
                else "Điểm tham quan"
            )

            # Get description with fallback chain
            description = (
                spot_data.get("description_short")
                or spot_data.get("description")
                or spot_data.get("description_full")
                or "Chưa có mô tả chi tiết."
            )

            address = spot_data.get("address", "Không có thông tin")
            province = spot_data.get("province_name") or spot_data.get("province", "")

            # Build reply
            reply_parts = [
                f"📍 **{name.upper()}**",
                f"📁 {category}" + (f" | {province}" if province else ""),
                "",
                f"📝 **Mô tả:**",
                description[:500] + ("..." if len(description) > 500 else ""),
                "",
            ]

            # Add address
            if address and address != "Không có thông tin":
                reply_parts.append(f"📍 **Địa chỉ:** {address}")

            # Add rating if available
            rating = spot_data.get("rating") or spot_data.get("google_rating")
            if rating:
                reply_parts.append(f"⭐ **Đánh giá:** {rating}/5")

            # Add visiting hours if available
            hours = spot_data.get("opening_hours") or spot_data.get("hours")
            if hours:
                reply_parts.append(f"⏰ **Giờ mở cửa:** {hours}")

            # Add entrance fee if available
            fee = spot_data.get("entrance_fee") or spot_data.get("price")
            if fee:
                reply_parts.append(f"🎫 **Giá vé:** {fee}")

            # Add tips if available
            tips = spot_data.get("tips") or spot_data.get("travel_tips")
            if tips:
                if isinstance(tips, list):
                    tips = tips[0] if tips else None
                if tips:
                    reply_parts.append(
                        f"\n💡 **Mẹo:** {tips[:200]}{'...' if len(str(tips)) > 200 else ''}"
                    )

            reply_parts.append("")
            reply_parts.append("━━━━━━━━━━━━━━━━━━━━")
            reply_parts.append("💬 **Cần thêm thông tin gì không?**")

            reply = "\n".join(reply_parts)

            # Build UI data
            ui_data = {
                "spot": {
                    "name": name,
                    "category": category,
                    "description": description,
                    "address": address,
                    "province": province,
                    "rating": rating,
                    "image": spot_data.get("image") or spot_data.get("image_url"),
                    "coordinates": {
                        "lat": spot_data.get("latitude")
                        or spot_data.get("coordinates", {}).get("lat"),
                        "lng": spot_data.get("longitude")
                        or spot_data.get("coordinates", {}).get("lng"),
                    },
                },
                "actions": [
                    {"label": "📝 Lưu ý khi đi", "action": f"lưu ý về {name}"},
                    {"label": "📍 Địa điểm gần đó", "action": f"địa điểm gần {name}"},
                    {"label": "🏨 Tìm khách sạn", "action": "tìm khách sạn"},
                ],
            }

            return {
                "reply": reply,
                "ui_type": "spot_detail",
                "ui_data": ui_data,
                "context": context.to_dict(),
                "status": "success",
            }

        except Exception as e:
            logger.error(f"❌ Place details error: {e}")
            import traceback

            traceback.print_exc()
            return {
                "reply": "Xin lỗi, không thể lấy thông tin chi tiết lúc này. Bạn hãy thử lại nhé! 🙏",
                "ui_type": "error",
                "context": context.to_dict(),
                "status": "error",
            }

    def _extract_specific_spot_from_message(
        self, user_message: str, context
    ) -> Optional[str]:
        """
        Extract specific spot name from user message.
        Returns spot name if user is asking about ONE specific spot, None otherwise.
        """
        import re

        message_lower = user_message.lower()

        # FIX 2026-01-18: Extract spot name from "Tôi quan tâm đến [spot]" pattern
        interest_patterns = [
            r"(?:tôi\s+)?quan\s+tâm\s+(?:đến|tới)\s+(.+?)(?:\.\s*hãy|\?\s*|$)",
            r"cho\s+(?:tôi\s+)?(?:thêm\s+)?thông\s+tin\s+(?:về\s+|chi\s+tiết\s+)?(.+?)(?:\.\s*|$)",
            r"giới\s+thiệu\s+(?:về\s+)?(.+?)(?:\.\s*|$)",
        ]
        for pattern in interest_patterns:
            match = re.search(pattern, message_lower, re.IGNORECASE)
            if match:
                extracted_name = match.group(1).strip()
                # Clean up common suffixes
                extracted_name = re.sub(
                    r"\.\s*hãy\s+cho.*$", "", extracted_name, flags=re.IGNORECASE
                )
                if len(extracted_name) >= 3:
                    # Try to find this in database
                    try:
                        spots_col = self.mongo_manager.get_collection("spots_detailed")
                        spot_doc = spots_col.find_one(
                            {"name": {"$regex": extracted_name, "$options": "i"}}
                        )
                        if spot_doc:
                            logger.info(
                                f"🎯 Extracted spot from 'quan tâm' pattern: {spot_doc.get('name')}"
                            )
                            return spot_doc.get("name")
                    except Exception as e:
                        logger.debug(f"DB lookup failed for extracted name: {e}")

        # Keywords indicating user wants ALL spots (not specific)
        plural_keywords = [
            "các địa điểm",
            "tất cả",
            "từng địa điểm",
            "những địa điểm",
            "mọi nơi",
            "tất cả điểm",
        ]
        if any(kw in message_lower for kw in plural_keywords):
            return None

        # Get spots from context to match against
        selected_spots = _get_context_value(context, "selected_spots", [])
        if not selected_spots:
            builder = _get_context_value(context, "itinerary_builder")
            if builder:
                days_plan = (
                    builder.get("days_plan", {}) if isinstance(builder, dict) else {}
                )
                for day_spots in days_plan.values():
                    selected_spots.extend(day_spots)

        # Try to find a specific spot name in the message
        for spot in selected_spots:
            spot_name = spot.get("name", "") if isinstance(spot, dict) else str(spot)
            if not spot_name:
                continue

            # Normalize for comparison
            spot_name_lower = spot_name.lower()

            # Check if spot name appears in message (fuzzy match)
            # Remove common suffixes for matching
            spot_variants = [spot_name_lower]
            for suffix in [" - phú quốc", " - đà nẵng", " - hà nội", " - hội an"]:
                if spot_name_lower.endswith(suffix):
                    spot_variants.append(spot_name_lower.replace(suffix, ""))

            for variant in spot_variants:
                if variant in message_lower or message_lower in variant:
                    logger.info(f"🎯 Found specific spot in message: {spot_name}")
                    return spot_name

        # Also check database for spot names mentioned
        try:
            spots_col = self.mongo_manager.get_collection("spots_detailed")
            # Extract potential spot names from message (words with capital letters)
            import re

            potential_names = re.findall(
                r"[A-ZĐÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴ][a-zđàáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵ]+(?:\s+[A-ZĐÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴ]?[a-zđàáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵ]+)*",
                user_message,
            )

            for name in potential_names:
                if len(name) >= 4:  # Skip very short names
                    spot_doc = spots_col.find_one(
                        {"name": {"$regex": name, "$options": "i"}}
                    )
                    if spot_doc:
                        logger.info(
                            f"🎯 Found spot in DB matching message: {spot_doc.get('name')}"
                        )
                        return spot_doc.get("name")
        except Exception as e:
            logger.debug(f"DB lookup for specific spot failed: {e}")

        return None

    def _handle_single_spot_info(
        self, spot_name: str, context, user_message: str
    ) -> Dict[str, Any]:
        """
        Handle request for information about a SINGLE specific spot.
        """
        try:
            # Get full details from database
            spots_col = self.mongo_manager.get_collection("spots_detailed")
            spot_doc = spots_col.find_one(
                {"name": {"$regex": spot_name, "$options": "i"}}
            )

            if not spot_doc:
                return {
                    "reply": f"Xin lỗi, tôi không tìm thấy thông tin chi tiết về {spot_name}. 🙏",
                    "ui_type": "none",
                    "context": context.to_dict(),
                    "status": "success",
                }

            location = getattr(context, "destination", "địa điểm này")

            # Build detailed info
            name = spot_doc.get("name", spot_name)
            category = spot_doc.get("category") or (
                spot_doc.get("tags", ["Điểm tham quan"])[0]
                if spot_doc.get("tags")
                else "Điểm tham quan"
            )
            description = (
                spot_doc.get("description_full")
                or spot_doc.get("description")
                or spot_doc.get("description_short", "")
            )
            address = spot_doc.get("address", "")
            rating = spot_doc.get("rating")
            price = spot_doc.get("price") or spot_doc.get("entrance_fee")
            open_hours = spot_doc.get("open_hours") or spot_doc.get("opening_hours")
            tips = spot_doc.get("tips") or spot_doc.get("travel_tips")

            # Generate LLM response for this specific spot
            llm_response = None
            if self.llm:
                try:
                    spot_context = f"""
- Tên: {name}
- Loại: {category}
- Mô tả: {description[:500] if description else 'N/A'}
- Địa chỉ: {address or 'N/A'}
- Rating: {rating if rating else 'N/A'}
- Giá vé: {price if price else 'N/A'}
- Giờ mở cửa: {open_hours if open_hours else 'N/A'}
- Tips: {tips[:300] if tips else 'N/A'}
"""

                    prompt = f"""Bạn là hướng dẫn viên du lịch chuyên nghiệp. User hỏi về địa điểm cụ thể.

THÔNG TIN ĐỊA ĐIỂM:
{spot_context}

USER HỎI: "{user_message}"

YÊU CẦU:
- Giới thiệu chi tiết về địa điểm này (4-6 câu)
- Nhấn mạnh điểm đặc biệt, nổi bật
- Đưa ra gợi ý thời điểm tham quan tốt nhất
- Lưu ý khi đến (nếu có)
- Dùng emoji phù hợp
- Tối đa 250 từ
- QUAN TRỌNG: Chỉ nói về địa điểm này, KHÔNG nhắc đến địa điểm khác

TRẢ LỜI:"""

                    llm_response = self.llm.complete(
                        prompt, temperature=0.7, max_tokens=400
                    )
                except Exception as e:
                    logger.warning(f"LLM response for single spot failed: {e}")

            # Build reply
            rating_str = f"⭐ {rating:.1f}/5" if rating else ""

            if llm_response and len(llm_response.strip()) > 50:
                reply = f"📍 **{name}** {rating_str}\n\n{llm_response.strip()}"
            else:
                # Fallback template
                reply = f"📍 **{name}** {rating_str}\n\n"
                reply += f"📂 Loại: {category}\n"
                if description:
                    reply += f"📝 {description[:300]}{'...' if len(description) > 300 else ''}\n\n"
                if address:
                    reply += f"📍 Địa chỉ: {address}\n"
                if price:
                    reply += f"💰 Giá vé: {price}\n"
                if open_hours:
                    reply += f"🕐 Giờ mở cửa: {open_hours}\n"
                if tips:
                    reply += (
                        f"\n💡 Lưu ý: {tips[:200]}{'...' if len(tips) > 200 else ''}"
                    )

            # UI data for single spot card
            ui_data = {
                "spots": [
                    {
                        "id": str(spot_doc.get("_id", "")),
                        "name": name,
                        "description": description[:200] if description else "",
                        "category": category,
                        "rating": rating,
                        "address": address,
                        "image": spot_doc.get("image")
                        or (
                            spot_doc.get("images", [""])[0]
                            if spot_doc.get("images")
                            else None
                        ),
                        "price": price,
                        "open_hours": open_hours,
                    }
                ],
                "total_spots": 1,
                "location": location,
            }

            return {
                "reply": reply,
                "ui_type": "spot_detail",
                "ui_data": ui_data,
                "context": context.to_dict(),
                "status": "success",
            }

        except Exception as e:
            logger.error(f"❌ Single spot info error: {e}")
            import traceback

            traceback.print_exc()
            return {
                "reply": f"Xin lỗi, không thể lấy thông tin về {spot_name}. 🙏",
                "ui_type": "error",
                "context": context.to_dict(),
                "status": "error",
            }

    def _handle_spot_info_request_sync(
        self, context, user_message: str
    ) -> Dict[str, Any]:
        """
        Handle request for spot information (not tips)
        When user asks "giới thiệu về các địa điểm"
        """
        try:
            # Get spots from itinerary or last_spots
            spots_to_show = []

            # Priority 0: Check selected_spots (permanent memory) FIRST
            selected_spots = _get_context_value(context, "selected_spots", [])
            if selected_spots:
                logger.info(
                    f"📍 Using {len(selected_spots)} spots from selected_spots memory"
                )
                spots_to_show = selected_spots

            # Priority 1: Check itinerary builder
            if not spots_to_show:
                builder = _get_context_value(context, "itinerary_builder")
                if builder:
                    days_plan = (
                        builder.get("days_plan", {})
                        if isinstance(builder, dict)
                        else getattr(builder, "days_plan", {})
                    )
                    for day_num, day_spots in days_plan.items():
                        spots_to_show.extend(day_spots)

            # Priority 2: Check last_itinerary
            if not spots_to_show:
                last_itinerary = _get_context_value(context, "last_itinerary")
                if last_itinerary and isinstance(last_itinerary, dict):
                    for day in last_itinerary.get("days", []):
                        for activity in day.get("activities", []):
                            if activity.get("location"):
                                spots_to_show.append({"name": activity["location"]})

            # Priority 3: Fallback to last_spots
            if not spots_to_show:
                spots_to_show = _get_context_value(context, "last_spots", [])

            if not spots_to_show:
                return {
                    "reply": "Bạn chưa có địa điểm nào trong lịch trình. Hãy tìm địa điểm trước nhé! 🔍",
                    "ui_type": "none",
                    "context": context.to_dict(),
                    "status": "success",
                }

            # Get full details from database
            spots_col = self.mongo_manager.get_collection("spots_detailed")
            detailed_spots = []

            for spot in spots_to_show[:10]:  # Limit to 10
                spot_name = spot.get("name", "")
                if spot_name:
                    spot_doc = spots_col.find_one(
                        {"name": {"$regex": spot_name, "$options": "i"}}
                    )
                    if spot_doc:
                        # Get category with better fallback logic
                        category = spot_doc.get("category")
                        if not category or category == "None":
                            # Try to infer from tags
                            tags = spot_doc.get("tags", [])
                            if tags and len(tags) > 0:
                                category = tags[0]
                            else:
                                category = "Điểm tham quan"

                        # Get description with fallback logic
                        desc = (
                            spot_doc.get("description_short")
                            or spot_doc.get("description")
                            or spot_doc.get("description_full", "")[:300]
                            or "Địa điểm du lịch nổi tiếng"
                        )

                        detailed_spots.append(
                            {
                                "id": str(spot_doc.get("_id", "")),
                                "name": spot_doc.get("name", spot_name),
                                "description": desc,
                                "category": category,
                                "rating": spot_doc.get("rating"),
                                "address": spot_doc.get("address", ""),
                                "image": (
                                    spot_doc.get("image")
                                    or (
                                        spot_doc.get("images", [""])[0]
                                        if spot_doc.get("images")
                                        else None
                                    )
                                ),
                            }
                        )

            if not detailed_spots:
                return {
                    "reply": "Xin lỗi, tôi không tìm thấy thông tin chi tiết về các địa điểm này. 🙏",
                    "ui_type": "none",
                    "context": context.to_dict(),
                    "status": "success",
                }

            # Build response with spot cards
            location = getattr(context, "destination", "địa điểm này")

            # OPTION 1: Use LLM with RAG context for intelligent summary
            llm_intro = None
            if self.llm and len(detailed_spots) > 0:
                try:
                    # Build rich context for LLM
                    spots_context = []
                    for spot in detailed_spots:
                        spot_info = f"- **{spot['name']}** ({spot.get('category', 'Điểm tham quan')})"
                        if spot.get("rating"):
                            spot_info += f" | Rating: {spot['rating']:.1f}/5"
                        if spot.get("description"):
                            spot_info += f"\n  Mô tả: {spot['description'][:200]}"
                        if spot.get("address"):
                            spot_info += f"\n  Địa chỉ: {spot['address']}"
                        spots_context.append(spot_info)

                    rag_prompt = f"""Bạn là hướng dẫn viên du lịch chuyên nghiệp. Dựa trên thông tin chi tiết sau, hãy giới thiệu ngắn gọn về các địa điểm du lịch tại {location}.

NGỮ CẢNH:
- User đã chọn {len(detailed_spots)} địa điểm cho lịch trình du lịch
- Các địa điểm này đã được user lựa chọn và lưu vào lịch trình

THÔNG TIN CÁC ĐỊA ĐIỂM (từ Database):
{chr(10).join(spots_context)}

USER HỎI: "{user_message}"

YÊU CẦU:
- Giới thiệu tổng quan về {len(detailed_spots)} địa điểm user ĐÃ CHỌN (2-3 câu)
- Nhấn mạnh điểm đặc biệt của mỗi nơi
- Gợi ý thứ tự tham quan hợp lý
- Ngắn gọn, súc tích, dùng emoji
- Tối đa 200 từ
- Nhắc rõ "các địa điểm bạn đã chọn" để user biết đây là spots họ đã pick

GIỚI THIỆU:"""

                    logger.info(
                        f"🤖 [RAG] Generating LLM intro for {len(detailed_spots)} spots with DB context"
                    )
                    llm_intro = self.llm.complete(
                        rag_prompt, temperature=0.7, max_tokens=300
                    )

                    if llm_intro and len(llm_intro.strip()) > 30:
                        logger.info(
                            "✅ [RAG] LLM intro generated with database context"
                        )
                    else:
                        llm_intro = None

                except Exception as llm_error:
                    logger.warning(
                        f"⚠️ [RAG] LLM intro failed: {llm_error}, using template"
                    )
                    llm_intro = None

            # Build reply text
            if llm_intro:
                # Use LLM-generated intro with RAG context
                reply = f"📍 **Các địa điểm tại {location}**\n\n{llm_intro.strip()}\n\n"
                reply += f"━━━━━━━━━━━━━━━━━━━━\n\n"
                reply += f"**Chi tiết {len(detailed_spots)} địa điểm:**\n\n"
            else:
                # Fallback to template
                reply = f"📍 **Giới thiệu các địa điểm tại {location}**\n\n"
                reply += f"Bạn đã chọn {len(detailed_spots)} địa điểm tuyệt vời:\n\n"

            # List spots with details from DB
            for i, spot in enumerate(detailed_spots, 1):
                # Get category with fallback to tags
                category = spot.get("category")
                if not category or category == "None":
                    tags = spot.get("tags", [])
                    category = tags[0] if tags else "Điểm tham quan"

                # Get description with fallback (priority: description_short > description > description_full)
                raw_desc = (
                    spot.get("description_short")
                    or spot.get("description")
                    or spot.get("description_full", "")
                )
                description = (
                    raw_desc[:150] + "..." if len(raw_desc) > 150 else raw_desc
                )

                rating_str = f"⭐ {spot['rating']:.1f}/5" if spot.get("rating") else ""

                reply += f"**{i}. {spot['name']}** {rating_str}\n"
                # Only show category if it's not None/empty
                if category and category != "Điểm tham quan":
                    reply += f"📂 {category}\n"
                if description:
                    reply += f"{description}\n"
                reply += "\n"

            reply += "━━━━━━━━━━━━━━━━━━━━\n\n"
            reply += "💬 **Bạn muốn biết thêm?**\n\n"
            reply += "🔍 Gõ **'chi tiết về [tên địa điểm]'** để xem thông tin đầy đủ\n"
            reply += "💡 Gõ **'lưu ý gì'** để xem tips du lịch\n"
            reply += "🏨 Gõ **'tìm khách sạn'** để chọn nơi ở\n"

            return {
                "reply": reply,
                "ui_type": "spot_cards",
                "ui_data": {"spots": detailed_spots},
                "context": context.to_dict(),
                "status": "success",
            }

        except Exception as e:
            logger.error(f"❌ Spot info request error: {e}")
            import traceback

            traceback.print_exc()
            return {
                "reply": "Xin lỗi, không thể lấy thông tin địa điểm lúc này. Bạn hãy thử lại nhé! 🙏",
                "ui_type": "error",
                "context": context.to_dict(),
                "status": "error",
            }

    def _handle_detail_request_sync(
        self, multi_intent, context, user_message: str
    ) -> Optional[Dict[str, Any]]:
        """Handle get_detail intent synchronously - show detailed info about a spot/hotel"""
        try:
            entity_name = None
            entity_data = None
            entity_type = None

            # Get last shown spots and hotels from context
            last_spots = getattr(context, "last_spots", []) or []
            last_hotels = getattr(context, "last_hotels", []) or []

            message_lower = user_message.lower()

            # Check for ordinal references like "đầu tiên", "thứ 2", "số 1"
            ordinal_index = self._extract_ordinal_index(message_lower)
            if ordinal_index is not None:
                # User is referring to an item by position
                if last_spots and ordinal_index < len(last_spots):
                    entity_data = last_spots[ordinal_index]
                    entity_name = entity_data.get("name")
                    entity_type = "spot"
                    logger.info(
                        f"📍 Found by ordinal #{ordinal_index + 1}: {entity_name}"
                    )
                elif last_hotels and ordinal_index < len(last_hotels):
                    entity_data = last_hotels[ordinal_index]
                    entity_name = entity_data.get("name")
                    entity_type = "hotel"
                    logger.info(
                        f"🏨 Found by ordinal #{ordinal_index + 1}: {entity_name}"
                    )

            # Search in spots from context by name match
            if not entity_name:
                for spot in last_spots:
                    name = spot.get("name", "").lower()
                    if name and name in message_lower:
                        entity_name = spot.get("name")
                        entity_data = spot
                        entity_type = "spot"
                        break

            # Search in hotels if not found in spots
            if not entity_name:
                for hotel in last_hotels:
                    name = hotel.get("name", "").lower()
                    if name and name in message_lower:
                        entity_name = hotel.get("name")
                        entity_data = hotel
                        entity_type = "hotel"
                        break

            # If not found in context, search directly in database
            if not entity_name and self.mongo_manager:
                # Try to extract spot/hotel name from message
                keywords = multi_intent.keywords if multi_intent.keywords else []

                # Also try to extract entity name from "chi tiết về X" patterns
                extracted_name = self._extract_entity_name_from_message(user_message)
                if extracted_name and extracted_name not in keywords:
                    keywords = [extracted_name] + keywords

                for kw in keywords:
                    entity_data, entity_type = self._search_entity_in_db_sync(
                        kw.lower(), multi_intent.location
                    )
                    if entity_data:
                        entity_name = entity_data.get("name")
                        break

                # If still not found, try searching with location context
                if not entity_name and extracted_name and multi_intent.location:
                    entity_data, entity_type = self._search_entity_in_db_combined(
                        extracted_name, multi_intent.location
                    )
                    if entity_data:
                        entity_name = entity_data.get("name")

            if entity_name and entity_data:
                # Format detailed response
                detail_response = self._format_entity_detail_sync(
                    entity_name, entity_data, entity_type
                )
                detail_response["context"] = context.to_dict()
                return detail_response

            # Entity not found - provide helpful response
            location = multi_intent.location or getattr(context, "destination", None)
            return {
                "reply": f"Tôi chưa tìm thấy thông tin chi tiết về địa điểm này.\n\n"
                f"💡 Bạn có thể:\n"
                f"• Chọn từ danh sách địa điểm đã gợi ý\n"
                f"• Hỏi: 'Địa điểm tham quan ở {location or 'X'}'\n"
                f"• Hoặc nói rõ tên địa điểm bạn quan tâm",
                "ui_type": "none",
                "context": context.to_dict(),
                "status": "partial",
            }

        except Exception as e:
            logger.error(f"❌ Detail request error: {e}")
            import traceback

            traceback.print_exc()
            return None

    def _search_entity_in_db_sync(
        self, search_phrase: str, location: str = None
    ) -> tuple:
        """Search for entity in database synchronously

        Supports both Vietnamese diacritics and non-diacritic (ASCII) search.
        Uses unidecode for normalization when direct regex fails.
        """
        if not self.mongo_manager:
            return None, None

        try:
            from unidecode import unidecode
        except ImportError:
            unidecode = None

        # Normalize search phrase
        search_lower = search_phrase.lower().strip()
        search_normalized = unidecode(search_lower) if unidecode else search_lower

        # Try spots collection first
        spots_col = self.mongo_manager.get_collection("spots_detailed")
        if spots_col is not None:
            # First try: direct regex match
            spot = spots_col.find_one(
                {"name": {"$regex": search_phrase, "$options": "i"}}
            )

            # Second try: search with normalized comparison (for non-diacritic queries)
            if not spot and unidecode:
                # Get candidates from location if available
                query = {}
                if location:
                    # Normalize location to province_id format
                    province_id = location.lower().replace(" ", "-")
                    province_id = unidecode(province_id).replace(" ", "-")
                    query["province_id"] = province_id

                # Search through candidates
                candidates = spots_col.find(query).limit(500)
                for candidate in candidates:
                    name = candidate.get("name", "")
                    name_normalized = unidecode(name.lower())
                    # Check if search phrase is contained in normalized name
                    if search_normalized in name_normalized:
                        spot = candidate
                        logger.info(
                            f"✅ Found spot via normalized search: '{search_phrase}' -> '{name}'"
                        )
                        break

            if spot:
                spot = _clean_mongo_doc(spot)
                logger.info(f"✅ Found spot in DB: {spot.get('name')}")
                return spot, "spot"

        # Try hotels collection
        hotels_col = self.mongo_manager.get_collection("hotels")
        if hotels_col is not None:
            # First try: direct regex match
            hotel = hotels_col.find_one(
                {"name": {"$regex": search_phrase, "$options": "i"}}
            )

            # Second try: normalized search
            if not hotel and unidecode:
                query = {}
                if location:
                    province_id = location.lower().replace(" ", "-")
                    province_id = unidecode(province_id).replace(" ", "-")
                    query["province_id"] = province_id

                candidates = hotels_col.find(query).limit(500)
                for candidate in candidates:
                    name = candidate.get("name", "")
                    name_normalized = unidecode(name.lower())
                    if search_normalized in name_normalized:
                        hotel = candidate
                        logger.info(
                            f"✅ Found hotel via normalized search: '{search_phrase}' -> '{name}'"
                        )
                        break

            if hotel:
                hotel = _clean_mongo_doc(hotel)
                logger.info(f"✅ Found hotel in DB: {hotel.get('name')}")
                return hotel, "hotel"

        return None, None

    def _extract_entity_name_from_message(self, message: str) -> Optional[str]:
        """Extract entity name from 'chi tiết về X' pattern"""
        import re

        # Patterns to extract entity name (both with and without Vietnamese diacritics)
        patterns = [
            # With diacritics
            r"chi tiết về (.+?)(?:\s+ở\s+|\s+tại\s+|\s*$)",
            r"thông tin về (.+?)(?:\s+ở\s+|\s+tại\s+|\s*$)",
            r"cho tôi biết về (.+?)(?:\s+ở\s+|\s+tại\s+|\s*$)",
            r"nói về (.+?)(?:\s+ở\s+|\s+tại\s+|\s*$)",
            r"giới thiệu về (.+?)(?:\s+ở\s+|\s+tại\s+|\s*$)",
            # Without diacritics
            r"chi tiet ve (.+?)(?:\s+o\s+|\s+tai\s+|\s*$)",
            r"thong tin ve (.+?)(?:\s+o\s+|\s+tai\s+|\s*$)",
            r"cho toi biet ve (.+?)(?:\s+o\s+|\s+tai\s+|\s*$)",
            r"noi ve (.+?)(?:\s+o\s+|\s+tai\s+|\s*$)",
            r"gioi thieu ve (.+?)(?:\s+o\s+|\s+tai\s+|\s*$)",
        ]

        message_lower = message.lower()
        for pattern in patterns:
            match = re.search(pattern, message_lower, re.IGNORECASE)
            if match:
                entity_name = match.group(1).strip()
                # Remove trailing punctuation
                entity_name = entity_name.rstrip(",.?!")
                logger.info(f"📝 Extracted entity name: '{entity_name}' from message")
                return entity_name

        return None

    def _search_entity_in_db_combined(self, entity_name: str, location: str) -> tuple:
        """
        [UPGRADED] Search using Hybrid Engine (Semantic + Keyword)
        Tìm kiếm thông minh: Lọc cứng theo tỉnh -> Semantic Search
        """
        # Nếu Hybrid Search chưa load được, fallback về hàm sync cũ (Regex)
        if not self.hybrid_search:
            logger.warning("⚠️ Hybrid search not available, fallback to regex")
            return self._search_entity_in_db_sync(entity_name, location)

        # Chuẩn hóa location để lọc cứng (VD: "Đà Nẵng" -> "da-nang")
        province_id = None
        if location:
            import unicodedata

            # Normalize location to slug format
            province_id = location.lower().strip()
            # Manual replacements for Vietnamese letters not handled by NFD
            province_id = province_id.replace("đ", "d")
            # Remove Vietnamese diacritics
            province_id = "".join(
                c
                for c in unicodedata.normalize("NFD", province_id)
                if unicodedata.category(c) != "Mn"
            )
            # Replace spaces with hyphens
            province_id = province_id.replace(" ", "-")

        logger.info(f"🔍 Hybrid Searching for '{entity_name}' in '{province_id}'...")

        # 1. Ưu tiên tìm trong SPOTS
        spots = self.hybrid_search.search_spots(
            query=entity_name,
            province_id=province_id,
            limit=1,
            threshold=0.25,  # Lower threshold for broader matching
        )

        if spots:
            best_spot = spots[0]
            logger.info(
                f"✅ Hybrid found spot: {best_spot.get('name')} (Score: {best_spot.get('score', 0):.3f})"
            )
            return _clean_mongo_doc(best_spot), "spot"

        # 2. Nếu không có Spot, tìm trong HOTELS
        hotels = self.hybrid_search.search_hotels(
            query=entity_name,
            province_id=province_id,
            limit=1,
            threshold=0.25,  # Lower threshold for broader matching
        )

        if hotels:
            best_hotel = hotels[0]
            logger.info(
                f"✅ Hybrid found hotel: {best_hotel.get('name')} (Score: {best_hotel.get('score', 0):.3f})"
            )
            return _clean_mongo_doc(best_hotel), "hotel"

        logger.info(f"❌ Hybrid search found nothing for '{entity_name}'")
        return None, None

    def _format_entity_detail_sync(
        self, name: str, data: dict, entity_type: str
    ) -> Dict[str, Any]:
        """Format detailed entity information synchronously"""
        if entity_type == "spot":
            # Check multiple possible description fields (based on actual DB structure)
            description = (
                data.get("description_full")
                or data.get("description")
                or data.get("introduction")
                or data.get("teaser_review")
                or data.get("description_short")
                or "Điểm tham quan hấp dẫn"
            )
            address = data.get("address") or data.get("location") or ""
            rating = data.get("rating") or 4.0
            category = data.get("category") or "Địa điểm tham quan"
            reviews_count = data.get("reviews_count", 0)
            image = data.get("image", "")
            url = data.get("url", "")

            reply = f"📍 **{name}**\n\n"
            reply += f"📝 **Mô tả:**\n{description}\n\n"
            if address:
                reply += f"📌 **Địa chỉ:** {address}\n"
            if rating and rating > 0:
                reply += f"⭐ **Đánh giá:** {rating}/5"
                if reviews_count:
                    reply += f" ({reviews_count:,} đánh giá)"
                reply += "\n"
            if category and category != "None":
                reply += f"🏷️ **Loại:** {category}\n"
            if url:
                reply += f"🔗 **Xem thêm:** [Chi tiết]({url})\n"
            reply += (
                f"\n💡 *Bạn có muốn xem thêm địa điểm khác hoặc lên lịch trình không?*"
            )

            return {
                "reply": reply,
                "ui_type": "spot_detail",
                "ui_data": {"name": name, "type": "spot", "image": image, "data": data},
                "status": "complete",
            }

        elif entity_type == "hotel":
            price = data.get("price", 0)
            address = data.get("address", "")
            rating = data.get("rating", 4.0)
            amenities = data.get("amenities", [])

            reply = f"🏨 **{name}**\n\n"
            if price:
                reply += f"💵 **Giá:** {price:,} VNĐ/đêm\n"
            if address:
                reply += f"📌 **Địa chỉ:** {address}\n"
            reply += f"⭐ **Đánh giá:** {rating}/10\n"
            if amenities:
                reply += f"🛎️ **Tiện ích:** {', '.join(amenities[:5])}\n"
            reply += f"\n💡 *Bạn có muốn đặt phòng tại đây không? Hỏi: 'Đặt phòng tại {name}'*"

            return {
                "reply": reply,
                "ui_type": "hotel_detail",
                "ui_data": {"name": name, "type": "hotel", "data": data},
                "status": "complete",
            }

        return {
            "reply": f"📌 **{name}**\n\n{data.get('description', 'Không có mô tả')}",
            "ui_type": "detail",
            "status": "complete",
        }

    async def _handle_special_intent(
        self, multi_intent, context, user_message: str
    ) -> Optional[Dict[str, Any]]:
        """
        Handle special intents that don't require task planning

        Returns response dict or None if normal processing should continue
        """
        intent = multi_intent.primary_intent
        workflow_state = getattr(context, "workflow_state", None)

        # === CHECK FOR ITINERARY BUILDER STATE FIRST ===
        # If user is in the middle of interactive itinerary building
        # FIX 2026-01-18: Skip builder mode if workflow_state is FINALIZED
        # When FINALIZED, user should be able to ask other questions without triggering builder
        if (
            hasattr(context, "itinerary_builder")
            and context.itinerary_builder
            and workflow_state != "FINALIZED"
        ):
            # FIX #3 & #4: Allow calculate_cost and distance queries even in builder mode
            if intent == "calculate_cost":
                logger.info(
                    "[FIX #3 ASYNC] 🎯 calculate_cost in builder mode - handling separately"
                )
                return self._handle_cost_calculation_sync(
                    multi_intent, context, user_message
                )

            if intent in ["get_distance", "get_directions"] or self._is_distance_query(
                user_message
            ):
                logger.info(
                    "[FIX #4 ASYNC] 📏 Distance query in builder mode - handling separately"
                )
                return self._handle_distance_query_sync(
                    multi_intent, context, user_message
                )

            # FIX 2026-01-18: Allow weather queries even in builder mode
            if intent == "get_weather_forecast":
                logger.info(
                    "[FIX] 🌤️ Weather query in builder mode - handling separately"
                )
                return self._handle_weather_sync(multi_intent, context, user_message)

            # FIX 2026-01-18: Allow show_itinerary to recall spots info in builder mode
            if intent == "show_itinerary" or self._is_recall_itinerary_request(
                user_message
            ):
                logger.info(
                    "[FIX] 📋 Show itinerary request in builder mode - handling separately"
                )
                return self._handle_recall_itinerary(context)

            logger.info(
                "🗓️ [ASYNC] User in itinerary builder mode, processing selection..."
            )
            builder_response = self._continue_interactive_itinerary_sync(
                user_message, context
            )
            if builder_response:
                return builder_response

        # === GREETING ===
        if intent == "greeting":
            # Use conversational LLM for natural greeting
            llm_response = self._handle_conversational_chat(
                user_message, context, intent_type="greeting"
            )
            if llm_response:
                return llm_response

            # Fallback template
            return {
                "reply": "Xin chào! 👋 Tôi là Saola - trợ lý du lịch AI của bạn. "
                "Tôi có thể giúp bạn:\n"
                "• 🗺️ Lên lịch trình du lịch\n"
                "• 🏨 Tìm khách sạn phù hợp\n"
                "• 📍 Gợi ý địa điểm tham quan\n"
                "• 🍜 Khám phá ẩm thực địa phương\n"
                "• 💰 Ước tính chi phí chuyến đi\n\n"
                "Bạn muốn đi đâu? 🌍",
                "ui_type": "greeting",
                "context": context.to_dict(),
                "status": "partial",
            }

        # === CHITCHAT / OFF-TOPIC ===
        if intent == "chitchat":
            # Use conversational LLM for natural chitchat
            llm_response = self._handle_conversational_chat(
                user_message, context, intent_type="chitchat"
            )
            if llm_response:
                return llm_response

            # Fallback template
            return {
                "reply": "Tôi là Saola - trợ lý du lịch AI! 🦌\n\n"
                "Tôi chuyên về du lịch Việt Nam và có thể giúp bạn:\n"
                "• Lên kế hoạch chuyến đi\n"
                "• Tìm khách sạn tốt nhất\n"
                "• Gợi ý điểm đến hấp dẫn\n\n"
                "Hãy cho tôi biết bạn muốn đi đâu nhé! 🗺️",
                "ui_type": "chitchat",
                "context": context.to_dict(),
                "status": "partial",
            }

        # === THANKS ===
        if intent == "thanks":
            # Use conversational LLM for natural thanks response
            llm_response = self._handle_conversational_chat(
                user_message, context, intent_type="thanks"
            )
            if llm_response:
                return llm_response

            return {
                "reply": "Không có gì ạ! 😊 Rất vui được giúp đỡ bạn. "
                "Nếu cần hỗ trợ thêm về chuyến đi, cứ hỏi tôi nhé! ✈️",
                "ui_type": "thanks",
                "context": context.to_dict(),
                "status": "partial",
            }

        # === FAREWELL ===
        if intent == "farewell":
            # Use conversational LLM for natural farewell
            llm_response = self._handle_conversational_chat(
                user_message, context, intent_type="farewell"
            )
            if llm_response:
                return llm_response

            return {
                "reply": "Tạm biệt bạn! 👋 Chúc bạn có chuyến đi thật vui vẻ! "
                "Hẹn gặp lại lần sau! 🌟",
                "ui_type": "farewell",
                "context": context.to_dict(),
                "status": "partial",
            }

        # === WEATHER FORECAST ===
        if intent == "get_weather_forecast":
            logger.info("🌤️ Weather forecast request detected")
            return self._handle_weather_sync(multi_intent, context, user_message)

        # === SHOW ITINERARY (RECALL) ===
        if intent == "show_itinerary" or self._is_recall_itinerary_request(
            user_message
        ):
            logger.info("📋 Show itinerary request detected")
            return self._handle_recall_itinerary(context)

        # === BOOKING REQUEST ===
        if intent == "book_hotel":
            try:
                hotel_name = multi_intent.keywords[0] if multi_intent.keywords else None
                location = getattr(context, "destination", None)

                logger.info(
                    f"📍 Book hotel request: hotel_name={hotel_name}, location={location}"
                )
                logger.info(f"📍 Keywords from intent: {multi_intent.keywords}")

                if hotel_name:
                    # Store selected hotel in context
                    context.selected_hotel = hotel_name

                    # Try to get hotel URL and price from database
                    hotel_url = None
                    hotel_price = None

                    # First, try to find hotel in last_hotels context (from previous search)
                    if hasattr(context, "last_hotels") and context.last_hotels:
                        for hotel in context.last_hotels:
                            hotel_name_in_list = hotel.get("name", "")
                            if (
                                hotel_name.lower() in hotel_name_in_list.lower()
                                or hotel_name_in_list.lower() in hotel_name.lower()
                            ):
                                hotel_price = hotel.get("price")
                                hotel_url = hotel.get("url")
                                logger.info(
                                    f"✅ Found hotel in context.last_hotels: {hotel_name_in_list}, price: {hotel_price}"
                                )
                                break

                    # If not found in context, search database
                    if not hotel_price and self.mongo_manager:
                        hotels_col = self.mongo_manager.get_collection("hotels")
                        if hotels_col is not None:
                            # Search for hotel by name (partial match with first word)
                            first_word = (
                                hotel_name.split()[0]
                                if hotel_name.split()
                                else hotel_name
                            )
                            hotel_doc = hotels_col.find_one(
                                {"name": {"$regex": first_word, "$options": "i"}}
                            )
                            if hotel_doc:
                                hotel_url = hotel_doc.get("url")
                                hotel_price = hotel_doc.get("price")
                                logger.info(
                                    f"✅ Found hotel in DB: {hotel_doc.get('name')}"
                                )
                            else:
                                logger.info(
                                    f"⚠️ Hotel not found in DB, using search links only"
                                )

                    # Save selected hotel price to context for cost calculation
                    if hotel_price:
                        context.selected_hotel_price = hotel_price
                        logger.info(
                            f"💰 Saved selected_hotel_price to context: {hotel_price:,} VNĐ"
                        )

                    # Build booking response with links
                    booking_links = []
                    if hotel_url:
                        booking_links.append(
                            f"🔗 [Đặt phòng tại website gốc]({hotel_url})"
                        )

                    # Add search links for popular booking sites
                    search_name = hotel_name.replace(" ", "+")
                    booking_links.extend(
                        [
                            f"🔗 [Tìm trên Booking.com](https://www.booking.com/searchresults.html?ss={search_name})",
                            f"🔗 [Tìm trên Agoda](https://www.agoda.com/search?q={search_name})",
                            f"🔗 [Tìm trên Traveloka](https://www.traveloka.com/vi-vn/hotel/search?q={search_name})",
                        ]
                    )

                    price_info = (
                        f"\n💰 Giá tham khảo: **{hotel_price:,} VNĐ/đêm**"
                        if hotel_price
                        else ""
                    )

                    return {
                        "reply": f"🏨 **Đặt phòng: {hotel_name}**{price_info}\n\n"
                        f"📱 **Cách đặt phòng:**\n"
                        f"{chr(10).join(booking_links)}\n\n"
                        f"💡 **Lưu ý khi đặt phòng:**\n"
                        f"• So sánh giá giữa các trang để tìm ưu đãi tốt nhất\n"
                        f"• Kiểm tra chính sách hủy phòng trước khi đặt\n"
                        f"• Đọc review gần đây từ khách hàng\n\n"
                        f"Bạn cần tôi ước tính chi phí toàn bộ chuyến đi không? 💰",
                        "ui_type": "booking",
                        "ui_data": {
                            "selected_hotel": hotel_name,
                            "hotel_url": hotel_url,
                            "hotel_price": hotel_price,
                            "booking_links": booking_links,
                        },
                        "status": "partial",
                        "context": context.to_dict(),
                    }
                else:
                    return {
                        "reply": "Bạn muốn đặt phòng khách sạn nào? 🏨\n"
                        "Hãy cho tôi biết tên khách sạn bạn quan tâm!",
                        "ui_type": "booking_prompt",
                        "context": context.to_dict(),
                        "status": "partial",
                    }
            except Exception as e:
                logger.error(f"❌ Book hotel error: {e}")
                import traceback

                traceback.print_exc()
                return {
                    "reply": f"🏨 Tôi ghi nhận bạn muốn đặt phòng.\n\n"
                    f"Bạn có thể tìm kiếm khách sạn trên:\n"
                    f"• [Booking.com](https://www.booking.com)\n"
                    f"• [Agoda](https://www.agoda.com)\n"
                    f"• [Traveloka](https://www.traveloka.com)\n\n"
                    f"Hoặc cho tôi biết tên khách sạn cụ thể bạn muốn đặt!",
                    "ui_type": "booking",
                    "context": context.to_dict(),
                    "status": "partial",
                }

        # === COST CALCULATION (context-aware) ===
        if intent == "calculate_cost":
            return await self._handle_cost_from_context(
                context, multi_intent, user_message
            )

        # === LOCATION TIPS (get_location_tips intent) ===
        if intent == "get_location_tips":
            logger.info("💡 [ASYNC] get_location_tips detected - providing tips")
            try:
                tips_response = self._handle_location_tips_sync(
                    multi_intent, context, user_message
                )
                logger.info(
                    f"📊 Tips response status: {tips_response.get('status') if tips_response else 'None'}"
                )
                if tips_response:
                    return tips_response
                else:
                    logger.warning(
                        "⚠️ Tips response is None, continuing to other handlers"
                    )
            except Exception as e:
                logger.error(f"❌ Error in tips handler: {e}")
                import traceback

                traceback.print_exc()

        # === LOCATION DETAILS - Show info about all spots in itinerary ===
        if intent == "get_location_details":
            # Check if this is asking for ALL spots (not a specific one)
            message_lower = user_message.lower()
            is_plural = any(
                word in message_lower
                for word in [
                    "các địa điểm",
                    "tất cả",
                    "từng địa điểm",
                    "những địa điểm",
                    "all",
                ]
            )

            if is_plural:
                logger.info(
                    "📍 [ASYNC] get_location_details (plural) - showing all spots"
                )
                # Reuse spot info handler (same as "giới thiệu về các địa điểm")
                info_response = self._handle_spot_info_request_sync(
                    context, user_message
                )
                if info_response:
                    return info_response

        # === GET DETAIL - User asking about specific spot/hotel ===
        if self._is_detail_request(user_message, context):
            return await self._handle_get_detail(user_message, context, multi_intent)

        # === BREAKDOWN - User wants cost breakdown by day ===
        if self._is_breakdown_request(user_message):
            return await self._handle_breakdown(context, multi_intent)

        # === CUSTOMIZE ITINERARY PER DAY - User specifies activities per day ===
        day_preferences = self._parse_day_preferences(user_message)
        if day_preferences:
            return await self._handle_customize_itinerary(
                day_preferences, context, multi_intent
            )

        # === REGION SEARCH - "Miền nam", "Miền bắc", etc. ===
        region = self._extract_region(user_message)
        if region:
            return await self._handle_region_search(region, context)

        # === RECALL ITINERARY - "Xem lại lịch trình", "Lịch trình của tôi" ===
        if self._is_recall_itinerary_request(user_message):
            return self._handle_recall_itinerary(context)

        # Not a special intent - continue normal processing
        return None

    def _parse_day_preferences(self, message: str) -> Optional[Dict[int, Dict]]:
        """
        Parse user's day-by-day preferences from message.

        Examples:
            "Ngày 1 muốn đi Cầu Rồng, Ngày 2 muốn đi Biển ăn hải sản, ngày 3 muốn đi chùa"
            -> {1: {"raw": "cầu rồng", "keywords": []},
                2: {"raw": "biển ăn hải sản", "keywords": ["hải sản"]},
                3: {"raw": "chùa", "keywords": []}}
        """
        import re

        message_lower = message.lower()

        # Best pattern: lookahead for next "ngày" or end of string
        # Handles comma/space separators and optional "muốn đi"
        day_pattern = (
            r"ngày\s*(\d+)\s*[:\s]*(?:muốn\s*)?(?:đi\s*)?(.+?)(?=,?\s*ngày\s*\d+|$)"
        )
        day_matches = re.findall(day_pattern, message_lower)

        if len(day_matches) < 2:  # Need at least 2 days to be considered day-specific
            return None

        preferences = {}

        for day_num_str, content in day_matches:
            day_num = int(day_num_str)
            content = content.strip().rstrip(",").strip()

            # Extract keywords
            keywords = []

            # Extract food keywords
            food_keywords = ["hải sản", "bún", "phở", "mì", "bánh", "ăn"]
            for kw in food_keywords:
                if kw in content:
                    keywords.append(kw)

            preferences[day_num] = {
                "raw": content,
                "activities": [content],
                "keywords": keywords,
            }

        return preferences if preferences else None

    async def _handle_customize_itinerary(
        self, day_preferences: Dict[int, Dict], context, multi_intent
    ) -> Dict[str, Any]:
        """
        Handle user request to customize itinerary per day.
        Search for relevant spots/hotels based on their preferences for each day.
        """
        location = (
            multi_intent.location or getattr(context, "destination", None) or "Đà Nẵng"
        )
        duration = len(day_preferences)

        # Update context
        context.destination = location
        context.duration = duration

        logger.info(f"🗓️ Customizing itinerary for {duration} days at {location}")
        logger.info(f"📋 Day preferences: {day_preferences}")

        # Build customized itinerary
        customized_days = []
        daily_costs = []

        for day_num in sorted(day_preferences.keys()):
            pref = day_preferences[day_num]
            raw_pref = pref.get("raw", "")
            keywords = pref.get("keywords", [])

            day_result = await self._build_day_itinerary(
                day_num=day_num,
                preference=raw_pref,
                keywords=keywords,
                location=location,
                is_last_day=(day_num == max(day_preferences.keys())),
                context=context,
            )

            customized_days.append(day_result)
            # Keep day number in cost
            cost_with_day = day_result.get("cost", {}).copy()
            cost_with_day["day"] = day_num
            daily_costs.append(cost_with_day)

        # Format response
        response_text = self._format_customized_itinerary(
            location=location, days=customized_days, daily_costs=daily_costs
        )

        # Update context with new itinerary
        context.last_itinerary = {"days": customized_days}

        return {
            "reply": response_text,
            "ui_type": "custom_itinerary",
            "ui_data": {
                "itinerary": customized_days,
                "daily_costs": daily_costs,
                "location": location,
                "duration": duration,
            },
            "context": context.to_dict(),
            "status": "complete",
        }

    async def _build_day_itinerary(
        self,
        day_num: int,
        preference: str,
        keywords: List[str],
        location: str,
        is_last_day: bool,
        context,
    ) -> Dict:
        """Build itinerary for a single day based on user preference"""

        day_data = {
            "day": day_num,
            "preference": preference,
            "spots": [],
            "hotel": None,
            "food": [],
            "cost": {
                "accommodation": 0,
                "activities": 0,
                "food": 0,
                "transport": 0,
                "total": 0,
            },
        }

        # Search for relevant spots based on preference
        spots = await self._search_spots_by_preference(preference, location)
        if spots:
            day_data["spots"] = spots[:2]  # Max 2 spots per day
            # Calculate activity cost
            for spot in day_data["spots"]:
                day_data["cost"]["activities"] += self._estimate_spot_cost(spot)

        # Search for food if mentioned
        if any(kw in preference for kw in ["ăn", "hải sản", "quán", "món"]):
            food = await self._search_food_by_preference(keywords, location)
            if food:
                day_data["food"] = food[:1]

        # Accommodation
        accommodation_type = self._detect_accommodation_from_preference(
            preference, is_last_day
        )
        if accommodation_type == "hotel":
            # Get default hotel price
            default_prices = self._get_location_default_prices(location)
            day_data["cost"]["accommodation"] = default_prices["hotel"]
            day_data["accommodation_note"] = "Khách sạn"
        elif accommodation_type == "friend":
            day_data["cost"]["accommodation"] = 0
            day_data["accommodation_note"] = "Ở nhà bạn bè"
        else:
            day_data["cost"]["accommodation"] = 0
            day_data["accommodation_note"] = "Về nhà"

        # Food cost
        default_prices = self._get_location_default_prices(location)
        if "hải sản" in preference:
            day_data["cost"]["food"] = (
                default_prices["food"] * 1.5
            )  # Seafood is more expensive
        else:
            day_data["cost"]["food"] = default_prices["food"]

        # Transport cost
        day_data["cost"]["transport"] = default_prices["transport"]
        if day_num == 1 or is_last_day:
            day_data["cost"]["transport"] *= 1.5  # First/last day has more travel

        # Calculate total
        day_data["cost"]["total"] = (
            day_data["cost"]["accommodation"]
            + day_data["cost"]["activities"]
            + day_data["cost"]["food"]
            + day_data["cost"]["transport"]
        )

        return day_data

    async def _search_spots_by_preference(
        self, preference: str, location: str
    ) -> List[Dict]:
        """Search for spots matching user preference"""
        if not self.mongo_manager:
            return []

        try:
            spots_col = self.mongo_manager.get_collection("spots_detailed")

            # Build search query
            search_terms = preference.lower().split()

            # Try exact match first
            for term in search_terms:
                if len(term) >= 3:
                    spots = list(
                        spots_col.find(
                            {
                                "$and": [
                                    {"name": {"$regex": term, "$options": "i"}},
                                    {
                                        "$or": [
                                            {
                                                "address": {
                                                    "$regex": location,
                                                    "$options": "i",
                                                }
                                            },
                                            {
                                                "province": {
                                                    "$regex": location,
                                                    "$options": "i",
                                                }
                                            },
                                        ]
                                    },
                                ]
                            }
                        ).limit(3)
                    )

                    if spots:
                        return [_clean_mongo_doc(s) for s in spots]

            # Fallback: search by location only
            spots = list(
                spots_col.find(
                    {
                        "$or": [
                            {"address": {"$regex": location, "$options": "i"}},
                            {"province": {"$regex": location, "$options": "i"}},
                        ]
                    }
                ).limit(3)
            )

            return [_clean_mongo_doc(s) for s in spots]

        except Exception as e:
            logger.error(f"❌ Error searching spots: {e}")
            return []

    async def _search_food_by_preference(
        self, keywords: List[str], location: str
    ) -> List[Dict]:
        """Search for food/restaurants matching keywords"""
        # Return food suggestions based on keywords
        food_suggestions = []

        if "hải sản" in keywords:
            food_suggestions.append(
                {
                    "name": f"Nhà hàng hải sản {location}",
                    "type": "seafood",
                    "estimated_price": 400_000,
                }
            )

        return food_suggestions

    def _detect_accommodation_from_preference(
        self, preference: str, is_last_day: bool
    ) -> str:
        """Detect accommodation type from preference"""
        pref_lower = preference.lower()

        if any(kw in pref_lower for kw in ["nhà bạn", "bạn bè", "ở nhờ"]):
            return "friend"
        elif is_last_day or any(
            kw in pref_lower for kw in ["về nhà", "về", "kết thúc"]
        ):
            return "home"
        else:
            return "hotel"

    def _estimate_spot_cost(self, spot: Dict) -> int:
        """Estimate entrance cost for a spot"""
        name_lower = spot.get("name", "").lower()

        # Paid attractions
        if any(kw in name_lower for kw in ["vinpearl", "bà nà", "sun world"]):
            return 800_000
        elif any(kw in name_lower for kw in ["bảo tàng", "museum"]):
            return 50_000
        elif any(kw in name_lower for kw in ["chùa", "đền", "miếu"]):
            return 0  # Free
        elif any(kw in name_lower for kw in ["biển", "bãi"]):
            return 0  # Free
        else:
            return 100_000  # Default

    def _format_customized_itinerary(
        self, location: str, days: List[Dict], daily_costs: List[Dict]
    ) -> str:
        """Format customized itinerary as markdown"""

        total_cost = sum(d.get("cost", {}).get("total", 0) for d in days)

        text = f"🗓️ **Lịch trình {len(days)} ngày tại {location}** (theo yêu cầu của bạn)\n\n"

        for day in days:
            day_num = day["day"]
            preference = day.get("preference", "")
            spots = day.get("spots", [])
            cost = day.get("cost", {})
            accommodation_note = day.get("accommodation_note", "")

            text += f"**📅 Ngày {day_num}:** _{preference}_\n"

            # Morning
            if spots:
                text += f"  • 09:00 - {spots[0].get('name', 'Tham quan')}\n"

            text += f"  • 12:00 - Ăn trưa\n"

            # Afternoon
            if len(spots) > 1:
                text += f"  • 14:00 - {spots[1].get('name', 'Tham quan')}\n"
            elif day.get("food"):
                text += (
                    f"  • 14:00 - {day['food'][0].get('name', 'Thưởng thức ẩm thực')}\n"
                )

            text += f"  • 18:00 - Ăn tối\n"

            # Accommodation
            if accommodation_note:
                text += f"  • 🏨 {accommodation_note}\n"

            # Day cost
            text += (
                f"  💰 **Chi phí ngày {day_num}: {cost.get('total', 0):,.0f} VNĐ**\n"
            )
            text += f"     _(Lưu trú: {cost.get('accommodation', 0):,.0f} | "
            text += f"Ăn uống: {cost.get('food', 0):,.0f} | "
            text += f"Tham quan: {cost.get('activities', 0):,.0f} | "
            text += f"Di chuyển: {cost.get('transport', 0):,.0f})_\n\n"

        text += f"{'─'*40}\n"
        text += f"💵 **TỔNG CHI PHÍ: {total_cost:,.0f} VNĐ**\n\n"
        text += f"💡 _Bạn muốn thay đổi điểm đến nào không? Hoặc tôi tìm khách sạn phù hợp cho từng ngày?_"

        return text

    def _is_detail_request(self, message: str, context) -> bool:
        """Check if user is asking for details about something"""
        detail_keywords = [
            "chi tiết",
            "thông tin",
            "cho biết về",
            "kể về",
            "nói về",
            "tôi quan tâm",
            "muốn biết thêm",
            "biết thêm",
            "giới thiệu về",
            "thế nào",
            "ra sao",
            "như thế nào",
            "cho tôi biết",
        ]
        message_lower = message.lower()
        return any(kw in message_lower for kw in detail_keywords)

    def _extract_location_and_duration_from_query(self, query: str) -> tuple:
        """
        Extract location and duration from a query string.

        Examples:
            "Đi Đà Nẵng 3 ngày hết bao nhiêu?" -> ("Đà Nẵng", 3)
            "Du lịch Phú Quốc 5 ngày chi phí?" -> ("Phú Quốc", 5)
        """
        import re

        query_lower = query.lower()

        # Known locations
        locations = {
            "đà nẵng": "Đà Nẵng",
            "da nang": "Đà Nẵng",
            "hội an": "Hội An",
            "hoi an": "Hội An",
            "nha trang": "Nha Trang",
            "phú quốc": "Phú Quốc",
            "phu quoc": "Phú Quốc",
            "đà lạt": "Đà Lạt",
            "da lat": "Đà Lạt",
            "sapa": "Sapa",
            "sa pa": "Sapa",
            "huế": "Huế",
            "hue": "Huế",
            "hà nội": "Hà Nội",
            "ha noi": "Hà Nội",
            "hạ long": "Hạ Long",
            "ha long": "Hạ Long",
            "ninh bình": "Ninh Bình",
            "quy nhơn": "Quy Nhơn",
            "cần thơ": "Cần Thơ",
            "vũng tàu": "Vũng Tàu",
            "bến tre": "Bến Tre",
            "tp.hcm": "TP.HCM",
            "tp hcm": "TP.HCM",
            "sài gòn": "TP.HCM",
            "hà giang": "Hà Giang",
            "cao bằng": "Cao Bằng",
            "buôn ma thuột": "Buôn Ma Thuột",
            "pleiku": "Pleiku",
        }

        # Find location
        found_location = None
        for key, value in locations.items():
            if key in query_lower:
                found_location = value
                break

        # Extract duration (number + ngày/đêm)
        duration = None
        duration_match = re.search(r"(\d+)\s*(?:ngày|đêm)", query_lower)
        if duration_match:
            duration = int(duration_match.group(1))

        return found_location, duration

    def _is_breakdown_request(self, message: str) -> bool:
        """Check if user wants cost breakdown"""
        breakdown_keywords = [
            "mỗi ngày",
            "từng ngày",
            "chi tiết chi phí",
            "phân tích",
            "chia ra",
            "breakdown",
            "cụ thể từng",
        ]
        message_lower = message.lower()
        return any(kw in message_lower for kw in breakdown_keywords)

    def _extract_region(self, message: str) -> Optional[str]:
        """Extract region from message"""
        regions = {
            "miền nam": [
                "Phú Quốc",
                "Cần Thơ",
                "Vũng Tàu",
                "TP.HCM",
                "Bến Tre",
                "An Giang",
            ],
            "miền bắc": [
                "Hà Nội",
                "Sapa",
                "Hạ Long",
                "Ninh Bình",
                "Hà Giang",
                "Cao Bằng",
            ],
            "miền trung": ["Đà Nẵng", "Huế", "Hội An", "Nha Trang", "Quy Nhơn"],
            "miền tây": ["Cần Thơ", "Bến Tre", "An Giang", "Cà Mau"],
            "tây nguyên": ["Đà Lạt", "Buôn Ma Thuột", "Pleiku"],
        }
        message_lower = message.lower()
        for region in regions.keys():
            if region in message_lower:
                return region
        return None

    def _is_recall_itinerary_request(self, message: str) -> bool:
        """Check if user wants to recall their saved itinerary"""
        message_lower = message.lower()
        recall_patterns = [
            "xem lại lịch trình",
            "lịch trình của tôi",
            "lịch trình đã tạo",
            "hiển thị lịch trình",
            "show itinerary",
            "my itinerary",
            "xem lịch trình",
            "cho tôi xem lịch trình",
            "lịch trình hôm nay",
            "kế hoạch của tôi",
            # FIX 2026-01-18: Add more patterns for asking about selected spots
            "các địa điểm sẽ đến",
            "những địa điểm sẽ đến",
            "địa điểm đã chọn",
            "những chỗ sẽ đến",
            "các chỗ sẽ đến",
            "thông tin địa điểm sẽ đến",
            "thông tin các địa điểm",
            "cho tôi thông tin các địa điểm",
            "điểm đến đã chọn",
            "các điểm đến",
            "những điểm đến",
            "spots i selected",
            "my spots",
            "selected spots",
        ]
        return any(p in message_lower for p in recall_patterns)

    def _handle_recall_itinerary(self, context) -> Dict[str, Any]:
        """Handle request to recall saved itinerary with FULL DATA INJECTION

        FIX 2026-01-18: Also check itinerary_builder if last_itinerary is not available.
        This handles the case when user asks about spots while still building the itinerary.
        """
        last_itinerary = getattr(context, "last_itinerary", None)
        itinerary_builder = getattr(context, "itinerary_builder", None)

        logger.info(
            f"🔍 DEBUG: Recall itinerary - has last_itinerary: {last_itinerary is not None}, has_builder: {itinerary_builder is not None}"
        )

        # FIX: If no last_itinerary, try to build from itinerary_builder
        if (not last_itinerary or not last_itinerary.get("days")) and itinerary_builder:
            logger.info("📋 Building itinerary data from itinerary_builder for recall")
            # Extract data from itinerary_builder
            location = itinerary_builder.get("location") or getattr(
                context, "destination", ""
            )
            duration = (
                itinerary_builder.get("total_days")
                or itinerary_builder.get("duration")
                or getattr(context, "duration", 3)
            )

            # Get selected spots from builder
            days_data = []
            selected_spots = itinerary_builder.get("selected_spots", [])
            days_info = itinerary_builder.get("days", [])

            # If we have days info from builder, use it
            if days_info:
                for day_info in days_info:
                    day_num = day_info.get("day", 0)
                    spots = day_info.get("spots", [])
                    # Convert to list of spot names if they are dicts
                    spot_names = []
                    for s in spots:
                        if isinstance(s, dict):
                            spot_names.append(s.get("name", str(s)))
                        else:
                            spot_names.append(str(s))
                    days_data.append({"day": day_num, "spots": spot_names})
            # Otherwise, build from selected_spots grouped by session
            elif selected_spots:
                # Group spots by day
                spots_by_day = {}
                for spot in selected_spots:
                    if isinstance(spot, dict):
                        day = spot.get("day", 1)
                        name = spot.get("name", str(spot))
                    else:
                        day = 1
                        name = str(spot)
                    if day not in spots_by_day:
                        spots_by_day[day] = []
                    spots_by_day[day].append(name)

                for day_num in sorted(spots_by_day.keys()):
                    days_data.append({"day": day_num, "spots": spots_by_day[day_num]})

            # Create temporary last_itinerary from builder
            if days_data:
                last_itinerary = {
                    "location": location,
                    "duration": duration,
                    "days": days_data,
                }
                logger.info(
                    f"✅ Built temp itinerary from builder: {len(days_data)} days"
                )

        if not last_itinerary or not last_itinerary.get("days"):
            # Also check if there are available_spots in builder that haven't been selected yet
            if itinerary_builder:
                available_spots = itinerary_builder.get("available_spots", [])
                current_day = itinerary_builder.get("current_day", 1)
                location = itinerary_builder.get("location") or getattr(
                    context, "destination", ""
                )

                if available_spots:
                    # Show available spots for selection
                    spots_list = []
                    for i, spot in enumerate(available_spots[:10], 1):
                        if isinstance(spot, dict):
                            name = spot.get("name", f"Địa điểm {i}")
                        else:
                            name = str(spot)
                        spots_list.append(f"  {i}. {name}")

                    return {
                        "reply": f"📋 **Bạn đang xây dựng lịch trình ở {location}**\n\n"
                        f"📅 Đang ở Ngày {current_day}\n\n"
                        "🔸 Bạn chưa chọn địa điểm nào. Hãy chọn từ danh sách:\n\n"
                        + "\n".join(spots_list)
                        + "\n\n"
                        "💡 Gõ số thứ tự (ví dụ: 1, 2, 3) để chọn địa điểm",
                        "ui_type": "text",
                        "context": context.to_dict(),
                        "status": "success",
                    }

            return {
                "reply": "📋 Bạn chưa tạo lịch trình nào!\n\n"
                '💡 Hãy thử: **"Lập lịch trình 3 ngày ở Đà Nẵng"**',
                "ui_type": "text",
                "context": context.to_dict(),
                "status": "success",
            }

        location = last_itinerary.get("location", "")
        duration = last_itinerary.get("duration", 0)
        days_data = last_itinerary.get("days", [])

        logger.info(
            f"📊 DEBUG: Recalling itinerary - {duration} days, {len(days_data)} day records"
        )

        # Build itinerary text with SPOT DETAILS
        itinerary_parts = []
        itinerary_items = []
        total_spots = 0
        spots_details = []  # NEW: Collect full spot details

        # Query MongoDB for spot details
        spots_collection = self.mongo_manager.get_collection("spots_detailed")

        for day_info in days_data:
            day_num = day_info.get("day", 0)
            spots = day_info.get("spots", [])
            total_spots += len(spots)

            if spots:
                # Handle both string and dict spot formats
                spot_names_for_text = []
                for s in spots:
                    if isinstance(s, dict):
                        spot_names_for_text.append(s.get("name", str(s)))
                    else:
                        spot_names_for_text.append(str(s))
                spots_text = "\n".join(
                    [f"    • {name}" for name in spot_names_for_text]
                )

                # NEW: Query MongoDB for each spot to get full details
                for spot_item in spots:
                    try:
                        # Extract spot_name from dict or string
                        if isinstance(spot_item, dict):
                            spot_name = spot_item.get("name", "")
                            # If we already have image/description from spot_item, use it
                            if spot_item.get("image") and spot_item.get("name"):
                                spots_details.append(
                                    {
                                        "name": spot_item.get("name", ""),
                                        "description": spot_item.get(
                                            "description", "Địa điểm du lịch nổi tiếng"
                                        ),
                                        "address": spot_item.get("address", ""),
                                        "price_range": spot_item.get(
                                            "price_range", "Miễn phí"
                                        ),
                                        "image_url": spot_item.get("image", ""),
                                        "category": spot_item.get("category", ""),
                                        "session": spot_item.get("session", ""),
                                        "rating": spot_item.get("rating"),
                                    }
                                )
                                continue
                        else:
                            spot_name = str(spot_item)

                        if not spot_name:
                            continue

                        # Try exact match first
                        spot_doc = spots_collection.find_one({"name": spot_name})

                        # Fallback: fuzzy search
                        if not spot_doc:
                            spot_doc = spots_collection.find_one(
                                {"name": {"$regex": spot_name, "$options": "i"}}
                            )

                        if spot_doc:
                            # Get description with fallback
                            desc = (
                                spot_doc.get("description_short")
                                or spot_doc.get("description")
                                or spot_doc.get("description_full", "")[:300]
                                or "Địa điểm du lịch nổi tiếng"
                            )
                            spots_details.append(
                                {
                                    "name": spot_doc.get("name", spot_name),
                                    "description": desc,
                                    "address": spot_doc.get("address", ""),
                                    "price_range": spot_doc.get(
                                        "price_range", "Miễn phí"
                                    ),
                                    "image_url": spot_doc.get("image_url")
                                    or spot_doc.get("image", ""),
                                    "source_url": spot_doc.get(
                                        "url", ""
                                    ),  # Link to original article
                                    "tips": spot_doc.get("tips", ""),
                                    # Remove rating, add images
                                    "images": spot_doc.get("images", []),
                                }
                            )
                        else:
                            # No data found, use basic info from spot_item if it's a dict
                            if isinstance(spot_item, dict):
                                spots_details.append(
                                    {
                                        "name": spot_item.get("name", spot_name),
                                        "description": spot_item.get(
                                            "description", "Địa điểm du lịch nổi tiếng"
                                        ),
                                        "address": spot_item.get("address", ""),
                                        "price_range": spot_item.get(
                                            "price_range", "Miễn phí"
                                        ),
                                        "rating": spot_item.get("rating", 4.5),
                                        "image_url": spot_item.get("image", ""),
                                        "category": spot_item.get("category", ""),
                                        "session": spot_item.get("session", ""),
                                        "tips": "",
                                    }
                                )
                            else:
                                spots_details.append(
                                    {
                                        "name": spot_name,
                                        "description": "Địa điểm du lịch nổi tiếng",
                                        "address": "",
                                        "price_range": "Miễn phí",
                                        "rating": 4.5,
                                        "image_url": "",
                                        "tips": "",
                                    }
                                )
                    except Exception as e:
                        logger.warning(
                            f"Could not fetch details for spot: {spot_item} - {e}"
                        )
                        # Fallback: use spot_item data if it's a dict
                        if isinstance(spot_item, dict):
                            spots_details.append(
                                {
                                    "name": spot_item.get("name", str(spot_item)),
                                    "description": spot_item.get(
                                        "description", "Địa điểm du lịch"
                                    ),
                                    "address": spot_item.get("address", ""),
                                    "price_range": spot_item.get(
                                        "price_range", "Miễn phí"
                                    ),
                                    "rating": spot_item.get("rating", 4.5),
                                    "image_url": spot_item.get("image", ""),
                                    "category": spot_item.get("category", ""),
                                    "session": spot_item.get("session", ""),
                                    "tips": "",
                                }
                            )
                        else:
                            spots_details.append(
                                {
                                    "name": str(spot_item),
                                    "description": "Địa điểm du lịch",
                                    "address": "",
                                    "price_range": "Miễn phí",
                                    "rating": 4.5,
                                    "image_url": "",
                                    "tips": "",
                                }
                            )
            else:
                spots_text = "    • Tự do khám phá"

            itinerary_parts.append(f"📅 **Ngày {day_num}:**\n{spots_text}")

            # Build UI data - extract spot names properly
            def get_spot_name(s):
                if isinstance(s, dict):
                    return s.get("name", str(s))
                return str(s)

            itinerary_items.append(
                {
                    "day": day_num,
                    "title": f"Khám phá {location}",
                    "morning": get_spot_name(spots[0]) if len(spots) > 0 else "Tự do",
                    "afternoon": (
                        get_spot_name(spots[1])
                        if len(spots) > 1
                        else (get_spot_name(spots[0]) if spots else "Tự do")
                    ),
                    "evening": (
                        get_spot_name(spots[2]) if len(spots) > 2 else "Nghỉ ngơi"
                    ),
                }
            )

        itinerary_text = "\n\n".join(itinerary_parts)

        # DATA INJECTION: Include selected hotel info
        selected_hotel = getattr(context, "selected_hotel", None)
        selected_hotel_price = getattr(context, "selected_hotel_price", None)

        hotel_info = ""
        if selected_hotel:
            hotel_info = f"\n\n🏨 **Khách sạn đã chọn:** {selected_hotel}"
            if selected_hotel_price:
                hotel_info += f" - {selected_hotel_price} VNĐ/đêm"

        reply = f"""🗓️ **LỊCH TRÌNH {duration} NGÀY TẠI {location.upper()}** (đã lưu)

{itinerary_text}{hotel_info}

━━━━━━━━━━━━━━━━━━━━

📊 **Tổng quan:** {total_spots} địa điểm đã chọn

💡 **Bạn có thể:**
• Gõ **"tìm khách sạn"** để xem các khách sạn tại {location}
• Gõ **"ước tính chi phí"** để tính chi phí chuyến đi
• Gõ **"lập lịch lại"** để tạo lịch trình mới"""

        logger.info(
            f"✅ DEBUG: Recall response ready - {len(reply)} chars, {len(itinerary_items)} days, {total_spots} spots"
        )
        logger.info(
            f"📍 DEBUG: Collected {len(spots_details)} spot details for recall display"
        )

        # FIX 2026-01-18: Return spot_cards UI with detailed info for better display
        # Build spots list for spot_cards UI type
        spots_for_ui = []
        for spot in spots_details:
            spots_for_ui.append(
                {
                    "id": spot.get("id", ""),
                    "name": spot.get("name", ""),
                    "description": (
                        spot.get("description", "")[:200]
                        if spot.get("description")
                        else "Địa điểm du lịch nổi tiếng"
                    ),
                    "rating": spot.get("rating", 4.5),
                    "image": spot.get("image_url") or spot.get("image", ""),
                    "address": spot.get("address", ""),
                }
            )

        return {
            "reply": reply,
            "ui_type": "spot_cards" if spots_for_ui else "itinerary",
            "ui_data": {
                "spots": spots_for_ui,
                "title": f"Các địa điểm tại {location}",
                "items": itinerary_items,
                "destination": location,
                "days": duration,
                "total_days": duration,
                "spots_details": spots_details,  # NEW: Full spot information
                # DATA INJECTION: Include facts for verification
                "spots_count": total_spots,
                "has_hotel": selected_hotel is not None,
            },
            "context": context.to_dict(),
            "status": "success",
        }

    async def _handle_get_detail(
        self, user_message: str, context, multi_intent
    ) -> Optional[Dict[str, Any]]:
        """Handle request for details about a specific entity

        PATCH 1: Priority order for finding entities:
        1. Check for general question patterns (e.g., "các địa điểm sắp đến")
        2. Check context (last_spots, last_hotels, last_itinerary)
        3. Search database with semantic search fallback
        """

        message_lower = user_message.lower()

        # 🔧 PATCH 1.1: Detect general questions and handle from context
        general_patterns = [
            "các địa điểm",
            "những địa điểm",
            "các chỗ",
            "những chỗ",
            "sắp đến",
            "sắp đi",
            "sẽ đi",
            "đã chọn",
            "khoảng cách",
            "xa gần",
            "bao xa",
            "đi lại",
            "tất cả",
            "toàn bộ",
            "list",
            "danh sách",
        ]

        is_general_question = any(
            pattern in message_lower for pattern in general_patterns
        )

        if is_general_question:
            logger.info(
                f"🔍 [PATCH 1] Detected general question, fetching from context"
            )

            # Get spots from itinerary or last_spots
            spots_info = []

            # Priority 1: Get from itinerary_builder (most recent)
            itinerary_builder = getattr(context, "itinerary_builder", None)
            if itinerary_builder and isinstance(itinerary_builder, dict):
                days_plan = itinerary_builder.get("days_plan", {})
                for day_num, day_spots in days_plan.items():
                    if isinstance(day_spots, list):
                        spots_info.extend(day_spots)

            # Priority 2: Get from last_itinerary
            if not spots_info:
                last_itinerary = getattr(context, "last_itinerary", {})
                if isinstance(last_itinerary, dict):
                    selected_spots = last_itinerary.get("selected_spots", [])
                    if selected_spots:
                        spots_info = selected_spots

            # Priority 3: Get from last_spots
            if not spots_info:
                spots_info = getattr(context, "last_spots", [])

            if spots_info:
                # Format list of spots from context
                def get_spot_desc(s):
                    """Get description with fallback"""
                    desc = (
                        s.get("description_short")
                        or s.get("description")
                        or s.get("description_full", "")
                    )
                    return desc[:100] if desc else ""

                def get_cat(s):
                    """Get category with fallback"""
                    cat = s.get("category")
                    if not cat or cat == "None":
                        tags = s.get("tags", [])
                        return tags[0] if tags else ""
                    return cat

                spots_list = "\n".join(
                    [
                        f"{i+1}. **{s.get('name', 'Unknown')}**"
                        + (f" - {get_cat(s)}" if get_cat(s) else "")
                        + (f"\n   📝 {get_spot_desc(s)}..." if get_spot_desc(s) else "")
                        for i, s in enumerate(spots_info[:10])
                    ]
                )

                reply = (
                    f"📍 **Các địa điểm trong lịch trình của bạn:**\n\n{spots_list}\n\n"
                )
                reply += (
                    "💡 Bạn muốn xem chi tiết địa điểm nào? Hãy nói tên hoặc số thứ tự."
                )

                return {
                    "reply": reply,
                    "ui_type": "spot_cards",
                    "ui_data": {"spots": spots_info[:10]},
                    "context": context.to_dict(),
                    "status": "complete",
                }

        # Try to find what entity user is asking about
        entity_name = None
        entity_data = None
        entity_type = None

        # Check last shown spots
        last_spots = getattr(context, "last_spots", [])
        last_hotels = getattr(context, "last_hotels", [])

        message_lower = user_message.lower()

        # Check for ordinal references like "đầu tiên", "thứ 2", "số 1"
        ordinal_index = self._extract_ordinal_index(message_lower)
        if ordinal_index is not None:
            # User is referring to an item by position
            if last_spots and ordinal_index < len(last_spots):
                entity_data = last_spots[ordinal_index]
                entity_name = entity_data.get("name")
                entity_type = "spot"
                logger.info(f"📍 Found by ordinal #{ordinal_index + 1}: {entity_name}")
            elif last_hotels and ordinal_index < len(last_hotels):
                entity_data = last_hotels[ordinal_index]
                entity_name = entity_data.get("name")
                entity_type = "hotel"
                logger.info(f"🏨 Found by ordinal #{ordinal_index + 1}: {entity_name}")

        # Search in spots from context by name match
        if not entity_name:
            for spot in last_spots:
                name = spot.get("name", "").lower()
                if name and name in message_lower:
                    entity_name = spot.get("name")
                    entity_data = spot
                    entity_type = "spot"
                    break

        # Search in hotels if not found in spots
        if not entity_name:
            for hotel in last_hotels:
                name = hotel.get("name", "").lower()
                if name and name in message_lower:
                    entity_name = hotel.get("name")
                    entity_data = hotel
                    entity_type = "hotel"
                    break

        # If not found in context, search directly in database
        if not entity_name and self.mongo_manager:
            entity_data, entity_type = await self._search_entity_in_db(
                message_lower, multi_intent
            )
            if entity_data:
                entity_name = entity_data.get("name")

        if entity_name and entity_data:
            # Generate detailed response using LLM if available
            if self.llm and entity_type == "spot":
                detail_response = await self._generate_spot_detail(
                    entity_name, entity_data, context
                )
            elif self.llm and entity_type == "hotel":
                detail_response = await self._generate_hotel_detail(
                    entity_name, entity_data, context
                )
            else:
                detail_response = self._format_entity_detail(
                    entity_name, entity_data, entity_type
                )

            return detail_response

        # Entity not found - provide helpful response
        location = multi_intent.location or getattr(context, "destination", None)
        return {
            "reply": f"Tôi chưa tìm thấy thông tin chi tiết về địa điểm này.\n\n"
            f"💡 Bạn có thể:\n"
            f"• Chọn từ danh sách địa điểm đã gợi ý\n"
            f"• Hỏi: 'Địa điểm tham quan ở {location or 'X'}'\n"
            f"• Hoặc nói rõ tên địa điểm bạn quan tâm",
            "ui_type": "none",
            "context": context.to_dict(),
            "status": "partial",
        }

    def _extract_ordinal_index(self, message: str) -> Optional[int]:
        """Extract ordinal number from message (0-indexed)

        Examples:
            "đầu tiên", "cái 1", "số 1" -> 0
            "thứ 2", "cái 2", "số 2" -> 1
            "thứ 3", "cái cuối" -> 2, last
        """
        import re

        # Vietnamese ordinal patterns
        ordinal_map = {
            # First
            "đầu tiên": 0,
            "thứ nhất": 0,
            "cái 1": 0,
            "số 1": 0,
            "option 1": 0,
            "lựa chọn 1": 0,
            "1.": 0,
            # Second
            "thứ 2": 1,
            "thứ hai": 1,
            "cái 2": 1,
            "số 2": 1,
            "option 2": 1,
            "lựa chọn 2": 1,
            "2.": 1,
            # Third
            "thứ 3": 2,
            "thứ ba": 2,
            "cái 3": 2,
            "số 3": 2,
            "option 3": 2,
            "lựa chọn 3": 2,
            "3.": 2,
            # Fourth
            "thứ 4": 3,
            "thứ tư": 3,
            "cái 4": 3,
            "số 4": 3,
            "option 4": 3,
            "lựa chọn 4": 3,
            "4.": 3,
            # Fifth
            "thứ 5": 4,
            "thứ năm": 4,
            "cái 5": 4,
            "số 5": 4,
            "option 5": 4,
            "lựa chọn 5": 4,
            "5.": 4,
            # Sixth
            "thứ 6": 5,
            "thứ sáu": 5,
            "cái 6": 5,
            "số 6": 5,
            "option 6": 5,
            "lựa chọn 6": 5,
            "6.": 5,
        }

        message_lower = message.lower()

        for pattern, index in ordinal_map.items():
            if pattern in message_lower:
                return index

        # Try regex for "thứ X" pattern
        match = re.search(r"thứ\s*(\d+)", message_lower)
        if match:
            return int(match.group(1)) - 1  # Convert to 0-indexed

        # Try regex for standalone number "1", "2", etc.
        match = re.search(r"\b(\d+)\b", message_lower)
        if match:
            num = int(match.group(1))
            if 1 <= num <= 10:
                return num - 1

        return None

    async def _search_entity_in_db(self, message_lower: str, multi_intent) -> tuple:
        """Search for entity directly in database when not found in context

        Uses priority-based matching:
        1. Exact phrase match (highest priority)
        2. All terms must be present (AND)
        3. Any term match with scoring (OR + rank by match count)

        Returns:
            tuple: (entity_data, entity_type) or (None, None)
        """
        import re

        # Extract potential entity name from message
        # Remove common Vietnamese question words
        stop_words = [
            "chi tiết",
            "thông tin",
            "cho biết",
            "kể về",
            "nói về",
            "giới thiệu",
            "về",
            "ở",
            "tại",
            "của",
            "trong",
            "ngoài",
            "gần",
            "xa",
            "cho",
            "tôi",
            "mình",
            "bạn",
            "hãy",
            "xin",
            "được",
            "không",
            "như thế nào",
            "ra sao",
            "thế nào",
            "gì",
            "đâu",
            "bao nhiêu",
            "muốn",
            "biết",
            "thêm",
            "xem",
            "có",
            "thể",
        ]

        search_text = message_lower
        for word in stop_words:
            search_text = search_text.replace(word, " ")

        # Clean up extra spaces and get potential name
        search_terms = [t.strip() for t in search_text.split() if len(t.strip()) > 1]

        if not search_terms:
            return None, None

        # Build search phrase (for exact match)
        search_phrase = " ".join(search_terms)

        logger.info(f"🔍 Searching DB for: '{search_phrase}' (terms: {search_terms})")

        # 🔥 FIX: Get current destination/province from context for geo-filtering
        current_province = None
        if hasattr(multi_intent, "location") and multi_intent.location:
            current_province = multi_intent.location
            logger.info(f"📍 Geo-filter active: {current_province}")

        # Convert province name to slug for matching
        province_slug = None
        if current_province:
            province_slug = current_province.lower()
            province_slug = (
                province_slug.replace("đ", "d").replace("ă", "a").replace("â", "a")
            )
            province_slug = (
                province_slug.replace("ê", "e").replace("ô", "o").replace("ơ", "o")
            )
            province_slug = province_slug.replace("ư", "u").replace(" ", "-")

        try:
            spots_col = self.mongo_manager.get_collection("spots_detailed")

            # Build base geo-filter if we have province context
            geo_filter = {}
            if province_slug:
                geo_filter = {"province_id": {"$regex": province_slug, "$options": "i"}}

            # Priority 1: Exact phrase match in name (WITH GEO-FILTER)
            query = {"name": {"$regex": search_phrase, "$options": "i"}}
            if geo_filter:
                query.update(geo_filter)

            spot = spots_col.find_one(query)
            if spot:
                spot = _clean_mongo_doc(spot)
                logger.info(f"✅ Found exact match: {spot.get('name')}")
                return spot, "spot"

            # Priority 2: Try combining key terms (e.g., "bãi sao" together)
            if len(search_terms) >= 2:
                # Try pairs of consecutive terms
                for i in range(len(search_terms) - 1):
                    pair = f"{search_terms[i]} {search_terms[i+1]}"
                    query = {"name": {"$regex": pair, "$options": "i"}}
                    if geo_filter:
                        query.update(geo_filter)

                    spot = spots_col.find_one(query)
                    if spot:
                        spot = _clean_mongo_doc(spot)
                        logger.info(f"✅ Found pair match '{pair}': {spot.get('name')}")
                        return spot, "spot"

            # Priority 3: All significant terms must be present (AND logic)
            # Filter out very short or common words
            significant_terms = [t for t in search_terms if len(t) >= 3]
            if len(significant_terms) >= 2:
                and_conditions = [
                    {"name": {"$regex": term, "$options": "i"}}
                    for term in significant_terms
                ]
                query = {"$and": and_conditions}
                if geo_filter:
                    and_conditions.append(geo_filter)
                    query = {"$and": and_conditions}

                spot = spots_col.find_one(query)
                if spot:
                    spot = _clean_mongo_doc(spot)
                    logger.info(f"✅ Found AND match: {spot.get('name')}")
                    return spot, "spot"

            # Priority 4: Score-based OR search (count matching terms)
            or_conditions = [
                {"name": {"$regex": term, "$options": "i"}}
                for term in search_terms
                if len(term) >= 3
            ]

            if or_conditions:
                # Get all candidates (with geo-filter if available)
                query = {"$or": or_conditions}
                if geo_filter:
                    query = {"$and": [geo_filter, {"$or": or_conditions}]}

                candidates = list(spots_col.find(query).limit(20))

                if candidates:
                    # Score each candidate by how many terms match
                    def score_candidate(doc):
                        name_lower = doc.get("name", "").lower()
                        score = 0
                        for term in search_terms:
                            if term in name_lower:
                                score += len(term)  # Longer term matches worth more
                        return score

                    # Sort by score (highest first)
                    candidates.sort(key=score_candidate, reverse=True)
                    best = _clean_mongo_doc(candidates[0])
                    logger.info(
                        f"✅ Found scored match: {best.get('name')} (score: {score_candidate(candidates[0])})"
                    )
                    return best, "spot"

            # Try hotels collection with same logic (WITH GEO-FILTER)
            hotels_col = self.mongo_manager.get_collection("hotels")
            if hotels_col is not None:
                # Exact match first
                query = {"name": {"$regex": search_phrase, "$options": "i"}}
                if geo_filter:
                    query.update(geo_filter)

                hotel = hotels_col.find_one(query)
                if hotel:
                    hotel = _clean_mongo_doc(hotel)
                    logger.info(f"✅ Found hotel: {hotel.get('name')}")
                    return hotel, "hotel"

        except Exception as e:
            logger.error(f"❌ Database search error: {e}")

        # PATCH 1.2: Semantic Search Fallback
        logger.info(f"⚠️ Keyword search failed for: {search_phrase}")
        logger.info(f"🔍 Attempting semantic search with embeddings...")

        try:
            # Check if embedding model is available
            if not hasattr(self, "embedding_model") or self.embedding_model is None:
                logger.warning(
                    "Embedding model not loaded, cannot perform semantic search"
                )
                logger.info(f"❌ No match found for: {search_phrase}")
                return None, None

            # Generate embedding for search query
            import torch

            query_embedding = self.embedding_model.encode(
                search_phrase, convert_to_tensor=True
            )

            # Search in spots collection with semantic similarity
            spots_col = self.mongo_manager.get_collection("tourist_spots")
            if spots_col is not None:
                # Get all spots (with geo-filter if provided)
                query = geo_filter if geo_filter else {}
                all_spots = list(
                    spots_col.find(
                        query,
                        {
                            "name": 1,
                            "description_short": 1,
                            "embedding": 1,
                            "address": 1,
                            "category": 1,
                        },
                    )
                )

                if all_spots:
                    best_match = None
                    best_score = -1.0

                    for spot in all_spots:
                        # Check if spot has embedding
                        if "embedding" not in spot or not spot["embedding"]:
                            continue

                        # Convert stored embedding to tensor
                        spot_embedding = torch.tensor(spot["embedding"])

                        # Calculate cosine similarity
                        from torch.nn.functional import cosine_similarity

                        similarity = cosine_similarity(
                            query_embedding.unsqueeze(0), spot_embedding.unsqueeze(0)
                        )
                        score = similarity.item()

                        # Track best match
                        if score > best_score:
                            best_score = score
                            best_match = spot

                    # Use threshold for semantic search (0.6 = 60% similarity)
                    SEMANTIC_THRESHOLD = 0.6
                    if best_match and best_score >= SEMANTIC_THRESHOLD:
                        # Fetch full document
                        full_doc = spots_col.find_one({"_id": best_match["_id"]})
                        if full_doc:
                            result = _clean_mongo_doc(full_doc)
                            logger.info(
                                f"✅ Found by semantic search: {result.get('name')} (similarity: {best_score:.2f})"
                            )
                            return result, "spot"
                    else:
                        logger.info(
                            f"⚠️ Best semantic match score too low: {best_score:.2f} < {SEMANTIC_THRESHOLD}"
                        )

            # Try semantic search in hotels if spots failed
            hotels_col = self.mongo_manager.get_collection("hotels")
            if hotels_col is not None:
                query = geo_filter if geo_filter else {}
                all_hotels = list(
                    hotels_col.find(
                        query,
                        {"name": 1, "description": 1, "embedding": 1, "address": 1},
                    )
                )

                if all_hotels:
                    best_match = None
                    best_score = -1.0

                    for hotel in all_hotels:
                        if "embedding" not in hotel or not hotel["embedding"]:
                            continue

                        hotel_embedding = torch.tensor(hotel["embedding"])
                        similarity = cosine_similarity(
                            query_embedding.unsqueeze(0), hotel_embedding.unsqueeze(0)
                        )
                        score = similarity.item()

                        if score > best_score:
                            best_score = score
                            best_match = hotel

                    SEMANTIC_THRESHOLD = 0.6
                    if best_match and best_score >= SEMANTIC_THRESHOLD:
                        full_doc = hotels_col.find_one({"_id": best_match["_id"]})
                        if full_doc:
                            result = _clean_mongo_doc(full_doc)
                            logger.info(
                                f"✅ Found hotel by semantic search: {result.get('name')} (similarity: {best_score:.2f})"
                            )
                            return result, "hotel"

        except Exception as e:
            logger.error(f"❌ Semantic search error: {e}")
            import traceback

            logger.error(traceback.format_exc())

        logger.info(f"❌ No match found for: {search_phrase}")
        return None, None

    async def _generate_spot_detail(self, name: str, data: Dict, context) -> Dict:
        """Generate detailed spot info using LLM"""
        prompt = f"""Bạn là hướng dẫn viên du lịch. Giới thiệu về: {name}

Dữ liệu có sẵn:
- Đánh giá: {data.get('rating', 'N/A')} sao ({data.get('reviews_count', 0)} đánh giá)
- Địa chỉ: {data.get('address', 'N/A')}
- Mô tả: {data.get('description_short', 'Chưa có mô tả')}
- Danh mục: {data.get('category', 'N/A')}

Viết giới thiệu hấp dẫn 3-5 câu, bao gồm:
1. Điểm đặc biệt
2. Thời gian tham quan lý tưởng
3. Tips khi đến
"""
        try:
            response = self.llm.chat([{"role": "user", "content": prompt}])
            reply = f"📍 **{name}**\n\n{response}\n\n"
            reply += f"⭐ Đánh giá: {data.get('rating', 'N/A')}/5 ({data.get('reviews_count', 0)} reviews)\n"
            reply += f"📮 Địa chỉ: {data.get('address', 'Đang cập nhật')}"
        except:
            reply = self._format_entity_detail(name, data, "spot")["reply"]

        return {
            "reply": reply,
            "ui_type": "spot_detail",
            "ui_data": {"spot": data},
            "context": context.to_dict(),
            "status": "partial",
        }

    async def _generate_hotel_detail(self, name: str, data: Dict, context) -> Dict:
        """Generate detailed hotel info using LLM"""
        prompt = f"""Bạn là chuyên gia đánh giá khách sạn. Giới thiệu về: {name}

Dữ liệu:
- Đánh giá: {data.get('rating', 'N/A')} sao
- Giá: {data.get('price', 'N/A')} VNĐ/đêm
- Địa chỉ: {data.get('address', 'N/A')}

Viết đánh giá ngắn gọn 2-3 câu về ưu điểm khách sạn.
"""
        try:
            response = self.llm.chat([{"role": "user", "content": prompt}])
            reply = f"🏨 **{name}**\n\n{response}\n\n"
            reply += f"⭐ Đánh giá: {data.get('rating', 'N/A')}/5\n"
            reply += f"💰 Giá: {data.get('price', 0):,} VNĐ/đêm\n"
            reply += f"📍 {data.get('address', 'Đang cập nhật')}"
        except:
            reply = self._format_entity_detail(name, data, "hotel")["reply"]

        return {
            "reply": reply,
            "ui_type": "hotel_detail",
            "ui_data": {"hotel": data},
            "context": context.to_dict(),
            "status": "partial",
        }

    def _format_entity_detail(self, name: str, data: Dict, entity_type: str) -> Dict:
        """Format entity detail without LLM"""
        if entity_type == "spot":
            reply = f"📍 **{name}**\n\n"
            reply += (
                f"{data.get('description_short', 'Một địa điểm du lịch hấp dẫn.')}\n\n"
            )
            reply += f"⭐ Đánh giá: {data.get('rating', 'N/A')}/5\n"
            reply += f"📮 Địa chỉ: {data.get('address', 'Đang cập nhật')}"
            ui_type = "spot_detail"
        else:
            reply = f"🏨 **{name}**\n\n"
            reply += f"⭐ Đánh giá: {data.get('rating', 'N/A')}/5\n"
            reply += f"💰 Giá: {data.get('price', 0):,} VNĐ/đêm\n"
            reply += f"📍 {data.get('address', 'Đang cập nhật')}"
            ui_type = "hotel_detail"

        return {"reply": reply, "ui_type": ui_type, "ui_data": {entity_type: data}}

    async def _handle_breakdown(self, context, multi_intent) -> Dict:
        """Handle cost breakdown by day request"""
        location = (
            multi_intent.location or getattr(context, "destination", None) or "điểm đến"
        )
        duration = multi_intent.duration or getattr(context, "duration", None) or 3
        people_count = multi_intent.people_count or getattr(context, "people_count", 1)

        # Get last cost if available
        last_cost = getattr(context, "last_cost", None)

        if last_cost:
            total = last_cost.get("total", 4500000)
            daily = total / duration
        else:
            daily = 1500000  # Default per day
            total = daily * duration

        # Create breakdown
        breakdown = f"📊 **Chi phí chi tiết từng ngày tại {location}**\n\n"

        for day in range(1, duration + 1):
            breakdown += f"**📅 Ngày {day}:**\n"
            breakdown += f"  🏨 Khách sạn: {500000:,} VNĐ\n"
            breakdown += f"  🍜 Ăn sáng: {50000:,} VNĐ\n"
            breakdown += f"  🍜 Ăn trưa: {100000:,} VNĐ\n"
            breakdown += f"  🍜 Ăn tối: {150000:,} VNĐ\n"
            breakdown += f"  🚕 Di chuyển: {200000:,} VNĐ\n"
            breakdown += f"  🎫 Tham quan: {500000:,} VNĐ\n"
            breakdown += f"  **Tổng ngày {day}: {1500000:,} VNĐ**\n\n"

        breakdown += f"💵 **TỔNG CỘNG {duration} NGÀY: {total:,} VNĐ**\n"
        if people_count > 1:
            breakdown += f"👥 Cho {people_count} người: {total * people_count:,} VNĐ\n"

        breakdown += f"\n💡 _Mẹo tiết kiệm: Đặt phòng trước 2 tuần để có giá tốt hơn!_"

        return {
            "reply": breakdown,
            "ui_type": "cost_breakdown",
            "ui_data": {
                "breakdown": {"daily": daily, "total": total, "duration": duration}
            },
            "context": context.to_dict(),
            "status": "partial",
        }

    async def _handle_region_search(self, region: str, context) -> Dict:
        """Handle search by region (miền nam, miền bắc, etc.)"""
        regions = {
            "miền nam": {
                "provinces": [
                    "Phú Quốc",
                    "Cần Thơ",
                    "Vũng Tàu",
                    "TP.HCM",
                    "Bến Tre",
                    "An Giang",
                ],
                "description": "Vùng đất phương Nam trù phú với sông nước, miệt vườn và biển đảo xinh đẹp",
                "highlights": "🏝️ Biển đảo, 🌴 Miệt vườn, 🍲 Ẩm thực phong phú",
            },
            "miền bắc": {
                "provinces": [
                    "Hà Nội",
                    "Sapa",
                    "Hạ Long",
                    "Ninh Bình",
                    "Hà Giang",
                    "Cao Bằng",
                ],
                "description": "Vùng đất ngàn năm văn hiến với núi non hùng vĩ và văn hóa đậm đà bản sắc",
                "highlights": "⛰️ Núi non, 🏛️ Di sản, 🍜 Ẩm thực Bắc",
            },
            "miền trung": {
                "provinces": ["Đà Nẵng", "Huế", "Hội An", "Nha Trang", "Quy Nhơn"],
                "description": "Dải đất miền Trung với biển xanh, cố đô và di sản văn hóa thế giới",
                "highlights": "🏖️ Biển đẹp, 🏛️ Cố đô, 🏮 Phố cổ",
            },
            "miền tây": {
                "provinces": ["Cần Thơ", "Bến Tre", "An Giang", "Cà Mau"],
                "description": "Vùng sông nước Cửu Long với chợ nổi, vườn trái cây và cuộc sống bình dị",
                "highlights": "🛶 Chợ nổi, 🥭 Miệt vườn, 🏡 Làng quê",
            },
            "tây nguyên": {
                "provinces": ["Đà Lạt", "Buôn Ma Thuột", "Pleiku"],
                "description": "Cao nguyên mát mẻ với hoa, cà phê và văn hóa dân tộc độc đáo",
                "highlights": "🌸 Hoa, ☕ Cà phê, 🎭 Văn hóa dân tộc",
            },
        }

        region_data = regions.get(region, regions["miền nam"])
        provinces = region_data["provinces"]

        reply = f"🗺️ **Du lịch {region.title()}**\n\n"
        reply += f"{region_data['description']}\n\n"
        reply += f"✨ **Điểm nổi bật:** {region_data['highlights']}\n\n"
        reply += f"📍 **Các điểm đến nổi bật:**\n"

        options = []
        for province in provinces:
            reply += f"• {province}\n"
            options.append({"label": province, "value": province, "icon": "📍"})

        reply += f"\n👇 Chọn điểm đến bên dưới hoặc gõ tên nơi bạn muốn đi!"

        return {
            "reply": reply,
            "ui_type": "options",
            "ui_data": {
                "options": options,
                "actions": [{"label": p, "value": p} for p in provinces[:5]],
            },
            "context": context.to_dict(),
            "status": "partial",
        }

    async def _handle_cost_from_context(
        self, context, multi_intent, user_message: str = ""
    ) -> Optional[Dict[str, Any]]:
        """
        Calculate cost from conversation context with SMART per-day breakdown.

        Handles special cases:
        - Ở nhà bạn bè / về nhà → No accommodation cost
        - Địa điểm miễn phí (chùa, công viên) → Reduced activity cost
        - Ngày cuối về nhà → No accommodation
        """

        location = multi_intent.location or getattr(context, "destination", None)
        duration = multi_intent.duration or getattr(context, "duration", None)

        # Fallback: Try to extract location from user message if not found
        if not location or not duration:
            extracted_location, extracted_duration = (
                self._extract_location_and_duration_from_query(user_message)
            )
            if not location:
                location = extracted_location
            if not duration:
                duration = extracted_duration

        # Default duration if still not found
        if not duration:
            duration = 3

        if not location:
            return {
                "reply": "Bạn muốn tính chi phí cho chuyến đi đến đâu? 🗺️\n"
                "Hãy cho tôi biết điểm đến và số ngày để tôi ước tính!",
                "ui_type": "cost_prompt",
                "context": context.to_dict(),
                "status": "partial",
            }

        # Update context with extracted values
        if location:
            context.destination = location
        if duration:
            context.duration = duration

        # Get itinerary if available for smart calculation
        last_itinerary = getattr(context, "last_itinerary", None)

        # Calculate per-day costs
        daily_costs = await self._calculate_smart_daily_costs(
            location=location,
            duration=duration,
            context=context,
            itinerary=last_itinerary,
        )

        # Generate detailed response
        cost_text = self._format_smart_cost_response(location, daily_costs)

        return {
            "reply": cost_text,
            "ui_type": "cost_breakdown",
            "ui_data": {
                "daily_costs": daily_costs,
                "location": location,
                "duration": len(daily_costs),
            },
            "context": context.to_dict(),
            "status": "partial",
        }

    async def _calculate_smart_daily_costs(
        self, location: str, duration: int, context, itinerary: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Calculate costs per day with smart logic.

        Considers:
        - Accommodation type (hotel, friend's house, home)
        - Activity types (paid attractions, free spots)
        - Transportation needs
        - Meal arrangements
        """
        daily_costs = []

        # Default prices (can be customized per location)
        default_prices = self._get_location_default_prices(location)

        # Get selected hotel price if available (priority: selected_hotel_price > default)
        selected_hotel = getattr(context, "selected_hotel", None)
        selected_hotel_price = getattr(context, "selected_hotel_price", None)
        hotel_price = (
            selected_hotel_price if selected_hotel_price else default_prices["hotel"]
        )

        if selected_hotel and selected_hotel_price:
            logger.info(
                f"💰 Using selected hotel price: {selected_hotel} - {selected_hotel_price:,} VNĐ/đêm"
            )

        for day_num in range(1, duration + 1):
            day_cost = {
                "day": day_num,
                "accommodation": {"cost": 0, "note": ""},
                "activities": {"cost": 0, "items": []},
                "food": {"cost": 0, "note": ""},
                "transport": {"cost": 0, "note": ""},
                "total": 0,
            }

            # Get day's activities from itinerary if available
            day_activities = (
                self._get_day_activities(itinerary, day_num) if itinerary else []
            )

            # === ACCOMMODATION ===
            is_last_day = day_num == duration
            accommodation_type = self._detect_accommodation_type(
                day_activities, is_last_day
            )

            if accommodation_type == "hotel":
                day_cost["accommodation"]["cost"] = hotel_price
                day_cost["accommodation"]["note"] = "Khách sạn"
            elif accommodation_type == "friend":
                day_cost["accommodation"]["cost"] = 0
                day_cost["accommodation"]["note"] = "Ở nhà bạn bè"
            elif accommodation_type == "home":
                day_cost["accommodation"]["cost"] = 0
                day_cost["accommodation"]["note"] = "Về nhà"
            else:
                # Default for non-last day
                day_cost["accommodation"]["cost"] = hotel_price
                day_cost["accommodation"]["note"] = "Khách sạn"

            # === ACTIVITIES ===
            activity_cost, activity_items = self._calculate_activity_costs(
                day_activities, default_prices
            )
            day_cost["activities"]["cost"] = activity_cost
            day_cost["activities"]["items"] = activity_items

            # === FOOD ===
            food_cost, food_note = self._calculate_food_costs(
                day_activities, default_prices
            )
            day_cost["food"]["cost"] = food_cost
            day_cost["food"]["note"] = food_note

            # === TRANSPORT ===
            transport_cost = self._calculate_transport_costs(
                day_num, duration, day_activities, default_prices
            )
            day_cost["transport"]["cost"] = transport_cost
            day_cost["transport"]["note"] = (
                "Di chuyển nội thành" if day_num not in [1, duration] else "Di chuyển"
            )

            # Calculate day total
            day_cost["total"] = (
                day_cost["accommodation"]["cost"]
                + day_cost["activities"]["cost"]
                + day_cost["food"]["cost"]
                + day_cost["transport"]["cost"]
            )

            daily_costs.append(day_cost)

        return daily_costs

    def _get_location_default_prices(self, location: str) -> Dict:
        """Get default prices based on location tier"""
        location_lower = location.lower()

        # Tier 1: Major tourist destinations (higher prices)
        tier1 = ["đà nẵng", "nha trang", "phú quốc", "sapa", "đà lạt"]
        # Tier 2: Medium cities
        tier2 = ["hội an", "huế", "hạ long", "ninh bình", "quy nhơn"]

        if any(loc in location_lower for loc in tier1):
            return {
                "hotel": 600_000,  # 600k/đêm
                "food": 350_000,  # 350k/ngày
                "transport": 250_000,  # 250k/ngày
                "activity": 200_000,  # 200k trung bình mỗi điểm
            }
        elif any(loc in location_lower for loc in tier2):
            return {
                "hotel": 450_000,
                "food": 280_000,
                "transport": 180_000,
                "activity": 150_000,
            }
        else:
            # Default pricing
            return {
                "hotel": 400_000,
                "food": 250_000,
                "transport": 150_000,
                "activity": 100_000,
            }

    def _get_day_activities(self, itinerary: Dict, day_num: int) -> List[str]:
        """Extract activities for a specific day from itinerary"""
        if not itinerary:
            return []

        days = itinerary.get("days", [])
        if day_num <= len(days):
            day_data = days[day_num - 1]
            if isinstance(day_data, dict):
                return day_data.get("activities", [])
            elif isinstance(day_data, list):
                return day_data
        return []

    def _detect_accommodation_type(self, activities: List, is_last_day: bool) -> str:
        """Detect accommodation type from activities"""
        activities_text = " ".join(str(a).lower() for a in activities)

        # Check for friend's house
        friend_keywords = [
            "nhà bạn",
            "bạn bè",
            "nhà người thân",
            "nhà họ hàng",
            "ở nhờ",
        ]
        if any(kw in activities_text for kw in friend_keywords):
            return "friend"

        # Check for going home
        home_keywords = ["về nhà", "trở về", "quay về", "kết thúc"]
        if is_last_day or any(kw in activities_text for kw in home_keywords):
            return "home"

        return "hotel"

    def _calculate_activity_costs(
        self, activities: List, default_prices: Dict
    ) -> tuple:
        """Calculate activity costs with smart detection"""

        # Free activities
        free_keywords = [
            "chùa",
            "đền",
            "miếu",
            "công viên",
            "bãi biển",
            "phố cổ",
            "chợ",
            "ngắm",
            "dạo",
            "chụp ảnh",
            "thiên nhiên",
            "hoàng hôn",
            "bình minh",
        ]

        # Paid attractions (with approximate prices)
        paid_attractions = {
            "vinpearl": 800_000,
            "bà nà": 900_000,
            "sun world": 700_000,
            "safari": 600_000,
            "aquarium": 200_000,
            "bảo tàng": 50_000,
            "fansipan": 750_000,
            "cable car": 400_000,
            "cáp treo": 400_000,
            "vé tham quan": 100_000,
        }

        total_cost = 0
        items = []

        activities_text = " ".join(str(a).lower() for a in activities)

        # Check for paid attractions
        for attraction, price in paid_attractions.items():
            if attraction in activities_text:
                total_cost += price
                items.append({"name": attraction.title(), "cost": price})

        # If no specific paid attractions found, estimate based on activity count
        if not items and activities:
            # Check if mostly free activities
            is_mostly_free = any(kw in activities_text for kw in free_keywords)
            if is_mostly_free:
                total_cost = 50_000  # Small incidentals
                items.append({"name": "Tham quan miễn phí", "cost": 50_000})
            else:
                # Default activity cost
                total_cost = default_prices["activity"] * min(2, len(activities))
                items.append({"name": "Tham quan", "cost": total_cost})

        return total_cost, items

    def _calculate_food_costs(self, activities: List, default_prices: Dict) -> tuple:
        """Calculate food costs"""
        activities_text = " ".join(str(a).lower() for a in activities)

        # Check for self-cooking or friend's house
        if any(kw in activities_text for kw in ["tự nấu", "nhà bạn", "ở nhà"]):
            return 100_000, "Nấu ăn tại chỗ"

        # Check for street food
        if any(kw in activities_text for kw in ["ăn vặt", "chợ", "quán nhỏ"]):
            return default_prices["food"] * 0.7, "Ăn bình dân"

        # Default
        return default_prices["food"], "Ăn uống"

    def _calculate_transport_costs(
        self, day_num: int, duration: int, activities: List, default_prices: Dict
    ) -> int:
        """Calculate transport costs"""

        # First day may have airport/bus transfer
        if day_num == 1:
            return default_prices["transport"] * 1.5

        # Last day - return trip
        if day_num == duration:
            return default_prices["transport"] * 1.5

        # Middle days - local transport
        return default_prices["transport"]

    def _format_smart_cost_response(
        self, location: str, daily_costs: List[Dict]
    ) -> str:
        """Format smart cost breakdown as markdown"""

        total_all = sum(d["total"] for d in daily_costs)
        duration = len(daily_costs)

        text = f"� **Chi phí chi tiết {duration} ngày tại {location}:**\n\n"

        # Summary totals
        total_accommodation = sum(d["accommodation"]["cost"] for d in daily_costs)
        total_activities = sum(d["activities"]["cost"] for d in daily_costs)
        total_food = sum(d["food"]["cost"] for d in daily_costs)
        total_transport = sum(d["transport"]["cost"] for d in daily_costs)

        text += "📊 **Tổng quan:**\n"
        text += f"🏨 Lưu trú: **{total_accommodation:,.0f}** VNĐ\n"
        text += f"🎫 Tham quan: **{total_activities:,.0f}** VNĐ\n"
        text += f"🍜 Ăn uống: **{total_food:,.0f}** VNĐ\n"
        text += f"🚕 Di chuyển: **{total_transport:,.0f}** VNĐ\n"
        text += f"\n**💵 TỔNG CỘNG: {total_all:,.0f} VNĐ**\n"

        # Per-day breakdown
        text += f"\n{'─'*30}\n"
        text += "📅 **Chi tiết từng ngày:**\n\n"

        for day in daily_costs:
            day_num = day["day"]
            text += f"**Ngày {day_num}:** {day['total']:,.0f} VNĐ\n"

            if day["accommodation"]["cost"] > 0:
                text += f"  • Lưu trú: {day['accommodation']['cost']:,.0f} ({day['accommodation']['note']})\n"
            elif day["accommodation"]["note"]:
                text += f"  • Lưu trú: 0 ({day['accommodation']['note']})\n"

            if day["activities"]["cost"] > 0:
                items_str = ", ".join(i["name"] for i in day["activities"]["items"])
                text += (
                    f"  • Tham quan: {day['activities']['cost']:,.0f} ({items_str})\n"
                )

            text += f"  • Ăn uống: {day['food']['cost']:,.0f}\n"
            text += f"  • Di chuyển: {day['transport']['cost']:,.0f}\n"
            text += "\n"

        text += "_* Chi phí ước tính, có thể thay đổi theo lựa chọn thực tế._"

        return text

    async def _create_smart_fallback(
        self, user_message: str, multi_intent, context
    ) -> Dict[str, Any]:
        """Create a smart fallback response when no tasks are created"""

        location = multi_intent.location or getattr(context, "destination", None)

        if location:
            # Update context with location
            context.destination = location

            # FIX: Get location-specific highlights from LOCATION_HIGHLIGHTS dict
            location_lower = location.lower()
            loc_info = LOCATION_HIGHLIGHTS.get(
                location_lower,
                {
                    "icon": "🌟",
                    "tagline": "điểm đến hấp dẫn",
                    "highlights": "Nhiều địa điểm tham quan thú vị",
                    "tags": ["du lịch", "khám phá"],
                },
            )

            icon = loc_info.get("icon", "🌟")
            tagline = loc_info.get("tagline", "điểm đến hấp dẫn")
            highlights = loc_info.get("highlights", "Nhiều địa điểm tham quan")
            tags = ", ".join(loc_info.get("tags", ["du lịch"]))

            # We have location but no tasks - prompt for more details with GenUI options
            return {
                "reply": f"{icon} **{location}** - {tagline}!\n\n"
                f"📍 Điểm nổi bật: {highlights} ✨ Phù hợp cho: {tags}\n\n"
                f"Để tôi lên kế hoạch tốt nhất cho bạn, cho tôi biết thêm:\n"
                f"1️⃣ **Bạn đi mấy ngày?** (VD: 3 ngày 2 đêm) "
                f"2️⃣ **Đi mấy người?** "
                f"3️⃣ **Ngân sách khoảng bao nhiêu?** (VD: 5 triệu/người) "
                f"4️⃣ **Bạn thích gì?** (biển, núi, ẩm thực, văn hóa...)\n\n"
                f'💡 Hoặc nói: "Lên lịch trình {location} 3 ngày 5 triệu"',
                "ui_type": "options",
                "ui_data": {
                    "title": "Chọn nhanh số ngày",
                    "options": [
                        f"Lên lịch trình {location} 2 ngày",
                        f"Lên lịch trình {location} 3 ngày",
                        f"Lên lịch trình {location} 5 ngày",
                        f"Tìm khách sạn {location}",
                        f"Địa điểm tham quan {location}",
                    ],
                },
                "context": context.to_dict(),
                "status": "partial",
            }

        # No location, no specific request - guide user with GenUI
        return {
            "reply": "Xin chào! Tôi là **Saola Travel AI** �\n\n"
            "Tôi có thể giúp bạn:\n"
            "🗺️ Lên lịch trình du lịch\n"
            "🏨 Tìm khách sạn phù hợp\n"
            "📍 Gợi ý địa điểm tham quan\n"
            "🍜 Đề xuất quán ăn ngon\n\n"
            "**Bạn muốn đi đâu?**",
            "ui_type": "options",
            "ui_data": {
                "title": "Địa điểm phổ biến",
                "options": [
                    "Du lịch Đà Nẵng",
                    "Du lịch Hội An",
                    "Du lịch Nha Trang",
                    "Du lịch Phú Quốc",
                    "Du lịch Sapa",
                ],
            },
            "context": context.to_dict(),
            "status": "partial",
        }

    async def _check_info_gathering_needed(
        self, multi_intent, context, user_message: str
    ) -> Optional[Dict[str, Any]]:
        """
        Check if we need to gather more information before planning.

        SMART CONVERSATION FLOW:
        - If user just mentions location without details → Ask questions
        - If user provides location + duration/budget → Proceed with planning
        - If user asks specific questions (hotels, spots) → Answer directly

        Returns response dict if info gathering needed, None to proceed with planning
        """
        location = multi_intent.location
        duration = multi_intent.duration
        intent = multi_intent.primary_intent

        # If user is asking for specific info (hotels, spots, food) → Don't block
        specific_intents = [
            "find_hotel",
            "find_spot",
            "find_food",
            "calculate_cost",
            "more_spots",
            "more_hotels",
            "more_food",
        ]
        if intent in specific_intents:
            return None  # Proceed with normal flow

        # Check if user is directly asking about places/spots - bypass info gathering
        query_lower = user_message.lower()
        direct_spot_patterns = [
            "địa điểm",
            "dia diem",
            "chỗ nào",
            "cho nao",
            "đi đâu",
            "di dau",
            "thăm quan",
            "tham quan",
            "tham quan",
            "điểm đến",
            "diem den",
            "nơi nào",
            "noi nao",
            "chỗ chơi",
            "cho choi",
            "đi chơi ở đâu",
            "có gì",
            "co gi",
        ]
        if any(p in query_lower for p in direct_spot_patterns):
            return None  # User asking about spots directly, proceed

        # If user wants full trip planning with enough info → START INTERACTIVE BUILDER
        if intent == "plan_trip" and location and duration:
            logger.info(
                f"🗓️ [ASYNC] Triggering interactive itinerary builder for {location}, {duration} days"
            )
            # Start interactive itinerary builder
            builder_response = self._start_interactive_itinerary_sync(
                location, duration, context
            )
            if builder_response:
                return builder_response
            # If builder failed, proceed with normal flow
            return None

        # If user just mentions wanting to go somewhere without details
        # Check if query is simple location mention
        simple_location_patterns = [
            "muốn đi",
            "muon di",  # With and without accent
            "đi đến",
            "di den",
            "đến",
            "den",
            "thăm",
            "tham",
            "du lịch",
            "du lich",
            "đi chơi",
            "di choi",
            "tới",
            "toi",
            "qua",  # "qua Đà Nẵng"
        ]

        is_simple_location_query = (
            location
            and not duration
            and any(pattern in query_lower for pattern in simple_location_patterns)
            and intent not in specific_intents
        )

        if is_simple_location_query:
            # User just said "I want to go to X" - Ask for more details
            return await self._create_location_intro_response(location, context)

        # === NEW: Handle when user wants to travel but NO location specified ===
        # e.g., "Tôi muốn đi du lịch", "Lên kế hoạch du lịch", "Tư vấn du lịch"
        no_location_travel_patterns = [
            "muốn đi du lịch",
            "muon di du lich",
            "đi du lịch",
            "di du lich",
            "lên kế hoạch",
            "len ke hoach",
            "tư vấn du lịch",
            "tu van du lich",
            "lập kế hoạch",
            "lap ke hoach",
            "giúp tôi lên lịch",
            "giup toi len lich",
            "kế hoạch du lịch",
            "ke hoach du lich",
            "chuyến đi",
            "chuyen di",
            "muốn đi chơi",
            "muon di choi",
        ]

        is_general_travel_query = (
            not location
            and not context.destination
            and any(pattern in query_lower for pattern in no_location_travel_patterns)
        )

        if is_general_travel_query:
            # User wants to travel but hasn't said where → Show province options
            return await self._create_destination_selection_response(context)

        # Default: proceed with normal flow
        return None

    async def _create_destination_selection_response(self, context) -> Dict[str, Any]:
        """Create response asking user to select destination"""

        response = "🌟 **Chào mừng bạn đến với Travel Assistant!**\n\n"
        response += (
            "Việt Nam có rất nhiều điểm đến tuyệt vời. Bạn muốn khám phá vùng nào?\n\n"
        )
        response += "🏖️ **Biển đảo**: Đà Nẵng, Nha Trang, Phú Quốc\n"
        response += "🏔️ **Núi rừng**: Đà Lạt, Sapa, Hà Giang\n"
        response += "🏛️ **Văn hóa**: Hà Nội, Huế, Hội An\n"
        response += "🌆 **Đô thị**: TP.HCM, Cần Thơ\n\n"
        response += "👇 **Chọn điểm đến bên dưới hoặc gõ tên nơi bạn muốn đi:**"

        # Popular destinations as options
        options = ["🏖️ Đà Nẵng", "🏔️ Đà Lạt", "🏝️ Phú Quốc", "🌆 Hà Nội", "🏛️ Huế"]

        return {
            "reply": response,
            "ui_type": "options",
            "ui_data": {
                "title": "Chọn điểm đến",
                "options": options,
                "awaiting_destination": True,
            },
            "status": "partial",
            "context": context.to_dict(),
        }

    async def _create_location_intro_response(
        self, location: str, context
    ) -> Dict[str, Any]:
        """Create a friendly intro for a location and gather trip details"""

        # Use global LOCATION_HIGHLIGHTS
        loc_key = location.lower()
        loc_info = LOCATION_HIGHLIGHTS.get(loc_key, LOCATION_HIGHLIGHTS["default"])

        # Map from global format to local format
        info = {
            "emoji": loc_info.get("icon", "🌍"),
            "tagline": loc_info.get("tagline", "điểm đến hấp dẫn"),
            "highlights": (
                loc_info.get("highlights", "").split(", ")
                if isinstance(loc_info.get("highlights"), str)
                else []
            ),
            "best_for": ", ".join(loc_info.get("tags", ["khám phá"])),
        }

        # Build response
        response = f"{info['emoji']} **{location}** - {info['tagline']}!\n\n"

        if info["highlights"]:
            response += "📍 Điểm nổi bật: " + ", ".join(info["highlights"][:3]) + "\n"

        response += f"✨ Phù hợp cho: {info['best_for']}\n\n"

        response += "---\n\n"
        response += "Để tôi lên kế hoạch tốt nhất cho bạn, cho tôi biết thêm:\n\n"
        response += "1️⃣ **Bạn đi mấy ngày?** (VD: 3 ngày 2 đêm)\n"
        response += "2️⃣ **Đi mấy người?**\n"
        response += "3️⃣ **Ngân sách khoảng bao nhiêu?** (VD: 5 triệu/người)\n"
        response += "4️⃣ **Bạn thích gì?** (biển, núi, ẩm thực, văn hóa...)\n\n"
        response += f'💡 _Hoặc nói: "Lên lịch trình {location} 3 ngày 5 triệu"_'

        # Store location in context for follow-up
        context.destination = location

        # Generate GenUI options for quick selection
        options = [
            f"Lên lịch trình {location} 2 ngày",
            f"Lên lịch trình {location} 3 ngày",
            f"Lên lịch trình {location} 5 ngày",
            f"Tìm khách sạn {location}",
            f"Địa điểm tham quan {location}",
        ]

        return {
            "reply": response,
            "ui_type": "options",
            "ui_data": {
                "title": "Chọn nhanh",
                "options": options,
                "location": location,
                "awaiting_details": True,
            },
            "status": "partial",
            "context": context.to_dict(),
        }

    def _execute_plan_subset(
        self, tasks: List, original_query: str, aggregated_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Execute a subset of tasks (for streaming)

        Args:
            tasks: List of SubTask to execute
            original_query: Original user message
            aggregated_data: Data from previous groups (spots, hotels, food) for dependencies
        """
        results = {}
        aggregated_data = aggregated_data or {}

        for task in tasks:
            try:
                start = time.time()
                task_type = task.task_type.value

                if task_type not in self.experts:
                    logger.warning(f"⚠️ No expert for {task_type}")
                    results[task.task_id] = None
                    continue

                expert = self.experts[task_type]

                # Prepare parameters like _execute_plan() does
                parameters = dict(task.parameters)
                if original_query:
                    parameters["original_query"] = original_query

                # CRITICAL: Pass data from previous groups for tasks that have dependencies
                # This is essential for itinerary and cost experts to work correctly
                if task.depends_on:
                    logger.info(
                        f"   📦 Task {task.task_id} depends on: {task.depends_on}"
                    )

                    # Pass spots data if dependency includes spots
                    if any("spots" in dep for dep in task.depends_on):
                        if aggregated_data.get("spots"):
                            parameters["spots_data"] = aggregated_data["spots"]
                            logger.info(
                                f"   ✓ Passing {len(aggregated_data['spots'])} spots to {task.task_id}"
                            )

                    # Pass food data if dependency includes food
                    if any("food" in dep for dep in task.depends_on):
                        if aggregated_data.get("food"):
                            parameters["food_data"] = aggregated_data["food"]
                            logger.info(
                                f"   ✓ Passing {len(aggregated_data['food'])} foods to {task.task_id}"
                            )

                    # Pass hotel data if dependency includes hotel
                    if any("hotel" in dep for dep in task.depends_on):
                        if aggregated_data.get("hotels"):
                            parameters["hotel_data"] = aggregated_data["hotels"]
                            logger.info(
                                f"   ✓ Passing {len(aggregated_data['hotels'])} hotels to {task.task_id}"
                            )

                    # Pass itinerary data for cost calculation
                    if any("itinerary" in dep for dep in task.depends_on):
                        if aggregated_data.get("itinerary"):
                            parameters["itinerary_data"] = aggregated_data["itinerary"]
                            logger.info(f"   ✓ Passing itinerary to {task.task_id}")

                # Execute expert
                result = expert.execute(task.query, parameters)

                elapsed = int((time.time() - start) * 1000)
                count = len(result.data) if result.data else 0
                logger.info(
                    f"   ✓ {task.task_id}: {count} results, {elapsed}ms, success={result.success}"
                )

                results[task.task_id] = result

            except Exception as e:
                logger.error(f"❌ Task {task.task_id} failed: {e}")
                results[task.task_id] = None

        return results

    def _get_last_user_message(self, messages: List[Dict]) -> Optional[str]:
        """Extract last user message from conversation"""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                return msg.get("content", "")
        return None

    # ============================================================
    # STATE GUARD: Chặn Intent "nhảy bước" dựa trên workflow_state
    # ============================================================

    def _validate_intent_flow(self, multi_intent, enhanced_context) -> tuple:
        """
        StateGuard: Lọc danh sách intents dựa trên workflow_state hiện tại.

        Returns:
            (valid_intents: List[str], blocked_reasons: List[str])
        """
        valid_intents = []
        blocked_reasons = []
        current_state = getattr(enhanced_context, "workflow_state", "INITIAL")

        # Get all intents: primary + sub_intents
        all_intents = [multi_intent.primary_intent] + (multi_intent.sub_intents or [])

        for intent in all_intents:
            rule = self.INTENT_DEPENDENCIES.get(intent)

            # Không có rule = cho phép tự do
            if not rule:
                valid_intents.append(intent)
                continue

            # Kiểm tra State
            allowed_states = rule.get("required_states", [])
            state_ok = current_state in allowed_states if allowed_states else True

            # Kiểm tra required fields trong context
            required_fields = rule.get("required_fields", [])
            fields_ok = all(
                getattr(enhanced_context, field, None) is not None
                for field in required_fields
            )

            if state_ok and fields_ok:
                valid_intents.append(intent)
            else:
                blocked_reasons.append(
                    {
                        "intent": intent,
                        "reason": rule.get("error_msg"),
                        "action": rule.get("error_action"),
                    }
                )
                logger.info(
                    f"🚫 StateGuard blocked: {intent} (state={current_state}, fields_ok={fields_ok})"
                )

        return valid_intents, blocked_reasons

    def _generate_state_guard_response(
        self, blocked_reasons: list, enhanced_context
    ) -> dict:
        """
        Tạo response thông minh khi Intent bị chặn.
        Dùng LLM để giải thích khéo léo thay vì template cứng.
        """
        if not blocked_reasons:
            return None

        # Lấy lý do đầu tiên (ưu tiên)
        first_block = blocked_reasons[0]
        error_msg = first_block.get("reason", "Hãy hoàn thành các bước trước nhé!")
        error_action = first_block.get("action")

        # Xác định UI phù hợp
        ui_type = "options"
        actions = []

        if error_action == "prompt_hotel":
            actions = [
                {"label": "🏨 Tìm khách sạn", "action": "find_hotel"},
                {"label": "📋 Xem lịch trình", "action": "view_itinerary"},
            ]
        elif error_action == "prompt_destination":
            actions = [{"label": "🗺️ Gợi ý điểm đến", "action": "suggest_destinations"}]

        return {
            "reply": error_msg,
            "ui_type": ui_type,
            "ui_data": {"actions": actions} if actions else {},
            "status": "blocked",
            "workflow_state": enhanced_context.workflow_state,
            "context": enhanced_context.to_dict(),
        }

    def _should_stay_in_builder(
        self, multi_intent, enhanced_context, user_message: str
    ) -> bool:
        """
        Kiểm tra xem user có đang trong Itinerary Builder không.
        Nếu có, ưu tiên giữ họ ở lại thay vì nhảy sang Intent khác.
        """
        current_state = getattr(enhanced_context, "workflow_state", "INITIAL")

        # PRIORITY 0: FIX 2026-01-18 - Don't stay in builder if workflow is FINALIZED
        if current_state == "FINALIZED":
            logger.info("✅ Workflow FINALIZED - not staying in builder")
            return False

        # PRIORITY 1: Check if user is giving NEW planning requirements
        intent = multi_intent.primary_intent if multi_intent else None

        # FIX 2026-01-18: Allow certain intents to bypass builder mode
        bypass_intents = [
            "get_weather_forecast",
            "get_distance",
            "get_directions",
            "calculate_cost",
            "show_itinerary",
            "book_hotel",
            "get_location_tips",
            "get_spot_detail",
        ]
        if intent in bypass_intents:
            logger.info(f"🔓 Intent '{intent}' bypasses builder mode")
            return False

        # Đang trong builder? (ĐÃ CÓ itinerary_builder object)
        has_builder = enhanced_context.itinerary_builder is not None

        # If ĐÃ ĐANG trong builder (có spots, có state) mà lại có intent "plan_trip"
        # → Chắc chắn là muốn lập kế hoạch MỚI, không phải nhập ngày
        if has_builder and intent in ["planning", "itinerary_planning", "plan_trip"]:
            logger.info(
                f"🔄 User in active builder but has plan_trip intent - allowing restart to new trip"
            )
            return False

        # CHƯA có builder (đang đợi nhập ngày khởi hành)
        if not has_builder:
            # If waiting for start_date (state = CHOOSING_SPOTS but no builder yet)
            # Stay in builder flow to process date input
            if current_state == "CHOOSING_SPOTS":
                logger.info("📅 Waiting for start_date - staying in builder flow")
                return True
            return False

        # State đang là CHOOSING_SPOTS hoặc CHOOSING_HOTEL
        if current_state in ["CHOOSING_SPOTS", "CHOOSING_HOTEL"]:
            # Check for new requirements in MultiIntent attributes
            if multi_intent:
                has_new_requirements = (
                    multi_intent.duration is not None
                    or multi_intent.budget is not None
                    or multi_intent.people_count
                    != getattr(enhanced_context, "people_count", 1)
                    or multi_intent.location is not None
                )
                if has_new_requirements:
                    logger.info(
                        f"🔄 New requirements detected - duration:{multi_intent.duration}, budget:{multi_intent.budget}, people:{multi_intent.people_count}, location:{multi_intent.location} - allowing restart"
                    )
                    return False

            # Chỉ thoát builder nếu user YÊU CẦU ĐÍCH DANH
            explicit_exit_keywords = [
                "hủy lịch",
                "hủy trip",
                "không cần nữa",
                "bỏ qua",
                "reset",
                "làm lại từ đầu",
                "đổi điểm đến",
            ]
            lower_msg = user_message.lower()

            if any(kw in lower_msg for kw in explicit_exit_keywords):
                logger.info(f"🚪 User explicitly exiting builder: {user_message[:30]}")
                return False

            # Mặc định: GIỮ user ở builder
            return True

        return False

    def _is_finalize_signal(self, user_message: str) -> bool:
        """
        Nhận diện các tín hiệu "hoàn tất bước hiện tại" từ user.
        Dùng kết hợp keywords đơn giản + LLM flow_action.
        """
        lower_msg = user_message.lower().strip()

        finalize_signals = [
            "xong",
            "done",
            "tiếp",
            "tiếp tục",
            "next",
            "được rồi",
            "ok rồi",
            "oke",
            "được",
            "tiếp đi",
            "chuyển sang",
            "bước tiếp",
            "hoàn tất",
            "kết thúc",
        ]

        # Check exact match hoặc starts with
        for signal in finalize_signals:
            if lower_msg == signal or lower_msg.startswith(signal + " "):
                return True

        return False

    def _is_backtrack_signal(self, user_message: str) -> bool:
        """
        Nhận diện tín hiệu user muốn QUAY LẠI chỉnh sửa lịch trình.
        Ví dụ: "thêm địa điểm", "sửa lại ngày 2", "thêm 1 chỗ check-in", etc.
        """
        lower_msg = user_message.lower().strip()

        backtrack_signals = [
            # Thêm địa điểm
            "thêm địa điểm",
            "thêm điểm",
            "thêm chỗ",
            "thêm spot",
            "thêm cho mình",
            "thêm 1",
            "thêm một",
            "add more",
            # Sửa lịch
            "sửa lịch",
            "chỉnh lịch",
            "thay đổi",
            "đổi lại",
            "modify",
            # Quay lại
            "quay lại",
            "back",
            "go back",
            "trở lại",
            # Bỏ / thay thế
            "bỏ",
            "xóa",
            "remove",
            "thay bằng",
            "đổi sang",
        ]

        # Check substring match
        for signal in backtrack_signals:
            if signal in lower_msg:
                return True

        # Check for day modification patterns
        import re

        day_modify_pattern = r"(ngày\s*\d+|day\s*\d+).*(thêm|sửa|xóa|bỏ|đổi)"
        if re.search(day_modify_pattern, lower_msg):
            return True

        return False

    def _restore_context(self, context: Dict = None) -> ConversationContext:
        """Restore or create conversation context (legacy)"""
        if not context:
            return ConversationContext()

        return ConversationContext(
            destination=context.get("destination"),
            duration=context.get("duration"),
            budget=context.get("budget"),
            budget_level=context.get("budget_level"),
            people_count=context.get("people_count", 1),
            interests=context.get("interests", []),
            last_intent=context.get("last_intent"),
            selected_hotel=context.get("selected_hotel"),
        )

    def _restore_enhanced_context(self, context: Dict = None):
        """Restore or create enhanced conversation context with memory"""
        if not context:
            return self.EnhancedConversationContext()

        enhanced = self.EnhancedConversationContext(
            destination=context.get("destination"),
            duration=context.get("duration"),
            budget=context.get("budget"),
            budget_level=context.get("budget_level"),
            people_count=context.get("people_count", 1),
            companion_type=context.get("companion_type"),
            interests=context.get("interests", []),
            last_intent=context.get("last_intent"),
            selected_hotel=context.get("selected_hotel"),
            selected_hotel_price=context.get("selected_hotel_price"),
            selected_spots=context.get(
                "selected_spots", []
            ),  # 🆕 RESTORE selected_spots
            answered_intents=context.get("answered_intents", []),
            conversation_summary=context.get("conversation_summary", ""),
            # Restore last search results for follow-up queries
            last_spots=context.get("last_spots", []),
            last_hotels=context.get("last_hotels", []),
            last_foods=context.get("last_foods", []),
            # Restore workflow state machine fields
            workflow_state=context.get("workflow_state", "INITIAL"),
            spots_selected_per_day=context.get("spots_selected_per_day", {}),
            hotels_selected_per_day=context.get("hotels_selected_per_day", {}),
        )

        # Restore itinerary builder state
        if "itinerary_builder" in context:
            enhanced.itinerary_builder = context["itinerary_builder"]

        # Restore saved itinerary for recall
        if "last_itinerary" in context:
            enhanced.last_itinerary = context["last_itinerary"]

        # Restore chat history if available
        if "chat_history" in context:
            from app.services.conversation_memory import ChatMessage

            enhanced.chat_history = [
                ChatMessage(**msg) if isinstance(msg, dict) else msg
                for msg in context["chat_history"][-10:]  # Keep last 10
            ]

        return enhanced

    def _execute_plan(self, plan, original_query: str = None) -> Dict[str, Any]:
        """Execute plan tasks using experts

        Args:
            plan: ExecutionPlan with tasks to execute
            original_query: Original user message (to preserve semantic intent)
        """
        results = {}

        # Get parallel task groups
        task_groups = plan.get_parallel_tasks()

        for group in task_groups:
            # Execute tasks in this group
            # (In a real implementation, these could run in parallel)
            for task in group:
                task_type = task.task_type.value

                if task_type in self.experts:
                    expert = self.experts[task_type]

                    # Add data from previous tasks if this task depends on them
                    parameters = dict(task.parameters)

                    # CRITICAL: Add original user query to preserve semantic intent
                    if original_query:
                        parameters["original_query"] = original_query

                    for dep_id in task.depends_on:
                        if dep_id in results:
                            # Pass data from dependency
                            dep_result = results[dep_id]
                            if "spots" in dep_id:
                                parameters["spots_data"] = dep_result.data
                            elif "food" in dep_id:
                                parameters["food_data"] = dep_result.data
                            elif "hotel" in dep_id:
                                parameters["hotel_data"] = dep_result.data

                    # Execute expert
                    result = expert.execute(task.query, parameters)
                    results[task.task_id] = result

                    logger.info(
                        f"   ✓ {task.task_id}: {len(result.data)} results, {result.execution_time_ms}ms"
                    )

        return results

    def _aggregate_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Aggregate results from all experts"""
        aggregated = {
            "spots": [],
            "hotels": [],
            "food": [],
            "itinerary": [],
            "costs": None,
            "general_info": [],
            "summaries": [],
        }

        for task_id, result in results.items():
            if not result or not result.success:
                continue

            # Categorize results
            if "spots" in task_id:
                aggregated["spots"].extend(result.data)
            elif "hotel" in task_id:
                aggregated["hotels"].extend(result.data)
            elif "food" in task_id:
                aggregated["food"].extend(result.data)
            elif "itinerary" in task_id:
                aggregated["itinerary"] = result.data
            elif "cost" in task_id:
                aggregated["costs"] = result.data[0] if result.data else None
            elif "info" in task_id:
                aggregated["general_info"].extend(result.data)

            if result.summary:
                aggregated["summaries"].append(result.summary)

        return aggregated

    def _generate_response(
        self,
        intent,
        aggregated: Dict[str, Any],
        context: ConversationContext,
        original_query: str,
    ) -> Dict[str, Any]:
        """Generate final response based on intent and aggregated data"""

        intent_type = intent.intent

        # Route to appropriate response generator
        if intent_type == "plan_trip":
            return self._generate_planning_response(intent, aggregated, context)
        elif intent_type == "find_hotel":
            return self._generate_hotel_response(intent, aggregated, context)
        elif intent_type == "find_food":
            return self._generate_food_response(intent, aggregated, context)
        elif intent_type == "find_spot":
            return self._generate_spot_response(intent, aggregated, context)
        else:
            return self._generate_general_response(
                intent, aggregated, context, original_query
            )

    def _generate_planning_response(self, intent, aggregated, context) -> Dict:
        """Generate response for trip planning"""

        location = intent.location or context.destination or "địa điểm"
        duration = intent.duration or context.duration or 2

        # Build reply
        reply_parts = []

        # Header
        reply_parts.append(f"🗓️ **Lịch trình {duration} ngày tại {location}**\n")

        # Itinerary
        if aggregated["itinerary"]:
            for day in aggregated["itinerary"]:
                day_num = day.get("day", "?")
                title = day.get("title", f"Ngày {day_num}")
                reply_parts.append(f"\n**{title}**")

                for activity in day.get("activities", []):
                    time_str = activity.get("time", "")
                    activity_name = activity.get("activity", "")
                    reply_parts.append(f"- {time_str}: {activity_name}")
        else:
            # Show spots instead
            reply_parts.append("\n**Địa điểm gợi ý:**")
            for spot in aggregated["spots"][:5]:
                name = spot.get("name", "?")
                rating = spot.get("rating", 0)
                reply_parts.append(f"- ⭐ {name} ({rating}/5)")

        # Costs
        if aggregated["costs"]:
            total = aggregated["costs"].get("total", 0)
            reply_parts.append(f"\n💰 **Tổng chi phí dự kiến:** {total:,.0f} VNĐ")

        # Hotels
        if aggregated["hotels"]:
            reply_parts.append("\n🏨 **Khách sạn gợi ý:**")
            for hotel in aggregated["hotels"][:3]:
                name = hotel.get("name", "?")
                price = hotel.get("price_formatted", "")
                reply_parts.append(f"- {name} - {price}")

        # UI options
        ui_options = [
            "📝 Xem lịch trình chi tiết",
            "🏨 Đổi khách sạn khác",
            "💰 Tính lại chi phí",
            "🔄 Làm lại với điều kiện khác",
        ]

        return {
            "reply": "\n".join(reply_parts),
            "ui_type": "options",
            "ui_data": {"options": ui_options},
            "intent": "plan_trip",
            "data": {
                "itinerary": aggregated["itinerary"],
                "spots": aggregated["spots"][:5],
                "hotels": aggregated["hotels"][:3],
                "costs": aggregated["costs"],
            },
        }

    def _generate_hotel_response(self, intent, aggregated, context) -> Dict:
        """Generate response for hotel search"""

        hotels = aggregated["hotels"]
        location = intent.location or context.destination or "khu vực"

        if not hotels:
            return {
                "reply": f"❌ Không tìm thấy khách sạn phù hợp ở {location}. Bạn thử tìm với điều kiện khác nhé!",
                "ui_type": "none",
                "intent": "find_hotel",
            }

        reply_parts = [f"🏨 **Khách sạn tại {location}**\n"]

        for i, hotel in enumerate(hotels[:5], 1):
            name = hotel.get("name", "?")
            price = hotel.get("price_formatted", "N/A")
            rating = hotel.get("rating", 0)
            facilities = hotel.get("facilities", "")[:50]

            reply_parts.append(f"**{i}. {name}**")
            reply_parts.append(f"   💵 {price} | ⭐ {rating}/10")
            if facilities:
                reply_parts.append(f"   🏷️ {facilities}...")
            reply_parts.append("")

        # UI options - hotel cards
        hotel_options = [
            {
                "label": h.get("name"),
                "value": h.get("id"),
                "price": h.get("price_formatted"),
            }
            for h in hotels[:5]
        ]

        return {
            "reply": "\n".join(reply_parts),
            "ui_type": "hotel_cards",
            "ui_data": {"hotels": hotel_options},
            "intent": "find_hotel",
            "data": {"hotels": hotels[:5]},
        }

    def _generate_food_response(self, intent, aggregated, context) -> Dict:
        """Generate response for food search"""

        foods = aggregated["food"]
        location = intent.location or context.destination or "khu vực"

        if not foods:
            return {
                "reply": f"🍜 Mình chưa có nhiều thông tin về quán ăn ở {location}. Bạn thử hỏi cụ thể hơn nhé!",
                "ui_type": "none",
                "intent": "find_food",
            }

        reply_parts = [f"🍜 **Ẩm thực {location}**\n"]

        for food in foods[:5]:
            if food.get("type") == "recommendation":
                # Regional specialty
                dishes = food.get("dishes", [])
                reply_parts.append(f"🌟 **Món đặc sản nên thử:**")
                reply_parts.append(f"   {', '.join(dishes[:5])}")
            else:
                name = food.get("name", "?")
                desc = food.get("description", "")[:80]
                rating = food.get("rating", 0)

                reply_parts.append(f"• **{name}** (⭐ {rating})")
                if desc:
                    reply_parts.append(f"  {desc}")
            reply_parts.append("")

        return {
            "reply": "\n".join(reply_parts),
            "ui_type": "none",
            "intent": "find_food",
            "data": {"food": foods[:5]},
        }

    def _generate_spot_response(self, intent, aggregated, context) -> Dict:
        """Generate response for spot search"""

        spots = aggregated["spots"]
        location = intent.location or context.destination or "Việt Nam"

        if not spots:
            return {
                "reply": f"🔍 Không tìm thấy địa điểm phù hợp ở {location}. Bạn thử từ khóa khác nhé!",
                "ui_type": "none",
                "intent": "find_spot",
            }

        reply_parts = [f"📍 **Địa điểm du lịch tại {location}**\n"]

        for i, spot in enumerate(spots[:6], 1):
            name = spot.get("name", "?")
            rating = spot.get("rating", 0)
            # Get description with fallback
            desc = (
                spot.get("description_short")
                or spot.get("description")
                or spot.get("description_full", "")
            )[:100]

            reply_parts.append(f"**{i}. {name}** ⭐ {rating}")
            if desc:
                reply_parts.append(f"   {desc}")
            reply_parts.append("")

        # UI - spot cards
        spot_options = [
            {"label": s.get("name"), "value": s.get("id"), "image": s.get("image")}
            for s in spots[:6]
        ]

        return {
            "reply": "\n".join(reply_parts),
            "ui_type": "spot_cards",
            "ui_data": {"spots": spot_options},
            "intent": "find_spot",
            "data": {"spots": spots[:6]},
        }

    def _generate_general_response(self, intent, aggregated, context, query) -> Dict:
        """Generate response for general questions"""

        # Check if asking about best time to visit
        location = intent.location or context.destination
        query_lower = query.lower()

        if location and any(
            kw in query_lower
            for kw in [
                "khi nào",
                "thời điểm",
                "tháng nào",
                "mùa nào",
                "when to visit",
                "best time",
            ]
        ):
            try:
                best_time_data = self.weather.get_best_time(location)

                return {
                    "reply": best_time_data.get("message", ""),
                    "ui_type": "month_suggestions",
                    "ui_data": {
                        "best_months": best_time_data.get("best_months", []),
                        "avoid_months": best_time_data.get("avoid_months", []),
                    },
                    "intent": "weather_best_time",
                }
            except Exception as e:
                logger.warning(f"⚠️ Weather best time query failed: {e}")
                # Fall through to general LLM response

        # Use LLM to generate response
        if self.llm:
            try:
                # Build context
                location_text = f" về {location}" if location else ""

                prompt = f"""Bạn là hướng dẫn viên du lịch Việt Nam.

Câu hỏi: "{query}"

Hãy trả lời ngắn gọn, hữu ích{location_text}.
Nếu câu hỏi liên quan đến địa điểm cụ thể, hãy gợi ý các hoạt động phù hợp.
"""
                response = self.llm.complete(prompt, temperature=0.7, max_tokens=500)

                return {"reply": response, "ui_type": "none", "intent": "general_qa"}

            except Exception as e:
                logger.error(f"❌ LLM response error: {e}")

        # Fallback response
        return {
            "reply": "Mình có thể giúp bạn lên kế hoạch du lịch, tìm khách sạn, địa điểm tham quan và quán ăn. Bạn muốn đi đâu?",
            "ui_type": "options",
            "ui_data": {
                "options": [
                    "🏝️ Gợi ý địa điểm hot",
                    "🗓️ Lên lịch trình",
                    "🏨 Tìm khách sạn",
                    "🍜 Gợi ý ẩm thực",
                ]
            },
            "intent": "general_qa",
        }

    # === PATCH 2: DISTANCE CALCULATION HELPERS ===

    def _is_distance_query(self, message: str) -> bool:
        """
        Detect if user is asking about distance/travel distance

        Examples:
            - "khoảng cách từ khách sạn đến địa điểm như thế nào"
            - "xa không"
            - "bao xa"
            - "đi lại thế nào"
            - "cách bao xa"
        """
        message_lower = message.lower()
        distance_patterns = [
            "khoảng cách",
            "xa không",
            "xa gần",
            "bao xa",
            "cách bao xa",
            "đi lại",
            "di lai",
            "quãng đường",
            "quang duong",
            "từ khách sạn",
            "tu khach san",
            "từ hotel",
            "tu hotel",
            "đi mất bao lâu",
            "di mat bao lau",
            "mất bao lâu",
            "mat bao lau",
        ]

        return any(pattern in message_lower for pattern in distance_patterns)

    def _extract_spot_names_from_query(self, query: str) -> list:
        """Extract spot names mentioned in distance query"""
        import re

        # Remove common distance query keywords
        cleaned = query.lower()

        # First, try to extract spots between "từ/tu" and "đến/den"
        # Pattern: "từ [SPOT] đến [HOTEL/khách sạn]"
        match = re.search(r"(?:từ|tu)\s+(.+?)\s+(?:đến|den)", cleaned)
        if match:
            spot_part = match.group(1).strip()
            # Remove hotel mentions from this part
            for hotel_keyword in ["khách sạn", "khach san", "hotel"]:
                spot_part = spot_part.replace(hotel_keyword, " ")

            # Split by "và/va" if multiple spots
            spots = []
            for delimiter in [" và ", " va ", ","]:
                if delimiter in spot_part:
                    spots = [s.strip() for s in spot_part.split(delimiter)]
                    break

            if not spots:
                spots = [spot_part.strip()]

            # Filter out short strings
            return [s for s in spots if len(s) > 3]

        # Fallback: just remove keywords and extract
        for keyword in [
            "khoảng cách",
            "khoang cach",
            "từ",
            "tu",
            "đến",
            "den",
            "tính",
            "tinh",
        ]:
            cleaned = cleaned.replace(keyword, " ")

        # Remove hotel mentions
        for hotel_keyword in ["khách sạn", "khach san", "hotel"]:
            cleaned = cleaned.replace(hotel_keyword, " ")

        cleaned = cleaned.strip()
        return [cleaned] if len(cleaned) > 3 else []

    def _handle_distance_query_sync(
        self, multi_intent, context, user_message: str
    ) -> Dict[str, Any]:
        """
        Handle distance calculation queries synchronously
        Calculates distance from selected hotel to itinerary spots
        """
        logger.info(f"📏 Distance query detected: {user_message}")

        # Extract spot names from query
        mentioned_spots = self._extract_spot_names_from_query(user_message)
        logger.info(f"📏 Extracted spot names from query: {mentioned_spots}")

        # Get selected hotel coordinates
        selected_hotel = getattr(context, "selected_hotel", None)

        # Handle both string and dict types for selected_hotel
        if isinstance(selected_hotel, str):
            logger.info(f"📏 Selected hotel from context (string): {selected_hotel}")
            # Need to convert string to dict by fetching from last_hotels
            last_hotels = getattr(context, "last_hotels", [])
            hotel_dict = None
            for h in last_hotels:
                if h.get("name") == selected_hotel:
                    hotel_dict = h
                    break
            selected_hotel = hotel_dict
        elif isinstance(selected_hotel, dict):
            logger.info(
                f"📏 Selected hotel from context (dict): {selected_hotel.get('name')}"
            )
        else:
            logger.info(f"📏 Selected hotel from context: None")

        if not selected_hotel:
            # Try to get from last_hotels
            last_hotels = getattr(context, "last_hotels", [])
            if last_hotels:
                selected_hotel = last_hotels[0]
                logger.info(
                    f"📏 Using hotel from last_hotels: {selected_hotel.get('name')}"
                )

        if not selected_hotel:
            return {
                "reply": "🏨 Bạn chưa chọn khách sạn nào. Hãy chọn khách sạn trước để tôi tính khoảng cách nhé!",
                "ui_type": "none",
                "context": context.to_dict(),
                "status": "partial",
            }

        # Try to get coordinates from selected_hotel (check both nested and root level)
        hotel_coords = selected_hotel.get("coordinates", {})
        hotel_lat = (
            hotel_coords.get("lat")
            or hotel_coords.get("latitude")
            or selected_hotel.get("latitude")
            or selected_hotel.get("lat")
        )
        hotel_lon = (
            hotel_coords.get("lon")
            or hotel_coords.get("longitude")
            or selected_hotel.get("longitude")
            or selected_hotel.get("lon")
        )

        # If no coordinates, try to fetch from DB
        if not hotel_lat or not hotel_lon:
            hotel_id = selected_hotel.get("id") or selected_hotel.get("_id")
            if hotel_id and self.mongo_manager:
                logger.info(f"📏 Fetching hotel coordinates from DB for: {hotel_id}")
                hotels_col = self.mongo_manager.get_collection("hotels")
                if hotels_col is not None:
                    from bson import ObjectId

                    try:
                        hotel_doc = hotels_col.find_one(
                            {"_id": ObjectId(str(hotel_id))}
                        )
                        if hotel_doc:
                            # Check nested coordinates object first
                            hotel_coords = hotel_doc.get("coordinates", {})
                            hotel_lat = hotel_coords.get("lat") or hotel_coords.get(
                                "latitude"
                            )
                            hotel_lon = hotel_coords.get("lon") or hotel_coords.get(
                                "longitude"
                            )

                            # If not found, check root level (MongoDB schema variation)
                            if not hotel_lat:
                                hotel_lat = hotel_doc.get("latitude") or hotel_doc.get(
                                    "lat"
                                )
                            if not hotel_lon:
                                hotel_lon = hotel_doc.get("longitude") or hotel_doc.get(
                                    "lon"
                                )

                            logger.info(
                                f"📏 Found coordinates from DB: lat={hotel_lat}, lon={hotel_lon}"
                            )
                    except Exception as e:
                        logger.error(f"❌ Error fetching hotel from DB: {e}")

        if not hotel_lat or not hotel_lon:
            logger.warning(
                f"⚠️ Hotel {selected_hotel.get('name')} has no coordinates, trying alternatives..."
            )

            # Fallback: Try other hotels from last_hotels that have coordinates
            last_hotels = getattr(context, "last_hotels", [])
            alternative_hotel = None

            for h in last_hotels:
                h_coords = h.get("coordinates", {})
                h_lat = h_coords.get("lat") or h_coords.get("latitude")
                h_lon = h_coords.get("lon") or h_coords.get("longitude")

                if h_lat and h_lon:
                    alternative_hotel = h
                    hotel_lat = h_lat
                    hotel_lon = h_lon
                    logger.info(
                        f"📏 Using alternative hotel with coordinates: {h.get('name')}"
                    )
                    selected_hotel = alternative_hotel
                    break

            # If still no coordinates, try fetching alternatives from DB
            if not hotel_lat or not hotel_lon:
                for h in last_hotels[:3]:  # Try first 3 hotels
                    h_id = h.get("id") or h.get("_id")
                    if h_id and self.mongo_manager:
                        hotels_col = self.mongo_manager.get_collection("hotels")
                        if hotels_col is not None:
                            from bson import ObjectId

                            try:
                                h_doc = hotels_col.find_one(
                                    {"_id": ObjectId(str(h_id))}
                                )
                                if h_doc:
                                    h_coords = h_doc.get("coordinates", {})
                                    h_lat = h_coords.get("lat") or h_coords.get(
                                        "latitude"
                                    )
                                    h_lon = h_coords.get("lon") or h_coords.get(
                                        "longitude"
                                    )

                                    if h_lat and h_lon:
                                        hotel_lat = h_lat
                                        hotel_lon = h_lon
                                        selected_hotel = h
                                        logger.info(
                                            f"📏 Found alternative hotel from DB: {h.get('name')} ({h_lat}, {h_lon})"
                                        )
                                        break
                            except Exception as e:
                                logger.error(
                                    f"❌ Error fetching alternative hotel: {e}"
                                )

            if not hotel_lat or not hotel_lon:
                return {
                    "reply": f"🏨 Rất tiếc, các khách sạn trong danh sách chưa có thông tin tọa độ. "
                    f"Tôi không thể tính khoảng cách chính xác được.\n\n"
                    f"💡 Hãy thử chọn khách sạn khác hoặc tôi có thể gợi ý khách sạn phù hợp nhé!",
                    "ui_type": "none",
                    "context": context.to_dict(),
                    "status": "partial",
                }

        # Get spots from context with priority order
        spots_to_check = []

        # Priority 0: selected_spots (permanent memory from spot selection)
        selected_spots = _get_context_value(context, "selected_spots", [])
        if selected_spots:
            logger.info(
                f"📏 Found {len(selected_spots)} spots in selected_spots memory"
            )
            spots_to_check = selected_spots

        # Priority 1: itinerary_builder.days_plan
        if not spots_to_check:
            itinerary_builder = _get_context_value(context, "itinerary_builder")
            if itinerary_builder:
                if hasattr(itinerary_builder, "days_plan"):
                    for day in itinerary_builder.days_plan:
                        for spot in day.get("spots", []):
                            spots_to_check.append(spot)
                elif isinstance(itinerary_builder, dict):
                    days_plan = itinerary_builder.get("days_plan", {})
                    for day_spots in days_plan.values():
                        if isinstance(day_spots, list):
                            spots_to_check.extend(day_spots)

        # Priority 2: last_itinerary.days (for auto-generated itinerary)
        if not spots_to_check:
            last_itinerary = _get_context_value(context, "last_itinerary")
            if last_itinerary:
                # First try selected_spots
                if (
                    hasattr(last_itinerary, "selected_spots")
                    and last_itinerary.selected_spots
                ):
                    spots_to_check = last_itinerary.selected_spots
                elif isinstance(last_itinerary, dict) and last_itinerary.get(
                    "selected_spots"
                ):
                    spots_to_check = last_itinerary.get("selected_spots", [])

                # If still empty, try days (for auto-generated itinerary)
                if not spots_to_check:
                    days_data = None
                    # Check dict first (most common case)
                    if isinstance(last_itinerary, dict):
                        days_data = last_itinerary.get("days", [])
                    elif hasattr(last_itinerary, "days") and not isinstance(
                        last_itinerary, dict
                    ):
                        days_data = last_itinerary.days

                    if days_data:
                        logger.info(
                            f"📏 Extracting spots from last_itinerary.days ({len(days_data)} days)"
                        )
                        for day_info in days_data:
                            day_spots = (
                                day_info.get("spots", [])
                                if isinstance(day_info, dict)
                                else []
                            )
                            for spot in day_spots:
                                if isinstance(spot, dict):
                                    spots_to_check.append(spot)
                                elif isinstance(spot, str):
                                    # Spot is just a name string, need to look up in DB
                                    spots_to_check.append({"name": spot})
                        logger.info(
                            f"📏 Found {len(spots_to_check)} spots from last_itinerary.days"
                        )

        # Priority 3: last_spots
        if not spots_to_check:
            spots_to_check = _get_context_value(context, "last_spots", [])

        # Priority 4: Extract spots mentioned in user query and search DB
        if not spots_to_check:
            logger.info("📏 No spots in context, extracting from query...")

            # Use GeneralInfoExpert's entity extractor to find spot names
            general_expert = self.experts.get("general_info")
            if general_expert and hasattr(general_expert, "entity_extractor"):
                entities = general_expert.entity_extractor.extract_entities(
                    user_message, context.to_dict()
                )
                spot_names = entities.get("spots", [])

                logger.info(f"📏 Extracted spot names from query: {spot_names}")

                # Search for these spots in MongoDB
                if spot_names and self.mongo_manager:
                    spots_col = self.mongo_manager.get_collection("spots_detailed")
                    if spots_col is not None:
                        for spot_name in spot_names[:5]:  # Limit to 5 spots
                            try:
                                # Fuzzy search for spot
                                spot_doc = spots_col.find_one(
                                    {"name": {"$regex": spot_name, "$options": "i"}}
                                )
                                if spot_doc:
                                    spots_to_check.append(
                                        {
                                            "_id": str(spot_doc.get("_id")),
                                            "name": spot_doc.get("name"),
                                            "address": spot_doc.get("address"),
                                            "coordinates": spot_doc.get("coordinates")
                                            or {
                                                "latitude": spot_doc.get("latitude"),
                                                "longitude": spot_doc.get("longitude"),
                                            },
                                        }
                                    )
                                    logger.info(
                                        f"📏 Found spot from query: {spot_doc.get('name')}"
                                    )
                            except Exception as e:
                                logger.error(
                                    f"❌ Error searching for spot '{spot_name}': {e}"
                                )

        if not spots_to_check:
            return {
                "reply": "📍 Tôi không tìm thấy địa điểm nào để tính khoảng cách.\n\n"
                "Bạn có thể:\n"
                "• Lên lịch trình trước\n"
                "• Hoặc nói cụ thể tên địa điểm, ví dụ: 'Khoảng cách từ Bãi Biển Mỹ Khê đến khách sạn'",
                "ui_type": "none",
                "context": context.to_dict(),
                "status": "partial",
            }

        logger.info(f"📏 Total spots to check: {len(spots_to_check)}")

        # FILTER: Only keep spots mentioned in query if query has specific spot names
        if mentioned_spots:
            filtered_spots = []
            for spot in spots_to_check:
                spot_name = spot.get("name", "").lower()
                # Check if any mentioned spot name is in this spot's name
                for mentioned in mentioned_spots:
                    if mentioned in spot_name or spot_name in mentioned:
                        filtered_spots.append(spot)
                        logger.info(
                            f"✅ Matched spot: {spot.get('name')} (query: {mentioned})"
                        )
                        break

            if filtered_spots:
                spots_to_check = filtered_spots
                logger.info(
                    f"📏 Filtered to {len(spots_to_check)} spots based on query"
                )
            else:
                logger.info(f"⚠️ No spots matched query, will calculate for all spots")

        # Calculate distances
        from math import radians, cos, sin, asin, sqrt

        def haversine(lat1, lon1, lat2, lon2):
            """Calculate distance in km using Haversine formula"""
            # Convert to radians
            lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

            # Haversine formula
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
            c = 2 * asin(sqrt(a))

            # Earth radius in km
            r = 6371

            return c * r

        distance_results = []

        logger.info(f"📏 Hotel coordinates: lat={hotel_lat}, lon={hotel_lon}")
        logger.info(f"📏 Checking {len(spots_to_check)} spots for distance calculation")

        # DEBUG: Log spots data
        for idx, spot in enumerate(spots_to_check[:10]):
            logger.info(
                f"📋 Spot {idx+1}: name={spot.get('name')}, id={spot.get('id') or spot.get('_id')}, lat={spot.get('latitude')}, lon={spot.get('longitude')}"
            )

        for spot in spots_to_check[:10]:  # Limit to 10 spots
            # FIX E: Track coordinate source for debugging
            coord_source = "unknown"

            # Try root-level coordinates first (new format with latitude/longitude keys)
            spot_lat = spot.get("latitude") or spot.get("lat")
            spot_lon = spot.get("longitude") or spot.get("lon")
            if spot_lat and spot_lon:
                coord_source = "spot_object"

            # If not found, try nested coordinates object
            if not spot_lat or not spot_lon:
                spot_coords = spot.get("coordinates", {})
                spot_lat = spot_coords.get("lat") or spot_coords.get("latitude")
                spot_lon = spot_coords.get("lon") or spot_coords.get("longitude")
                if spot_lat and spot_lon:
                    coord_source = "nested_coords"

            # If STILL no coordinates, try to fetch from available_spots (may have full data)
            if not spot_lat or not spot_lon:
                spot_name = spot.get("name", "")
                available_spots = _get_context_value(context, "available_spots", [])
                if isinstance(available_spots, list):
                    for avail_spot in available_spots:
                        if avail_spot.get("name") == spot_name:
                            spot_lat = avail_spot.get("latitude") or avail_spot.get(
                                "lat"
                            )
                            spot_lon = avail_spot.get("longitude") or avail_spot.get(
                                "lon"
                            )
                            if spot_lat and spot_lon:
                                coord_source = "available_spots"
                                logger.info(
                                    f"📏 Found coordinates from available_spots for {spot_name}: lat={spot_lat}, lon={spot_lon}"
                                )
                            break

            # If STILL no coordinates, try to fetch from DB by ID or NAME
            if not spot_lat or not spot_lon:
                spot_id = spot.get("id") or spot.get("_id")
                spot_name = spot.get("name", "")
                if self.mongo_manager:
                    spots_col = self.mongo_manager.get_collection("spots_detailed")
                    if spots_col is not None:
                        from bson import ObjectId

                        try:
                            spot_doc = None
                            # Try by ID first
                            if spot_id:
                                try:
                                    spot_doc = spots_col.find_one(
                                        {"_id": ObjectId(str(spot_id))}
                                    )
                                except Exception:
                                    pass

                            # If not found by ID, try by name (fuzzy search)
                            if not spot_doc and spot_name:
                                # Exact match first
                                spot_doc = spots_col.find_one({"name": spot_name})
                                if not spot_doc:
                                    # Fuzzy match
                                    spot_doc = spots_col.find_one(
                                        {"name": {"$regex": spot_name, "$options": "i"}}
                                    )
                                if spot_doc:
                                    logger.info(
                                        f"📏 Found spot by name search: {spot_doc.get('name')}"
                                    )

                            if spot_doc:
                                spot_coords = spot_doc.get("coordinates", {})
                                spot_lat = (
                                    spot_coords.get("lat")
                                    or spot_coords.get("latitude")
                                    or spot_doc.get("latitude")
                                )
                                spot_lon = (
                                    spot_coords.get("lon")
                                    or spot_coords.get("longitude")
                                    or spot_doc.get("longitude")
                                )
                                if spot_lat and spot_lon:
                                    coord_source = "mongodb_search"
                                logger.info(
                                    f"📏 Fetched coordinates for {spot.get('name')}: lat={spot_lat}, lon={spot_lon}"
                                )
                        except Exception as e:
                            logger.error(f"❌ Error fetching spot from DB: {e}")

            if not spot_lat or not spot_lon:
                logger.warning(
                    f"⚠️ Spot {spot.get('name')} has no coordinates, skipping (coord_source={coord_source})"
                )
                continue

            # FIX E: Log coordinate source for debugging suspicious same-distance issues
            logger.info(
                f"📏 [FIX E] Calculating distance for '{spot.get('name')}': ({hotel_lat}, {hotel_lon}) -> ({spot_lat}, {spot_lon}) [source={coord_source}]"
            )
            distance_km = haversine(hotel_lat, hotel_lon, spot_lat, spot_lon)

            # Enrich with image if available
            spot_image = spot.get("image")
            if not spot_image:
                # Try to get image from available_spots
                spot_name = spot.get("name", "")
                available_spots = _get_context_value(context, "available_spots", [])
                if isinstance(available_spots, list):
                    for avail_spot in available_spots:
                        if avail_spot.get("name") == spot_name:
                            spot_image = avail_spot.get("image")
                            if spot_image:
                                logger.info(
                                    f"📸 Found image for {spot_name} from available_spots"
                                )
                            break

            # Fallback: Try to fetch image from MongoDB
            if not spot_image:
                spot_id = spot.get("id") or spot.get("_id")
                spot_name = spot.get("name", "")
                if self.mongo_manager:
                    spots_col = self.mongo_manager.get_collection("spots_detailed")
                    if spots_col is not None:
                        from bson import ObjectId

                        try:
                            # Try by ID first
                            if spot_id:
                                spot_doc = spots_col.find_one(
                                    {"_id": ObjectId(str(spot_id))}
                                )
                                if spot_doc:
                                    spot_image = spot_doc.get("image")
                                    if spot_image:
                                        logger.info(
                                            f"📸 Fetched image for {spot_name} from MongoDB (ID)"
                                        )

                            # Try by name if not found by ID
                            if not spot_image and spot_name:
                                spot_doc = spots_col.find_one({"name": spot_name})
                                if spot_doc:
                                    spot_image = spot_doc.get("image")
                                    if spot_image:
                                        logger.info(
                                            f"📸 Fetched image for {spot_name} from MongoDB (name)"
                                        )
                        except Exception as e:
                            logger.warning(f"⚠️ Error fetching image from MongoDB: {e}")

            # FIX E: Include coord_source in results for debugging
            distance_results.append(
                {
                    "name": spot.get("name"),
                    "distance_km": round(distance_km, 2),
                    "address": spot.get("address", "N/A"),
                    "image": spot_image,
                    "coord_source": coord_source,  # FIX E: Track coordinate source
                    "coordinates": {"lat": spot_lat, "lng": spot_lon},
                }
            )

        logger.info(f"📏 Calculated distances for {len(distance_results)} spots")

        if not distance_results:
            return {
                "reply": "⚠️ Các địa điểm trong lịch trình chưa có thông tin tọa độ. "
                "Tôi không thể tính khoảng cách chính xác được.",
                "ui_type": "none",
                "context": context.to_dict(),
                "status": "partial",
            }

        # Sort by distance
        distance_results.sort(key=lambda x: x["distance_km"])

        # Generate response
        hotel_name = selected_hotel.get("name", "Khách sạn của bạn")
        reply_lines = [f"📏 **Khoảng cách từ {hotel_name}:**\n"]

        for result in distance_results[:8]:  # Show top 8
            name = result["name"]
            dist = result["distance_km"]

            # Add travel time estimate (assume 30 km/h avg speed in city)
            time_minutes = int((dist / 30) * 60)
            time_str = (
                f"{time_minutes} phút"
                if time_minutes < 60
                else f"{time_minutes // 60}h{time_minutes % 60}m"
            )

            reply_lines.append(f"📍 **{name}**: {dist} km (~{time_str})")

        reply_lines.append(
            f"\n💡 *Thời gian di chuyển ước tính với tốc độ trung bình 30 km/h*"
        )

        return {
            "reply": "\n".join(reply_lines),
            "ui_type": "distance_info",
            "ui_data": {"hotel": hotel_name, "distances": distance_results[:8]},
            "context": context.to_dict(),
            "status": "complete",
        }

    # === END PATCH 2 ===

    def _error_response(self, error_message: str) -> Dict:
        """Generate error response"""
        return {
            "reply": f"⚠️ Xin lỗi, có lỗi xảy ra: {error_message}. Bạn thử lại nhé!",
            "ui_type": "none",
            "intent": "error",
            "error": error_message,
        }

    def _determine_ui_type(self, answered_sections: List[str], aggregated: Dict) -> str:
        """Determine UI type based on answered sections"""
        if "plan_trip" in answered_sections and aggregated.get("itinerary"):
            return "itinerary"
        elif len(answered_sections) > 1:
            return "comprehensive"
        elif "find_hotel" in answered_sections:
            return "hotel_cards"
        elif "find_spot" in answered_sections:
            return "spot_cards"
        elif "find_food" in answered_sections:
            return "food_cards"
        else:
            return "none"

    def _build_ui_data(self, answered_sections: List[str], aggregated: Dict) -> Dict:
        """Build UI data for answered sections"""
        ui_data = {}

        if "find_hotel" in answered_sections and aggregated.get("hotels"):
            ui_data["hotels"] = aggregated["hotels"][:5]

        if "find_spot" in answered_sections and aggregated.get("spots"):
            # For spot_cards UI type, frontend expects data in 'options'
            # For comprehensive UI type, frontend expects data in 'spots'
            spots_data = aggregated["spots"][:6]
            if len(answered_sections) == 1:
                # Single intent - use options for spot_cards
                ui_data["options"] = spots_data
            else:
                # Multi-intent - use spots for comprehensive
                ui_data["spots"] = spots_data

        if "find_food" in answered_sections and aggregated.get("food"):
            ui_data["food"] = aggregated["food"][:5]

        if "plan_trip" in answered_sections:
            if aggregated.get("itinerary"):
                ui_data["itinerary"] = aggregated["itinerary"]
            if aggregated.get("costs"):
                ui_data["costs"] = aggregated["costs"]

        return ui_data

    def _generate_clarification_request(
        self, multi_intent, unanswered_intents: List[tuple], context
    ) -> str:
        """Generate friendly clarification request"""

        lines = ["👋 Xin chào! Mình có thể giúp bạn lên kế hoạch du lịch nhé!"]
        lines.append("")

        # Ask for missing info
        missing_msg = context.get_missing_params_message(multi_intent.primary_intent)
        if missing_msg:
            lines.append(missing_msg)
        else:
            lines.append("Bạn muốn đi đâu và trong bao lâu?")

        return "\n".join(lines)

    def _generate_clarification_options(self, context) -> Dict:
        """Generate options for clarification"""
        options = []

        if not context.destination:
            options.extend(["🏖️ Đà Nẵng", "🏔️ Đà Lạt", "🏝️ Phú Quốc", "🌆 Hồ Chí Minh"])
        elif not context.duration:
            options.extend(["2 ngày 1 đêm", "3 ngày 2 đêm", "4-5 ngày"])

        return {"options": options} if options else {}

    def _calculate_result_quality(
        self, group_name: str, results: Dict[str, Any]
    ) -> float:
        """
        Calculate quality score (0-1) for results from a task group
        Based on: quantity, completeness, relevance
        """
        score = 0.0

        if group_name == "spots":
            spots = results.get("spots", [])
            if spots:
                score = min(len(spots) / 10.0, 1.0)  # Normalize to 10 spots
                # Bonus for complete data (has description, rating)
                complete_count = sum(
                    1 for s in spots if s.get("description") and s.get("rating")
                )
                if complete_count > 0:
                    score += (complete_count / len(spots)) * 0.3

        elif group_name == "hotels":
            hotels = results.get("hotels", [])
            if hotels:
                score = min(len(hotels) / 8.0, 1.0)  # Normalize to 8 hotels
                # Bonus for price/rating data
                complete_count = sum(
                    1 for h in hotels if h.get("price") and h.get("rating")
                )
                if complete_count > 0:
                    score += (complete_count / len(hotels)) * 0.3

        elif group_name == "food":
            food = results.get("food", [])
            if food:
                score = min(len(food) / 5.0, 1.0)  # Normalize to 5 dishes

        elif group_name == "itinerary":
            itinerary = results.get("itinerary", [])
            if itinerary:
                # High score for complete itinerary
                days_count = len([d for d in itinerary if d.get("activities")])
                score = min(days_count / 3.0, 1.0)  # Normalize to 3 days
                score += 0.3  # Bonus for having itinerary

        elif group_name == "cost":
            costs = results.get("costs", {})
            if costs and costs.get("total"):
                score = 0.8  # High score for cost calculation

        return min(score, 1.0)

    def _should_rerank_intent(
        self,
        current_group: str,
        primary_intent: str,
        current_quality: float,
        all_results: Dict[str, Any],
    ) -> bool:
        """
        Decide if we should re-rank intent based on result quality

        Re-rank if:
        1. Current group has high quality (>0.7)
        2. Primary intent has low/no results
        3. Current group is more relevant to user's implicit need
        """
        # Map group names to intent names
        group_to_intent = {
            "spots": "find_spot",
            "hotels": "find_hotel",
            "food": "find_food",
            "itinerary": "plan_trip",
            "cost": "calculate_cost",
        }

        current_intent = group_to_intent.get(current_group, current_group)

        # Don't re-rank if already primary
        if current_intent == primary_intent:
            return False

        # Check primary intent results quality
        primary_group = None
        for grp, intent in group_to_intent.items():
            if intent == primary_intent:
                primary_group = grp
                break

        if primary_group:
            primary_results = all_results.get(primary_group, [])
            primary_quality = self._calculate_result_quality(
                primary_group, {primary_group: primary_results}
            )

            # Re-rank if:
            # 1. Current is significantly better (>0.4 difference) AND current quality >0.6
            # 2. OR primary completely failed (quality <0.2) and current is decent (>0.5)
            if current_quality - primary_quality > 0.4 and current_quality > 0.6:
                logger.info(
                    f"   Primary '{primary_intent}' quality: {primary_quality:.2f}, Current '{current_intent}' quality: {current_quality:.2f}"
                )
                return True
            elif primary_quality < 0.2 and current_quality > 0.5:
                logger.info(
                    f"   Primary '{primary_intent}' failed ({primary_quality:.2f}), switching to '{current_intent}' ({current_quality:.2f})"
                )
                return True

        # Special case: Always prioritize itinerary if it exists (user wants planning)
        if current_group == "itinerary" and current_quality > 0.7:
            return True

        return False

    def _handle_conversational_chat(
        self, user_message: str, context, intent_type: str = "chitchat"
    ) -> Optional[Dict[str, Any]]:
        """
        Handle conversational chat with LLM using full conversation context.
        This makes the chatbot feel more natural and professional.

        Args:
            user_message: The user's message
            context: Current conversation context
            intent_type: Type of intent (greeting, chitchat, thanks, farewell, general_qa)

        Returns:
            Response dict or None if LLM fails
        """
        if not self.llm:
            return None

        try:
            # Build conversation context summary
            context_summary = self._build_conversation_context_summary(context)

            # Define persona and rules based on intent type
            persona_rules = {
                "greeting": """Bạn đang chào đón người dùng. Hãy:
- Chào thân thiện, tự nhiên
- Giới thiệu ngắn gọn về khả năng hỗ trợ du lịch
- Hỏi xem họ muốn đi đâu hoặc cần giúp gì
- Dùng emoji phù hợp""",
                "chitchat": """Đây là câu hỏi chitchat/off-topic. Hãy:
- Trả lời thân thiện, tự nhiên
- Khéo léo đưa câu chuyện về chủ đề du lịch nếu có thể
- Nếu câu hỏi không liên quan, nhẹ nhàng nhắc về khả năng hỗ trợ du lịch
- Giữ tone vui vẻ, không robot""",
                "thanks": """Người dùng cảm ơn. Hãy:
- Đáp lại lịch sự, khiêm tốn
- Nhắc nhẹ họ có thể hỏi thêm nếu cần
- Chúc chuyến đi vui vẻ (nếu đang có kế hoạch)""",
                "farewell": """Người dùng tạm biệt. Hãy:
- Tạm biệt thân thiện
- Chúc chuyến đi tốt đẹp (nếu có lịch trình)
- Mời quay lại khi cần hỗ trợ""",
                "general_qa": """Đây là câu hỏi chung về du lịch. Hãy:
- Trả lời dựa trên kiến thức về du lịch Việt Nam
- Cung cấp thông tin hữu ích, chính xác
- Gợi ý các bước tiếp theo nếu phù hợp""",
            }

            rules = persona_rules.get(intent_type, persona_rules["chitchat"])

            # Build system prompt
            system_prompt = f"""Bạn là Saola - trợ lý du lịch AI chuyên về du lịch Việt Nam.
Tính cách: Thân thiện, chuyên nghiệp, am hiểu về du lịch Việt Nam, nhiệt tình hỗ trợ.

{rules}

CONTEXT CUỘC TRÒ CHUYỆN HIỆN TẠI:
{context_summary}

QUY TẮC:
- Trả lời bằng tiếng Việt, tự nhiên như người thật
- Dùng emoji phù hợp (không quá nhiều)
- Ngắn gọn (2-4 câu), không dài dòng
- Nếu có lịch trình/khách sạn đã chọn, có thể nhắc đến
- KHÔNG tự bịa thông tin về giá cả, địa điểm cụ thể"""

            # Build messages for chat
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ]

            # Call LLM
            response = self.llm.chat(messages, temperature=0.7, max_tokens=300)

            if response and len(response.strip()) > 10:
                logger.info(
                    f"💬 Conversational LLM response generated for {intent_type}"
                )
                return {
                    "reply": response.strip(),
                    "ui_type": intent_type,
                    "context": context.to_dict(),
                    "status": "partial",
                }

        except Exception as e:
            logger.warning(f"⚠️ Conversational chat LLM failed: {e}")

        return None

    def _build_conversation_context_summary(self, context) -> str:
        """
        Build a summary of the current conversation context for LLM.
        """
        summary_parts = []

        # Destination
        destination = getattr(context, "destination", None)
        if destination:
            summary_parts.append(f"- Điểm đến: {destination}")

        # Duration
        duration = getattr(context, "duration", None)
        if duration:
            summary_parts.append(f"- Số ngày: {duration} ngày")

        # People count
        people_count = getattr(context, "people_count", None)
        if people_count and people_count > 1:
            summary_parts.append(f"- Số người: {people_count}")

        # Workflow state
        workflow_state = getattr(context, "workflow_state", None)
        if workflow_state and workflow_state != "INITIAL":
            state_vi = {
                "GATHERING_INFO": "Đang thu thập thông tin",
                "CHOOSING_SPOTS": "Đang chọn địa điểm tham quan",
                "CHOOSING_HOTEL": "Đang chọn khách sạn",
                "READY_TO_FINALIZE": "Sẵn sàng hoàn tất",
                "COST_ESTIMATION": "Đang tính chi phí",
            }.get(workflow_state, workflow_state)
            summary_parts.append(f"- Trạng thái: {state_vi}")

        # Selected spots
        selected_spots = _get_context_value(context, "selected_spots", [])
        if selected_spots:
            spot_names = [
                s.get("name", "") for s in selected_spots[:3] if isinstance(s, dict)
            ]
            if spot_names:
                summary_parts.append(f"- Địa điểm đã chọn: {', '.join(spot_names)}")

        # Selected hotel
        selected_hotel = getattr(context, "selected_hotel", None)
        if selected_hotel:
            hotel_name = (
                selected_hotel.get("name", selected_hotel)
                if isinstance(selected_hotel, dict)
                else selected_hotel
            )
            summary_parts.append(f"- Khách sạn đã chọn: {hotel_name}")

        # Last itinerary status
        last_itinerary = _get_context_value(context, "last_itinerary")
        if last_itinerary and isinstance(last_itinerary, dict):
            days_count = len(last_itinerary.get("days", []))
            if days_count > 0:
                summary_parts.append(f"- Lịch trình: {days_count} ngày đã lên")

        if not summary_parts:
            return "- Chưa có thông tin cụ thể (cuộc trò chuyện mới bắt đầu)"

        return "\n".join(summary_parts)


# Factory function
def create_master_controller() -> MasterController:
    """Create MasterController instance"""
    return MasterController()
