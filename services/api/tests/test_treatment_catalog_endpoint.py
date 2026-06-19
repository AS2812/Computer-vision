from fastapi.testclient import TestClient

from app.schemas import PriceEvidence
from app.main import app


def test_tomato_treatment_catalog_exposes_products_doses_safety_and_price_sources(monkeypatch):
    def fake_price_sources(treatment):
        return [
            PriceEvidence(
                source="Test dealer",
                title=treatment.name_en,
                url="https://example.test/product",
                price_text="EGP 100.00",
                availability_en="available online",
                availability_ar="متوفر أونلاين",
                checked_at="2026-06-18",
                live=True,
                note_en="Retail signal, not official.",
                note_ar="مؤشر بيع، ليس سعرًا رسميًا.",
            )
        ]

    monkeypatch.setattr("app.main.price_sources_for_treatment", fake_price_sources)
    response = TestClient(app).get("/api/treatments/tomato/tomato_late_blight")

    assert response.status_code == 200
    body = response.json()
    assert body["disease_key"] == "tomato_late_blight"
    assert body["treatments"]
    first = body["treatments"][0]
    assert "Mandipropamid" in first["name_en"]
    assert first["dose_en"]
    assert first["phi_en"]
    assert first["hazard_en"]
    assert first["price_sources"][0]["price_text"] == "EGP 100.00"
    assert first["price_sources"][0]["live"] is True
    assert body["availability"]["apc_url"].startswith("https://")
    assert "retail-price API" in body["availability"]["price_status_en"]
    assert body["prevention"]["en"]


def test_tomato_treatment_catalog_404_for_unknown_key():
    response = TestClient(app).get("/api/treatments/tomato/not-a-disease")

    assert response.status_code == 404
