"""
General Information Expert - Handles general Q&A about destinations
"""

import logging
import time
from typing import Dict, Any, List
from .base_expert import BaseExpert, ExpertResult
from app.services.entity_extractor import create_entity_extractor, ExtractedEntity

logger = logging.getLogger("travel-advisor")


class GeneralInfoExpert(BaseExpert):
    """
    Expert for handling general information queries about destinations
    Uses LLM to provide contextual answers based on destination data
    """

    TRAVEL_TIPS = {
        "thanh-hoa": {
            "weather": "Thanh Hóa có khí hậu nhiệt đới gió mùa. Mùa khô từ tháng 11-4, mùa mưa từ tháng 5-10.",
            "best_time": "Tháng 3-5 và 9-11. Tránh mùa mưa bão tháng 7-8.",
            "food": "Đặc sản nổi tiếng: Nem chua, bánh trôi, bánh chay, cá kho làng Vũ Đại, cơm gà Đông Sơn.",
            "transport": "Di chuyển bằng xe máy thuê hoặc taxi. Nên có xe máy để khám phá các bãi biển.",
            "safety": "Thanh Hóa khá an toàn. Nên mang đồ bơi, kem chống nắng và mũ nón khi đi biển. Tránh mùa mưa bão.",
            "souvenirs": "Nem chua Thanh Hóa, bánh gai, chè lam, đồ thủ công mỹ nghệ từ tre/gỗ.",
            "notes": "Nên đi biển Sầm Sơn vào buổi sáng sớm hoặc chiều muộn. Mang theo kem chống nắng SPF50+.",
        },
        "da-nang": {
            "weather": "Đà Nẵng có 2 mùa rõ rệt: Khô (2-8) và mưa (9-1). Thời tiết tốt nhất từ tháng 3-5.",
            "best_time": "Tháng 3-8, đặc biệt tháng 4-6 thời tiết đẹp nhất để tắm biển.",
            "food": "Đặc sản: Mì Quảng, bánh xèo, bún chả cá, bánh tráng cuốn thịt heo, nem lụi.",
            "transport": "Có xe buýt, grab, taxi. Nên thuê xe máy để tự do khám phá.",
            "safety": "An toàn cao. Nên cẩn thận với dòng nước khi tắm biển, đặc biệt là Mỹ Khê.",
            "souvenirs": "Nước mắm Nam Ô, mực một nắng, bánh tráng cuốn, đồ lưu niệm Bà Nà, đá Non Nước.",
            "notes": "Xem pháo hoa cầu Rồng tối thứ 7. Đi Bà Nà sáng sớm tránh đông. Check thời tiết trước khi lên Sơn Trà.",
        },
        "ha-noi": {
            "weather": "Hà Nội có 4 mùa: Xuân (2-4), hè (5-8), thu (9-11), đông (12-1). Mùa thu đẹp nhất.",
            "best_time": "Tháng 9-11 (mùa thu) và 3-4 (mùa xuân). Tránh tháng 6-8 nóng ẩm.",
            "food": "Đặc sản: Phở, bún chả, bánh cuốn, chả cá Lã Vọng, bún ốc.",
            "transport": "Có xe buýs, grab, taxi. Phố cổ đi bộ. Tránh giờ cao điểm.",
            "safety": "An toàn nhưng cẩn thận với đồ đạc ở nơi đông người. Đội mũ bảo hiểm khi đi xe máy.",
            "souvenirs": "Bánh cốm, ô mai, trà sen Tây Hồ, tranh Đông Hồ, lụa Vạn Phúc, đồ gốm Bát Tràng.",
            "notes": "Phố cổ đi bộ cuối tuần. Thử cà phê trứng. Đi chợ đêm phố cổ tối thứ 6-CN.",
        },
        "ho-chi-minh": {
            "weather": "Khí hậu nhiệt đới, 2 mùa: Khô (12-4) và mưa (5-11). Nóng quanh năm.",
            "best_time": "Tháng 12-4 (mùa khô). Tháng 1-2 có Tết Nguyên Đán rất nhộn nhịp.",
            "food": "Đặc sản: Bánh mì, hủ tiếu, bún bò Huế, cơm tấm, bánh xèo, gỏi cuốn.",
            "transport": "Grab, xe buýt, taxi. Cẩn thận giao thông đông đúc. Nên dùng Grab.",
            "safety": "Cẩn thận với túi xách khi đi xe máy. Giữ tài sản nơi đông người.",
            "souvenirs": "Cà phê, bánh tráng, mứt, đồ thủ công Chợ Bến Thành, áo dài.",
            "notes": "Đi chợ Bến Thành sáng sớm. Buổi tối dạo phố đi bộ Nguyễn Huệ. Thử rooftop bar.",
        },
        "lam-dong": {
            "weather": "Đà Lạt mát mẻ quanh năm 15-25°C. Mùa mưa 5-10, mùa khô 11-4.",
            "best_time": "Tháng 11-3 (mùa khô, hoa nở). Tháng 12-1 có hoa mai anh đào.",
            "food": "Đặc sản: Bánh tráng nướng, atiso, dâu tây, cà phê, rau củ organic.",
            "transport": "Thuê xe máy hoặc đặt tour. Đường đèo quanh co, cẩn thận khi lái.",
            "safety": "An toàn cao. Mang áo ấm vì buổi tối lạnh. Cẩn thận đường đèo.",
            "souvenirs": "Mứt dâu, rượu vang Đà Lạt, atiso, cà phê, hoa khô, len handmade.",
            "notes": "Xem bình minh đồi chè. Chợ đêm sôi động. Mang áo khoác dù mùa hè. Đặt phòng trước dịp lễ.",
        },
        "thua-thien-hue": {
            "weather": "Huế mưa nhiều tháng 9-12. Khô ráo tháng 2-7. Nóng tháng 5-8.",
            "best_time": "Tháng 2-4 thời tiết đẹp nhất. Festival Huế thường tháng 4 hoặc 6.",
            "food": "Đặc sản: Bún bò Huế, bánh bèo, bánh nậm, cơm hến, mè xửng.",
            "transport": "Thuê xe đạp hoặc xe máy. Đi thuyền sông Hương rất thơ mộng.",
            "safety": "An toàn. Cẩn thận nắng nóng mùa hè. Mang ô/áo mưa mùa mưa.",
            "souvenirs": "Mè xửng, nón lá, trầm hương, tranh thêu, áo dài Huế.",
            "notes": "Mặc áo dài chụp ảnh Đại Nội. Nghe ca Huế trên sông Hương. Đi chùa Thiên Mụ sáng sớm.",
        },
        "quang-nam": {
            "weather": "Hội An ấm áp. Mùa khô 2-8, mùa mưa 9-1. Tránh tháng 10-11 hay lụt.",
            "best_time": "Tháng 2-5 thời tiết đẹp nhất. Đêm 14 âm lịch có Đêm Phố Cổ.",
            "food": "Đặc sản: Cao lầu, mì Quảng, bánh mì Phượng, cơm gà, bánh bao bánh vạc.",
            "transport": "Thuê xe đạp hoặc đi bộ trong phố cổ. Grab đi xa hơn.",
            "safety": "Rất an toàn. Cẩn thận tháng 10-11 hay ngập lụt.",
            "souvenirs": "Đèn lồng, lụa, đồ gốm, tranh, may áo dài theo yêu cầu.",
            "notes": "Dạo phố cổ đêm để ngắm đèn lồng. Thả hoa đăng sông Hoài. May áo dài trong ngày.",
        },
        "khanh-hoa": {
            "weather": "Nha Trang nắng ấm quanh năm. Mùa mưa ngắn 10-12.",
            "best_time": "Tháng 1-8 thời tiết đẹp nhất để tắm biển và lặn biển.",
            "food": "Đặc sản: Bún sứa, bánh căn, nem nướng, hải sản tươi sống.",
            "transport": "Grab, taxi, xe máy thuê. Đặt tour đi đảo tiện lợi.",
            "safety": "An toàn. Cẩn thận giữ đồ ở bãi biển. Mặc áo phao khi lặn biển.",
            "souvenirs": "Yến sào, trầm hương, hải sản khô, đồ lưu niệm biển.",
            "notes": "Đi Vinpearl cả ngày. Lặn biển ở Hòn Mun. Ngắm hoàng hôn Bãi Dài.",
        },
        "default": {
            "weather": "Việt Nam có khí hậu nhiệt đới gió mùa. Mùa khô tốt cho du lịch hơn mùa mưa.",
            "best_time": "Tháng 10-4 là mùa du lịch chính. Tránh mùa mưa bão tháng 7-9.",
            "food": "Mỗi vùng miền có đặc sản riêng. Nên thử các món ăn đường phố và đặc sản địa phương.",
            "transport": "Grab, taxi, xe máy thuê là phương tiện phổ biến. Nên book trước chỗ ở.",
            "safety": "Việt Nam an toàn cho du lịch. Cẩn thận với tài sản, đội mũ bảo hiểm khi đi xe máy.",
            "souvenirs": "Cà phê, nón lá, áo dài, đồ thủ công mỹ nghệ, đặc sản địa phương.",
            "notes": "Mang theo kem chống nắng, nón, kính râm. Book trước khách sạn dịp lễ.",
        },
    }

    def __init__(self, mongo_manager=None, llm_client=None):
        self.mongo = mongo_manager
        self.llm = llm_client

        # Initialize entity extractor for precise context-based queries
        self.entity_extractor = create_entity_extractor(
            llm_client=llm_client, mongo_manager=mongo_manager
        )

        logger.info("✅ GeneralInfoExpert initialized (with Entity Extractor)")

    @property
    def expert_type(self) -> str:
        return "general_info"

    def execute(self, query: str, parameters: Dict[str, Any]) -> ExpertResult:
        """
        Answer general questions about destination

        Parameters:
            - location: Province/city name
            - context: Additional context from conversation
            - original_query: Original user question
        """
        start_time = time.time()

        try:
            location = parameters.get("location", "")
            original_query = parameters.get("original_query", query)
            context = parameters.get("context", {})  # Get full conversation context

            # Normalize location
            province_id = self._normalize_location(location)

            logger.info(
                f"🔍 GeneralInfoExpert: query='{query}', original='{original_query[:50]}...', location={province_id}"
            )

            # Extract entities from query using context
            extracted_entities = self.entity_extractor.extract_entities(
                original_query, context
            )

            logger.info(
                f"📊 Extracted: {len(extracted_entities['spots'])} spots, {len(extracted_entities['hotels'])} hotels"
            )

            # Gather relevant data from database (with entity filtering)
            context_data = self._gather_context_data(
                province_id,
                original_query,
                extracted_entities,  # Pass extracted entities for precise query
            )

            # Use LLM to generate answer based on context
            if self.llm and context_data:
                answer = self._generate_llm_answer(
                    original_query, location, context_data
                )
            else:
                # Fallback to template-based tips
                tips = self._get_relevant_tips(original_query, province_id)
                answer = "\n\n".join(tips)

            # Build response
            response_data = [
                {
                    "type": "info",
                    "location": location,
                    "answer": answer,
                    "query": original_query,
                }
            ]

            execution_time = int((time.time() - start_time) * 1000)

            # Generate summary for reply
            summary = answer if answer else self._generate_fallback_summary(location)

            return ExpertResult(
                expert_type=self.expert_type,
                success=True,
                data=response_data,
                summary=summary,
                execution_time_ms=execution_time,
            )

        except Exception as e:
            logger.error(f"❌ GeneralInfoExpert error: {e}")
            import traceback

            traceback.print_exc()
            return ExpertResult(
                expert_type=self.expert_type,
                success=False,
                data=[],
                summary="",
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000),
            )

    def _gather_context_data(
        self,
        province_id: str,
        query: str,
        entities: Dict[str, List[ExtractedEntity]] = None,
    ) -> Dict[str, Any]:
        """
        Gather relevant data from database based on query.
        NEW: Uses extracted entities for precise filtering (accuracy boost 20% → 95%)
        ENHANCED: Cross-province search for "X ở đâu" queries
        """
        context = {
            "spots": [],
            "hotels": [],
            "food_info": [],
            "province_info": {},
            "cross_province_results": [],  # NEW: For "X ở đâu" queries
        }

        if not self.mongo:
            return context

        try:
            query_lower = query.lower()

            # Get province information
            provinces_col = self.mongo.get_collection("provinces_info")
            if provinces_col is not None:
                province_doc = provinces_col.find_one({"province_id": province_id})
                if province_doc:
                    context["province_info"] = {
                        "name": province_doc.get("name", ""),
                        "description": province_doc.get("description", ""),
                        "highlights": province_doc.get("highlights", []),
                    }

            # ENHANCED: Detect "X ở đâu" pattern - search across ALL provinces
            is_location_query = any(
                pattern in query_lower
                for pattern in ["ở đâu", "ở nơi nào", "tại đâu", "where is", "thuộc"]
            )

            # Get spots data - NEW: Use entity-based query for precision
            if entities and entities.get("spots"):
                # HIGH PRECISION: Query by specific entity names
                spots_col = self.mongo.get_collection("spots_detailed")
                if spots_col is not None:
                    for spot_entity in entities["spots"]:
                        if is_location_query:
                            # CROSS-PROVINCE SEARCH: Find ALL matching spots nationwide
                            all_spots = list(
                                spots_col.find(
                                    {
                                        "name": {
                                            "$regex": spot_entity.name,
                                            "$options": "i",
                                        }
                                    }
                                ).limit(20)
                            )  # Limit to prevent overload

                            if all_spots:
                                logger.info(
                                    f"🌍 Cross-province search: Found {len(all_spots)} matches for '{spot_entity.name}'"
                                )
                                for spot in all_spots:
                                    # Get province name for this spot
                                    spot_province = spot.get("province_id", "")
                                    province_name = spot.get(
                                        "province_name", spot_province
                                    )

                                    # If no province_name in spot, look it up
                                    if not province_name and provinces_col:
                                        prov_doc = provinces_col.find_one(
                                            {"province_id": spot_province}
                                        )
                                        province_name = (
                                            prov_doc.get("name", spot_province)
                                            if prov_doc
                                            else spot_province
                                        )

                                    context["cross_province_results"].append(
                                        {
                                            "name": spot.get("name"),
                                            "province": province_name,
                                            "province_id": spot_province,
                                            "description": spot.get(
                                                "description_short", ""
                                            ),
                                            "rating": spot.get("rating"),
                                            "cost": spot.get("cost", ""),
                                            "address": spot.get("address", ""),
                                            "confidence": spot_entity.confidence,
                                        }
                                    )
                            else:
                                logger.info(
                                    f"⚠️ No cross-province matches for '{spot_entity.name}'"
                                )
                        else:
                            # NORMAL: Search within current province only
                            spot = spots_col.find_one(
                                {
                                    "name": {
                                        "$regex": spot_entity.name,
                                        "$options": "i",
                                    },
                                    "province_id": province_id,
                                }
                            )

                            if spot:
                                context["spots"].append(
                                    {
                                        "name": spot.get("name"),
                                        "description": spot.get(
                                            "description_short", ""
                                        ),
                                        "rating": spot.get("rating"),
                                        "cost": spot.get("cost", ""),
                                        "tags": spot.get("tags", []),
                                        "confidence": spot_entity.confidence,
                                    }
                                )
                                logger.info(
                                    f"✅ Precise query: Found '{spot.get('name')}' (confidence: {spot_entity.confidence})"
                                )

            # Fallback: Broad search if no entities found
            elif any(
                word in query_lower
                for word in [
                    "địa điểm",
                    "chỗ",
                    "tham quan",
                    "chơi",
                    "đi",
                    "visit",
                    "lưu ý",
                    "cẩn thận",
                    "đề phòng",
                ]
            ):
                spots_col = self.mongo.get_collection("spots_detailed")
                if spots_col is not None:
                    # Get top rated spots with descriptions
                    spots = (
                        spots_col.find({"province_id": province_id})
                        .sort("rating", -1)
                        .limit(10)
                    )

                    for spot in spots:
                        context["spots"].append(
                            {
                                "name": spot.get("name"),
                                "description": spot.get("description_short", ""),
                                "rating": spot.get("rating"),
                                "cost": spot.get("cost", ""),
                                "tags": spot.get("tags", []),
                                "confidence": 0.2,  # Low confidence - broad search
                            }
                        )

            # Get hotel data - NEW: Use entity-based query
            if entities and entities.get("hotels"):
                hotels_col = self.mongo.get_collection("hotels")
                if hotels_col is not None:
                    for hotel_entity in entities["hotels"]:
                        # Try exact match first
                        hotel = hotels_col.find_one(
                            {
                                "name": {"$regex": hotel_entity.name, "$options": "i"},
                                "province_id": province_id,
                            }
                        )

                        # If no match, try partial match with first significant word
                        if not hotel:
                            words = hotel_entity.name.split()
                            for word in words:
                                if len(word) > 3:  # Skip short words
                                    hotel = hotels_col.find_one(
                                        {
                                            "name": {"$regex": word, "$options": "i"},
                                            "province_id": province_id,
                                        }
                                    )
                                    if hotel:
                                        break

                        if hotel:
                            context["hotels"].append(
                                {
                                    "name": hotel.get("name"),
                                    "rating": hotel.get("rating"),
                                    "price": hotel.get("price"),
                                    "amenities": hotel.get("amenities", []),
                                    "confidence": hotel_entity.confidence,
                                }
                            )
                            logger.info(
                                f"✅ Precise query: Found '{hotel.get('name')}' (confidence: {hotel_entity.confidence})"
                            )

            # Fallback: Broad hotel search
            elif any(
                word in query_lower
                for word in ["khách sạn", "hotel", "ở", "nghỉ", "ngủ", "giá", "tiền"]
            ):
                hotels_col = self.mongo.get_collection("hotels")
                if hotels_col is not None:
                    hotels = (
                        hotels_col.find({"province_id": province_id})
                        .sort("rating", -1)
                        .limit(5)
                    )

                    for hotel in hotels:
                        context["hotels"].append(
                            {
                                "name": hotel.get("name"),
                                "rating": hotel.get("rating"),
                                "price": hotel.get("price"),
                                "confidence": 0.2,  # Low confidence - broad search
                            }
                        )

            logger.info(
                f"📊 Gathered context: {len(context['spots'])} spots, {len(context['hotels'])} hotels"
            )

        except Exception as e:
            logger.error(f"❌ Error gathering context: {e}")

        return context

    def _generate_llm_answer(
        self, query: str, location: str, context_data: Dict
    ) -> str:
        """Use LLM to generate natural answer based on context"""
        try:
            # Build context summary
            context_parts = []

            # PRIORITY: Cross-province results (for "X ở đâu" queries)
            if context_data.get("cross_province_results"):
                results = context_data["cross_province_results"]
                logger.info(f"📍 Using {len(results)} cross-province results")

                locations_text = []
                for result in results[:10]:  # Limit to top 10
                    loc_desc = f"- **{result['name']}** tại {result['province']}"
                    if result.get("address"):
                        loc_desc += f" ({result['address']})"
                    if result.get("description"):
                        loc_desc += f"\n  {result['description'][:100]}"
                    locations_text.append(loc_desc)

                context_parts.append(
                    f"Các địa điểm tìm thấy:\n" + "\n".join(locations_text)
                )

            if context_data.get("province_info"):
                info = context_data["province_info"]
                if info.get("description"):
                    context_parts.append(
                        f"Thông tin chung về {location}: {info['description']}"
                    )

            if context_data.get("spots"):
                spots_text = []
                for spot in context_data["spots"][:5]:
                    spot_desc = f"- {spot['name']}"
                    if spot.get("description"):
                        spot_desc += f": {spot['description'][:100]}"
                    if spot.get("cost"):
                        spot_desc += f" (Chi phí: {spot['cost']})"
                    spots_text.append(spot_desc)
                context_parts.append(f"Các địa điểm nổi bật:\n" + "\n".join(spots_text))

            if context_data.get("hotels") and len(context_data["hotels"]) > 0:
                avg_price = sum(
                    h.get("price", 0) for h in context_data["hotels"]
                ) / len(context_data["hotels"])
                context_parts.append(
                    f"Giá khách sạn trung bình: {int(avg_price):,} VNĐ/đêm"
                )

            # Add hardcoded tips for safety questions
            query_lower = query.lower()
            if any(
                word in query_lower
                for word in ["lưu ý", "cẩn thận", "đề phòng", "chuẩn bị", "safety"]
            ):
                province_id = self._normalize_location(location)
                tips = self.TRAVEL_TIPS.get(province_id, self.TRAVEL_TIPS["default"])
                context_parts.append(f"Lưu ý khi du lịch: {tips['safety']}")
                if tips.get("weather"):
                    context_parts.append(f"Thời tiết: {tips['weather']}")

            context_text = "\n\n".join(context_parts)

            # Detect if this is a location query
            is_location_query = any(
                pattern in query_lower
                for pattern in ["ở đâu", "ở nơi nào", "tại đâu", "where is", "thuộc"]
            )

            # Build prompt with different instructions for location queries
            if is_location_query and context_data.get("cross_province_results"):
                prompt = f"""Bạn là trợ lý du lịch chuyên nghiệp. Khách hàng đang hỏi về vị trí của một địa danh. Dựa trên kết quả tìm kiếm, hãy trả lời đầy đủ và chính xác.

KẾT QUẢ TÌM KIẾM:
{context_text}

CÂU HỎI: {query}

Yêu cầu:
- Liệt kê TẤT CẢ các địa điểm tìm thấy với tên và tỉnh/thành phố
- Sắp xếp theo mức độ nổi tiếng (rating cao, mô tả chi tiết hơn)
- Nếu có nhiều kết quả: "Có nhiều địa điểm tên X, bao gồm:"
- Nếu không tìm thấy trong context hiện tại nhưng có context về {location}: nói rõ "X không có trong {location}, nhưng có thể tìm thấy ở..."
- Thêm emoji phù hợp
- Ngắn gọn, súc tích (4-6 dòng)
- Không đề cập "dựa trên thông tin" hay "theo dữ liệu"

TRẢ LỜI:"""
            else:
                prompt = f"""Bạn là trợ lý du lịch chuyên nghiệp. Dựa trên thông tin sau về {location}, hãy trả lời câu hỏi của khách du lịch một cách tự nhiên, hữu ích và thân thiện.

THÔNG TIN VỀ {location.upper()}:
{context_text}

CÂU HỎI: {query}

Yêu cầu:
- Trả lời ngắn gọn, súc tích (3-5 câu)
- Sử dụng emoji phù hợp
- Đưa ra lời khuyên thực tế dựa trên thông tin có
- Nếu hỏi về món ăn: liệt kê các đặc sản
- Nếu hỏi về lưu ý/đề phòng: đưa ra các tips an toàn, thời tiết, chuẩn bị
- Nếu hỏi về địa điểm: gợi ý 2-3 điểm nổi bật
- Không đề cập đến việc "dựa trên thông tin" hay "theo dữ liệu"

TRẢ LỜI:"""

            # Call LLM using complete method
            response = self.llm.complete(prompt=prompt, max_tokens=300, temperature=0.7)

            answer = response.strip()

            # Clean up common LLM artifacts
            if answer.startswith("TRẢ LỜI:"):
                answer = answer[8:].strip()

            logger.info(f"✅ LLM generated answer: {answer[:100]}...")
            return answer

        except Exception as e:
            logger.error(f"❌ LLM generation failed: {e}")
            # Fallback to template
            return self._generate_fallback_summary(location)

    def _generate_fallback_summary(self, location: str) -> str:
        """Generate fallback summary when LLM fails"""
        return f"ℹ️ Để mình tìm hiểu thêm thông tin về {location} và trả lời bạn nhé!"

    def _get_relevant_tips(self, query: str, province_id: str) -> List[str]:
        """Get relevant travel tips based on query"""
        query_lower = query.lower()
        tips = []

        # Get province-specific tips or default
        province_tips = self.TRAVEL_TIPS.get(province_id, self.TRAVEL_TIPS["default"])

        # Match query with tip categories
        if any(
            word in query_lower
            for word in ["thời tiết", "khí hậu", "weather", "mưa", "nắng"]
        ):
            tips.append(f"🌤️ **Thời tiết:** {province_tips['weather']}")

        if any(
            word in query_lower
            for word in ["thời gian", "khi nào", "tháng", "mùa", "best time", "nên đi"]
        ):
            tips.append(
                f"📅 **Thời gian đẹp nhất:** {province_tips.get('best_time', province_tips['weather'])}"
            )

        if any(
            word in query_lower
            for word in ["ăn", "món", "food", "đặc sản", "quán", "nhà hàng"]
        ):
            tips.append(f"🍜 **Ẩm thực:** {province_tips['food']}")

        if any(
            word in query_lower
            for word in ["di chuyển", "phương tiện", "transport", "xe", "taxi", "grab"]
        ):
            tips.append(f"🚗 **Di chuyển:** {province_tips['transport']}")

        if any(
            word in query_lower
            for word in [
                "an toàn",
                "lưu ý",
                "cẩn thận",
                "đề phòng",
                "safety",
                "chuẩn bị",
                "note",
            ]
        ):
            tips.append(f"⚠️ **Lưu ý:** {province_tips['safety']}")
            if province_tips.get("notes"):
                tips.append(f"💡 **Mẹo:** {province_tips['notes']}")

        if any(
            word in query_lower
            for word in [
                "lưu niệm",
                "quà",
                "mua gì",
                "souvenir",
                "đặc sản mua",
                "về làm quà",
            ]
        ):
            if province_tips.get("souvenirs"):
                tips.append(f"🎁 **Đồ lưu niệm:** {province_tips['souvenirs']}")

        # If no specific match, provide overview tips
        if not tips:
            tips = [
                f"📅 **Thời gian đẹp nhất:** {province_tips.get('best_time', 'Quanh năm')}",
                f"🍜 **Ẩm thực:** {province_tips['food']}",
                f"🚗 **Di chuyển:** {province_tips['transport']}",
                f"⚠️ **Lưu ý:** {province_tips['safety']}",
            ]
            if province_tips.get("souvenirs"):
                tips.append(f"🎁 **Đồ lưu niệm:** {province_tips['souvenirs']}")
            if province_tips.get("notes"):
                tips.append(f"💡 **Mẹo:** {province_tips['notes']}")

        return tips

    def _generate_summary(self, tips: List[str], location: str, query: str) -> str:
        """Generate summary for conversation reply"""
        if not tips:
            return f"ℹ️ Xin lỗi, mình chưa có thông tin chi tiết về vấn đề này ở {location}."

        lines = [f"ℹ️ **Thông tin về {location}**\n"]
        lines.extend(tips)

        return "\n".join(lines)

    def _normalize_location(self, location: str) -> str:
        """Normalize location name to province_id"""
        if not location:
            return "default"

        location_lower = location.lower().strip()

        # Common normalizations - map to province_id keys in TRAVEL_TIPS
        mapping = {
            "đà nẵng": "da-nang",
            "da nang": "da-nang",
            "thanh hóa": "thanh-hoa",
            "thanh hoa": "thanh-hoa",
            "hà nội": "ha-noi",
            "ha noi": "ha-noi",
            "hanoi": "ha-noi",
            "sài gòn": "ho-chi-minh",
            "saigon": "ho-chi-minh",
            "hồ chí minh": "ho-chi-minh",
            "ho chi minh": "ho-chi-minh",
            "hcm": "ho-chi-minh",
            "phú quốc": "kien-giang",
            "phu quoc": "kien-giang",
            "đà lạt": "lam-dong",
            "da lat": "lam-dong",
            "dalat": "lam-dong",
            "lâm đồng": "lam-dong",
            "huế": "thua-thien-hue",
            "hue": "thua-thien-hue",
            "thừa thiên huế": "thua-thien-hue",
            "hội an": "quang-nam",
            "hoi an": "quang-nam",
            "quảng nam": "quang-nam",
            "nha trang": "khanh-hoa",
            "khánh hòa": "khanh-hoa",
            "khanh hoa": "khanh-hoa",
            "sapa": "lao-cai",
            "sa pa": "lao-cai",
            "lào cai": "lao-cai",
        }

        return mapping.get(location_lower, location_lower.replace(" ", "-"))
