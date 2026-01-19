"""
LLM Prompt Manager - Centralized prompt templates for different use cases
Supports both structured output and natural conversation
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from app.core import logger


@dataclass
class PromptTemplate:
    """A prompt template with system and user parts"""
    name: str
    system_prompt: str
    user_template: str
    expected_format: str  # "json", "text", "markdown"
    fallback_response: str  # Default response if LLM fails


class LLMPromptManager:
    """
    Manages LLM prompts for different scenarios
    Ensures consistent output format
    """
    
    def __init__(self):
        self.templates = self._init_templates()
        logger.info(f"✅ LLMPromptManager initialized with {len(self.templates)} templates")
    
    def _init_templates(self) -> Dict[str, PromptTemplate]:
        """Initialize all prompt templates"""
        return {
            # ============================================
            # ITINERARY GENERATION
            # ============================================
            "create_itinerary": PromptTemplate(
                name="create_itinerary",
                system_prompt="""Bạn là chuyên gia lên lịch trình du lịch Việt Nam.
Nhiệm vụ: Tạo lịch trình CHI TIẾT và THỰC TẾ dựa trên dữ liệu địa điểm được cung cấp.

QUAN TRỌNG:
1. CHỈ sử dụng các địa điểm trong danh sách được cung cấp
2. Sắp xếp theo vị trí địa lý hợp lý (gần nhau cùng ngày)
3. Mỗi ngày có: sáng, trưa, chiều, tối
4. Thêm thời gian di chuyển thực tế
5. Gợi ý món ăn địa phương phù hợp
6. KHÔNG lặp lại địa điểm đã được chọn trong các ngày trước

CONTEXT AWARENESS:
- Nếu user đã có lịch trình từ các ngày trước, TUYỆT ĐỐI không sử dụng lại các địa điểm đó
- Khi user nói "xem lại lịch trình", trả về lịch trình đã lưu, KHÔNG tạo mới
- Khi user nói "xong", "chốt", "hoàn thành" → finalize lịch trình hiện tại
- Khi user nói "tính tiền" kèm context có lịch trình → tính toán chi phí dựa trên lịch trình đó

OUTPUT FORMAT (JSON):
{
    "days": [
        {
            "day": 1,
            "title": "Tiêu đề ngày",
            "activities": [
                {
                    "time": "08:00",
                    "activity": "Tên hoạt động",
                    "location": "Tên địa điểm từ danh sách",
                    "duration": "2 tiếng",
                    "tips": "Mẹo hữu ích",
                    "cost": 100000
                }
            ]
        }
    ],
    "summary": "Tóm tắt chuyến đi",
    "tips": ["Mẹo 1", "Mẹo 2"]
}""",
                user_template="""Tạo lịch trình {duration} ngày tại {location} cho {people_count} người.

CONTEXT:
- Budget level: {budget_level} (tiết kiệm / trung bình / sang trọng)
- Loại người đồng hành: {companion_type}
- Sở thích: {interests}

DANH SÁCH ĐỊA ĐIỂM CÓ SẴN (chưa được chọn):
{spots_list}

KHÁCH SẠN ĐÃ CHỌN/GỢI Ý:
{hotel_info}

MÓN ĂN ĐỊA PHƯƠNG:
{food_list}

LƯU Ý: Nếu danh sách địa điểm có note "đã chọn ngày X", BỎ QUA những địa điểm đó.

Hãy tạo lịch trình chi tiết theo format JSON, phù hợp với budget_level đã chọn.""",
                expected_format="json",
                fallback_response=""
            ),
            
            # ============================================
            # GET DETAIL - Chi tiết về địa điểm/khách sạn
            # ============================================
            "get_detail": PromptTemplate(
                name="get_detail",
                system_prompt="""Bạn là hướng dẫn viên du lịch chuyên nghiệp.
Nhiệm vụ: Cung cấp thông tin CHI TIẾT và HỮU ÍCH về địa điểm/khách sạn.

Bao gồm:
1. Mô tả hấp dẫn (2-3 câu)
2. Điểm nổi bật
3. Thời gian tham quan lý tưởng
4. Chi phí ước tính
5. Mẹo khi đến
6. Đánh giá cá nhân

Viết tự nhiên, thân thiện, như đang trò chuyện.""",
                user_template="""Cho tôi thông tin chi tiết về: {entity_name}

Dữ liệu có sẵn:
{entity_data}

Địa điểm: {location}
Người dùng đang tìm hiểu để đi du lịch.""",
                expected_format="text",
                fallback_response="Xin lỗi, tôi chưa có thông tin chi tiết về địa điểm này. Bạn có thể hỏi về địa điểm khác hoặc tôi có thể tìm kiếm thêm cho bạn."
            ),
            
            # ============================================
            # BREAKDOWN - Phân tích chi tiết chi phí
            # ============================================
            "breakdown": PromptTemplate(
                name="breakdown",
                system_prompt="""Bạn là chuyên gia tư vấn chi phí du lịch.
