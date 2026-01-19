import re

with open("app/services/weather/weather_service.py", "r", encoding="utf-8") as f:
    content = f.read()

old_init = """class WeatherService:

    def __init__(self):
        self.data_dir = Path(__file__).parent.parent / "data"

    # =================================================
    # 1. GET WEATHER – JSON SOURCE OF TRUTH
    # =================================================

    def get_weather(self, location: str, start_date: str, days: int) -> Dict:
        dates = generate_dates(start_date, days)
        climate_zone = get_climate_zone(location)"""

new_init = '''class WeatherService:

    def __init__(self, mongo_manager=None):
        self.data_dir = Path(__file__).parent.parent / "data"
        self.mongo_manager = mongo_manager

        # Load province_id to province name mapping from geographical data
        self.province_map = {}  # province_id -> province_name
        self._load_province_map()

    def _load_province_map(self):
        """Load province_id to province_name mapping from geographical_information.csv"""
        geo_file = self.data_dir / "geographical_information.csv"
        if geo_file.exists():
            try:
                df = read_csv(geo_file)
                # Create mapping: province_name -> province_name (for reference)
                from unidecode import unidecode
                for _, row in df.iterrows():
                    prov_name = row['location']
                    prov_id = unidecode(prov_name.lower()).replace(" ", "-")
                    self.province_map[prov_id] = prov_name
            except Exception as e:
                import logging
                logging.warning(f"⚠️ Could not load province map: {e}")

    # =================================================
    # 0. GET CLIMATE ZONE (WITH DB FALLBACK)
    # =================================================

    def get_climate_zone(self, location: str) -> str:
        """
        Map province/location to climate zone.

        Logic:
        1. Direct match in CLIMATE_ZONES
        2. Fallback: Query MongoDB spots to find province for this location
        3. Map province -> zone
        """
        from .date_predict_service import CLIMATE_ZONES
        import logging
        logger = logging.getLogger(__name__)

        # Direct match first
        for zone, provinces in CLIMATE_ZONES.items():
            if location in provinces:
                return zone

        # Fallback: Try MongoDB spots query
        if self.mongo_manager:
            try:
                from unidecode import unidecode
                normalized_id = unidecode(location.lower()).replace(" ", "-")

                spots_col = self.mongo_manager.get_collection("spots_detailed")
                if spots_col:
                    # Try multiple query patterns
                    query = {
                        "$or": [
                            {"province_id": normalized_id},
                            {"province": {"$regex": location, "$options": "i"}},
                            {"location": {"$regex": location, "$options": "i"}},
                        ]
                    }
                    spot = spots_col.find_one(query)
                    if spot:
                        province_name = spot.get("province")
                        if province_name:
                            logger.info(f"✅ Found location '{location}' in DB -> province: {province_name}")
                            # Try to match province name
                            for zone, provinces in CLIMATE_ZONES.items():
                                if province_name in provinces:
                                    return zone
            except Exception as e:
                logger.warning(f"⚠️ MongoDB lookup failed for '{location}': {e}")

        # Last fallback: use old function
        try:
            from .date_predict_service import get_climate_zone as old_get_climate_zone
            return old_get_climate_zone(location)
        except Exception as e:
            import logging
            logging.error(f"❌ Could not find climate zone for '{location}': {e}")
            raise

    # =================================================
    # 1. GET WEATHER – JSON SOURCE OF TRUTH
    # =================================================

    def get_weather(self, location: str, start_date: str, days: int) -> Dict:
        dates = generate_dates(start_date, days)
        climate_zone = self.get_climate_zone(location)'''

if old_init in content:
    content = content.replace(old_init, new_init)
    with open("app/services/weather/weather_service.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("✅ Updated weather_service.py")
else:
    print("❌ Could not find the section to replace")
