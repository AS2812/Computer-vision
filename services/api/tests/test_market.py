import httpx

from app import market
from app.main import app
from fastapi.testclient import TestClient


def test_parse_oboor_tomato_price_from_arabic_row():
    html = "<div>طماطم. من سعر : 10 الى سعر : 17.5. العبوة: قفص</div>"

    assert market._parse_oboor_tomato_price(html) == (10.0, 17.5)


def test_market_endpoint_returns_live_oboor_price(monkeypatch):
    def fake_get(url, **kwargs):
        return httpx.Response(
            200,
            text="<html><body>طماطم من سعر : 10 الى سعر : 17.5 كيلو</body></html>",
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(market.httpx, "get", fake_get)

    response = TestClient(app).get("/api/market/tomato")

    assert response.status_code == 200
    body = response.json()
    assert body["live"] is True
    assert body["low_egp_per_kg"] == 10.0
    assert body["high_egp_per_kg"] == 17.5
    assert "oboormarket" in body["source_url"]


def test_market_endpoint_is_honest_when_unavailable(monkeypatch):
    def fake_get(*args, **kwargs):
        raise httpx.ConnectError("offline")

    monkeypatch.setattr(market.httpx, "get", fake_get)

    body = TestClient(app).get("/api/market/tomato").json()

    assert body["live"] is False
    assert body["low_egp_per_kg"] is None
    assert "No live tomato price" in body["note"]
