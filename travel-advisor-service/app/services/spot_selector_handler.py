"""
Spot Selector Handler - Manages optional multi-choice spot selection

This module implements the spot_selector_table UI pattern:
- Display spots in a table format with multi-choice checkboxes
- Handle submit/cancel/skip/select_all/clear_all actions
- Integrate with workflow state machine

UI Payload (backend → frontend):
{
  "reply": "Bạn có muốn chọn địa điểm không? (Có thể bỏ qua)",
  "ui_type": "spot_selector_table",
  "ui_data": {
    "columns": ["Chọn", "Tên", "Loại", "Rating", "Gợi ý thời điểm", "Thời lượng", "Khu vực"],
    "rows": [...],
    "default_selected_ids": [...],
    "actions": ["submit", "cancel", "skip", "select_all", "clear_all"]
  }
}

User Action Payload (frontend → backend):
{
  "action": "submit_spot_selection",
  "selected_ids": [...],
  "removed_ids": [...],
  "selection_mode": "custom"
}
"""

from typing import Dict, Any, List, Optional
from app.core import logger


# Default best_visit_time derivation from category/tags
CATEGORY_BEST_TIME = {
    "night_market": ["evening", "night"],
    "nightlife": ["evening", "night"],
    "bar": ["evening", "night"],
    "chợ_đêm": ["evening", "night"],
    "beach": ["morning", "afternoon"],
    "biển": ["morning", "afternoon"],
    "temple": ["morning", "afternoon"],
    "pagoda": ["morning", "afternoon"],
    "chùa": ["morning", "afternoon"],
    "museum": ["morning", "afternoon"],
    "park": ["morning", "afternoon", "evening"],
    "theme_park": ["morning", "afternoon"],
    "sunset": ["afternoon", "evening"],
    "sunrise": ["early_morning"],
    "shopping": ["afternoon", "evening"],
    "restaurant": ["morning", "afternoon", "evening"],
    "cafe": ["morning", "afternoon", "evening"],
    "landmark": ["morning", "afternoon", "evening"],
}

# Default duration estimation (minutes)
CATEGORY_DURATION = {
    "beach": 120,
    "museum": 90,
    "temple": 60,
    "pagoda": 60,
    "theme_park": 240,
    "park": 90,
    "shopping": 120,
    "restaurant": 60,
    "night_market": 90,
    "landmark": 45,
    "cafe": 60,
    "bar": 120,
}


