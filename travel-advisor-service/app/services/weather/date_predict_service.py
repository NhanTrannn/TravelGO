"""
Weather Prediction Service - Shortened Version with Logit Models
=================================================================

A streamlined weather forecasting service with logit-transformed humidity and cloud_cover models.

Key Features:
    ✓ Logit transformation for percentage targets (humidity, cloud_cover)
    ✓ Metadata-driven feature validation
    ✓ Recursive multi-day forecasting
    ✓ Production logging
    ✓ Type-safe schema (Pydantic)

Author: ML Engineering Team
Version: 3.0.0 (Logit-enhanced)
"""

import os
import json
import logging
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, List, Any

import pandas as pd
import numpy as np
from pydantic import BaseModel
from .weather_models import WeatherData, RegionType, AreaType

# ==============================================================================
# LOGGING & PATHS
# ==============================================================================

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

CURRENT_FILE = Path(__file__).resolve()
SERVICE_DIR = CURRENT_FILE.parent  # .../weather
APP_DIR = SERVICE_DIR.parent  # .../services
PROJECT_ROOT = (
    APP_DIR.parent.parent
)  # .../travel-advisor-service (go up 2 levels from services)

# Debug path resolution
logger.info(f"🔍 PROJECT_ROOT = {PROJECT_ROOT}")

# ==============================================================================
# LOGIT TRANSFORMATIONS FOR PERCENTAGE TARGETS
# ==============================================================================


def to_logit(h: float) -> float:
    """Convert percentage to logit space for training."""
    eps = 1e-4
    h = np.clip(h / 100.0, eps, 1 - eps)
    return np.log(h / (1 - h))


def to_percent(z: float) -> float:
    """Convert logit prediction back to percentage."""
    return 100 / (1 + np.exp(-z))


# ==============================================================================
# DATA LOADING
# ==============================================================================


def load_weather_history() -> pd.DataFrame:
    """Load and preprocess weather history."""
    filepath = PROJECT_ROOT / "data" / "weather_vn_2125.csv"
    logger.info(f"🔍 DEBUG: PROJECT_ROOT = {PROJECT_ROOT}")
    logger.info(f"🔍 DEBUG: filepath = {filepath}")
    logger.info(f"🔍 DEBUG: filepath exists? {filepath.exists()}")
    df = pd.read_csv(filepath)
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)

    # Terrain flags
    df["coastal_flag"] = df["terrain"].isin(["ven biển", "Coastal"]).astype(int)
    df["highland_flag"] = df["terrain"].isin(["miền núi", "Highland"]).astype(int)
    df["lowland_flag"] = df["terrain"].isin(["đồng bằng", "Lowland"]).astype(int)

    return df


def load_geographical_data() -> Dict[str, str]:
    """Load province-to-terrain mapping."""
    filepath = PROJECT_ROOT / "data" / "geographical_information.csv"
    geo_df = pd.read_csv(filepath)

    terrain_map = {}
    for _, row in geo_df.iterrows():
        province = row["location"]
        terrain = row["terrain"]

        if "ven biển" in terrain or "Biển" in terrain:
            region_type = RegionType.coastal.value
        elif "miền núi" in terrain or "núi" in terrain:
            region_type = RegionType.highland.value
        else:
            region_type = RegionType.lowland.value

        terrain_map[province] = region_type

    return terrain_map


def load_area_data() -> Dict[str, str]:
    """Load province-to-area mapping."""
    filepath = PROJECT_ROOT / "data" / "weather_vn_2125.csv"
    weather_df = pd.read_csv(filepath)

    area_map = {}
    for _, row in weather_df.iterrows():
        province = row["location"]
        area = row["area"]
        if province not in area_map:
            area_map[province] = area

    return area_map


# ==============================================================================
# CLIMATE ZONES
# ==============================================================================

