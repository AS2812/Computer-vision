from __future__ import annotations

from dataclasses import dataclass

import httpx

from .config import settings


@dataclass(frozen=True)
class WeatherObservation:
    temperature_c: float
    wind_kph: float
    precipitation_mm: float
    condition: str
    condition_ar: str
    source: str = "Open-Meteo"


def egypt_reference_weather() -> WeatherObservation:
    """Fixed, clearly labelled weather used by the offline Egypt demo."""
    return WeatherObservation(
        temperature_c=24,
        wind_kph=9,
        precipitation_mm=0,
        condition="partly cloudy",
        condition_ar="غائم جزئيًا",
        source="Egypt demo reference (not live)",
    )


def _condition(code: int) -> tuple[str, str]:
    if code == 0:
        return "clear", "صحو"
    if code in {1, 2, 3}:
        return "partly cloudy", "غائم جزئيًا"
    if code in {45, 48}:
        return "fog", "ضباب"
    if code in {51, 53, 55, 56, 57}:
        return "drizzle", "رذاذ"
    if code in {61, 63, 65, 66, 67, 80, 81, 82}:
        return "rain", "أمطار"
    if code in {71, 73, 75, 77, 85, 86}:
        return "snow", "ثلوج"
    if code in {95, 96, 99}:
        return "thunderstorm", "عاصفة رعدية"
    return "unknown conditions", "حالة غير معروفة"


def weather_for_coords(lat: float, lon: float) -> WeatherObservation | None:
    try:
        response = httpx.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,precipitation,weather_code,wind_speed_10m",
                "timezone": "auto",
            },
            timeout=settings.weather_timeout_seconds,
        )
        response.raise_for_status()
        current = response.json()["current"]
        condition, condition_ar = _condition(int(current["weather_code"]))
        return WeatherObservation(
            temperature_c=float(current["temperature_2m"]),
            wind_kph=float(current["wind_speed_10m"]),
            precipitation_mm=float(current["precipitation"]),
            condition=condition,
            condition_ar=condition_ar,
        )
    except (httpx.HTTPError, KeyError, TypeError, ValueError):
        return None


def current_weather() -> WeatherObservation | None:
    if not settings.weather_enabled:
        return None
    try:
        response = httpx.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": settings.weather_latitude,
                "longitude": settings.weather_longitude,
                "current": "temperature_2m,precipitation,weather_code,wind_speed_10m",
                "timezone": "auto",
            },
            timeout=settings.weather_timeout_seconds,
        )
        response.raise_for_status()
        current = response.json()["current"]
        condition, condition_ar = _condition(int(current["weather_code"]))
        return WeatherObservation(
            temperature_c=float(current["temperature_2m"]),
            wind_kph=float(current["wind_speed_10m"]),
            precipitation_mm=float(current["precipitation"]),
            condition=condition,
            condition_ar=condition_ar,
        )
    except (httpx.HTTPError, KeyError, TypeError, ValueError):
        return None


def weather_pressure_calculator(
    disease_class: str,
    temp: float | None,
    humidity: float | None,
    precip: float | None,
    wind: float | None,
    scenario: str | None = None
) -> dict:
    missing = []
    if temp is None:
        missing.append("temperature")
    if humidity is None:
        missing.append("humidity")
    if precip is None:
        missing.append("precipitation")
    if wind is None:
        missing.append("wind")

    # Bacterial spot specific risk evaluation
    temp_ok = temp is not None
    precip_ok = precip is not None
    humidity_ok = humidity is not None
    
    # Warm temp: 18C - 30C
    temp_risk = temp_ok and (18 <= temp <= 30)
    # Wet/splash: precipitation > 0.1mm
    precip_risk = precip_ok and (precip > 0.1)
    # Humidity: > 70%
    humidity_risk = humidity_ok and (humidity > 70)
    
    if "humidity" in missing:
        # Partial calculations
        if temp_ok and precip_ok:
            if temp_risk and precip_risk:
                level = "Partial high"
                score = 80
            elif temp_risk or precip_risk:
                level = "Partial medium"
                score = 55
            else:
                level = "Partial low"
                score = 25
        else:
            level = "Partial medium"
            score = 50
    else:
        # Full calculations
        high_count = sum([temp_risk, precip_risk, humidity_risk])
        if high_count >= 2:
            level = "high"
            score = 85
        elif high_count == 1:
            level = "medium"
            score = 60
        else:
            level = "low"
            score = 20
            
    reason_en = "temperature and precipitation were available; humidity was not available." if "humidity" in missing else "all weather fields were available."
    reason_ar = "درجة الحرارة وكمية الأمطار متوفرة؛ الرطوبة غير متوفرة." if "humidity" in missing else "جميع حقول الطقس متوفرة."
    
    return {
        "weather_pressure_score": score,
        "weather_pressure_level": level,
        "missing_weather_fields": missing,
        "reason_en": reason_en,
        "reason_ar": reason_ar
    }

