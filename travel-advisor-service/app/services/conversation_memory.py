"""
Conversation Memory - Enhanced context tracking with chat history
Stores conversation history, unanswered questions, and partial results
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from app.core import logger


@dataclass
class ChatMessage:
    """Single chat message"""

    role: str  # user, assistant, system
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UnansweredQuestion:
    """Question that couldn't be fully answered"""

    question: str
    intent: str
    reason: str  # "no_data", "incomplete_data", "need_clarification"
    attempted_at: str = field(default_factory=lambda: datetime.now().isoformat())
    retry_count: int = 0


@dataclass
class PartialResult:
    """Partial answer for a sub-intent"""

    intent: str
    answered: bool
    data: Dict[str, Any] = field(default_factory=dict)
    message: str = ""


@dataclass
class EnhancedConversationContext:
    """Enhanced conversation context with memory"""

    # Basic context (existing)
    destination: Optional[str] = None
    duration: Optional[int] = None
    start_date: Optional[str] = None  # YYYY-MM-DD format for trip start date
    budget: Optional[int] = None
    budget_level: Optional[str] = None
    people_count: int = 1
    companion_type: Optional[str] = None  # solo, couple, family, friends, business
    interests: List[str] = field(default_factory=list)
    last_intent: Optional[str] = None
    selected_hotel: Optional[str] = None
    selected_hotel_price: Optional[int] = None  # Price of selected hotel in VND
    selected_spots: List[Dict] = field(
        default_factory=list
    )  # 🆕 NEW: Permanently store selected spots
    itinerary: List[Dict] = field(default_factory=list)
    itinerary_builder: Optional[Dict] = None  # For interactive itinerary building

    # CRITICAL: State Machine for workflow tracking
    # States: INITIAL → GATHERING_INFO → CHOOSING_SPOTS → CHOOSING_HOTEL → READY_TO_FINALIZE
    workflow_state: str = "INITIAL"
    spots_selected_per_day: Dict[str, List[Dict]] = field(
        default_factory=dict
    )  # {"day_1": [spot1, spot2], ...}
    hotels_selected_per_day: Dict[str, Dict] = field(
        default_factory=dict
    )  # {"day_1": hotel_obj, ...}

    # NEW: Spot Selector State - for optional multi-choice selection
    spot_selector_state: Optional[Dict] = None  # {
    #   "candidate_spots": [...],      # All spots suggested
    #   "selected_ids": [...],         # User's selected spot IDs
    #   "removed_ids": [...],          # User's removed spot IDs
    #   "selection_mode": "default"|"custom"|"skipped",
    #   "awaiting_submit": bool        # Waiting for user to submit selection
    # }

    # Last search results - for follow-up queries like "chi tiết về X"
    last_spots: List[Dict] = field(default_factory=list)  # Last spot search results
    last_hotels: List[Dict] = field(default_factory=list)  # Last hotel search results
    last_foods: List[Dict] = field(default_factory=list)  # Last food search results
    last_itinerary: Dict = field(default_factory=dict)  # Last generated itinerary
    last_cost_breakdown: Dict = field(default_factory=dict)  # Last cost calculation

    # NEW: Verified itinerary after ItineraryVerifier check
    verified_itinerary: Optional[Dict] = None  # Itinerary after rule+LLM verification
    verification_issues: List[Dict] = field(
        default_factory=list
    )  # Issues found during verification

    # Enhanced features
    chat_history: List[ChatMessage] = field(default_factory=list)
    unanswered_questions: List[UnansweredQuestion] = field(default_factory=list)
    answered_intents: List[str] = field(
        default_factory=list
    )  # Track what's been answered
    partial_results: Dict[str, PartialResult] = field(default_factory=dict)
    conversation_summary: str = ""  # LLM-generated summary of conversation so far

    def add_message(self, role: str, content: str, metadata: Dict = None):
        """Add message to chat history"""
        msg = ChatMessage(role=role, content=content, metadata=metadata or {})
        self.chat_history.append(msg)

        # Keep only last 20 messages to prevent memory bloat
        if len(self.chat_history) > 20:
            self.chat_history = self.chat_history[-20:]

    def add_unanswered_question(self, question: str, intent: str, reason: str):
        """Add question that couldn't be answered"""
        unanswered = UnansweredQuestion(question=question, intent=intent, reason=reason)
        self.unanswered_questions.append(unanswered)
        logger.info(f"❓ Unanswered question stored: {intent} - {reason}")

    def mark_intent_answered(self, intent: str, data: Dict = None):
        """Mark an intent as successfully answered"""
        if intent not in self.answered_intents:
            self.answered_intents.append(intent)

        # Store partial result
        self.partial_results[intent] = PartialResult(
            intent=intent, answered=True, data=data or {}
        )
        logger.info(f"✅ Intent answered: {intent}")

    def get_unanswered_count(self) -> int:
        """Get count of unanswered questions"""
        return len(self.unanswered_questions)

    def get_recent_context(self, last_n: int = 5) -> List[Dict]:
        """Get recent conversation context for LLM"""
        recent = self.chat_history[-last_n:] if self.chat_history else []
        return [{"role": msg.role, "content": msg.content} for msg in recent]

    def has_sufficient_info_for_intent(self, intent: str) -> bool:
        """Check if we have enough info to answer this intent"""
        if intent == "plan_trip":
            return bool(self.destination and self.duration)
        elif intent in ["find_hotel", "find_spot", "find_food"]:
            return bool(self.destination)
        return True

    def get_missing_params_message(self, intent: str) -> str:
        """Get friendly message about missing parameters"""
        missing = []

        if intent == "plan_trip":
            if not self.destination:
                missing.append("điểm đến")
            if not self.duration:
                missing.append("số ngày")
            if not self.budget:
                missing.append("ngân sách (tùy chọn)")
        elif intent in ["find_hotel", "find_spot", "find_food"]:
            if not self.destination:
                missing.append("điểm đến")

        if missing:
            return f"Để mình có thể gợi ý tốt hơn, bạn cho mình biết thêm về: {', '.join(missing)} nhé!"
        return ""

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
        if hasattr(intent, "companion_type") and intent.companion_type:
            self.companion_type = intent.companion_type
        if intent.interests:
            self.interests = intent.interests
        self.last_intent = intent.intent

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for API response"""
        return {
            "destination": self.destination,
            "duration": self.duration,
            "start_date": self.start_date,
            "budget": self.budget,
            "budget_level": self.budget_level,
            "people_count": self.people_count,
            "companion_type": self.companion_type,
            "interests": self.interests,
            "last_intent": self.last_intent,
            "selected_hotel": self.selected_hotel,
            "selected_hotel_price": self.selected_hotel_price,
            "selected_spots": self.selected_spots,  # 🆕 NEW
            "answered_intents": self.answered_intents,
            "unanswered_count": self.get_unanswered_count(),
            "conversation_summary": self.conversation_summary,
            # Last search results for follow-up queries
            "last_spots": self.last_spots,
            "last_hotels": self.last_hotels,
            "last_foods": self.last_foods,
            # Interactive itinerary builder state
            "itinerary_builder": self.itinerary_builder,
            # Saved itinerary for recall
            "last_itinerary": self.last_itinerary,
            # State Machine fields for workflow tracking
            "workflow_state": self.workflow_state,
            "spots_selected_per_day": self.spots_selected_per_day,
            "hotels_selected_per_day": self.hotels_selected_per_day,
            # NEW: Spot selector state for optional multi-choice
            "spot_selector_state": self.spot_selector_state,
            # NEW: Verified itinerary
            "verified_itinerary": self.verified_itinerary,
            "verification_issues": self.verification_issues,
        }

    def to_full_dict(self) -> Dict[str, Any]:
        """Convert to full dict including history (for internal use)"""
        return asdict(self)

    # --- Last Results Management ---
    def update_last_spots(self, spots: List[Dict]):
        """Store last spot search results for follow-up queries"""
        self.last_spots = spots[:10] if spots else []  # Keep max 10
        logger.debug(f"📍 Stored {len(self.last_spots)} spots in context")

    def update_last_hotels(self, hotels: List[Dict]):
        """Store last hotel search results for follow-up queries"""
        self.last_hotels = hotels[:10] if hotels else []
        logger.debug(f"🏨 Stored {len(self.last_hotels)} hotels in context")

    def update_last_foods(self, foods: List[Dict]):
        """Store last food search results for follow-up queries"""
        self.last_foods = foods[:10] if foods else []
        logger.debug(f"🍜 Stored {len(self.last_foods)} foods in context")

    def update_last_itinerary(self, itinerary: Dict):
        """Store last generated itinerary"""
        self.last_itinerary = itinerary or {}
        logger.debug(f"📅 Stored itinerary in context")

    def update_last_cost(self, cost_data: Dict):
        """Store last cost calculation"""
        self.last_cost_breakdown = cost_data or {}
        logger.debug(f"💰 Stored cost breakdown in context")

    def find_spot_by_name(self, name: str) -> Optional[Dict]:
        """Find a spot in last results by partial name match"""
        name_lower = name.lower()
        for spot in self.last_spots:
            spot_name = spot.get("name", "").lower()
            if name_lower in spot_name or spot_name in name_lower:
                return spot
        return None

    def find_hotel_by_name(self, name: str) -> Optional[Dict]:
        """Find a hotel in last results by partial name match"""
        name_lower = name.lower()
        for hotel in self.last_hotels:
            hotel_name = hotel.get("name", "").lower()
            if name_lower in hotel_name or hotel_name in name_lower:
                return hotel
        return None

    def get_all_last_results(self) -> Dict[str, List[Dict]]:
        """Get all last search results"""
        return {
            "spots": self.last_spots,
            "hotels": self.last_hotels,
            "foods": self.last_foods,
        }


class ConversationMemoryManager:
    """
    Manages conversation memory and progressive disclosure
    Handles partial answers, unanswered questions, and context building
    """

    def __init__(self, llm_client=None):
        self.llm = llm_client
        logger.info("✅ ConversationMemoryManager initialized")

    def create_progressive_response(
        self,
        multi_intent,
        results: Dict[str, Any],
        context: EnhancedConversationContext,
    ) -> Dict[str, Any]:
        """
        Create progressive response - answer what we can, defer what we can't
        """

        all_intents = [multi_intent.primary_intent] + multi_intent.sub_intents
        answered_sections = []
        unanswered_intents = []

        # Check each intent
        for intent in all_intents:
            if self._can_answer_intent(intent, results, context):
                # We have data - mark as answered
                context.mark_intent_answered(
                    intent, results.get(self._get_result_key(intent))
                )
                answered_sections.append(intent)
            else:
                # Can't answer - store for later
                reason = self._get_failure_reason(intent, results, context)
                context.add_unanswered_question(
                    question=f"Query về {intent}", intent=intent, reason=reason
                )
                unanswered_intents.append((intent, reason))

        logger.info(
            f"📊 Progressive response: {len(answered_sections)} answered, {len(unanswered_intents)} deferred"
        )

        return {
            "answered_sections": answered_sections,
            "unanswered_intents": unanswered_intents,
            "has_partial_answer": len(answered_sections) > 0,
        }

    def build_progressive_reply(
        self,
        answered_sections: List[str],
        unanswered_intents: List[tuple],
        results: Dict[str, Any],
        location: str,
        context: EnhancedConversationContext,
    ) -> str:
        """Build reply with answered parts + deferred parts"""

        sections = []

        # Header
        if answered_sections:
            sections.append(f"🎯 **Gợi ý du lịch {location}**\n")

        # Answered sections
        for intent in answered_sections:
            section_text = self._format_answered_section(intent, results, context)
            if section_text:
                sections.append(section_text)

        # Unanswered sections (friendly deferral)
        if unanswered_intents:
            sections.append(
                self._format_unanswered_sections(unanswered_intents, context)
            )

        # Next steps suggestion
        if unanswered_intents or context.get_unanswered_count() > 0:
            sections.append(self._format_next_steps(context))

        return "\n\n".join(sections)

    def _can_answer_intent(self, intent: str, results: Dict, context) -> bool:
        """Check if we have sufficient data to answer this intent"""

        # Check if we have necessary context
        if not context.has_sufficient_info_for_intent(intent):
            return False

        # Check if we have data
        result_key = self._get_result_key(intent)
        data = results.get(result_key, [])

        if intent == "plan_trip":
            # Need itinerary data
            return bool(results.get("itinerary"))
        elif intent in ["find_hotel", "find_spot", "find_food"]:
            # Need at least 1 result
            return isinstance(data, list) and len(data) > 0

        return True

    def _get_result_key(self, intent: str) -> str:
        """Map intent to result key"""
        mapping = {
            "find_hotel": "hotels",
            "find_spot": "spots",
            "find_food": "food",
            "plan_trip": "itinerary",
            "general_qa": "general_info",
        }
        return mapping.get(intent, "data")

    def _get_failure_reason(self, intent: str, results: Dict, context) -> str:
        """Determine why we can't answer"""

        if not context.has_sufficient_info_for_intent(intent):
            return "need_clarification"

        result_key = self._get_result_key(intent)
        data = results.get(result_key, [])

        if not data or (isinstance(data, list) and len(data) == 0):
            return "no_data"

        return "incomplete_data"

    def _format_answered_section(self, intent: str, results: Dict, context) -> str:
        """Format a successfully answered section"""

        result_key = self._get_result_key(intent)
        data = results.get(result_key, [])

        if intent == "find_hotel":
            return self._format_hotels(data)
        elif intent == "find_spot":
            return self._format_spots(data)
        elif intent == "find_food":
            return self._format_food(data)
        elif intent == "plan_trip":
            return self._format_itinerary(results, context)
        elif intent == "general_qa":
            return self._format_general_info(data)

        return ""

    def _format_hotels(self, hotels: List[Dict]) -> str:
        """Format hotels section"""
        lines = ["🏨 **Khách sạn đề xuất**\n"]

        for i, hotel in enumerate(hotels[:5], 1):
            name = hotel.get("name", "N/A")
            price = hotel.get("price_formatted", "N/A")
            rating = hotel.get("rating", 0)

            lines.append(f"**{i}. {name}**")
            lines.append(f"   💵 {price}/đêm | ⭐ {rating}/10")
            lines.append("")

        return "\n".join(lines)

    def _format_spots(self, spots: List[Dict]) -> str:
        """Format spots section"""
        lines = ["📍 **Địa điểm tham quan**\n"]

        for i, spot in enumerate(spots[:6], 1):
            name = spot.get("name", "N/A")
            rating = spot.get("rating", 0)
            desc = spot.get("description", "")[:80]

            lines.append(f"**{i}. {name}** ⭐ {rating}")
            if desc:
                lines.append(f"   {desc}...")
            lines.append("")

        return "\n".join(lines)

    def _format_food(self, food_items: List[Dict]) -> str:
        """Format food section"""
        lines = ["🍜 **Ẩm thực địa phương**\n"]

        seen_ids = set()  # Track to avoid duplicates
        recommendation_added = False

        for item in food_items[:10]:  # Check more items for dedup
            item_id = item.get("id")

            # Skip duplicates
            if item_id in seen_ids:
                continue
            seen_ids.add(item_id)

            if item.get("type") == "recommendation":
                if not recommendation_added:  # Only add once
                    dishes = item.get("dishes", [])
                    lines.append(f"🌟 **Món đặc sản nên thử:** {', '.join(dishes[:5])}")
                    lines.append("")
                    recommendation_added = True
            else:
                name = item.get("name", "N/A")
                rating = item.get("rating", 0)
                lines.append(f"• **{name}** ⭐ {rating}")
                lines.append("")

        # If only recommendations (no real restaurants), add helpful note
        if recommendation_added and len(seen_ids) == 1:
            lines.append(
                "ℹ️ *Mình chưa có database quán ăn cụ thể, nhưng đây là những món đặc sản bạn nên thử!*"
            )
            lines.append("")

        return "\n".join(lines)

    def _format_itinerary(self, results: Dict, context) -> str:
        """Format itinerary section"""
        duration = context.duration or 3
        itinerary = results.get("itinerary", [])

        lines = [f"🗓️ **Lịch trình {duration} ngày**\n"]

        for day_plan in itinerary[:duration]:
            day = day_plan.get("day", 1)
            activities = day_plan.get("activities", [])

            lines.append(f"**Ngày {day}:**")
            for activity in activities[:4]:
                time = activity.get("time", "")
                name = activity.get("activity", "N/A")
                lines.append(f"  • {time} - {name}")
            lines.append("")

        return "\n".join(lines)

    def _format_general_info(self, info_data: List[Dict]) -> str:
        """Format general information section"""
        if not info_data or len(info_data) == 0:
            return ""

        info = info_data[0]  # Get first info item

        # Check if we have LLM-generated answer
        if "answer" in info and info["answer"]:
            return info["answer"]

        # Fallback to tips format
        tips = info.get("tips", [])
        if not tips:
            return ""

        lines = []
        for tip in tips:
            lines.append(tip)
            lines.append("")

        return "\n".join(lines)

    def _format_unanswered_sections(self, unanswered: List[tuple], context) -> str:
        """Format friendly message about unanswered parts"""

        lines = ["---", ""]

        need_clarification = [
            intent for intent, reason in unanswered if reason == "need_clarification"
        ]
        no_data = [intent for intent, reason in unanswered if reason == "no_data"]

        if need_clarification:
            missing_msg = context.get_missing_params_message(need_clarification[0])
            if missing_msg:
                lines.append(f"💭 {missing_msg}")

        if no_data:
            intent_names = {
                "find_hotel": "khách sạn",
                "find_spot": "địa điểm tham quan",
                "find_food": "quán ăn",
            }
            items = [intent_names.get(i, i) for i in no_data]
            lines.append(
                f"ℹ️ Mình chưa có nhiều thông tin về {', '.join(items)} ở khu vực này."
            )
            lines.append(
                f"Bạn có thể thử hỏi về địa điểm khác hoặc mình sẽ tìm hiểu thêm!"
            )

        return "\n".join(lines)

    def _format_next_steps(self, context) -> str:
        """Format suggested next steps"""
        lines = ["", "💡 **Bạn có thể hỏi tiếp:**"]

        if "find_hotel" not in context.answered_intents:
            lines.append("• Khách sạn ở đây thế nào?")
        if "find_spot" not in context.answered_intents:
            lines.append("• Địa điểm nào đáng tham quan?")
        if "find_food" not in context.answered_intents:
            lines.append("• Món ăn đặc sản là gì?")
        if "plan_trip" not in context.answered_intents and context.destination:
            lines.append("• Lên lịch trình chi tiết")

        return "\n".join(lines)


def create_conversation_memory_manager(llm_client=None) -> ConversationMemoryManager:
    """Factory function"""
    return ConversationMemoryManager(llm_client)
