"""
Multi-Intent Extractor - Enhanced NLU for multi-question queries
Handles complex queries with multiple intents (e.g., "hotel + spot + food")
"""

import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from app.core import logger
from app.services.intent_extractor import ExtractedIntent, IntentExtractor


@dataclass
class MultiIntent:
    """
    Multiple intents extracted from a single query - Enhanced for complex compound queries
    with LLM-based semantic understanding and state management
    """
    primary_intent: str  # Main intent (plan_trip, find_hotel, etc.)
    sub_intents: List[str] = field(default_factory=list)  # Additional intents
    location: Optional[str] = None
    duration: Optional[int] = None
    budget: Optional[int] = None
    budget_level: Optional[str] = None  # "tiết kiệm", "trung bình", "sang trọng"
    people_count: int = 1
    companion_type: Optional[str] = None  # "gia đình", "bạn bè", "couple", "một mình"
    accommodation: str = "required"
    interests: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    confidence: float = 0.0
    
    # NEW: Original user message for LLM context
    original_message: str = ""
    
    # Flow control signals (xong, tiếp tục, chốt)
    has_flow_control: bool = False
    flow_action: Optional[str] = None  # "finalize", "continue", "back", "recall"
    
    # NEW: Context-aware fields for conversation continuity
    context_relation: str = "new_topic"  # "new_topic", "continuation", "correction", "backtrack"
    target_entities: List[str] = field(default_factory=list)  # ["selected_spots", "selected_hotel"]
    next_action: Optional[str] = None  # "find_hotel", "calculate_cost", "provide_tips", "backtrack_to_spots"
    reasoning: Optional[str] = None  # LLM's explanation for debugging
    current_step: Optional[str] = None  # "choosing_spots", "choosing_hotel", "finalizing"
    is_confirmed: bool = False  # User said "xong", "chốt" to finalize
    
    # 🔄 BACKTRACKING support
    state_transition: Optional[str] = None  # "CHOOSING_HOTEL → CHOOSING_SPOTS"
    preserve_data: List[str] = field(default_factory=list)  # ["selected_spots", "selected_hotel"] - data to keep during backtrack
    
    # Intent-specific parameters
    intent_params: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    def to_extracted_intent(self) -> ExtractedIntent:
        """Convert to ExtractedIntent for backward compatibility"""
        return ExtractedIntent(
            intent=self.primary_intent,
            location=self.location,
            duration=self.duration,
            budget=self.budget,
            budget_level=self.budget_level,
            people_count=self.people_count,
            interests=self.interests,
            keywords=self.keywords,
            confidence=self.confidence
        )