CLIMATE_ZONES = {
    "northwest": ["Lai Châu", "Điện Biên", "Sơn La", "Hòa Bình", "Lào Cai", "Yên Bái"],
    "northeast": [
        "Hà Giang",
        "Cao Bằng",
        "Bắc Kạn",
        "Lạng Sơn",
        "Thái Nguyên",
        "Tuyên Quang",
        "Phú Thọ",
        "Quảng Ninh",
        "Bắc Giang",
    ],
    "red_river_delta": [
        "Hà Nội",
        "Hải Phòng",
        "Hải Dương",
        "Hưng Yên",
        "Bắc Ninh",
        "Hà Nam",
        "Thái Bình",
        "Nam Định",
        "Ninh Bình",
        "Vĩnh Phúc",
    ],
    "north_central": [
        "Thanh Hóa",
        "Nghệ An",
        "Hà Tĩnh",
        "Quảng Bình",
        "Quảng Trị",
        "Thừa Thiên Huế",
    ],
    "south_central_coast": [
        "Đà Nẵng",
        "Quảng Nam",
        "Quảng Ngãi",
        "Bình Định",
        "Phú Yên",
        "Khánh Hòa",
        "Ninh Thuận",
        "Bình Thuận",
    ],
    "central_highlands": ["Kon Tum", "Gia Lai", "Đắk Lắk", "Đắk Nông", "Lâm Đồng"],
    "southern": [
        "Hồ Chí Minh",
        "Bình Phước",
        "Tây Ninh",
        "Bình Dương",
        "Đồng Nai",
        "Bà Rịa Vũng Tàu",
        "Long An",
        "Tiền Giang",
        "Bến Tre",
        "Trà Vinh",
        "Vĩnh Long",
        "Đồng Tháp",
        "An Giang",
        "Kiên Giang",
        "Hậu Giang",
        "Sóc Trăng",
        "Bạc Liêu",
        "Cà Mau",
        "Cần Thơ",
    ],
}


def get_climate_zone(province: str) -> str:
    """
    Map province/location to climate zone.

    Logic:
    1. Direct match in CLIMATE_ZONES
    2. Fallback: check location_to_province.csv mapping
    3. Then match province to zone
    """
    # Direct match first
    for zone, provinces in CLIMATE_ZONES.items():
        if province in provinces:
            return zone

    # Fallback: check location_to_province.csv mapping
    location_map_file = PROJECT_ROOT / "data" / "location_to_province.csv"
    if location_map_file.exists():
        try:
            location_df = pd.read_csv(location_map_file)
            matching = location_df[
                location_df["location"].str.lower() == province.lower()
            ]
            if not matching.empty:
                actual_province = matching.iloc[0]["province"]
                # Try again with mapped province
                for zone, provinces in CLIMATE_ZONES.items():
                    if actual_province in provinces:
                        logger.info(
                            f"✅ Mapped location '{province}' -> province '{actual_province}' -> zone '{zone}'"
                        )
                        return zone
        except Exception as e:
            logger.warning(f"⚠️  Location mapping lookup failed for '{province}': {e}")

    # Last fallback: try geographical_information.csv
    geo_file = PROJECT_ROOT / "data" / "geographical_information.csv"
    if geo_file.exists():
        try:
            geo_df = pd.read_csv(geo_file)
            matching_row = geo_df[geo_df["location"].str.lower() == province.lower()]
            if not matching_row.empty:
                actual_province = matching_row.iloc[0]["location"]
                for zone, provinces in CLIMATE_ZONES.items():
                    if actual_province in provinces:
                        logger.info(
                            f"✅ Matched location '{province}' in geo_data -> zone '{zone}'"
                        )
                        return zone
        except Exception as e:
            logger.warning(f"⚠️  Geo lookup failed for '{province}': {e}")

    raise ValueError(f"Unknown province/location: {province}")


# ==============================================================================
# METADATA MANAGEMENT
# ==============================================================================


