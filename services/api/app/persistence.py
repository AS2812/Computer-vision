from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx

from .config import settings
from .schemas import AnalysisResponse


class SupabaseAnalysisStore:
    """Best-effort local persistence that never makes image analysis unavailable."""

    def __init__(self) -> None:
        self.url = (settings.supabase_url or "").rstrip("/")
        self.key = settings.supabase_service_role_key or ""
        self.enabled = bool(self.url and self.key)
        self.owner_id: str | None = None
        self.farm_id: str | None = None
        self.mission_id: str | None = None
        self.last_error: str | None = None

    @property
    def mode(self) -> str:
        if not self.enabled:
            return "memory-only"
        return "supabase-error" if self.last_error else "supabase"

    def _headers(self, prefer: str | None = None) -> dict[str, str]:
        headers = {"apikey": self.key, "Authorization": f"Bearer {self.key}"}
        if prefer:
            headers["Prefer"] = prefer
        return headers

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        response = httpx.request(
            method,
            f"{self.url}{path}",
            headers={**self._headers(), **kwargs.pop("headers", {})},
            timeout=settings.supabase_timeout_seconds,
            **kwargs,
        )
        response.raise_for_status()
        return response

    def _ensure_context(self) -> bool:
        if not self.enabled:
            return False
        if self.owner_id and self.mission_id:
            return True
        try:
            users = self._request("GET", "/auth/v1/admin/users?per_page=1000").json().get("users", [])
            user = next((item for item in users if item.get("email") == settings.supabase_demo_email), None)
            if not user:
                user = self._request(
                    "POST",
                    "/auth/v1/admin/users",
                    json={
                        "email": settings.supabase_demo_email,
                        "password": settings.supabase_demo_password,
                        "email_confirm": True,
                        "user_metadata": {"display_name": "AgroVision Demo"},
                    },
                ).json()
            self.owner_id = user["id"]
            self._request(
                "POST",
                "/rest/v1/profiles?on_conflict=id",
                headers={"Prefer": "resolution=merge-duplicates"},
                json={"id": self.owner_id, "display_name": "AgroVision Demo", "locale": "ar"},
            )

            farms = self._request(
                "GET",
                f"/rest/v1/farms?owner_id=eq.{self.owner_id}&select=id&limit=1",
            ).json()
            if farms:
                self.farm_id = farms[0]["id"]
            else:
                self.farm_id = self._request(
                    "POST",
                    "/rest/v1/farms",
                    headers={"Prefer": "return=representation"},
                    json={"owner_id": self.owner_id, "name": "Alexandria Demo Farm", "location": "Alexandria, Egypt"},
                ).json()[0]["id"]

            missions = self._request(
                "GET",
                f"/rest/v1/missions?farm_id=eq.{self.farm_id}&select=id&limit=1",
            ).json()
            if missions:
                self.mission_id = missions[0]["id"]
            else:
                self.mission_id = self._request(
                    "POST",
                    "/rest/v1/missions",
                    headers={"Prefer": "return=representation"},
                    json={"owner_id": self.owner_id, "farm_id": self.farm_id, "name": "Local image checks"},
                ).json()[0]["id"]
            self.last_error = None
            return True
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            self.last_error = type(exc).__name__
            return False

    def _upload(self, bucket: str, path: str, content: bytes, content_type: str) -> None:
        self._request(
            "POST",
            f"/storage/v1/object/{bucket}/{quote(path, safe='/')}",
            headers={"Content-Type": content_type, "x-upsert": "true"},
            content=content,
        )

    def save_analysis(
        self,
        analysis: AnalysisResponse,
        image_content: bytes | None = None,
        content_type: str = "image/jpeg",
    ) -> bool:
        if not self._ensure_context():
            return False
        try:
            asset_id = None
            if image_content:
                filename = Path(analysis.filename).name.replace(" ", "_")
                storage_path = f"{self.owner_id}/{analysis.analysis_id}/{filename}"
                self._upload("mission-images", storage_path, image_content, content_type)
                asset_id = self._request(
                    "POST",
                    "/rest/v1/uploaded_assets",
                    headers={"Prefer": "return=representation"},
                    json={
                        "owner_id": self.owner_id,
                        "mission_id": self.mission_id,
                        "storage_path": storage_path,
                        "mime_type": content_type,
                    },
                ).json()[0]["id"]

            self._request(
                "POST",
                "/rest/v1/analysis_runs?on_conflict=id",
                headers={"Prefer": "resolution=merge-duplicates"},
                json={
                    "id": analysis.analysis_id,
                    "owner_id": self.owner_id,
                    "asset_id": asset_id,
                    "status": "complete",
                    "provider": analysis.provider,
                    "processing_ms": analysis.processing_ms,
                    "peak_memory_mb": analysis.peak_memory_mb,
                    "response": analysis.model_dump(mode="json"),
                },
            )
            feature_rows = [
                {
                    "owner_id": self.owner_id,
                    "analysis_id": analysis.analysis_id,
                    "feature": result.feature,
                    "level": result.level,
                    "score": result.score,
                    "confidence": result.confidence,
                    "value": {
                        "title": result.title,
                        "title_ar": result.title_ar,
                        "value": result.value,
                        "value_ar": result.value_ar,
                    },
                    "evidence": result.evidence,
                    "limitation": result.limitation,
                }
                for result in analysis.results
            ]
            self._request("POST", "/rest/v1/feature_results", json=feature_rows)
            self._request(
                "POST",
                "/rest/v1/recommendations",
                json=[
                    {
                        "owner_id": self.owner_id,
                        "analysis_id": analysis.analysis_id,
                        "body_ar": item.ar,
                        "body_en": item.en,
                        "reviewed": True,
                    }
                    for item in analysis.recommendations
                ],
            )
            self._request(
                "POST",
                "/rest/v1/alerts",
                json=[
                    {
                        "owner_id": self.owner_id,
                        "analysis_id": analysis.analysis_id,
                        "severity": "warning",
                        "message": json.dumps(item.model_dump(), ensure_ascii=False),
                    }
                    for item in analysis.alerts
                ],
            )
            self.last_error = None
            return True
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            self.last_error = type(exc).__name__
            return False

    def load_analysis(self, analysis_id: str) -> AnalysisResponse | None:
        if not self._ensure_context():
            return None
        try:
            rows = self._request(
                "GET",
                f"/rest/v1/analysis_runs?id=eq.{quote(analysis_id)}&select=response&limit=1",
            ).json()
            if not rows or not rows[0].get("response"):
                return None
            self.last_error = None
            return AnalysisResponse.model_validate(rows[0]["response"])
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError):
            return None

    def list_analyses(self, limit: int = 20) -> list[AnalysisResponse]:
        if not self._ensure_context():
            return []
        try:
            rows = self._request(
                "GET",
                f"/rest/v1/analysis_runs?response=not.is.null&select=response&order=created_at.desc&limit={min(max(limit, 1), 100)}",
            ).json()
            analyses = [
                AnalysisResponse.model_validate(row["response"])
                for row in rows
                if row.get("response")
            ]
            self.last_error = None
            return analyses
        except (httpx.HTTPError, KeyError, TypeError, ValueError):
            return []

    def save_report(self, analysis_id: str, report_format: str, content: bytes, content_type: str) -> bool:
        if not self._ensure_context():
            return False
        try:
            storage_path = f"{self.owner_id}/{analysis_id}/{analysis_id}.{report_format}"
            self._upload("analysis-reports", storage_path, content, content_type)
            self._request(
                "POST",
                "/rest/v1/reports",
                json={
                    "owner_id": self.owner_id,
                    "analysis_id": analysis_id,
                    "format": report_format,
                    "storage_path": storage_path,
                },
            )
            self.last_error = None
            return True
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            self.last_error = type(exc).__name__
            return False


analysis_store = SupabaseAnalysisStore()
