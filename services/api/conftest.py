"""Pytest configuration for the AgroVision API suite.

The hosted vision "second opinion" is a real network call. It is exercised by
dedicated unit tests with the HTTP layer mocked; everywhere else we disable it so
endpoint and integration tests stay deterministic and offline even when a real
API key is present in the local ``.env``. Individual tests can re-enable it via
monkeypatch when they mock the transport.
"""

from app.config import settings

settings.external_vision_enabled = False
# Keep the suite offline: the no-GPS analyze path defaults to live Alexandria weather,
# so disable the live provider here and let it fall back to the labelled reference.
settings.weather_enabled = False
