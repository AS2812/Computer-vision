from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from threading import RLock
from typing import Any
from urllib.parse import quote

import httpx

from app.config import settings
from app.contracts.cases import CropCase, SystemOutput


class InMemoryCaseRepository:
    """Thread-safe local-demo repository behind a replaceable adapter boundary."""

    def __init__(self) -> None:
        self._cases: dict[str, CropCase] = {}
        self._assets: dict[str, list[dict[str, Any]]] = {}
        self._reports: dict[str, SystemOutput] = {}
        self._lock = RLock()

    def save(self, case: CropCase) -> CropCase:
        with self._lock:
            self._cases[case.case_id] = deepcopy(case)
            return deepcopy(case)

    def get(self, case_id: str) -> CropCase | None:
        with self._lock:
            case = self._cases.get(case_id)
            return deepcopy(case) if case else None

    def list(self, limit: int = 20) -> list[CropCase]:
        bounded = min(max(limit, 1), 100)
        with self._lock:
            ordered = sorted(self._cases.values(), key=lambda item: item.updated_at, reverse=True)
            return deepcopy(ordered[:bounded])

    def clear(self) -> None:
        with self._lock:
            self._cases.clear()
            self._assets.clear()
            self._reports.clear()

    def save_asset(
        self,
        case: CropCase,
        filename: str,
        content: bytes,
        content_type: str,
        view_type: str,
        evidence: dict[str, Any],
    ) -> bool:
        with self._lock:
            self._assets.setdefault(case.case_id, []).append(
                {
                    "filename": filename,
                    "content_type": content_type,
                    "view_type": view_type,
                    "evidence": deepcopy(evidence),
                }
            )
        return True

    def save_report(self, case: CropCase, report: SystemOutput) -> bool:
        with self._lock:
            self._reports[case.case_id] = deepcopy(report)
        return True


