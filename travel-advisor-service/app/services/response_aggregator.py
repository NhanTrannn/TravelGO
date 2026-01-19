"""
Response Aggregator - Combines multiple expert results into coherent response
Handles multi-section responses with clear structure
"""

from typing import Dict, Any, List, Optional
from app.core import logger


def get_spot_description(spot: Dict, max_length: int = 300) -> str:
    """
    Get description from spot data, checking multiple field names.

    Priority: description_short > description > description_full (truncated)

    Args:
        spot: Spot data dictionary
        max_length: Maximum length for description

    Returns:
        Description string or empty string
    """
    desc = (
        spot.get("description_short")
        or spot.get("description")
        or (
            spot.get("description_full", "")[:max_length]
            if spot.get("description_full")
            else ""
        )
    )
    return str(desc).strip() if desc else ""


def get_spot_category(spot: Dict) -> str:
    """
    Get category from spot data with fallback to tags.

    Priority: category > tags[0] > "Điểm tham quan"

    Args:
        spot: Spot data dictionary

    Returns:
        Category string
    """
    category = spot.get("category")
    if not category or category == "None" or category == "null":
        tags = spot.get("tags", [])
        if tags and len(tags) > 0:
            category = tags[0]
        else:
            category = "Điểm tham quan"
    return category


def get_spot_image(spot: Dict) -> Optional[str]:
    """
    Get image URL from spot data, checking multiple field names.

    Priority: image > image_url > images[0]

    Args:
        spot: Spot data dictionary

    Returns:
        Image URL string or None
    """
    return (
        spot.get("image")
        or spot.get("image_url")
        or (spot.get("images", [None])[0] if spot.get("images") else None)
    )