class MetadataManager:
    """Manages model metadata."""

    def __init__(self, model_root: str = None):
        self.model_root = str(model_root or PROJECT_ROOT / "saved_models")
        self.metadata_cache: Dict[tuple, Dict[str, Any]] = {}

    def load_metadata(self, region: str, target: str) -> Dict[str, Any]:
        cache_key = (region, target)
        if cache_key in self.metadata_cache:
            return self.metadata_cache[cache_key]

        path = os.path.join(self.model_root, region, f"model_{target}.metadata.json")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Metadata not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        self.metadata_cache[cache_key] = metadata
        return metadata

    def get_features(self, region: str, target: str) -> List[str]:
        return self.load_metadata(region, target).get("features", [])


# ==============================================================================
# MODEL REGISTRY
# ==============================================================================


class ModelRegistry:
    """Loads and caches models with metadata."""

    def __init__(self, model_root: str = None):
        self.model_root = str(model_root or PROJECT_ROOT / "saved_models")
        self.models: Dict[tuple, Any] = {}
        self.feature_orders: Dict[tuple, List[str]] = {}
        self.metadata_manager = MetadataManager(self.model_root)
        self._load_models()

    def _load_models(self):
        targets = [
            "temp",
            "temp_max",
            "temp_min",
            "humidity",
            "rain_sum",
            "wind_speed",
            "cloud_cover",
        ]

        for region_dir in os.listdir(self.model_root):
            region_path = os.path.join(self.model_root, region_dir)
            if not os.path.isdir(region_path):
                continue

            for target in targets:
                model_file = os.path.join(region_path, f"model_{target}.pkl")
                try:
                    metadata = self.metadata_manager.load_metadata(region_dir, target)
                    if os.path.exists(model_file):
                        with open(model_file, "rb") as f:
                            model = pickle.load(f)

                        self.models[(region_dir, target)] = model
                        feature_order = self._extract_feature_order(model)
                        self.feature_orders[(region_dir, target)] = feature_order

                except Exception as e:
                    logger.warning(f"Skipping {region_dir}/{target}: {e}")

    def _extract_feature_order(self, model) -> List[str]:
        try:
            if hasattr(model, "named_steps") and "scaler" in model.named_steps:
                scaler = model.named_steps["scaler"]
                if hasattr(scaler, "get_feature_names_out"):
                    return list(scaler.get_feature_names_out())
        except:
            pass
        return (
            list(model.feature_names_in_) if hasattr(model, "feature_names_in_") else []
        )

    def get_model(self, region: str, target: str):
        if (region, target) not in self.models:
            raise ValueError(f"Model not available: {region}/{target}")
        return self.models[(region, target)]

    def get_feature_order(self, region: str, target: str) -> List[str]:
        return self.feature_orders.get((region, target), [])


# ==============================================================================
# FEATURE ENGINEERING
# ==============================================================================


