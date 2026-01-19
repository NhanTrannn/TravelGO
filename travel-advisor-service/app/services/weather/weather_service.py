from typing import List, Dict
from datetime import datetime, timedelta
from pathlib import Path
import json
import logging
from pandas import read_csv

from .date_predict_service import predict, PROJECT_ROOT
from app.utils.date_normalizer import normalize_date
from .weather_models import WeatherData, RegionType, AreaType


# =====================================================
# ACTIVITY BASE – KHỞI TẠO 1 LẦN, DỄ MỞ RỘNG
# =====================================================

BASE_ACTIVITIES = {
    "general": {
        "outdoor": [
            "tham quan ngoài trời",
            "chụp ảnh",
            "dạo bộ",
            "khám phá địa phương",
        ],
        "indoor": ["ẩm thực", "café", "bảo tàng", "mua sắm"],
    },
    RegionType.coastal: {
        "good": ["tắm biển", "ngắm hoàng hôn", "chụp ảnh biển", "thưởng thức hải sản"],
        "avoid": ["đi tàu thuyền", "thể thao biển mạo hiểm"],
    },
    RegionType.highland: {
        "good": [
            "trekking nhẹ",
            "săn mây",
            "chụp ảnh thiên nhiên",
            "tham quan cao nguyên",
        ],
        "avoid": ["leo núi dài ngày", "di chuyển đèo dốc ban đêm"],
    },
    AreaType.urban: {
        "good": ["tham quan đô thị", "chợ đêm", "ẩm thực địa phương"],
        "avoid": ["di chuyển ngoài trời giờ cao điểm"],
    },
    AreaType.rural: {
        "good": ["tham quan làng quê", "trải nghiệm nông nghiệp", "chợ địa phương"],
        "avoid": ["di chuyển đường đất khi mưa"],
    },
}


# =====================================================
# DATE UTILS
# =====================================================


def generate_dates(start_date: str, days: int) -> List[str]:
    start_date = normalize_date(start_date)
    start = datetime.strptime(start_date, "%Y-%m-%d")
    return [(start + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days)]


# =====================================================
# CORE WEATHER SERVICE
# =====================================================