Nhiệm vụ: Phân tích và giải thích chi phí THEO TỪNG NGÀY, phù hợp với mức budget_level.

CONTEXT AWARENESS:
- Nếu user nói "tính tiền lịch trình này" và context có last_itinerary → sử dụng chi tiết lịch trình đó
- Budget level (tiết kiệm / trung bình / sang trọng) ảnh hưởng đến chi phí khách sạn, ăn uống
- Nếu user nói "xem lại chi phí" → hiển thị lại calculation từ context

Format output:
📅 **Ngày 1:**
- 🏨 Khách sạn: X VNĐ
- 🍜 Ăn uống: Y VNĐ  
- 🚕 Di chuyển: Z VNĐ
- 🎫 Tham quan: W VNĐ
- **Tổng ngày 1:** ABC VNĐ

📅 **Ngày 2:**
...

💰 **Tổng cộng:** XYZ VNĐ ({budget_level})

Giải thích rõ từng khoản, đưa ra tips tiết kiệm nếu budget_level = "tiết kiệm".""",
                user_template="""Phân tích chi phí từng ngày cho chuyến đi:
- Địa điểm: {location}
- Số ngày: {duration}
- Số người: {people_count}
- Budget level: {budget_level}
- Tổng chi phí đã tính: {total_cost}

Chi tiết:
{cost_breakdown}

Hãy chia nhỏ theo từng ngày và giải thích, phù hợp với mức {budget_level}.""",
                expected_format="markdown",
                fallback_response="Dựa trên tổng chi phí, mỗi ngày bạn sẽ chi khoảng {daily_avg} VNĐ."
            ),
            
            # ============================================
            # COMPARE - So sánh
            # ============================================
            "compare": PromptTemplate(
                name="compare",
                system_prompt="""Bạn là chuyên gia so sánh du lịch.
Nhiệm vụ: So sánh các lựa chọn một cách CÔNG BẰNG và HỮU ÍCH.

Format:
| Tiêu chí | Lựa chọn 1 | Lựa chọn 2 |
|----------|------------|------------|
| Giá      | ...        | ...        |
| Vị trí   | ...        | ...        |

Cuối cùng: Đưa ra GỢI Ý phù hợp với từng đối tượng.""",
                user_template="""So sánh:
{items_to_compare}

Ngữ cảnh: {context}""",
                expected_format="markdown",
                fallback_response="Cả hai lựa chọn đều tốt, tùy thuộc vào nhu cầu của bạn."
            ),
            
            # ============================================
            # EXPLAIN - Giải thích
            # ============================================
            "explain": PromptTemplate(
                name="explain",
                system_prompt="""Bạn là trợ lý du lịch thông minh.
Nhiệm vụ: Giải thích LÝ DO đằng sau các gợi ý.

Trả lời ngắn gọn, rõ ràng, thuyết phục.
Dựa trên dữ liệu thực tế (rating, reviews, giá...).""",
                user_template="""Người dùng hỏi: {question}

Gợi ý trước đó:
{previous_recommendation}

Dữ liệu:
{supporting_data}

Giải thích tại sao đây là gợi ý tốt.""",
                expected_format="text",
                fallback_response="Gợi ý này dựa trên đánh giá của khách du lịch và phù hợp với yêu cầu của bạn."
            ),
            
            # ============================================
            # BOOK HOTEL - Hướng dẫn đặt phòng
            # ============================================
            "book_hotel": PromptTemplate(
                name="book_hotel",
                system_prompt="""Bạn là trợ lý đặt phòng khách sạn.
Nhiệm vụ: Hướng dẫn người dùng đặt phòng.

Cung cấp:
1. Thông tin khách sạn
2. Link đặt phòng (Booking.com, Agoda, Traveloka)
3. Tips khi đặt phòng
4. Lưu ý quan trọng""",
                user_template="""Người dùng muốn đặt: {hotel_name}

Thông tin khách sạn:
{hotel_info}

Ngày dự kiến: {dates}
Số người: {people_count}

Hướng dẫn đặt phòng.""",
                expected_format="markdown",
                fallback_response="Bạn có thể đặt phòng qua Booking.com, Agoda hoặc Traveloka. Nhớ so sánh giá trước khi đặt!"
            ),
            
            # ============================================
            # FALLBACK - Khi không hiểu
            # ============================================
            "fallback": PromptTemplate(
                name="fallback",
                system_prompt="""Bạn là Saola - trợ lý du lịch AI thân thiện.
Khi không hiểu câu hỏi, hãy:
1. Thừa nhận không hiểu rõ
2. Đoán ý người dùng
3. Đề xuất câu hỏi rõ ràng hơn
4. Gợi ý những gì bạn có thể giúp

