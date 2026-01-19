"""
Itinerary Expert - Generates day-by-day travel itineraries
"""

import time
from typing import Dict, Any, List, Optional
from .base_expert import BaseExpert, ExpertResult
from app.core import logger
from app.services.weather import WeatherService


class ItineraryExpert(BaseExpert):
    """
    Expert for creating detailed itineraries
    Uses LLM to synthesize spots, food, and hotel data into a coherent plan
    """

    def __init__(self, mongodb_manager, vector_store, llm_client):
        super().__init__(mongodb_manager, vector_store, llm_client)
        self.weather = WeatherService()

    @property
    def expert_type(self) -> str:
        return "itinerary_expert"

    def execute(self, query: str, parameters: Dict[str, Any]) -> ExpertResult:
        """
        Create itinerary from collected data

        Parameters:
            - location: Destination
            - duration: Number of days
            - people_count: Number of travelers
            - budget: Total budget
            - interests: List of interests
            - spots_data: Data from SpotExpert
            - food_data: Data from FoodExpert
            - hotel_data: Data from HotelExpert
        """
        start_time = time.time()

        try:
            location = parameters.get("location", "Việt Nam")

            # FIX P1: Đảm bảo duration là số nguyên và lấy đúng từ tham số
            raw_duration = parameters.get("duration") or parameters.get("num_days") or 3
            try:
                duration = int(raw_duration)
            except (ValueError, TypeError):
                logger.warning(f"⚠️ Invalid duration '{raw_duration}', defaulting to 3")
                duration = 3

            people_count = parameters.get("people_count", 1)
            budget = parameters.get("budget")
            interests = parameters.get("interests", [])

            # Get data from other experts (passed via parameters)
            spots_data = parameters.get("spots_data", [])
            food_data = parameters.get("food_data", [])
            hotel_data = parameters.get("hotel_data", [])

            # Get weather data if start_date is provided
            start_date = parameters.get("start_date")
            weather_data = None
            weather_prompt = ""

            if start_date:
                try:
                    weather_summary = self.weather.get_weather(
                        location, start_date, duration
                    )
                    weather_data = weather_summary
                    weather_prompt = self.weather.build_weather_prompt(weather_summary)
                    logger.info(
                        f"☀️ Weather data retrieved: {weather_summary['overall']['comfort_level']}"
                    )
                except Exception as e:
                    logger.warning(f"⚠️ Weather service error: {e}")

            logger.info(
                f"🔍 ItineraryExpert: {location}, {duration} days (parsed from {raw_duration}), {len(spots_data)} spots"
            )

            # Generate itinerary
            if self.llm:
                itinerary = self._generate_with_llm(
                    location,
                    duration,
                    people_count,
                    budget,
                    interests,
                    spots_data,
                    food_data,
                    hotel_data,
                    weather_prompt,
                )
            else:
                itinerary = self._generate_simple(
                    location, duration, spots_data, food_data, hotel_data
                )

            execution_time = int((time.time() - start_time) * 1000)

            return ExpertResult(
                expert_type=self.expert_type,
                success=True,
                data=itinerary,
                summary=f"Lịch trình {duration} ngày tại {location}",
                execution_time_ms=execution_time,
            )

        except Exception as e:
            logger.error(f"❌ ItineraryExpert error: {e}")
            return ExpertResult(
                expert_type=self.expert_type,
                success=False,
                data=[],
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000),
            )

    def _generate_with_llm(
        self,
        location: str,
        duration: int,
        people_count: int,
        budget: int,
        interests: List[str],
        spots: List[Dict],
        foods: List[Dict],
        hotels: List[Dict],
        weather_prompt: str = "",
    ) -> List[Dict]:
        """Generate itinerary using LLM"""

        # Prepare context
        spots_context = (
            "\n".join(
                [
                    f"- {s.get('name')} (Rating: {s.get('rating', 'N/A')})"
                    for s in spots[:8]
                ]
            )
            if spots
            else "Chưa có thông tin địa điểm"
        )

        foods_context = (
            "\n".join(
                [
                    f"- {f.get('name')}: {f.get('description', '')[:50]}"
                    for f in foods[:5]
                ]
            )
            if foods
            else "Chưa có thông tin ẩm thực"
        )

        hotels_context = (
            "\n".join(
                [
                    f"- {h.get('name')} ({h.get('price_formatted', 'N/A')})"
                    for h in hotels[:3]
                ]
            )
            if hotels
            else "Chưa chọn khách sạn"
        )

        budget_text = f"{budget:,} VNĐ" if budget else "Linh hoạt"
        interests_text = ", ".join(interests) if interests else "Tham quan, trải nghiệm"

        # Weather context block
        weather_block = f"\n\n{weather_prompt}\n" if weather_prompt else ""

        prompt = f"""Bạn là chuyên gia du lịch Việt Nam. Hãy tạo lịch trình {duration} ngày cho {people_count} người tại **{location}**.
{weather_block}
⚠️ QUY TẮC BẮT BUỘC:
1. TẤT CẢ địa điểm PHẢI ở {location}. KHÔNG đề cập thành phố/tỉnh khác!
2. KHÔNG được lặp lại bất kỳ địa điểm nào giữa các ngày - mỗi địa điểm chỉ xuất hiện MỘT LẦN trong toàn bộ lịch trình
3. Mỗi ngày phải có địa điểm KHÁC BIỆT hoàn toàn với các ngày khác
4. Đa dạng loại hình: thiên nhiên, văn hóa, ẩm thực, giải trí xen kẽ

THÔNG TIN CHUYẾN ĐI:
- Điểm đến: {location}
- Thời gian: {duration} ngày
- Số người: {people_count}
- Ngân sách: {budget_text}
- Sở thích: {interests_text}

ĐỊA ĐIỂM TẠI {location.upper()} (dùng những địa điểm này nếu có):
{spots_context}

ẨM THỰC TẠI {location.upper()}:
{foods_context}

KHÁCH SẠN TẠI {location.upper()}:
{hotels_context}

YÊU CẦU CHI TIẾT:
1. Sáng: 1-2 điểm tham quan chính
2. Trưa: Ăn trưa tại nhà hàng/quán địa phương
3. Chiều: 1-2 điểm tham quan hoặc trải nghiệm
4. Tối: Ăn tối, nghỉ ngơi hoặc hoạt động nhẹ
5. Nếu không đủ dữ liệu, gợi ý địa điểm NỔI TIẾNG KHÁC NHAU của {location}
6. {'Dựa vào thông tin thời tiết để gợi ý hoạt động phù hợp cho từng ngày' if weather_prompt else ''}

⚠️ KIỂM TRA TRƯỚC KHI TRẢ VỀ: Đảm bảo KHÔNG có địa điểm nào bị lặp lại!

Trả về JSON format:
[
  {{
    "day": 1,
    "title": "Tiêu đề ngày (mô tả theme của ngày)",
    "activities": [
      {{"time": "08:00", "activity": "Tên hoạt động", "location": "Địa điểm cụ thể", "type": "sightseeing|food|culture|nature"}},
      ...
    ],
    "meals": {{"breakfast": "...", "lunch": "...", "dinner": "..."}},
    "hotel": "Tên khách sạn"
  }},
  ...
]

CHỈ trả về JSON, không giải thích."""

        try:
            result = self.llm.extract_json(prompt)

            if isinstance(result, list):
                return result
            elif isinstance(result, dict) and "days" in result:
                return result["days"]
            else:
                return [result]

        except Exception as e:
            logger.error(f"❌ LLM itinerary generation failed: {e}")
            return self._generate_simple(location, duration, spots, foods, hotels)

    def _generate_simple(
        self,
        location: str,
        duration: int,
        spots: List[Dict],
        foods: List[Dict],
        hotels: List[Dict],
    ) -> List[Dict]:
        """Generate simple itinerary without LLM"""

        itinerary = []
        spots_per_day = max(1, len(spots) // duration) if spots else 1

        for day in range(1, duration + 1):
            # Get spots for this day
            start_idx = (day - 1) * spots_per_day
            end_idx = start_idx + spots_per_day
            day_spots = spots[start_idx:end_idx] if spots else []

            # Get food for this day
            day_food = foods[(day - 1) % len(foods)] if foods else None

            # Get hotel
            hotel = hotels[0] if hotels else None

            activities = []

            # Morning activity
            if day_spots:
                activities.append(
                    {
                        "time": "09:00",
                        "activity": f"Tham quan {day_spots[0].get('name', 'địa điểm')}",
                        "location": day_spots[0].get("name", ""),
                        "note": (
                            day_spots[0].get("description", "")[:100]
                            if day_spots[0].get("description")
                            else ""
                        ),
                    }
                )

            # Lunch
            activities.append(
                {
                    "time": "12:00",
                    "activity": "Ăn trưa",
                    "location": (
                        day_food.get("name", "Quán ăn địa phương")
                        if day_food
                        else "Quán ăn địa phương"
                    ),
                    "note": "",
                }
            )

            # Afternoon activity
            if len(day_spots) > 1:
                activities.append(
                    {
                        "time": "14:00",
                        "activity": f"Tham quan {day_spots[1].get('name', 'địa điểm')}",
                        "location": day_spots[1].get("name", ""),
                        "note": "",
                    }
                )

            # Evening
            activities.append(
                {
                    "time": "18:00",
                    "activity": "Ăn tối và nghỉ ngơi",
                    "location": "",
                    "note": "",
                }
            )

            itinerary.append(
                {
                    "day": day,
                    "title": f"Ngày {day}: Khám phá {location}",
                    "activities": activities,
                    "meals": {
                        "breakfast": "Tại khách sạn" if hotel else "Quán ăn sáng",
                        "lunch": (
                            day_food.get("name", "Quán ăn địa phương")
                            if day_food
                            else "Quán ăn địa phương"
                        ),
                        "dinner": "Nhà hàng địa phương",
                    },
                    "hotel": hotel.get("name", "") if hotel else "",
                }
            )

        return itinerary


class CostCalculatorExpert(BaseExpert):
    """Expert for calculating trip costs"""

    # Average costs by category (VND)
    COST_ESTIMATES = {
        "accommodation": {
            "tiết kiệm": 300_000,
            "trung bình": 800_000,
            "sang trọng": 2_500_000,
        },
        "food_per_day": {
            "tiết kiệm": 200_000,
            "trung bình": 500_000,
            "sang trọng": 1_000_000,
        },
        "transport_per_day": {
            "tiết kiệm": 100_000,
            "trung bình": 300_000,
            "sang trọng": 800_000,
        },
        "activities_per_day": {
            "tiết kiệm": 100_000,
            "trung bình": 300_000,
            "sang trọng": 500_000,
        },
    }

    @property
    def expert_type(self) -> str:
        return "cost_calculator_expert"

    def execute(self, query: str, parameters: Dict[str, Any]) -> ExpertResult:
        """
        Calculate trip costs

        Parameters:
            - duration: Number of days
            - people_count: Number of travelers
            - budget_level: tiết kiệm/trung bình/sang trọng
            - hotel_data: Selected hotel data
        """
        start_time = time.time()

        try:
            duration = parameters.get("duration", 2)
            people_count = parameters.get("people_count", 1)
            budget_level = parameters.get("budget_level", "trung bình")
            hotel_data = parameters.get("hotel_data", [])

            # Calculate costs
            costs = self._calculate_costs(
                duration, people_count, budget_level, hotel_data
            )

            execution_time = int((time.time() - start_time) * 1000)

            return ExpertResult(
                expert_type=self.expert_type,
                success=True,
                data=[costs],
                summary=f"Tổng chi phí dự kiến: {costs['total']:,.0f} VNĐ",
                execution_time_ms=execution_time,
            )

        except Exception as e:
            logger.error(f"❌ CostCalculatorExpert error: {e}")
            return ExpertResult(
                expert_type=self.expert_type,
                success=False,
                data=[],
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000),
            )

    def _calculate_costs(
        self,
        duration: int,
        people_count: int,
        budget_level: str,
        hotel_data: List[Dict],
    ) -> Dict[str, Any]:
        """Calculate detailed costs"""

        level = budget_level.lower() if budget_level else "trung bình"
        if level not in self.COST_ESTIMATES["accommodation"]:
            level = "trung bình"

        # Accommodation
        if hotel_data and hotel_data[0].get("price"):
            accommodation = (
                hotel_data[0]["price"] * (duration - 1)
                if duration > 1
                else hotel_data[0]["price"]
            )
        else:
            accommodation = (
                self.COST_ESTIMATES["accommodation"][level] * (duration - 1)
                if duration > 1
                else 0
            )

        # Food
        food = self.COST_ESTIMATES["food_per_day"][level] * duration * people_count

        # Transport
        transport = self.COST_ESTIMATES["transport_per_day"][level] * duration

        # Activities
        activities = (
            self.COST_ESTIMATES["activities_per_day"][level] * duration * people_count
        )

        # Total
        total = accommodation + food + transport + activities

        return {
            "accommodation": accommodation,
            "food": food,
            "transport": transport,
            "activities": activities,
            "total": total,
            "per_person": total // people_count if people_count > 0 else total,
            "budget_level": budget_level,
            "duration": duration,
            "people_count": people_count,
            "breakdown": {
                "accommodation_per_night": (
                    accommodation // max(duration - 1, 1) if accommodation else 0
                ),
                "food_per_person_per_day": self.COST_ESTIMATES["food_per_day"][level],
                "transport_per_day": self.COST_ESTIMATES["transport_per_day"][level],
                "activities_per_person_per_day": self.COST_ESTIMATES[
                    "activities_per_day"
                ][level],
            },
        }
