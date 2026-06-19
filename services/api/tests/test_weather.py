import httpx

from app import weather
from app.config import settings


def test_current_weather_returns_live_observation(monkeypatch):
    def fake_get(url, **kwargs):
        return httpx.Response(
            200,
            json={
                "current": {
                    "temperature_2m": 29.4,
                    "wind_speed_10m": 12.1,
                    "precipitation": 0.2,
                    "weather_code": 61,
                }
            },
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(settings, "weather_enabled", True)
    monkeypatch.setattr(weather.httpx, "get", fake_get)

    result = weather.current_weather()

    assert result is not None
    assert result.temperature_c == 29.4
    assert result.condition == "rain"
    assert result.condition_ar == "أمطار"
    assert result.precipitation_mm == 0.2


def test_current_weather_falls_back_when_offline(monkeypatch):
    monkeypatch.setattr(settings, "weather_enabled", True)
    monkeypatch.setattr(weather.httpx, "get", lambda *args, **kwargs: (_ for _ in ()).throw(httpx.ConnectError("offline")))

    assert weather.current_weather() is None


def test_current_weather_can_be_disabled(monkeypatch):
    monkeypatch.setattr(settings, "weather_enabled", False)

    assert weather.current_weather() is None