class WeatherService:

    def __init__(self, mongo_manager=None):
        self.data_dir = PROJECT_ROOT / "data"
        self.mongo_manager = mongo_manager
        self.province_map: Dict[str, str] = {}  # province_id -> province_name
        self._load_province_map()

    def _load_province_map(self) -> None:
        """Load province_id → province_name from geographical_information.csv."""
        geo_file = self.data_dir / "geographical_information.csv"
        if not geo_file.exists():
            return
        try:
            df = read_csv(geo_file)
            from unidecode import unidecode

            for _, row in df.iterrows():
                prov_name = row["location"]
                prov_id = unidecode(prov_name.lower()).replace(" ", "-")
                self.province_map[prov_id] = prov_name
        except Exception as e:  # pragma: no cover - defensive logging
            logging.warning(f"⚠️ Could not load province map: {e}")

    def get_climate_zone(self, location: str) -> str:
        """Resolve climate zone using DB fallback to map location → province."""
        from .date_predict_service import CLIMATE_ZONES

        # 1) Direct match + small manual mapping for common locations
        manual_map = {
            "phú quốc": "Kiên Giang",
            "phu quoc": "Kiên Giang",
            "kien giang": "Kiên Giang",
        }
        loc_lower = location.lower()
        mapped = manual_map.get(loc_lower)
        for zone, provinces in CLIMATE_ZONES.items():
            if location in provinces or (mapped and mapped in provinces):
                return zone

        # 2) Mongo lookup: find province_name from spots
        if self.mongo_manager is not None:
            try:
                from unidecode import unidecode

                norm_id = unidecode(location.lower()).replace(" ", "-")
                spots_col = self.mongo_manager.get_collection("spots_detailed")
                if spots_col is not None:
                    query = {
                        "$or": [
                            {"province_id": norm_id},
                            {"province": {"$regex": location, "$options": "i"}},
                            {"location": {"$regex": location, "$options": "i"}},
                        ]
                    }
                    spot = spots_col.find_one(query)
                    if spot:
                        province_name = spot.get("province")
                        if province_name:
                            logging.info(
                                f"✅ Found '{location}' in DB -> province: {province_name}"
                            )
                            for zone, provinces in CLIMATE_ZONES.items():
                                if province_name in provinces:
                                    return zone
                        province_id = spot.get("province_id")
                        if province_id and province_id in self.province_map:
                            province_name = self.province_map[province_id]
                            for zone, provinces in CLIMATE_ZONES.items():
                                if province_name in provinces:
                                    return zone
            except Exception as e:  # pragma: no cover - defensive logging
                logging.warning(f"⚠️ MongoDB lookup failed for '{location}': {e}")

        # 3) Fallback to legacy function (may raise)
        from .date_predict_service import get_climate_zone as legacy_get_climate_zone

        return legacy_get_climate_zone(location)

    # =================================================
    # 1. GET WEATHER – JSON SOURCE OF TRUTH
    # =================================================

    def get_weather(self, location: str, start_date: str, days: int) -> Dict:
        dates = generate_dates(start_date, days)
        climate_zone = self.get_climate_zone(location)

        daily_weather: List[WeatherData] = [predict(d, location) for d in dates]

        temps_max = [w.temp_max for w in daily_weather]
        temps_min = [w.temp_min for w in daily_weather]
        humidities = [w.humidity for w in daily_weather]
        winds = [w.wind_speed for w in daily_weather]
        rains = [w.rain_sum for w in daily_weather]
        clouds = [w.cloud_cover for w in daily_weather]

        avg_temp = sum((a + b) / 2 for a, b in zip(temps_max, temps_min)) / days
        avg_humidity = sum(humidities) / days
        max_wind = max(winds)
        total_rain = sum(rains)

        rainy_dates = [w.datetime for w in daily_weather if w.rain_sum >= 5]

        # -----------------------------
        # Characterization
        # -----------------------------

        rain_desc = (
            "khô ráo"
            if total_rain == 0
            else (
                "mưa nhẹ rải rác"
                if total_rain <= 15
                else "mưa rào" if total_rain <= 40 else "mưa nhiều"
            )
        )

        humidity_desc = (
            "khô" if avg_humidity < 40 else "dễ chịu" if avg_humidity <= 70 else "oi ẩm"
        )

        wind_desc = (
            "gió nhẹ" if max_wind < 12 else "gió vừa" if max_wind < 20 else "gió mạnh"
        )

        # -----------------------------
        # Daily scoring & activities
        # -----------------------------

        daily_scores = []

        for w in daily_weather:
            score = 100
            best_for = []
            avoid = []

            if w.rain_sum >= 20:
                score -= 30
                best_for += BASE_ACTIVITIES["general"]["indoor"]
                avoid += BASE_ACTIVITIES["general"]["outdoor"]
            else:
                best_for += BASE_ACTIVITIES["general"]["outdoor"]

            if w.wind_speed >= 20:
                score -= 15

            daily_scores.append(
                {
                    "date": w.datetime,
                    "score": max(0, score),
                    "label": (
                        "rất tốt"
                        if score >= 85
                        else (
                            "tốt"
                            if score >= 70
                            else "trung bình" if score >= 55 else "không thuận lợi"
                        )
                    ),
                    "best_for": sorted(set(best_for)),
                    "avoid": sorted(set(avoid)),
                }
            )

        avg_score = sum(d["score"] for d in daily_scores) / days

        # -----------------------------
        # Notes
        # -----------------------------

        notes = {
            "packing": [
                "Quần áo thoáng mát, dễ khô",
                (
                    "Áo mưa mỏng hoặc ô gấp"
                    if rainy_dates
                    else "Không cần mang đồ mưa cồng kềnh"
                ),
                "Giày dễ di chuyển, chống trơn",
            ],
            "tips": [
                "Ưu tiên hoạt động ngoài trời vào buổi sáng",
                "Linh hoạt đổi lịch nếu gặp mưa",
                "Uống đủ nước khi di chuyển nhiều",
            ],
        }

        return {
            "location": location,
            "climate_zone": climate_zone,
            "date_range": {"start": dates[0], "end": dates[-1], "days": days},
            "metrics": {
                "temperature": {
                    "avg": round(avg_temp, 1),
                    "min": min(temps_min),
                    "max": max(temps_max),
                },
                "rain": {
                    "total": round(total_rain, 1),
                    "rainy_days": rainy_dates,
                    "description": rain_desc,
                },
                "humidity": {
                    "avg": round(avg_humidity, 1),
                    "description": humidity_desc,
                },
                "wind": {"max": round(max_wind, 1), "description": wind_desc},
                "cloud": {"avg": round(sum(clouds) / days, 1)},
            },
            "daily_scores": daily_scores,
            "overall": {
                "average_score": round(avg_score, 1),
                "comfort_level": (
                    "rất dễ chịu"
                    if avg_score >= 80
                    else (
                        "khá dễ chịu"
                        if avg_score >= 65
                        else "trung bình" if avg_score >= 50 else "không thuận lợi"
                    )
                ),
            },
            "notes": notes,
        }

    # =================================================
    # 2. RESPONSE – NÓI CHUYỆN VỚI NGƯỜI DÙNG
    # =================================================

    def build_weather_response(self, summary: Dict) -> str:
        m = summary["metrics"]
        days = summary["daily_scores"]

        rainy = [
            d["date"] for d in days if d["label"] in {"trung bình", "không thuận lợi"}
        ]

        return f"""

**TỔNG QUAN THỜI TIẾT CHUYẾN ĐI**
📍 **Thời tiết tại {summary['location']}**
📅 {summary['date_range']['start']} → {summary['date_range']['end']}

🌤️ **Tổng quan**
- Nhiệt độ trung bình khoảng {m['temperature']['avg']}°C (dao động {m['temperature']['min']}–{m['temperature']['max']}°C)
- Mưa: {m['rain']['description']}
- Độ ẩm: {m['humidity']['description']} (~{m['humidity']['avg']}%)
- Gió: {m['wind']['description']} (tối đa {m['wind']['max']} km/h)

📆 **Theo từng ngày**
{chr(10).join(f"- {d['date']}: {d['label']} ({d['score']}/100)" for d in days)}

🌧️ **Lưu ý mưa**
{"Có khả năng mưa vào: " + ", ".join(rainy) if rainy else "Không có ngày mưa đáng kể."}

🎒 **Gợi ý chuẩn bị**
{chr(10).join(f"- {n}" for n in summary['notes']['packing'])}\n

""".strip()

    # =================================================
    # 3. PROMPT – DÀNH CHO LLM LẬP KẾ HOẠCH
    # =================================================

    def build_weather_prompt(self, summary: Dict) -> str:
        m = summary["metrics"]

        day_lines = [
            f"- {d['date']}: {d['label']} → nên ưu tiên {', '.join(d['best_for'])}"
            for d in summary["daily_scores"]
        ]

        return f"""
BỐI CẢNH THỜI TIẾT CHO LẬP KẾ HOẠCH DU LỊCH

Tổng quan:
- Mức độ dễ chịu: {summary['overall']['comfort_level']}
- Nhiệt độ: {m['temperature']['avg']}°C (min {m['temperature']['min']} – max {m['temperature']['max']})
- Mưa: {m['rain']['description']}
- Độ ẩm: {m['humidity']['description']}
- Gió: {m['wind']['description']}

Theo từng ngày:
{chr(10).join(day_lines)}

Lưu ý du lịch:
{chr(10).join(f"- {n}" for n in summary['notes']['packing'])}

Yêu cầu:
Sắp xếp hoạt động ngoài trời vào ngày thời tiết tốt,
ưu tiên hoạt động trong nhà khi mưa hoặc điều kiện không thuận lợi.
""".strip()

    def get_best_time(self, location: str) -> Dict:
        # Map special locations to their province
        alias = {
            "Phú Quốc": "Kiên Giang",
            "Phu Quoc": "Kiên Giang",
        }
        base_location = alias.get(location, location)

        climate_zone = self.get_climate_zone(location)
        best_time_file = self.data_dir / "best_time.json"

        # Map climate zones to Vietnamese region names
        ZONE_TO_REGION = {
            "southern": "Đồng Bằng Sông Cửu Long",
            "northeast": "Đông Bắc Bộ",
            "northwest": "Tây Bắc Bộ",
            "red_river_delta": "Đồng Bằng Sông Hồng",
            "north_central": "Bắc Trung Bộ",
            "south_central_coast": "Duyên Hải Nam Trung Bộ",
            "central_highlands": "Tây Nguyên",
        }
        
        # Try to get region from geographical_information.csv, fallback to zone mapping
        region = None
        geo_file = self.data_dir / "geographical_information.csv"
        if geo_file.exists():
            try:
                geo_df = read_csv(geo_file)
                location_to_region = {
                    row["location"]: row["region"] for _, row in geo_df.iterrows()
                }
                region = location_to_region.get(base_location, None)
            except Exception as e:
                logging.warning(f"⚠️ Failed to read geographical_information.csv: {e}")
        
        # Fallback to zone-based region name
        if not region:
            region = ZONE_TO_REGION.get(climate_zone, climate_zone)

        with open(best_time_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        if climate_zone not in data:
            return {
                "best_months": [],
                "avoid_months": [],
                "reasons": f"{location} chưa có đủ dữ liệu khí hậu để đưa ra gợi ý thời điểm du lịch phù hợp.",
            }

        info = data[climate_zone]

        best_months = info["best_months"]
        avoid_months = info["avoid_months"]
        summary = info["summary"]
        best_reason = info["reasons"]["best"]
        avoid_reason = info["reasons"]["avoid"]

        message = (
            f"{location} thuộc vùng {region}, {summary}. "
            f"Thời điểm lý tưởng để du lịch {location} là {best_reason}. "
            f"Bạn không nên đi vào {avoid_reason}"
        )

        return {
            "best_months": best_months,
            "avoid_months": avoid_months,
            "message": message,
        }


# service = WeatherService()
# w = service.get_weather("Bình Định", "2026-01-12", 3)
# from rich import print as rprint
# rprint(w)
# rprint(service.build_weather_response(w))
# rprint(service.build_weather_prompt(w))