def build_prediction_features(
    history_df: pd.DataFrame,
    prediction_date: pd.Timestamp,
    target_col: str,
    metadata: Dict[str, Any],
    feature_order: List[str] = None,
) -> pd.DataFrame:
    """Build features for prediction."""
    if len(history_df) < 14:
        raise ValueError(f"Need ≥14 days history, have {len(history_df)}")

    features = {}
    required_features = set(metadata.get("features", []))
    last_row = history_df.iloc[-1]
    prev_val = float(history_df.iloc[-2][target_col]) if len(history_df) > 1 else 0

    # Temporal features
    doy = prediction_date.dayofyear
    if "dayofyear" in required_features:
        features["dayofyear"] = int(doy)
    if "month" in required_features:
        features["month"] = int(prediction_date.month)
    if "season" in required_features:
        features["season"] = int(prediction_date.month // 4)

    # Cyclical encoding
    if "doy_sin" in required_features:
        features["doy_sin"] = float(np.sin(2 * np.pi * doy / 365))
    if "doy_cos" in required_features:
        features["doy_cos"] = float(np.cos(2 * np.pi * doy / 365))
    if "month_sin" in required_features:
        features["month_sin"] = float(np.sin(2 * np.pi * prediction_date.month / 12))
    if "month_cos" in required_features:
        features["month_cos"] = float(np.cos(2 * np.pi * prediction_date.month / 12))

    # Monsoon indicators
    if "is_southwest_monsoon" in required_features:
        features["is_southwest_monsoon"] = int(prediction_date.month in [5, 6, 7, 8, 9])
    if "is_northeast_monsoon" in required_features:
        features["is_northeast_monsoon"] = int(
            prediction_date.month in [10, 11, 12, 1, 2, 3, 4]
        )

    # Lag features
    for lag in [1, 3, 7, 14]:
        feat_name = f"{target_col}_lag_{lag}"
        if feat_name in required_features and len(history_df) > lag:
            features[feat_name] = float(history_df.iloc[-lag][target_col])

    # Rolling stats
    for window in [3, 7, 14]:
        mean_name = f"{target_col}_rolling_mean_{window}"
        std_name = f"{target_col}_rolling_std_{window}"
        if (mean_name in required_features or std_name in required_features) and len(
            history_df
        ) >= window:
            window_data = history_df.iloc[-window:][target_col]
            if mean_name in required_features:
                features[mean_name] = float(window_data.mean())
            if std_name in required_features:
                features[std_name] = float(window_data.std())

    # Rolling sums
    for window in [7, 14, 30]:
        feat_name = f"{target_col}_sum_{window}d"
        if feat_name in required_features and len(history_df) >= window:
            features[feat_name] = float(history_df.iloc[-window:][target_col].sum())

    # Momentum
    if f"{target_col}_change" in required_features and len(history_df) >= 2:
        features[f"{target_col}_change"] = float(last_row[target_col] - prev_val)

    # Terrain flags
    for flag in ["coastal_flag", "highland_flag", "lowland_flag"]:
        if flag in required_features:
            features[flag] = int(last_row.get(flag, 0))

    result_df = pd.DataFrame([features])

    # Validate features
    missing = required_features - set(result_df.columns)
    if missing:
        raise ValueError(f"Missing features: {missing}")

    # Return in correct order
    if feature_order:
        return result_df[feature_order]
    feature_list = metadata.get("features", [])
    return (
        result_df[feature_list]
        if feature_list
        else result_df[sorted(required_features)]
    )


# ==============================================================================
# PREDICTION SERVICE
# ==============================================================================


class WeatherPredictionService:
    """Streamlined weather prediction service."""

    def __init__(self):
        self.weather_history = load_weather_history()
        self.terrain_map = load_geographical_data()
        self.area_map = load_area_data()
        self.model_registry = ModelRegistry()

    def _apply_constraints(self, preds: Dict[str, float]) -> Dict[str, float]:
        temp = preds["temp"]

        preds["temp_max"] = max(preds["temp_max"], temp)
        preds["temp_min"] = min(preds["temp_min"], temp)

        preds["humidity"] = float(np.clip(preds["humidity"], 20, 100))
        preds["cloud_cover"] = float(np.clip(preds["cloud_cover"], 0, 100))

        preds["rain_sum"] = max(0.0, preds["rain_sum"])
        preds["wind_speed"] = max(0.0, preds["wind_speed"])

        return preds

    def seasonal_baseline(
        self, history_df: pd.DataFrame, target: str, doy: int, window: int = 7
    ) -> float:
        """
        Seasonal anchor to prevent recursive drift.
        """
        df = history_df.copy()
        df["doy"] = df["date"].dt.dayofyear

        subset = df[(df["doy"] >= doy - window) & (df["doy"] <= doy + window)]

        if subset.empty:
            return float(df[target].mean())

        return float(subset[target].mean())

    def predict_single_day(
        self, prediction_date: pd.Timestamp, location: str
    ) -> Dict[str, float]:

        alias = {
            "Phú Quốc": "Kiên Giang",
            "Phu Quoc": "Kiên Giang",
        }
        base_location = alias.get(location, location)

        history = self.weather_history[
            self.weather_history["location"] == base_location
        ].sort_values("date")

        if history.empty:
            raise ValueError(f"No history for {location}")

        climate_zone = get_climate_zone(base_location)
        doy = prediction_date.dayofyear

        targets = [
            "temp",
            "temp_max",
            "temp_min",
            "humidity",
            "rain_sum",
            "wind_speed",
            "cloud_cover",
        ]

        results = {}

        for target in targets:
            # Try ML model first, fallback to seasonal baseline if unavailable
            try:
                metadata = self.model_registry.metadata_manager.load_metadata(
                    climate_zone, target
                )
                feature_order = self.model_registry.get_feature_order(
                    climate_zone, target
                )

                features = build_prediction_features(
                    history, prediction_date, target, metadata, feature_order
                )

                model = self.model_registry.get_model(climate_zone, target)
                pred = float(model.predict(features)[0])

                if target in ["humidity", "cloud_cover"]:
                    pred = to_percent(pred)

                baseline = self.seasonal_baseline(history, target, doy)

                # blend to prevent drift
                alpha = 0.65 if target.startswith("temp") else 0.7
                pred = alpha * pred + (1 - alpha) * baseline

            except (ValueError, FileNotFoundError) as e:
                # Fallback to seasonal baseline when model unavailable
                logger.warning(
                    f"⚠️ Model unavailable for {climate_zone}/{target}, using seasonal baseline"
                )
                pred = self.seasonal_baseline(history, target, doy)

            results[target] = pred

        return self._apply_constraints(results)

    def _extend_history(
        self,
        history_df: pd.DataFrame,
        date: pd.Timestamp,
        predictions: Dict[str, float],
    ) -> pd.DataFrame:
        """Add predictions to history for recursive forecasting."""
        new_row = {"date": date, "location": history_df.iloc[0]["location"]}
        new_row.update(predictions)

        # Copy terrain flags
        for col in ["coastal_flag", "highland_flag", "lowland_flag"]:
            if col in history_df.columns:
                new_row[col] = history_df.iloc[0][col]

        return pd.concat([history_df, pd.DataFrame([new_row])], ignore_index=True)

    def predict(self, date: str, location: str) -> WeatherData:
        prediction_date = pd.to_datetime(date).normalize()

        alias = {
            "Phú Quốc": "Kiên Giang",
            "Phu Quoc": "Kiên Giang",
        }
        base_location = alias.get(location, location)

        if base_location not in self.terrain_map:
            raise ValueError(f"Unknown location: {location}")

        region = self.terrain_map[base_location]
        area = self.area_map.get(base_location, AreaType.rural.value)

        preds = self.predict_single_day(prediction_date, base_location)

        return WeatherData(
            location=location,
            datetime=prediction_date.strftime("%Y-%m-%d"),
            region=RegionType(region),
            area=AreaType(area),
            temp=round(preds["temp"], 1),
            temp_max=round(preds["temp_max"], 1),
            temp_min=round(preds["temp_min"], 1),
            humidity=int(round(preds["humidity"])),
            rain_sum=round(preds["rain_sum"], 2),
            wind_speed=round(preds["wind_speed"], 1),
            cloud_cover=round(preds["cloud_cover"], 1),
        )


# ==============================================================================
# PUBLIC API
# ==============================================================================

_service_instance: Optional[WeatherPredictionService] = None


def get_service() -> WeatherPredictionService:
    global _service_instance
    if _service_instance is None:
        _service_instance = WeatherPredictionService()
    return _service_instance


def predict(date: str, location: str) -> WeatherData:
    """Main prediction entry point."""
    service = get_service()
    return service.predict(date, location)


if __name__ == "__main__":
    result = predict("2025-01-05", "Gia Lai")
    print(result.model_dump())