class SupabaseCaseRepository(InMemoryCaseRepository):
    """Memory-first case repository with best-effort local Supabase persistence."""

    def __init__(self) -> None:
        super().__init__()
        self.url = (settings.supabase_url or "").rstrip("/")
        self.key = settings.supabase_service_role_key or ""
        self.enabled = bool(self.url and self.key)
        self.owner_id: str | None = None
        self.farm_id: str | None = None
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
        if self.owner_id and self.farm_id:
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
            self.last_error = None
            return True
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            self.last_error = type(exc).__name__
            return False

    def save(self, case: CropCase) -> CropCase:
        saved = super().save(case)
        if not self._ensure_context():
            return saved
        try:
            snapshot = saved.model_dump(mode="json")
            self._request(
                "POST",
                "/rest/v1/crop_cases?on_conflict=id",
                headers={"Prefer": "resolution=merge-duplicates"},
                json={
                    "id": saved.case_id,
                    "owner_id": self.owner_id,
                    "farm_id": self.farm_id,
                    "status": saved.status,
                    "crop_type": saved.crop,
                    "location": saved.location,
                    "farm_type": saved.farm_type,
                    "growth_stage": saved.growth_stage,
                    "symptoms": saved.symptoms,
                    "snapshot": snapshot,
                    "created_at": snapshot["created_at"],
                    "updated_at": snapshot["updated_at"],
                },
            )
            if saved.observations:
                self._request(
                    "POST",
                    "/rest/v1/case_observations?on_conflict=case_id,observation_type",
                    headers={"Prefer": "resolution=merge-duplicates"},
                    json=[
                        {
                            "owner_id": self.owner_id,
                            "case_id": saved.case_id,
                            "observation_type": key,
                            "value": value,
                            "source": saved.observation_sources.get(key, "farmer_answer"),
                            "updated_at": snapshot["updated_at"],
                        }
                        for key, value in saved.observations.items()
                    ],
                )
            if saved.diagnosis.top_disease:
                diagnosis_source = "image_model"
                if saved.diagnosis.confirmation:
                    diagnosis_source = (
                        "expert"
                        if saved.diagnosis.confirmation.confirmation_type.value == "egyptian_agronomist"
                        else "lab"
                    )
                self._request(
                    "POST",
                    "/rest/v1/case_diagnoses?on_conflict=case_id",
                    headers={"Prefer": "resolution=merge-duplicates"},
                    json={
                        "owner_id": self.owner_id,
                        "case_id": saved.case_id,
                        "top_disease": saved.diagnosis.top_disease,
                        "confidence": saved.diagnosis.confidence,
                        "alternatives": [item.model_dump(mode="json") for item in saved.diagnosis.alternatives],
                        "evidence": saved.diagnosis.evidence,
                        "missing_info": saved.diagnosis.missing_info,
                        "source": diagnosis_source,
                        "updated_at": snapshot["updated_at"],
                    },
                )
            if saved.treatment_rule_version:
                self._request(
                    "POST",
                    "/rest/v1/case_treatment_plans?on_conflict=case_id",
                    headers={"Prefer": "resolution=merge-duplicates"},
                    json={
                        "owner_id": self.owner_id,
                        "case_id": saved.case_id,
                        "disease_class": saved.disease_class,
                        "rule_version": saved.treatment_rule_version,
                        "plan": saved.treatment_plan.model_dump(mode="json"),
                        "updated_at": snapshot["updated_at"],
                    },
                )
            self.last_error = None
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            self.last_error = type(exc).__name__
        return saved

    def get(self, case_id: str) -> CropCase | None:
        local = super().get(case_id)
        if local or not self._ensure_context():
            return local
        try:
            rows = self._request(
                "GET",
                f"/rest/v1/crop_cases?id=eq.{quote(case_id)}&select=snapshot&limit=1",
            ).json()
            if not rows:
                return None
            loaded = CropCase.model_validate(rows[0]["snapshot"])
            super().save(loaded)
            self.last_error = None
            return loaded
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            self.last_error = type(exc).__name__
            return None

    def list(self, limit: int = 20) -> list[CropCase]:
        bounded = min(max(limit, 1), 100)
        local = {case.case_id: case for case in super().list(bounded)}
        if not self._ensure_context():
            return list(local.values())
        try:
            rows = self._request(
                "GET",
                f"/rest/v1/crop_cases?select=snapshot&order=updated_at.desc&limit={bounded}",
            ).json()
            for row in rows:
                case = CropCase.model_validate(row["snapshot"])
                local[case.case_id] = case
                super().save(case)
            self.last_error = None
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            self.last_error = type(exc).__name__
        return sorted(local.values(), key=lambda item: item.updated_at, reverse=True)[:bounded]

    def save_asset(
        self,
        case: CropCase,
        filename: str,
        content: bytes,
        content_type: str,
        view_type: str,
        evidence: dict[str, Any],
    ) -> bool:
        super().save_asset(case, filename, content, content_type, view_type, evidence)
        if not self._ensure_context():
            return False
        try:
            safe_name = Path(filename).name.replace(" ", "_")
            storage_path = f"{self.owner_id}/{case.case_id}/{safe_name}"
            self._request(
                "POST",
                f"/storage/v1/object/case-images/{quote(storage_path, safe='/')}",
                headers={"Content-Type": content_type, "x-upsert": "true"},
                content=content,
            )
            self._request(
                "POST",
                "/rest/v1/case_assets",
                json={
                    "owner_id": self.owner_id,
                    "case_id": case.case_id,
                    "storage_path": storage_path,
                    "mime_type": content_type,
                    "view_type": view_type,
                    "model_evidence": evidence,
                },
            )
            self.last_error = None
            return True
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            self.last_error = type(exc).__name__
            return False

    def save_report(self, case: CropCase, report: SystemOutput) -> bool:
        super().save_report(case, report)
        if not self._ensure_context():
            return False
        try:
            self._request(
                "POST",
                "/rest/v1/case_reports?on_conflict=case_id",
                headers={"Prefer": "resolution=merge-duplicates"},
                json={
                    "owner_id": self.owner_id,
                    "case_id": case.case_id,
                    "system_output": report.model_dump(mode="json"),
                    "updated_at": case.updated_at.isoformat(),
                },
            )
            self.last_error = None
            return True
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            self.last_error = type(exc).__name__
            return False