class SpotSelectorHandler:
    """
    Handles optional spot selection with multi-choice table UI.
    
    Key Features:
    - Creates spot_selector_table UI data
    - Processes submit/cancel/skip actions
    - Derives best_visit_time from category when missing
    - Integrates with workflow state machine
    """
    
    def __init__(self, mongo_manager=None, llm_client=None):
        self.mongo = mongo_manager
        self.llm = llm_client
        logger.info("✅ SpotSelectorHandler initialized")
    
    def create_selector_table(
        self,
        spots: List[Dict],
        location: str,
        duration: int,
        context: Any
    ) -> Dict[str, Any]:
        """
        Create spot_selector_table UI data from spots list.
        
        Args:
            spots: List of spot dictionaries from database
            location: Destination name
            duration: Trip duration in days
            context: EnhancedConversationContext
            
        Returns:
            Response dict with ui_type="spot_selector_table"
        """
        if not spots:
            return self._create_empty_response(location, context)
        
        # Enrich spots with derived fields
        enriched_spots = []
        for i, spot in enumerate(spots):
            enriched = self._enrich_spot(spot, i)
            enriched_spots.append(enriched)
        
        # Select default spots (top rated, balanced categories)
        default_selected = self._select_default_spots(enriched_spots, duration)
        default_selected_ids = [s["id"] for s in default_selected]
        
        # Build table rows
        rows = []
        for spot in enriched_spots:
            rows.append({
                "id": spot["id"],
                "name": spot["name"],
                "category": spot["category"],
                "rating": spot.get("rating", 0),
                "best_time": spot.get("best_visit_time", []),
                "avg_duration_min": spot.get("avg_duration_min", 60),
                "area": spot.get("area", location),
                "image": spot.get("image", ""),
                "description": spot.get("description", "")[:100]
            })
        
        # Update context with spot selector state
        context.spot_selector_state = {
            "candidate_spots": enriched_spots,
            "selected_ids": default_selected_ids,
            "removed_ids": [],
            "selection_mode": "default",
            "awaiting_submit": True
        }
        context.workflow_state = "CHOOSING_SPOTS"
        
        reply = f"""🗓️ **Lập lịch trình {duration} ngày tại {location}**

Tôi đã tìm thấy **{len(spots)} địa điểm** phù hợp. Bạn có thể:

✅ **Chọn** các địa điểm muốn đi (đã chọn sẵn {len(default_selected_ids)} địa điểm hot nhất)
⏭️ **Bỏ qua** để tôi tự động lên lịch với các địa điểm đề xuất
🔄 **Hủy** để quay lại chọn số ngày/ngân sách

💡 *Gợi ý thời điểm giúp bạn tránh xếp chợ đêm vào buổi sáng!*"""

        return {
            "reply": reply,
            "ui_type": "spot_selector_table",
            "ui_data": {
                "columns": ["Chọn", "Tên", "Loại", "Rating", "Gợi ý thời điểm", "Thời lượng", "Khu vực"],
                "rows": rows,
                "default_selected_ids": default_selected_ids,
                "destination": location,
                "duration": duration,
                "actions": ["submit", "cancel", "skip", "select_all", "clear_all"]
            },
            "context": context.to_dict(),
            "status": "partial"
        }
    
    def handle_selection_action(
        self,
        action: str,
        selected_ids: List[str],
        removed_ids: List[str],
        context: Any
    ) -> Dict[str, Any]:
        """
        Handle user's spot selection action.
        
        Actions:
        - submit: Confirm selection, proceed to next step
        - cancel: Reset to default selection
        - skip: Skip spot selection, use auto-generated
        - select_all: Select all spots
        - clear_all: Deselect all spots
        """
        selector_state = context.spot_selector_state
        
        if not selector_state:
            return {
                "reply": "⚠️ Không tìm thấy trạng thái chọn địa điểm. Vui lòng thử lại.",
                "ui_type": "none",
                "context": context.to_dict(),
                "status": "error"
            }
        
        candidate_spots = selector_state.get("candidate_spots", [])
        
        if action == "submit":
            return self._handle_submit(selected_ids, candidate_spots, context)
        
        elif action == "cancel":
            return self._handle_cancel(selector_state, context)
        
        elif action == "skip":
            return self._handle_skip(selector_state, context)
        
        elif action == "select_all":
            all_ids = [s["id"] for s in candidate_spots]
            selector_state["selected_ids"] = all_ids
            selector_state["selection_mode"] = "custom"
            context.spot_selector_state = selector_state
            return {
                "reply": f"✅ Đã chọn tất cả **{len(all_ids)} địa điểm**. Bấm **Submit** để xác nhận.",
                "ui_type": "spot_selector_update",
                "ui_data": {"selected_ids": all_ids},
                "context": context.to_dict(),
                "status": "partial"
            }
        
        elif action == "clear_all":
            selector_state["selected_ids"] = []
            selector_state["selection_mode"] = "custom"
            context.spot_selector_state = selector_state
            return {
                "reply": "🔄 Đã bỏ chọn tất cả. Chọn lại địa điểm hoặc bấm **Skip** để bỏ qua.",
                "ui_type": "spot_selector_update",
                "ui_data": {"selected_ids": []},
                "context": context.to_dict(),
                "status": "partial"
            }
        
        else:
            return {
                "reply": f"⚠️ Không hiểu action: {action}",
                "ui_type": "none",
                "context": context.to_dict(),
                "status": "error"
            }
    
    def _handle_submit(
        self, 
        selected_ids: List[str], 
        candidate_spots: List[Dict],
        context: Any
    ) -> Dict[str, Any]:
        """Handle submit action - confirm selection and proceed."""
        # Get selected spots
        selected_spots = [
            s for s in candidate_spots 
            if s["id"] in selected_ids
        ]
        
        if not selected_spots:
            return {
                "reply": "⚠️ Bạn chưa chọn địa điểm nào. Chọn ít nhất 1 địa điểm hoặc bấm **Skip** để bỏ qua.",
                "ui_type": "none",
                "context": context.to_dict(),
                "status": "partial"
            }
        
        # Update context
        context.spot_selector_state["selected_ids"] = selected_ids
        context.spot_selector_state["selection_mode"] = "custom"
        context.spot_selector_state["awaiting_submit"] = False
        
        # Store selected spots in context
        context.last_spots = selected_spots
        
        # Transition to next state
        context.workflow_state = "CHOOSING_HOTEL"
        
        # Format selected spots for display
        spots_text = "\n".join([
            f"  ✅ {s['name']} ({s.get('category', 'Tham quan')})"
            for s in selected_spots[:10]
        ])
        
        reply = f"""🎯 **Đã chốt {len(selected_spots)} địa điểm!**

{spots_text}

━━━━━━━━━━━━━━━━━━━━

🎯 **BƯỚC TIẾP THEO: Chọn khách sạn**

Bạn muốn tìm khách sạn không? Gõ **"tìm khách sạn"** hoặc bấm nút bên dưới.

💡 *Sau khi chọn khách sạn, tôi sẽ sắp xếp lịch trình tối ưu theo khoảng cách!*"""

        return {
            "reply": reply,
            "ui_type": "options",
            "ui_data": {
                "options": [
                    "🏨 Tìm khách sạn",
                    "📋 Xem lịch trình dự kiến",
                    "⏭️ Bỏ qua, tự lên lịch"
                ]
            },
            "context": context.to_dict(),
            "status": "partial"
        }
    
    def _handle_cancel(self, selector_state: Dict, context: Any) -> Dict[str, Any]:
        """Handle cancel action - reset to default."""
        default_ids = selector_state.get("default_selected_ids", [])
        if not default_ids:
            # Recalculate default
            candidate_spots = selector_state.get("candidate_spots", [])
            default_spots = self._select_default_spots(candidate_spots, context.duration or 3)
            default_ids = [s["id"] for s in default_spots]
        
        selector_state["selected_ids"] = default_ids
        selector_state["removed_ids"] = []
        selector_state["selection_mode"] = "default"
        context.spot_selector_state = selector_state
        
        return {
            "reply": f"🔄 Đã reset về lựa chọn mặc định ({len(default_ids)} địa điểm).",
            "ui_type": "spot_selector_update",
            "ui_data": {"selected_ids": default_ids},
            "context": context.to_dict(),
            "status": "partial"
        }
    
    def _handle_skip(self, selector_state: Dict, context: Any) -> Dict[str, Any]:
        """Handle skip action - use default/auto selection."""
        selector_state["selection_mode"] = "skipped"
        selector_state["awaiting_submit"] = False
        context.spot_selector_state = selector_state
        
        # Use default selected spots
        default_ids = selector_state.get("selected_ids", [])
        candidate_spots = selector_state.get("candidate_spots", [])
        
        selected_spots = [s for s in candidate_spots if s["id"] in default_ids]
        context.last_spots = selected_spots
        
        # Skip directly to hotel selection
        context.workflow_state = "CHOOSING_HOTEL"
        
        return {
            "reply": f"""⏭️ **Đã bỏ qua bước chọn địa điểm**

Tôi sẽ sử dụng **{len(default_ids)} địa điểm đề xuất** để lập lịch trình.

🏨 **Tiếp theo: Chọn khách sạn?** Gõ "tìm khách sạn" hoặc "bỏ qua" để tôi tự động lên lịch hoàn chỉnh.""",
            "ui_type": "options",
            "ui_data": {
                "options": [
                    "🏨 Tìm khách sạn",
                    "⏭️ Bỏ qua, tự lên lịch hoàn chỉnh"
                ]
            },
            "context": context.to_dict(),
            "status": "partial"
        }
    
    def _enrich_spot(self, spot: Dict, index: int) -> Dict:
        """
        Enrich spot with derived fields (best_visit_time, avg_duration_min).
        
        If spot doesn't have these fields, derive from category/tags.
        """
        enriched = spot.copy()
        
        # Ensure ID
        if "id" not in enriched:
            enriched["id"] = spot.get("_id") or f"spot_{index}"
        if isinstance(enriched["id"], object) and hasattr(enriched["id"], "__str__"):
            enriched["id"] = str(enriched["id"])
        
        # Get category
        category = spot.get("category", "").lower()
        if not category:
            tags = spot.get("tags", [])
            category = tags[0].lower() if tags else ""
        
        enriched["category"] = category or "attraction"
        
        # Derive best_visit_time if missing
        if not enriched.get("best_visit_time"):
            # Try exact match first
            best_time = CATEGORY_BEST_TIME.get(category, [])
            
            # Try partial match
            if not best_time:
                for cat_key, times in CATEGORY_BEST_TIME.items():
                    if cat_key in category or category in cat_key:
                        best_time = times
                        break
            
            # Check name patterns for night markets
            name_lower = enriched.get("name", "").lower()
            if "chợ đêm" in name_lower or "night market" in name_lower:
                best_time = ["evening", "night"]
            elif "bình minh" in name_lower or "sunrise" in name_lower:
                best_time = ["early_morning"]
            elif "hoàng hôn" in name_lower or "sunset" in name_lower:
                best_time = ["afternoon", "evening"]
            
            # Default if still nothing
            enriched["best_visit_time"] = best_time or ["morning", "afternoon", "evening"]
        
        # Derive avg_duration_min if missing
        if not enriched.get("avg_duration_min"):
            duration = CATEGORY_DURATION.get(category, 60)
            
            # Adjust based on type
            if "theme_park" in category or "safari" in name_lower if "name_lower" in dir() else False:
                duration = 240
            
            enriched["avg_duration_min"] = duration
        
        # Extract area from address
        if not enriched.get("area"):
            address = enriched.get("address", "")
            if address:
                # Try to extract district/ward
                parts = address.split(",")
                if len(parts) >= 2:
                    enriched["area"] = parts[-2].strip()
                else:
                    enriched["area"] = address[:30]
        
        return enriched
    
    def _select_default_spots(self, spots: List[Dict], duration: int) -> List[Dict]:
        """
        Select default spots for the trip.
        
        Strategy:
        - Pick 2-3 spots per day
        - Balance categories (don't pick all beaches)
        - Prioritize by rating
        """
        spots_per_day = 3
        target_count = duration * spots_per_day
        
        # Sort by rating
        sorted_spots = sorted(
            spots, 
            key=lambda x: x.get("rating", 0), 
            reverse=True
        )
        
        # Pick with category diversity
        selected = []
        selected_categories = {}
        max_per_category = target_count // 3 + 1
        
        for spot in sorted_spots:
            if len(selected) >= target_count:
                break
            
            category = spot.get("category", "other")
            
            # Limit per category for diversity
            if selected_categories.get(category, 0) >= max_per_category:
                continue
            
            selected.append(spot)
            selected_categories[category] = selected_categories.get(category, 0) + 1
        
        return selected
    
    def _create_empty_response(self, location: str, context: Any) -> Dict[str, Any]:
        """Create response when no spots found."""
        return {
            "reply": f"⚠️ Chưa tìm thấy địa điểm nào tại **{location}**.\n\n"
                     f"Bạn có thể:\n"
                     f"• Thử địa điểm khác\n"
                     f"• Để tôi tìm kiếm trên web",
            "ui_type": "options",
            "ui_data": {
                "options": [
                    "🔍 Tìm trên web",
                    "📍 Thử địa điểm khác"
                ]
            },
            "context": context.to_dict(),
            "status": "partial"
        }


def create_spot_selector_handler(mongo_manager=None, llm_client=None) -> SpotSelectorHandler:
    """Factory function to create SpotSelectorHandler."""
    return SpotSelectorHandler(mongo_manager, llm_client)
