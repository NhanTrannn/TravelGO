from pydantic import BaseModel, Field
from typing import Optional, Literal, List, Tuple

from enum import Enum


class RegionType(str, Enum):
    coastal = "coastal"
    highland = "highland"
    lowland = "lowland"

class AreaType(str, Enum):
    urban = "urban"
    rural = "rural"


class WeatherData(BaseModel):
    location: str = Field(..., description="Tên địa điểm du lịch")
    datetime: str = Field(..., description="Ngày dự báo")
    region: RegionType = Field(
        ...,
        description="Đặc điểm địa hình của location"
    )
    area: AreaType = Field(
        ..., description="Đặc điểm dân cư của location"
    )

    temp: float = Field(..., description="Nhiệt độ trung bình (°C)")
    temp_max: float = Field(..., description="Nhiệt độ cao nhất (°C)")
    temp_min: float = Field(..., description="Nhiệt độ thấp nhất (°C)")

    humidity: int = Field(..., ge=0, le=100, description="Độ ẩm (%)")

    rain_sum: float = Field(
        0.0,
        description="Lượng mưa trong ngày (mm)"
    )

    wind_speed: float = Field(
        ...,
        description="Tốc độ gió (m/s)"
    )

    cloud_cover: float = Field(
        ...,
        ge=0, le=100,
        description="Mây che phủ (%)"
    )

class TravelInsights(BaseModel):
    location: str = Field(..., description="Tên địa điểm du lịch")
    datetime: str = Field(..., description="Ngày dự báo")
    comfort_level: Literal[
        "rất dễ chịu",
        "dễ chịu",
        "trung bình",
        "khó chịu",
        "nguy hiểm"
    ] = Field(..., description="Mức độ dễ chịu cho du lịch")

    positives: List[str]
    risks: List[Tuple[int, str]] = Field(
    default_factory=list,
    description="Danh sách rủi ro, mỗi phần tử là (severity_score, risk_description)"
)

    travel_score: Optional[int] = Field(
        None,
        ge=0,
        le=100,
        description="Điểm đánh giá mức độ phù hợp du lịch (0-100)"
    )

    is_outdoor_friendly: bool = Field(
        ...,
        description="Có phù hợp cho hoạt động ngoài trời hay không"
    )

    notes: Optional[str] = Field(
        None,
        description="Ghi chú bổ sung về thời tiết"
    )

