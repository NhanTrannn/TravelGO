"""
Weather Service Package

Provides weather information and forecasts for travel planning.
"""

from .weather_service import WeatherService

__all__ = ["WeatherService", "create_weather_service"]


def create_weather_service() -> WeatherService:
    """
    Factory function to create WeatherService instance

    Returns:
        WeatherService: Configured weather service instance

    Example:
        >>> weather = create_weather_service()
        >>> forecast = weather.get_weather("Đà Nẵng", "2026-01-20", 3)
    """
    return WeatherService()
