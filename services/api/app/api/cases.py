from __future__ import annotations

import io
from hashlib import sha256
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response
from PIL import Image, UnidentifiedImageError

from app.adapters.case_repository import SupabaseCaseRepository
from app.application.case_service import CaseNotFoundError, CaseService
from app.application.image_diagnosis import diagnose_image, measure_image
from app.config import settings
from app.vision_llm import vision_diagnose
from app.contracts.cases import (
    CostBenefitInput,
    CropCase,
    CropCaseCreate,
    CropCasePatch,
    DiagnosisInput,
    DiagnosisConfirmationInput,
    DiagnosisConfirmationType,
    ImageViewType,
    ObservationInput,
    SystemOutput,
)
from app.reports import case_csv, case_pdf


router = APIRouter(prefix="/api/v1/cases", tags=["crop-cases"])
case_repository = SupabaseCaseRepository()
case_service = CaseService(case_repository)


def _not_found(error: CaseNotFoundError) -> HTTPException:
    return HTTPException(status_code=404, detail=f"Case not found: {error.args[0]}")


@router.post("", response_model=CropCase, status_code=201)
def create_case(request: CropCaseCreate) -> CropCase:
    return case_service.create(request)


@router.get("", response_model=list[CropCase])
def list_cases(limit: int = Query(default=20, ge=1, le=100)) -> list[CropCase]:
    return case_service.list(limit)


@router.get("/{case_id}", response_model=CropCase)
def get_case(case_id: str) -> CropCase:
    try:
        return case_service.get(case_id)
    except CaseNotFoundError as error:
        raise _not_found(error) from None


@router.patch("/{case_id}", response_model=CropCase)
def patch_case(case_id: str, request: CropCasePatch) -> CropCase:
    try:
        return case_service.patch(case_id, request)
    except CaseNotFoundError as error:
        raise _not_found(error) from None


@router.post("/{case_id}/observations", response_model=CropCase)
def add_observations(case_id: str, request: ObservationInput) -> CropCase:
    try:
        return case_service.add_observations(case_id, request)
    except CaseNotFoundError as error:
        raise _not_found(error) from None


@router.get("/{case_id}/questions", response_model=list[str])
def get_questions(case_id: str, limit: int = Query(default=3, ge=1, le=5)) -> list[str]:
    try:
        return case_service.ask_questions(case_id, limit)
    except CaseNotFoundError as error:
        raise _not_found(error) from None


@router.post("/{case_id}/diagnosis", response_model=CropCase)
def set_diagnosis(case_id: str, request: DiagnosisInput) -> CropCase:
    try:
        return case_service.set_diagnosis(case_id, request)
    except CaseNotFoundError as error:
        raise _not_found(error) from None
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from None


@router.post("/{case_id}/analyze-image", response_model=CropCase)
async def analyze_case_image(
    case_id: str,
    file: Annotated[UploadFile, File(...)],
    view_type: Annotated[ImageViewType, Form()] = ImageViewType.CLOSE_UP_LEAF,
) -> CropCase:
    try:
        case = case_service.get(case_id)
    except CaseNotFoundError as error:
        raise _not_found(error) from None
    if case.crop.value != "tomato":
        raise HTTPException(status_code=422, detail="Image diagnosis currently supports tomato only.")

    content = await file.read()
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image exceeds the local upload limit.")
    try:
        image = Image.open(io.BytesIO(content))
        image.verify()
        image = Image.open(io.BytesIO(content)).convert("RGB")
    except (UnidentifiedImageError, OSError):
        raise HTTPException(status_code=422, detail="Upload a supported image file.") from None

    try:
        measurements = measure_image(image, view_type.value)
        case_service.add_observations(
            case_id,
            ObservationInput(values=measurements, source="image_measurement"),
        )
        diagnosis = diagnose_image(image, case.crop.value, vision=vision_diagnose(image))
        result = case_service.set_diagnosis(case_id, diagnosis)
        case_service.save_asset(
            case_id,
            file.filename or "case-image",
            content,
            file.content_type or "image/jpeg",
            view_type.value,
            {
                "diagnosis": diagnosis.model_dump(mode="json"),
                "measurements": measurements,
            },
        )
        return result
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from None


@router.post("/{case_id}/confirm-diagnosis", response_model=CropCase)
async def confirm_case_diagnosis(
    case_id: str,
    file: Annotated[UploadFile, File(...)],
    disease: Annotated[str, Form(min_length=2, max_length=160)],
    confirmation_type: Annotated[DiagnosisConfirmationType, Form()],
    organization: Annotated[str, Form(min_length=2, max_length=200)],
    report_reference: Annotated[str, Form(min_length=2, max_length=200)],
    confirmer_name: Annotated[str | None, Form(max_length=160)] = None,
    notes: Annotated[str | None, Form(max_length=1000)] = None,
) -> CropCase:
    try:
        case_service.get(case_id)
    except CaseNotFoundError as error:
        raise _not_found(error) from None

    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail="Attach the Egyptian expert or lab evidence file.")
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Confirmation evidence exceeds the local upload limit.")
    content_type = file.content_type or "application/octet-stream"
    if content_type != "application/pdf" and not content_type.startswith("image/"):
        raise HTTPException(status_code=422, detail="Confirmation evidence must be a PDF or image.")

    request = DiagnosisConfirmationInput(
        disease=disease,
        confirmation_type=confirmation_type,
        organization=organization,
        report_reference=report_reference,
        confirmer_name=confirmer_name,
        notes=notes,
    )
    filename = file.filename or "egyptian-diagnosis-confirmation"
    digest = sha256(content).hexdigest()
    case_service.save_asset(
        case_id,
        filename,
        content,
        content_type,
        "diagnosis_confirmation",
        {
            "confirmation": request.model_dump(mode="json"),
            "evidence_sha256": digest,
            "verification_notice": "Submitted evidence is recorded but not independently authenticated by AgroVision.",
        },
    )
    try:
        return case_service.confirm_diagnosis(case_id, request, filename, digest)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from None


@router.post("/{case_id}/cost-benefit", response_model=CropCase)
def calculate_cost_benefit(case_id: str, request: CostBenefitInput) -> CropCase:
    try:
        return case_service.calculate_economics(case_id, request)
    except CaseNotFoundError as error:
        raise _not_found(error) from None
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from None


@router.post("/{case_id}/recommendation", response_model=CropCase)
def build_recommendation(case_id: str) -> CropCase:
    try:
        return case_service.build_recommendation(case_id)
    except CaseNotFoundError as error:
        raise _not_found(error) from None
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from None


@router.get("/{case_id}/report.json", response_model=SystemOutput)
def report(case_id: str) -> SystemOutput:
    try:
        return case_service.report(case_id)
    except CaseNotFoundError as error:
        raise _not_found(error) from None
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from None


@router.get("/{case_id}/report.csv")
def report_csv(case_id: str) -> Response:
    report_data = report(case_id)
    return Response(
        case_csv(report_data),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="agrovision-case-{case_id}.csv"'},
    )


@router.get("/{case_id}/report.pdf")
def report_pdf(case_id: str) -> Response:
    report_data = report(case_id)
    return Response(
        case_pdf(report_data),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="agrovision-case-{case_id}.pdf"'},
    )