KHÔNG nói "Tôi không biết" mà hãy chuyển hướng tích cực.""",
                user_template="""Người dùng nói: "{query}"

Ngữ cảnh hiện tại:
- Điểm đến: {destination}
- Số ngày: {duration}
- Đang xem: {current_view}

Trả lời thân thiện và gợi ý tiếp.""",
                expected_format="text",
                fallback_response="Tôi chưa hiểu rõ ý bạn. Bạn có thể nói rõ hơn không? Ví dụ: 'Tìm khách sạn Đà Nẵng' hoặc 'Lịch trình 3 ngày Phú Quốc'."
            ),
            
            # ============================================
            # NATURAL RESPONSE - Cho follow-up chung
            # ============================================
            "natural_response": PromptTemplate(
                name="natural_response",
                system_prompt="""Bạn là Saola - trợ lý du lịch AI của Việt Nam.
Phong cách: Thân thiện, nhiệt tình, am hiểu du lịch Việt Nam.

Nguyên tắc:
1. Trả lời TỰ NHIÊN như đang trò chuyện
2. Dùng emoji phù hợp 🌟
3. Ngắn gọn, đi vào trọng tâm
4. Luôn đưa ra bước tiếp theo hoặc gợi ý
5. Nhớ context và tham chiếu lại khi cần""",
                user_template="""Cuộc hội thoại:
{conversation_history}

Câu hỏi mới: {query}

Ngữ cảnh:
{context}

Trả lời tự nhiên.""",
                expected_format="text",
                fallback_response="Tôi hiểu rồi! Bạn cần gì thêm không?"
            ),
        }
    
    def get_template(self, name: str) -> Optional[PromptTemplate]:
        """Get a prompt template by name"""
        return self.templates.get(name)
    
    def render_prompt(
        self, 
        template_name: str, 
        variables: Dict[str, Any]
    ) -> tuple[str, str]:
        """
        Render a prompt with variables
        
        Returns:
            (system_prompt, user_prompt)
        """
        template = self.templates.get(template_name)
        if not template:
            logger.warning(f"⚠️ Template not found: {template_name}, using fallback")
            template = self.templates["fallback"]
        
        try:
            # Render user template with variables
            user_prompt = template.user_template.format(**variables)
            return template.system_prompt, user_prompt
        except KeyError as e:
            logger.warning(f"⚠️ Missing variable in template {template_name}: {e}")
            # Return with placeholders for missing vars
            user_prompt = template.user_template
            for key, value in variables.items():
                user_prompt = user_prompt.replace(f"{{{key}}}", str(value))
            return template.system_prompt, user_prompt
    
    def get_fallback_response(self, template_name: str) -> str:
        """Get fallback response for a template"""
        template = self.templates.get(template_name)
        if template:
            return template.fallback_response
        return "Xin lỗi, tôi gặp sự cố. Bạn có thể thử lại không?"
    
    def get_expected_format(self, template_name: str) -> str:
        """Get expected output format for a template"""
        template = self.templates.get(template_name)
        if template:
            return template.expected_format
        return "text"
    
    # ============================================
    # HELPER METHODS FOR COMMON PROMPTS
    # ============================================
    
    def format_spots_for_prompt(self, spots: List[Dict]) -> str:
        """Format spots list for prompt"""
        if not spots:
            return "Không có dữ liệu địa điểm"
        
        lines = []
        for i, spot in enumerate(spots, 1):
            name = spot.get("name", "N/A")
            rating = spot.get("rating", "N/A")
            category = spot.get("category", "")
            description = spot.get("description_short", "")[:100]
            lines.append(f"{i}. {name} (⭐{rating}) - {category}")
            if description:
                lines.append(f"   {description}...")
        
        return "\n".join(lines)
    
    def format_hotels_for_prompt(self, hotels: List[Dict]) -> str:
        """Format hotels list for prompt"""
        if not hotels:
            return "Không có dữ liệu khách sạn"
        
        lines = []
        for i, hotel in enumerate(hotels, 1):
            name = hotel.get("name", "N/A")
            rating = hotel.get("rating", "N/A")
            price = hotel.get("price", 0)
            address = hotel.get("address", "")[:50]
            lines.append(f"{i}. {name} (⭐{rating}) - {price:,} VNĐ/đêm")
            if address:
                lines.append(f"   📍 {address}")
        
        return "\n".join(lines)
    
    def format_foods_for_prompt(self, foods: List[Dict]) -> str:
        """Format foods list for prompt"""
        if not foods:
            return "Không có dữ liệu ẩm thực"
        
        lines = []
        for i, food in enumerate(foods, 1):
            name = food.get("name", "N/A")
            lines.append(f"{i}. {name}")
        
        return "\n".join(lines)


def create_prompt_manager() -> LLMPromptManager:
    """Factory function"""
    return LLMPromptManager()