class MultiIntentExtractor:
    """
    Enhanced Intent Extractor for multi-question queries
    
    Example query: "Gợi ý khách sạn ở Đà Nẵng + địa điểm check-in + quán ăn ngon"
    → Extracts: ["find_hotel", "find_spot", "find_food"]
    """
    
    # Intent detection patterns with priority (ONLY travel-related intents)
    INTENT_PATTERNS = {
        "find_hotel": {
            "keywords": ["khách sạn", "hotel", "resort", "homestay", "chỗ ở", "phòng nghỉ", "lưu trú"],
            "priority": 2
        },
        "find_spot": {
            "keywords": ["địa điểm", "chỗ nào", "ở đâu", "tham quan", "check-in", "chụp ảnh", "cảnh đẹp", 
                        "đi đâu", "điểm đến", "spot", "nơi nào", "chỗ chơi"],  # Thêm keywords
            "priority": 1  # FIX P1: Đẩy lên ưu tiên 1 để ưu tiên tìm địa điểm
        },
        "find_food": {
            "keywords": ["ăn gì", "quán ăn", "nhà hàng", "món ngon", "bún", "phở", "cơm", "bánh", "hải sản", "ẩm thực", "đặc sản", "thức ăn", "food"],
            "priority": 2
        },
        "plan_trip": {
            "keywords": ["lịch trình", "kế hoạch", "tour", "hành trình", "chuyến đi", "tạo tour", "lên lịch"],  # Bớt "du lịch" ra
            "priority": 2  # FIX P1: Hạ xuống ưu tiên 2 để nhường chỗ cho find_spot
        },
        "recall_itinerary": {
            "keywords": ["xem lại", "hiển thị", "cho tôi xem", "lịch trình của tôi", "lịch trình đã tạo"],
            "priority": 1
        },
        "calculate_cost": {
            "keywords": ["tính tiền", "chi phí", "giá bao nhiêu", "tốn bao nhiêu", "ngân sách", "estimate"],
            "priority": 2
        },
        "get_location_tips": {
            "keywords": ["lưu ý", "kinh nghiệm", "tips", "có gì cần biết", "nên biết", "chú ý", "khuyến cáo", "mẹo"],
            "priority": 2
        },
        "flow_control": {
            "keywords": ["xong", "done", "tiếp tục", "tiep tuc", "ok", "chốt", "chot", "hoàn thành", "kết thúc"],
            "priority": 3  # Highest - always detect
        }
    }
    
    # Budget level patterns
    BUDGET_PATTERNS = {
        "tiết kiệm": ["tiết kiệm", "rẻ", "bình dân", "giá mềm", "tầm trung dưới"],
        "trung bình": ["trung bình", "vừa phải", "moderate", "tầm trung"],
        "sang trọng": ["sang trọng", "cao cấp", "luxury", "resort 5 sao", "xịn xò", "đẳng cấp"]
    }
    
    # Query split patterns
    SPLIT_PATTERNS = [
        r'\s+và\s+',  # "hotel và spot"
        r'\s+\+\s+',  # "hotel + spot"
        r',\s*',      # "hotel, spot"
        r'\s+cùng\s+',  # "hotel cùng spot"
        r'\s+kèm\s+',  # "hotel kèm spot"
    ]
    
    def __init__(self, base_extractor: IntentExtractor):
        self.base_extractor = base_extractor
        logger.info("✅ MultiIntentExtractor initialized")
    
    def _extract_people_count_regex(self, query: str, context_people: int = 1) -> int:
        """
        Extract people count using regex patterns as fallback
        Returns context value if no match found
        """
        query_lower = query.lower()
        
        # Pattern 1: Số + người (2 người, 5 người đi)
        match = re.search(r'(\d+)\s*người', query_lower)
        if match:
            return int(match.group(1))
        
        # Pattern 2: "vợ chồng và X con" or "bố mẹ và X con" (2 + X)
        match = re.search(r'(vợ chồng|bố mẹ|ba mẹ)\s+và\s+(\d+)\s+con', query_lower)
        if match:
            num_children = int(match.group(2))
            return 2 + num_children  # 2 parents + children
        
        # Pattern 3: Semantic mappings
        semantic_patterns = {
            1: ['một mình', 'solo', 'mình đi', 'tôi đi'],
            2: ['cặp đôi', 'couple', 'hai người', 'vợ chồng', 'bạn gái', 'bạn trai', 
                'mình và', 'mình với'],
            3: ['ba người', 'nhóm ba'],
            4: ['bốn người', 'nhóm bốn', 'gia đình 4'],
            5: ['năm người', 'nhóm năm'],
            6: ['sáu người', 'nhóm sáu']
        }
        
        for count, patterns in semantic_patterns.items():
            if any(pattern in query_lower for pattern in patterns):
                return count
        
        # Pattern 4: Team/nhóm + số
        match = re.search(r'(team|nhóm|group)\s*(\d+)', query_lower)
        if match:
            return int(match.group(2))
        
        # Return context value if no match
        return context_people
    
    def extract(self, query: str, context: Dict[str, Any] = None) -> MultiIntent:
        """
        Extract multiple intents from query with LLM-based semantic understanding
        
        Priority:
        1. LLM extraction (if available and context is complex)
        2. Regex fallback (for simple queries or LLM failure)
        
        Args:
            query: User's query (possibly multi-intent)
            context: Conversation context with history
            
        Returns:
            MultiIntent with semantic understanding and next action suggestions
        """
        context = context or {}
        query_lower = query.lower()
        
        # === PRE-LLM CHECKS: Delegate to base extractor for high-confidence patterns ===
        # FIX #1 & #3: Check compound patterns BEFORE LLM to avoid misinterpretation
        
        # Check if base extractor has pre-LLM detection methods
        if hasattr(self.base_extractor, '_is_booking_request'):
            if self.base_extractor._is_booking_request(query_lower):
                logger.info("[FIX #1] 🎯 Booking pattern detected, using base extractor")
                base_result = self.base_extractor.extract(query, context)
                return MultiIntent(
                    primary_intent=base_result.intent,
                    sub_intents=[],
                    location=base_result.location,
                    keywords=base_result.keywords,
                    confidence=base_result.confidence,
                    original_message=query
                )
        
        if hasattr(self.base_extractor, '_is_budget_calculation_request'):
            if self.base_extractor._is_budget_calculation_request(query_lower):
                logger.info("[FIX #3] 🎯 Budget calculation pattern detected, using base extractor")
                base_result = self.base_extractor.extract(query, context)
                return MultiIntent(
                    primary_intent=base_result.intent,
                    sub_intents=[],
                    location=base_result.location,
                    duration=base_result.duration,
                    budget=base_result.budget,
                    confidence=base_result.confidence,
                    original_message=query
                )
        
        # === NORMAL FLOW: LLM or regex extraction ===
        
        # Check if we have LLM client and complex context
        has_llm = hasattr(self.base_extractor, 'llm_client') and self.base_extractor.llm_client is not None
        is_complex_context = (
            context.get("itinerary_builder") or 
            context.get("last_itinerary") or 
            context.get("selected_spots") or
            len(query.strip()) < 20  # Short queries need context understanding
        )
        
        # Try LLM extraction first for complex contexts
        if has_llm and is_complex_context:
            try:
                logger.info("🤖 Using LLM-based extraction for context-aware understanding")
                return self._extract_with_llm(query, context)
            except Exception as e:
                logger.warning(f"⚠️ LLM extraction failed: {e}, falling back to regex")
        
        # Fallback to regex-based extraction
        return self._extract_with_regex(query, context)
    
    def _extract_with_llm(self, query: str, context: Dict[str, Any]) -> MultiIntent:
        """
        LLM-based extraction with semantic understanding and state management
        Uses Saola 3.1 as reasoning engine to understand context and conversation flow
        """
        
        # Build context summary for LLM (OPTIMIZED - only essential data)
        context_summary = self._build_context_summary(context)
        
        system_prompt = """Bạn là "Flow Manager" - bộ não điều khiển luồng hội thoại du lịch.
Nhiệm vụ: Phân tích query và STATE hiện tại để quyết định next_action (hành động tiếp theo).

📊 TRÍCH XUẤT PEOPLE_COUNT (FEW-SHOT EXAMPLES):
Học cách quy đổi mọi cách nói về số người thành con số:

'2 người' → people_count: 2
'2 người đi' → people_count: 2
'mình và bạn gái' → people_count: 2
'mình với vợ' → people_count: 2
'cặp đôi' → people_count: 2
'couple' → people_count: 2

'gia đình 4 người' → people_count: 4
'vợ chồng và 2 con' → people_count: 4
'bố mẹ và 2 con' → people_count: 4

'một mình' → people_count: 1
'đi một mình' → people_count: 1
'solo' → people_count: 1
'mình đi' → people_count: 1

'3 người' → people_count: 3
'nhóm 5 người' → people_count: 5
'team 8 người' → people_count: 8

⚠️ QUAN TRỌNG: Luôn trả về people_count là số nguyên. Nếu không nhắc đến số người thì giữ giá trị từ context.

🎯 NGUYÊN TẮC VÀ​NG: STATE-FIRST, INTENT-SECOND
   → Luôn ưu tiên workflow_state hiện tại hơn là intent mới
   → KHÔNG ĐƯỢC nhảy bước lung tung, phá vỡ quy trình

🧠 STATE MACHINE LOGIC - QUY TRÌNH DU LỊCH CHUẨN:

1️⃣ INITIAL / GATHERING_INFO: Thu thập địa điểm, số ngày, ngân sách
   → Next: CHOOSING_SPOTS
   → ⚠️ CHỈ TRẢ VỀ plan_trip, TUYỆT ĐỐI KHÔNG kèm find_hotel hay find_food!

2️⃣ CHOOSING_SPOTS: Chọn địa điểm tham quan cho từng ngày
   - User nói "xong" / "tiếp tục" / "kết thúc" → Chuyển sang: CHOOSING_HOTEL
   - User hỏi "ở đây có gì" / "địa điểm nào" → Tiếp tục gợi ý (KHÔNG RESET!)
   - Chưa đủ spots → Tiếp tục gợi ý thêm
   - ⚠️ KHÔNG ĐƯỢC tính tiền khi chưa có khách sạn!
   - ⚠️ KHÔNG ĐƯỢC trả về find_hotel hoặc find_food tự động!

3️⃣ CHOOSING_HOTEL: Chọn nơi ở
   - User nói "tìm khách sạn" / "hotel" → Action: find_hotel
   - User nói "xong khách sạn" → Chuyển sang: READY_TO_FINALIZE
   - User hỏi "tính tiền" → Yêu cầu chọn khách sạn trước
   - 🔄 **BACKTRACK**: User nói "thêm địa điểm" / "thêm spot" → Quay lại: CHOOSING_SPOTS
   - ⚠️ KHÔNG ĐƯỢC trả về find_food tự động!

4️⃣ READY_TO_FINALIZE: Sẵn sàng tổng hợp
   - User nói "tính tiền" / "chi phí" → Action: calculate_cost
   - User nói "xem lại" → Action: show_itinerary
   - User nói "tìm quán ăn" / "food" → Action: find_food
   - 🔄 **BACKTRACK**: User nói "đổi khách sạn" → Quay lại: CHOOSING_HOTEL

⚠️ QUY TẮC CHUYỂN TRẠNG THÁI (Critical Rules):

1. TÍNH KẾ THỪA (Context Continuation):
   - "đã chọn", "ở đó", "vừa nãy" → context_relation: "continuation"
   - Tham chiếu lịch sử: selected_spots, selected_hotel, last_itinerary

2. XỬ LÝ Ý ĐỊNH ẨN (Implicit Intent):
   - "Có lưu ý gì?" → get_location_tips (KHÔNG RESET!)
   - "Xong" trong CHOOSING_SPOTS → flow_control + next_action: "suggest_hotel"
   - "Xong" trong CHOOSING_HOTEL → flow_control + next_action: "ready_to_calculate"
   - Số (1,2,3) hoặc (1,3,5) → select_items

3. 🔄 BACKTRACKING (Quay xe):
   - Đang ở CHOOSING_HOTEL, user nói "thêm địa điểm" / "thêm spot nữa" / "còn thiếu điểm" 
     → Intent: plan_trip, Action: backtrack_to_spots, state_transition: "CHOOSING_HOTEL → CHOOSING_SPOTS"
   - Đang ở READY_TO_FINALIZE, user nói "đổi khách sạn" / "chọn lại hotel"
     → Intent: find_hotel, Action: backtrack_to_hotel, state_transition: "READY_TO_FINALIZE → CHOOSING_HOTEL"
   - ⚠️ QUAN TRỌNG: Không làm mất dữ liệu cũ! Chỉ thêm/sửa, không xóa.

4. PHÂN BIỆT READ VS WRITE:
   - "Xem lại lịch trình" → show_itinerary (READ)
   - "Lên lịch trình" → plan_trip (WRITE)
   - "Tính tiền" khi chưa có hotel → yêu cầu: "Bạn cần chọn khách sạn trước"

5. TRÁNH RESET (NO RESET):
   - Đang trong tiến trình → KHÔNG trả về greeting/chitchat
   - Giữ location, duration từ context nếu query không nhắc lại

6. KIỂM TRA ĐIỀU KIỆN (Constraint Validation):
   - calculate_cost cần: selected_spots + selected_hotel (cho ít nhất 1 ngày)
   - Nếu thiếu → next_action: "prompt_missing_data"

7. ĐA Ý ĐỊNH (Multi-Intent):
   - "Xem lại và tính tiền" → ["show_itinerary", "calculate_cost"]
   - Hỗ trợ tối đa 3 intents cùng lúc

🎯 PROACTIVE GUIDANCE (Dẫn dắt chủ động):
   - Sau mỗi bước hoàn thành, phải gợi ý next_step rõ ràng:
     * Chọn xong spots → "Giờ chọn khách sạn nhé?"
     * Chọn xong hotel → "Bạn muốn tính tổng chi phí không?"
     * Backtrack → "Được! Tôi giữ nguyên [X] đã chọn, giờ thêm [Y] nhé?"

OUTPUT FORMAT (JSON):
{
    "intents": ["plan_trip"],
    "context_relation": "continuation" | "new_topic" | "correction" | "backtrack",
    "target_entities": ["selected_spots"],
    "next_action": "backtrack_to_spots" | "suggest_hotel_selection" | "calculate_cost",
    "state_transition": "CHOOSING_HOTEL → CHOOSING_SPOTS",
    "preserve_data": ["selected_spots", "selected_hotel"],
    "current_step": "choosing_spots" | "choosing_hotel" | "ready_to_finalize",
    "is_confirmed": false,
    "missing_requirements": [],
    "proactive_message": "Được! Tôi giữ nguyên 5 điểm đã chọn, giờ thêm điểm mới nhé?",
    "location": "Đà Nẵng",
    "duration": 3,
    "budget_level": "tiết kiệm",
    "reasoning": "User ở bước choosing_hotel nhưng muốn thêm spot → backtrack về choosing_spots",
    "confidence": 0.95
}

CHỈ trả về JSON, KHÔNG giải thích thêm."""

        # Build user prompt with context
        user_prompt = f"""User Query: "{query}"

Context Data:
- Current Step: {context.get('current_step', 'unknown')}
- Destination: {context.get('destination', 'not set')}
- Duration: {context.get('duration', 'not set')} ngày
- Budget Level: {context.get('budget_level', 'not set')}
- People Count: {context.get('people_count', 1)}

{context_summary}

Phân tích query với context trên và trả về JSON."""

        try:
            llm_client = self.base_extractor.llm_client
            result = llm_client.extract_json(user_prompt, system_prompt)
            
            # Map LLM response to MultiIntent
            intents = result.get("intents", ["general_qa"])
            
            # 🔧 FIX 1: People Count with Regex Fallback
            llm_people_count = result.get("people_count")
            context_people_count = context.get("people_count", 1)
            
            # Validate LLM output
            if llm_people_count and isinstance(llm_people_count, int) and llm_people_count > 0:
                final_people_count = llm_people_count
            else:
                # Fallback to regex extraction
                final_people_count = self._extract_people_count_regex(query, context_people_count)
                logger.info(f"🔄 People count fallback: LLM={llm_people_count} → Regex={final_people_count}")
            
            return MultiIntent(
                primary_intent=intents[0] if intents else "general_qa",
                sub_intents=intents[1:] if len(intents) > 1 else [],
                location=result.get("location") or context.get("destination"),
                duration=result.get("duration") or context.get("duration"),
                budget=context.get("budget"),
                budget_level=result.get("budget_level") or context.get("budget_level"),
                people_count=final_people_count,  # ✅ FIXED: Use validated people count
                companion_type=context.get("companion_type"),
                confidence=result.get("confidence", 0.85),
                original_message=query,  # ✅ NEW: Store original message for LLM context
                # Context-aware fields
                context_relation=result.get("context_relation", "new_topic"),
                target_entities=result.get("target_entities", []),
                next_action=result.get("next_action"),
                reasoning=result.get("reasoning"),
                current_step=result.get("current_step") or context.get("current_step"),
                is_confirmed=result.get("is_confirmed", False),
                has_flow_control="flow_control" in intents,
                flow_action=self._determine_flow_action(query, result),
                # 🔄 Backtracking fields
                state_transition=result.get("state_transition"),
                preserve_data=result.get("preserve_data", [])
            )
            
        except Exception as e:
            logger.error(f"❌ LLM extraction error: {e}")
            raise
    
    def _build_context_summary(self, context: Dict[str, Any]) -> str:
        """
        Build OPTIMIZED context summary for LLM
        CRITICAL: Only include essential data to avoid token bloat and maintain LLM focus
        """
        summary_parts = []
        
        # Current workflow state (MOST IMPORTANT)
        workflow_state = context.get("workflow_state", "INITIAL")
        summary_parts.append(f"- Workflow State: {workflow_state}")
        
        # Itinerary builder state (only if active)
        builder = context.get("itinerary_builder")
        if builder:
            current_day = builder.get("current_day", 1)
            total_days = builder.get("total_days", 3)
            days_plan = builder.get("days_plan", {})
            summary_parts.append(f"- Đang lập lịch: Ngày {current_day}/{total_days}")
            
            # OPTIMIZATION: Only show spot COUNTS, not full names (to save tokens)
            if days_plan:
                total_selected = sum(len(spots) for spots in days_plan.values())
                summary_parts.append(f"  - Đã chọn {total_selected} spots cho {len(days_plan)} ngày")
                # Only show names for CURRENT day if needed
                current_day_spots = days_plan.get(str(current_day), [])
                if current_day_spots:
                    spot_names = [s.get("name") for s in current_day_spots[:3]]  # Max 3 names
                    summary_parts.append(f"  - Ngày {current_day}: {', '.join(spot_names)}...")
        
        # Last itinerary (only if exists and workflow_state allows backtracking)
        last_itinerary = context.get("last_itinerary")
        if last_itinerary and isinstance(last_itinerary, dict):
            days = last_itinerary.get("days", [])
            summary_parts.append(f"- Có lịch trình hoàn chỉnh: {len(days)} ngày")
        
        # Selected hotel (CRITICAL for cost calculation)
        selected_hotel = context.get("selected_hotel")
        if selected_hotel:
            summary_parts.append(f"- Đã chọn khách sạn: {selected_hotel}")
        
        # Basic travel info (location, duration)
        destination = context.get("destination")
        duration = context.get("duration")
        if destination:
            summary_parts.append(f"- Điểm đến: {destination}")
        if duration:
            summary_parts.append(f"- Số ngày: {duration}")
        
        return "\n".join(summary_parts) if summary_parts else "- Context rỗng"
    
    def _determine_flow_action(self, query: str, llm_result: Dict[str, Any]) -> Optional[str]:
        """Determine flow action from query and LLM result"""
        query_lower = query.lower()
        
        if any(kw in query_lower for kw in ["xong", "done", "chốt", "hoàn thành"]):
            return "finalize"
        elif any(kw in query_lower for kw in ["xem lại", "hiển thị", "cho tôi xem"]):
            return "recall"
        elif any(kw in query_lower for kw in ["tiếp tục", "ok", "được", "next"]):
            return "continue"
        elif re.match(r"^\d+(,\s*\d+)*$", query.strip()):  # "1,3,5" or "1, 3, 5"
            return "select_items"
        
        return llm_result.get("flow_action")
    
    def _extract_with_regex(self, query: str, context: Dict[str, Any]) -> MultiIntent:
        """
        Fallback regex-based extraction (simplified, delegates to base extractor)
        Only used when LLM is not available or fails
        """
        # Step 1: Detect if query contains multiple intents
        detected_intents = self._detect_intents(query)
        
        if len(detected_intents) <= 1:
            # Single intent - use base extractor
            base_result = self.base_extractor.extract(query, context)
            return MultiIntent(
                primary_intent=base_result.intent,
                sub_intents=[],
                location=base_result.location,
                duration=base_result.duration,
                budget=base_result.budget,
                budget_level=base_result.budget_level,
                people_count=base_result.people_count,
                interests=base_result.interests,
                keywords=base_result.keywords,
                confidence=base_result.confidence,
                original_message=query  # ✅ NEW: Store original message
            )
        
        # Step 2: Multi-intent detected - decompose query
        logger.info(f"🎯 Multi-intent detected: {detected_intents}")
        
        # Step 3: Split query into sub-queries
        sub_queries = self._split_query(query, detected_intents)
        
        # Step 4: Extract parameters for each intent
        multi_intent = self._extract_multi_intent(query, detected_intents, sub_queries, context)
        
        return multi_intent
    
    def _detect_intents(self, query: str) -> List[str]:
        """
        Detect ALL intents in query without early stopping (no break)
        Example: "xem lại lịch trình và tính tiền" → ["recall_itinerary", "calculate_cost"]
        """
        detected = []
        query_lower = query.lower()
        
        # CRITICAL: Collect ALL matching intents (no break statement)
        for intent, config in self.INTENT_PATTERNS.items():
            keywords = config["keywords"]
            if any(kw in query_lower for kw in keywords):
                detected.append(intent)
                logger.debug(f"  ✓ Detected intent: {intent}")
        
        # If no intent detected, default to general_qa
        if not detected:
            detected = ["general_qa"]
            logger.debug(f"  → No intent matched, defaulting to general_qa")
        
        # Sort by priority (highest priority first: flow_control, plan_trip, recall, others)
        detected.sort(key=lambda i: self.INTENT_PATTERNS.get(i, {"priority": 10})["priority"])
        
        logger.info(f"🎯 Detected intents (sorted by priority): {detected}")
        return detected
    
    def _split_query(self, query: str, intents: List[str]) -> Dict[str, str]:
        """
        Split query into sub-queries for each intent
        
        Example: "khách sạn ở Đà Nẵng và địa điểm check-in"
        → {"find_hotel": "khách sạn ở Đà Nẵng", "find_spot": "địa điểm check-in"}
        """
        sub_queries = {}
        
        # Try to split by patterns
        for pattern in self.SPLIT_PATTERNS:
            parts = re.split(pattern, query)
            if len(parts) > 1:
                # Match parts to intents based on keywords
                for part in parts:
                    part = part.strip()
                    matched_intent = self._match_part_to_intent(part, intents)
                    if matched_intent and matched_intent not in sub_queries:
                        sub_queries[matched_intent] = part
                
                if len(sub_queries) >= len(intents):
                    break
        
        # If split failed, assign full query to each intent
        if not sub_queries:
            for intent in intents:
                sub_queries[intent] = query
        
        return sub_queries
    
    def _match_part_to_intent(self, part: str, intents: List[str]) -> Optional[str]:
        """Match a query part to an intent"""
        part_lower = part.lower()
        
        for intent in intents:
            keywords = self.INTENT_PATTERNS[intent]["keywords"]
            if any(kw in part_lower for kw in keywords):
                return intent
        
        return None
    
    def _extract_multi_intent(
        self,
        query: str,
        intents: List[str],
        sub_queries: Dict[str, str],
        context: Dict[str, Any]
    ) -> MultiIntent:
        """Extract complete multi-intent with parameters"""
        
        # Use base extractor for overall parameters
        base_result = self.base_extractor.extract(query, context)
        
        # Primary intent: highest priority or first detected
        primary_intent = intents[0] if intents else "general_qa"
        sub_intents = intents[1:] if len(intents) > 1 else []
        
        # Detect flow control signals
        has_flow_control = "flow_control" in intents
        flow_action = None
        if has_flow_control:
            query_lower = query.lower()
            if any(kw in query_lower for kw in ["xong", "done", "chốt", "hoàn thành", "kết thúc"]):
                flow_action = "finalize"
            elif any(kw in query_lower for kw in ["xem lại", "hiển thị", "cho tôi xem"]):
                flow_action = "recall"
            elif any(kw in query_lower for kw in ["tiếp tục", "ok", "được"]):
                flow_action = "continue"
        
        # Detect budget level
        budget_level = base_result.budget_level
        if not budget_level:
            query_lower = query.lower()
            for level, keywords in self.BUDGET_PATTERNS.items():
                if any(kw in query_lower for kw in keywords):
                    budget_level = level
                    logger.info(f"💰 Budget level detected: {budget_level}")
                    break
        
        # Extract intent-specific parameters
        intent_params = {}
        for intent, sub_query in sub_queries.items():
            intent_result = self.base_extractor.extract(sub_query, context)
            intent_params[intent] = {
                "query": sub_query,
                "keywords": intent_result.keywords,
                "interests": intent_result.interests
            }
        
        return MultiIntent(
            primary_intent=primary_intent,
            sub_intents=sub_intents,
            location=base_result.location,
            duration=base_result.duration,
            budget=base_result.budget,
            budget_level=budget_level,
            people_count=base_result.people_count,
            companion_type=base_result.companion_type,
            accommodation=base_result.accommodation,
            interests=base_result.interests,
            keywords=base_result.keywords,
            confidence=base_result.confidence,
            original_message=query,  # ✅ NEW: Store original message
            has_flow_control=has_flow_control,
            flow_action=flow_action,
            intent_params=intent_params
        )


def create_multi_intent_extractor(base_extractor: IntentExtractor) -> MultiIntentExtractor:
    """Factory function"""
    return MultiIntentExtractor(base_extractor)