class ResponseAggregator:
    """
    Aggregates results from multiple experts into structured response

    Handles multi-intent responses like:
    - Hotel + Spot + Food → Comprehensive travel guide
    - Spot + Food → Activity recommendations
    - Hotel + Spot → Accommodation + attractions
    """

    def __init__(self, llm_client=None):
        self.llm = llm_client
        logger.info("✅ ResponseAggregator initialized")

    def _clean_spot_data(self, spot: Dict) -> Dict:
        """Clean and enrich spot data for better UI display"""
        cleaned = spot.copy()

        # Remove non-JSON-serializable fields (numpy arrays, etc.)
        non_serializable_fields = ["embedding", "vector", "embeddings", "_id"]
        for field in non_serializable_fields:
            cleaned.pop(field, None)

        # Normalize rating (spots use 0-5 scale already, but handle edge cases)
        raw_rating = cleaned.get("rating")
        if raw_rating in [0, 0.0, None, ""]:
            cleaned["rating"] = None
            cleaned["rating_display"] = "Chưa có đánh giá"
        else:
            try:
                rating = float(raw_rating)
                if rating > 5:
                    # If somehow on 0-10 scale, convert
                    rating = rating / 2
                cleaned["rating"] = round(rating, 1)
                cleaned["rating_display"] = f"⭐ {rating:.1f}/5"
            except:
                cleaned["rating"] = None
                cleaned["rating_display"] = "Chưa có đánh giá"

        # Clean description - check multiple field names
        desc = (
            cleaned.get("description_short")
            or cleaned.get("description")
            or cleaned.get("description_full", "")[:300]
        )
        if desc:
            desc = str(desc).strip()
            if len(desc) > 150:
                cleaned["description"] = desc[:147] + "..."
            else:
                cleaned["description"] = desc
        else:
            cleaned["description"] = ""

        # Ensure tags is a list
        if cleaned.get("tags"):
            if isinstance(cleaned["tags"], str):
                cleaned["tags"] = [cleaned["tags"]]
            elif not isinstance(cleaned["tags"], list):
                cleaned["tags"] = []

        # Add display-friendly fields
        if cleaned.get("location"):
            cleaned["location_short"] = str(cleaned["location"])[:50]

        # Ensure image has fallback
        if not cleaned.get("image"):
            cleaned["image"] = (
                "https://images.unsplash.com/photo-1469474968028-56623f02e42e?w=400"
            )

        return cleaned

    def _clean_hotel_data(self, hotel: Dict) -> Dict:
        """Clean hotel data and normalize rating"""
        cleaned = hotel.copy()

        # Remove non-JSON-serializable fields (numpy arrays, etc.)
        non_serializable_fields = ["embedding", "vector", "embeddings", "_id"]
        for field in non_serializable_fields:
            cleaned.pop(field, None)

        # Normalize rating: convert 0-10 scale to 0-5 scale
        raw_rating = cleaned.get("rating")
        if raw_rating in [0, 0.0, None, ""]:
            # No rating available
            cleaned["rating"] = None
            cleaned["rating_display"] = "Chưa có đánh giá"
        else:
            try:
                rating = float(raw_rating)
                if rating > 5:
                    # Convert from 0-10 scale to 0-5 scale
                    rating = rating / 2
                cleaned["rating"] = round(rating, 1)
                cleaned["rating_display"] = f"⭐ {rating:.1f}/5"
            except:
                cleaned["rating"] = None
                cleaned["rating_display"] = "Chưa có đánh giá"

        # Format price - ensure priceRange exists for frontend compatibility
        if cleaned.get("price"):
            try:
                price = int(cleaned["price"])
                if price > 0:
                    cleaned["price_display"] = f"{price:,} đ"
                    # Add priceRange for frontend (uses priceRange or price_formatted)
                    if not cleaned.get("priceRange"):
                        cleaned["priceRange"] = cleaned.get(
                            "price_formatted"
                        ) or f"{price:,.0f} VNĐ/đêm".replace(",", ".")
                else:
                    cleaned.pop("price", None)
            except:
                pass

        # Ensure priceRange exists with fallback
        if not cleaned.get("priceRange"):
            cleaned["priceRange"] = cleaned.get("price_formatted", "Liên hệ")

        # Ensure image has fallback - MongoDB uses 'image_url' for hotels
        if not cleaned.get("image"):
            # Try image_url field (MongoDB hotels use this)
            if cleaned.get("image_url"):
                cleaned["image"] = cleaned["image_url"]
            else:
                cleaned["image"] = (
                    "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=400"
                )

        return cleaned

    def aggregate(
        self,
        intents: List[str],
        aggregated_data: Dict[str, Any],
        location: Optional[str] = None,
        context: Dict[str, Any] = None,
        streaming: bool = False,
    ) -> Dict[str, Any]:
        """
        Aggregate multi-intent results into structured response

        Args:
            intents: List of intents (e.g., ["find_hotel", "find_spot", "find_food"])
            aggregated_data: Dict with keys {spots, hotels, food, itinerary, costs}
            location: Location name
            context: Conversation context
            streaming: If True, skip header/footer to avoid duplication in chunks

        Returns:
            Response dict with reply, ui_type, ui_data
        """
        context = context or {}
        location = location or context.get("destination", "khu vực này")

        # Determine response type based on intents
        if len(intents) == 1:
            # Single intent - use specific formatter
            return self._format_single_intent(
                intents[0], aggregated_data, location, context
            )

        # Multi-intent - create comprehensive response
        logger.info(
            f"📝 Aggregating multi-intent response: {intents} (streaming={streaming})"
        )

        return self._format_multi_intent(
            intents, aggregated_data, location, context, streaming
        )

    def _format_single_intent(
        self, intent: str, data: Dict[str, Any], location: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Format single-intent response"""

        if intent == "find_hotel":
            return self._format_hotels(data["hotels"], location)
        elif intent == "find_spot":
            return self._format_spots(data["spots"], location)
        elif intent == "find_food":
            return self._format_food(data["food"], location)
        elif intent == "plan_trip":
            return self._format_itinerary(data, location, context)
        else:
            return {"reply": "Xin lỗi, mình chưa hiểu câu hỏi này.", "ui_type": "none"}

    def _format_multi_intent(
        self,
        intents: List[str],
        data: Dict[str, Any],
        location: str,
        context: Dict[str, Any],
        streaming: bool = False,
    ) -> Dict[str, Any]:
        """
        Format multi-intent response with clear sections

        Args:
            streaming: If True, skip header and footer (for progressive chunks)
        """

        sections = []
        ui_data = {}
        duration = context.get("duration", 3)
        budget = context.get("budget")
        budget_level = (
            context.get("budget_level") or budget
        )  # Use budget_level or fallback to budget
        people_count = context.get("people_count", 1)

        # === REORDERED FLOW FOR BETTER UX ===

        # 1. HEADER - Trip Overview (skip in streaming)
        if not streaming:
            header = self._create_trip_header(
                location, duration, budget_level, people_count
            )
            sections.append(header)

        # 2. ITINERARY TEMPLATE (with time slots for selection)
        if "plan_trip" in intents and data.get("itinerary"):
            itinerary_section = self._create_itinerary_section(
                data["itinerary"], duration
            )
            sections.append(itinerary_section)
            ui_data["itinerary"] = self._enhance_itinerary_for_ui(
                data["itinerary"], duration
            )

        # 3. SPOTS SUGGESTIONS (for user to choose and add to itinerary)
        if data.get("spots"):
            cleaned_spots = [self._clean_spot_data(s) for s in data["spots"][:8]]
            spot_section = self._create_spot_section(cleaned_spots)
            sections.append(spot_section)
            ui_data["spots"] = cleaned_spots
            ui_data["spots_selectable"] = True  # Flag for frontend

        # 4. HOTELS (matching budget)
        if data.get("hotels"):
            cleaned_hotels = [self._clean_hotel_data(h) for h in data["hotels"][:5]]
            hotel_section = self._create_hotel_section(cleaned_hotels)
            sections.append(hotel_section)
            ui_data["hotels"] = cleaned_hotels
            ui_data["hotels_selectable"] = True

        # 5. FOOD RECOMMENDATIONS
        if data.get("food"):
            food_section = self._create_food_section(data["food"])
            sections.append(food_section)
            ui_data["food"] = data["food"][:5]

        # 6. COST BREAKDOWN (detailed, based on actual data)
        if data.get("costs") or (data.get("hotels") and duration):
            cost_data = self._calculate_detailed_cost(
                hotels=data.get("hotels", []),
                spots=data.get("spots", []),
                duration=duration,
                people_count=people_count,
                budget=budget_level,
                existing_costs=data.get("costs"),
            )
            cost_section = self._create_detailed_cost_section(cost_data, location)
            sections.append(cost_section)
            ui_data["costs"] = cost_data

        # Footer with suggestions - skip in streaming mode
        if not streaming:
            sections.append(self._create_footer(intents, location))

        reply = "\n\n".join(sections)

        return {
            "reply": reply,
            "ui_type": "comprehensive",
            "ui_data": ui_data,
            "intent": "multi_intent",
            "intents": intents,
        }

    def _create_hotel_section(self, hotels: List[Dict]) -> str:
        """Create hotels section"""
        lines = ["🏨 **Khách sạn đề xuất**\n"]

        for i, hotel in enumerate(hotels[:5], 1):
            name = hotel.get("name", "N/A")
            price = hotel.get("price_formatted", "N/A")
            address = hotel.get("address", "")[:50]

            # Use rating_display if available, otherwise format rating
            rating_display = hotel.get("rating_display")
            if not rating_display:
                rating = hotel.get("rating")
                if rating and rating > 0:
                    # Already converted to 0-5 scale in _clean_hotel_data
                    rating_display = f"⭐ {rating}/5"
                else:
                    rating_display = ""

            lines.append(f"**{i}. {name}**")
            if rating_display:
                lines.append(f"   💵 {price}/đêm | {rating_display}")
            else:
                lines.append(f"   💵 {price}/đêm")
            if address:
                lines.append(f"   📍 {address}...")
            lines.append("")

        return "\n".join(lines)

    def _create_spot_section(self, spots: List[Dict]) -> str:
        """Create spots section with better formatting"""
        lines = ["📍 **Địa điểm tham quan**\n"]

        for i, spot in enumerate(spots[:6], 1):
            name = spot.get("name", "N/A")
            rating = spot.get("rating", 0)
            desc = spot.get("description", "")
            location = spot.get("location", "")
            tags = spot.get("tags", [])

            # Format spot name with rating (only if > 0)
            if rating and rating > 0:
                lines.append(f"**{i}. {name}** ⭐ {rating}")
            else:
                lines.append(f"**{i}. {name}**")

            # Add location if available
            if location:
                lines.append(f"   📍 {location}")

            # Add tags if available
            if tags and isinstance(tags, list):
                tag_str = " • ".join(tags[:3])  # Top 3 tags
                lines.append(f"   🏷️ {tag_str}")

            # Add description (truncate if too long)
            if desc:
                clean_desc = desc.strip()[:100]
                if len(desc) > 100:
                    clean_desc += "..."
                lines.append(f"   {clean_desc}")

            lines.append("")  # Empty line between spots

        return "\n".join(lines)

    def _create_food_section(self, food_items: List[Dict]) -> str:
        """Create food section"""
        lines = ["🍜 **Ẩm thực địa phương**\n"]

        for item in food_items[:5]:
            if item.get("type") == "recommendation":
                dishes = item.get("dishes", [])
                lines.append(f"🌟 **Món đặc sản:** {', '.join(dishes[:5])}")
            else:
                name = item.get("name", "N/A")
                rating = item.get("rating", 0)
                price = item.get("price_range", "")

                lines.append(f"• **{name}** ⭐ {rating}")
                if price:
                    lines.append(f"  💵 {price}")
            lines.append("")

        return "\n".join(lines)

    def _create_itinerary_section(self, itinerary: List[Dict], duration: int) -> str:
        """Create itinerary section"""
        lines = [f"🗓️ **Lịch trình {duration} ngày**\n"]

        for day_plan in itinerary[:duration]:
            day = day_plan.get("day", 1)
            activities = day_plan.get("activities", [])

            lines.append(f"**Ngày {day}:**")
            for activity in activities[:4]:
                time = activity.get("time", "")
                name = activity.get("activity", "N/A")
                act_type = activity.get("type", "")

                icon = self._get_activity_icon(act_type)
                lines.append(f"  {icon} {time} - {name}")
            lines.append("")

        return "\n".join(lines)

    def _create_cost_section(self, costs: Dict[str, Any]) -> str:
        """Create cost breakdown section"""
        lines = ["💰 **Ước tính chi phí**\n"]

        total = costs.get("total", 0)
        breakdown = costs.get("breakdown", {})

        for category, amount in breakdown.items():
            category_name = self._translate_cost_category(category)
            lines.append(f"• {category_name}: {self._format_money(amount)}")

        lines.append(f"\n**Tổng cộng:** {self._format_money(total)}")
        lines.append("")

        return "\n".join(lines)

    def _create_footer(self, intents: List[str], location: str) -> str:
        """Create footer with suggestions"""
        lines = ["---", "💡 **Gợi ý tiếp theo:**"]

        if "plan_trip" not in intents:
            lines.append("• Lên lịch trình chi tiết")
        if "find_food" not in intents:
            lines.append("• Tìm quán ăn ngon")
        if "find_hotel" not in intents:
            lines.append("• Xem thêm khách sạn")

        return "\n".join(lines)

    def _format_hotels(self, hotels: List[Dict], location: str) -> Dict:
        """Format hotel-only response - concise text since UI cards show details"""
        if not hotels:
            return {
                "reply": f"❌ Không tìm thấy khách sạn ở {location}",
                "ui_type": "none",
            }

        # Clean hotel data
        cleaned_hotels = [self._clean_hotel_data(h) for h in hotels[:5]]

        # Short reply since UI cards show full details
        reply = f"🏨 Tìm thấy **{len(cleaned_hotels)} khách sạn** tại {location}:\n\n"
        reply += "_Chọn khách sạn bên dưới để xem chi tiết hoặc đặt phòng._"

        return {
            "reply": reply,
            "ui_type": "hotel_cards",
            "ui_data": {
                "hotels": cleaned_hotels,
                "actions": [
                    {"label": "🔍 Xem thêm khách sạn", "action": "more_hotels"},
                    {"label": "💰 So sánh giá", "action": "compare_prices"},
                    {"label": "📍 Tìm địa điểm gần đây", "action": "find_spots"},
                ],
            },
        }

    def _format_spots(self, spots: List[Dict], location: str) -> Dict:
        """Format spot-only response - concise text since UI cards show details"""
        if not spots:
            return {
                "reply": f"❌ Không tìm thấy địa điểm ở {location}",
                "ui_type": "none",
            }

        # Clean spot data
        cleaned_spots = [self._clean_spot_data(s) for s in spots[:6]]

        # Short reply since UI cards show full details
        reply = f"📍 Tìm thấy **{len(cleaned_spots)} địa điểm** tại {location}:\n\n"
        reply += "_Chọn địa điểm bên dưới để xem chi tiết._"

        return {
            "reply": reply,
            "ui_type": "spot_cards",
            "ui_data": {
                "spots": cleaned_spots,
                "actions": [
                    {"label": "➕ Xem thêm địa điểm", "action": "more_spots"},
                    {"label": "🏨 Tìm khách sạn gần đây", "action": "find_hotels"},
                    {"label": "🗓️ Lên lịch trình", "action": "plan_trip"},
                ],
            },
        }

    def _format_food(self, food: List[Dict], location: str) -> Dict:
        """Format food-only response - concise text"""
        if not food:
            return {
                "reply": f"🍜 Mình chưa có nhiều thông tin về quán ăn ở {location}",
                "ui_type": "none",
            }

        # Short reply
        reply = f"🍜 Tìm thấy **{len(food[:5])} quán ăn/món ngon** tại {location}:\n\n"
        reply += "_Chọn để xem chi tiết._"

        return {
            "reply": reply,
            "ui_type": "food_cards",
            "ui_data": {
                "food": food[:5],
                "actions": [
                    {"label": "➕ Xem thêm quán ăn", "action": "more_food"},
                    {"label": "📍 Địa điểm gần đây", "action": "find_spots"},
                ],
            },
        }

    def _format_itinerary(self, data: Dict, location: str, context: Dict) -> Dict:
        """Format itinerary response"""
        duration = context.get("duration", 3)

        sections = [
            f"🗓️ **Lịch trình {duration} ngày {location}**\n",
            self._create_itinerary_section(data.get("itinerary", []), duration),
        ]

        if data.get("costs"):
            sections.append(self._create_cost_section(data["costs"]))

        return {
            "reply": "\n\n".join(sections),
            "ui_type": "itinerary",
            "ui_data": {
                "itinerary": data.get("itinerary", []),
                "hotels": data.get("hotels", [])[:3],
                "spots": data.get("spots", [])[:5],
                "costs": data.get("costs", {}),
            },
        }

    # Helper methods
    # =========== NEW HELPER FUNCTIONS FOR UX FLOW ===========

    def _create_trip_header(
        self, location: str, duration: int, budget_level: str, people_count: int
    ) -> str:
        """Create trip header with overview"""
        # Normalize budget for display
        budget_normalized = (
            self._normalize_budget_level(budget_level) if budget_level else "mid"
        )
        budget_text = {
            "budget": "tiết kiệm 💰",
            "mid": "trung bình 💵💵",
            "luxury": "cao cấp 💎",
        }.get(budget_normalized, "linh hoạt")

        people_text = f"{people_count} người" if people_count > 1 else ""

        header = f"""🌟 **Chuyến du lịch {location}**
📅 {duration} ngày | 👥 {people_text} | {budget_text}"""

        return header.strip()

    def _enhance_itinerary_for_ui(
        self, itinerary: List[Dict], duration: int
    ) -> List[Dict]:
        """Enhance itinerary data for frontend interactive selection"""
        enhanced = []
        for day_plan in itinerary[:duration]:
            day = day_plan.get("day", 1)
            activities = day_plan.get("activities", [])

            enhanced_day = {
                "day": day,
                "activities": [],
                "selectable_slots": [
                    {"time": "Sáng", "slot_id": f"day{day}_morning", "selected": None},
                    {"time": "Trưa", "slot_id": f"day{day}_noon", "selected": None},
                    {
                        "time": "Chiều",
                        "slot_id": f"day{day}_afternoon",
                        "selected": None,
                    },
                    {"time": "Tối", "slot_id": f"day{day}_evening", "selected": None},
                ],
            }

            # Map existing activities to slots
            for act in activities:
                time = act.get("time", "").lower()
                enhanced_act = {
                    "activity": act.get("activity", ""),
                    "type": act.get("type", "spot"),
                    "time": act.get("time", ""),
                    "cost_estimate": act.get("cost", 0),
                    "selectable": True,
                }
                enhanced_day["activities"].append(enhanced_act)

                # Pre-fill slots
                if "sáng" in time or "7:" in time or "8:" in time or "9:" in time:
                    enhanced_day["selectable_slots"][0]["selected"] = enhanced_act
                elif "trưa" in time or "12:" in time or "11:" in time:
                    enhanced_day["selectable_slots"][1]["selected"] = enhanced_act
                elif "chiều" in time or "14:" in time or "15:" in time or "16:" in time:
                    enhanced_day["selectable_slots"][2]["selected"] = enhanced_act
                elif "tối" in time or "18:" in time or "19:" in time or "20:" in time:
                    enhanced_day["selectable_slots"][3]["selected"] = enhanced_act

            enhanced.append(enhanced_day)

        return enhanced

    def _calculate_detailed_cost(
        self,
        hotels: List[Dict],
        spots: List[Dict],
        duration: int,
        people_count: int,
        budget: str,
        existing_costs: Dict = None,
    ) -> Dict:
        """Calculate detailed costs based on actual data"""

        # If we have existing costs, enhance them
        if existing_costs and existing_costs.get("total", 0) > 0:
            return existing_costs

        # Normalize budget level to standard keys
        budget_normalized = self._normalize_budget_level(budget)

        # Calculate accommodation cost from hotels
        accommodation_per_night = 0
        if hotels:
            # Get average price from available hotels
            valid_prices = []
            for h in hotels[:3]:
                price = h.get("price_per_night", 0) or h.get("price", 0)
                if isinstance(price, str):
                    # Parse string like "500,000 VND"
                    price = int("".join(filter(str.isdigit, price)) or 0)
                if price > 0:
                    valid_prices.append(price)

            if valid_prices:
                accommodation_per_night = sum(valid_prices) // len(valid_prices)
            else:
                # Use budget-based estimate
                accommodation_per_night = {
                    "budget": 400_000,
                    "mid": 800_000,
                    "luxury": 2_000_000,
                }.get(budget_normalized, 600_000)
        else:
            accommodation_per_night = {
                "budget": 400_000,
                "mid": 800_000,
                "luxury": 2_000_000,
            }.get(budget_normalized, 600_000)

        # Daily estimates per person
        daily_food = {"budget": 200_000, "mid": 400_000, "luxury": 800_000}.get(
            budget_normalized, 300_000
        )

        daily_activities = {"budget": 100_000, "mid": 200_000, "luxury": 500_000}.get(
            budget_normalized, 150_000
        )

        daily_transport = {"budget": 100_000, "mid": 200_000, "luxury": 400_000}.get(
            budget_normalized, 150_000
        )

        # Calculate totals
        total_accommodation = accommodation_per_night * duration
        total_food = daily_food * duration * people_count
        total_activities = daily_activities * duration * people_count
        total_transport = daily_transport * duration

        grand_total = (
            total_accommodation + total_food + total_activities + total_transport
        )

        return {
            "total": grand_total,
            "per_person": (
                grand_total // people_count if people_count > 1 else grand_total
            ),
            "breakdown": {
                "accommodation": total_accommodation,
                "food": total_food,
                "activities": total_activities,
                "transport": total_transport,
            },
            "daily_estimate": {
                "accommodation": accommodation_per_night,
                "food": daily_food * people_count,
                "activities": daily_activities * people_count,
                "transport": daily_transport,
            },
            "duration": duration,
            "people_count": people_count,
            "budget_level": budget_normalized,
        }

    def _create_detailed_cost_section(self, cost_data: Dict, location: str) -> str:
        """Create detailed cost breakdown section"""
        lines = ["💰 **Ước tính chi phí**\n"]

        breakdown = cost_data.get("breakdown", {})
        daily = cost_data.get("daily_estimate", {})
        duration = cost_data.get("duration", 3)
        people = cost_data.get("people_count", 1)

        # Header info
        if people > 1:
            lines.append(f"📊 *Chi phí cho {people} người, {duration} ngày*\n")

        # Breakdown by category
        for category, total in breakdown.items():
            category_name = self._translate_cost_category(category)
            daily_cost = daily.get(category, 0)

            if daily_cost > 0:
                lines.append(
                    f"• **{category_name}:** ~{self._format_money(daily_cost)}/ngày"
                )
                lines.append(f"  └ Tổng: {self._format_money(total)}")
            else:
                lines.append(f"• **{category_name}:** {self._format_money(total)}")

        lines.append("")

        # Total
        total = cost_data.get("total", 0)
        per_person = cost_data.get("per_person", total)

        lines.append(f"**💵 Tổng chi phí:** {self._format_money(total)}")
        if people > 1:
            lines.append(f"**👤 Mỗi người:** ~{self._format_money(per_person)}")

        # Budget note
        budget = cost_data.get("budget_level", "mid")
        budget_notes = {
            "budget": "💡 *Đây là mức chi tiêu tiết kiệm*",
            "mid": "💡 *Đây là mức chi tiêu trung bình phổ biến*",
            "luxury": "💡 *Đây là mức chi tiêu cao cấp*",
        }
        if budget in budget_notes:
            lines.append(f"\n{budget_notes[budget]}")

        return "\n".join(lines)

    def _normalize_budget_level(self, budget_level: str) -> str:
        """Normalize budget level from various formats to standard keys"""
        if not budget_level:
            return "mid"

        budget_lower = budget_level.lower().strip()

        # Vietnamese to English mapping
        mapping = {
            # Tiết kiệm / Budget
            "tiết kiệm": "budget",
            "tiet kiem": "budget",
            "bình dân": "budget",
            "binh dan": "budget",
            "rẻ": "budget",
            "re": "budget",
            "thấp": "budget",
            "low": "budget",
            "budget": "budget",
            # Trung bình / Mid
            "trung bình": "mid",
            "trung binh": "mid",
            "vừa": "mid",
            "vua": "mid",
            "phổ thông": "mid",
            "pho thong": "mid",
            "mid": "mid",
            "medium": "mid",
            "standard": "mid",
            # Sang trọng / Luxury
            "sang trọng": "luxury",
            "sang trong": "luxury",
            "cao cấp": "luxury",
            "cao cap": "luxury",
            "xa xỉ": "luxury",
            "luxury": "luxury",
            "high": "luxury",
            "premium": "luxury",
        }

        return mapping.get(budget_lower, "mid")

    def _get_activity_icon(self, act_type: str) -> str:
        """Get emoji for activity type"""
        icons = {"spot": "📍", "food": "🍜", "hotel": "🏨", "transport": "🚗"}
        return icons.get(act_type, "•")

    def _translate_cost_category(self, category: str) -> str:
        """Translate cost category to Vietnamese"""
        translations = {
            "accommodation": "Chỗ ở",
            "food": "Ăn uống",
            "transport": "Di chuyển",
            "activities": "Hoạt động",
            "other": "Khác",
        }
        return translations.get(category, category)

    def _format_money(self, amount: int) -> str:
        """Format VND amount"""
        if amount >= 1_000_000:
            return f"{amount/1_000_000:.1f} triệu"
        else:
            return f"{amount:,}đ"


def create_response_aggregator(llm_client=None) -> ResponseAggregator:
    """Factory function"""
    return ResponseAggregator(llm_client)
