import io
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from PIL import Image, UnidentifiedImageError

from .api.cases import case_repository, router as cases_router
from .analysis import analyze_image
from .assistant import answer_question
from .config import settings
from .crop_knowledge import tomato_article
from .diseases import disease_info
from .market import current_tomato_market_price
from .model_runtime import disease_runtime
from .persistence import analysis_store
from .reports import analysis_csv, analysis_pdf
from .schemas import AnalysisResponse, AssistantRequest, AssistantResponse, MarketPriceResponse
from .treatment_prices import price_sources_for_treatment
from .vision_llm import vision_diagnose, vision_enabled
from .weather import current_weather, egypt_reference_weather, weather_for_coords

app = FastAPI(title=settings.app_name, version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(cases_router)

analyses: dict[str, AnalysisResponse] = {}


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "mode": "local",
        "disease_runtime": disease_runtime.provider,
        "disease_level": disease_runtime.level,
        "tomato_model": disease_runtime.model_path.name if disease_runtime.session else "deterministic-fallback",
        "vision_second_opinion": settings.external_vision_model if vision_enabled() else "disabled",
        "assistant_mode": "online-grounded" if settings.external_llm_api_key else "offline-bilingual",
        "persistence_mode": analysis_store.mode,
        "case_persistence_mode": case_repository.mode,
        "weather_mode": "egypt-reference-not-live",
    }


@app.get("/api/demo")
def demo_analysis() -> AnalysisResponse:
    image = Image.new("RGB", (640, 420), (55, 135, 62))
    result = analyze_image(image, "seeded-demo-field.png", weather=egypt_reference_weather(), crop="tomato")
    analyses[result.analysis_id] = result
    analysis_store.save_analysis(result)
    return result


@app.post("/api/analyze")
async def analyze(
    file: Annotated[UploadFile, File(...)],
    crop: Annotated[str, Form()] = "tomato",
    lat: Annotated[float | None, Form()] = None,
    lon: Annotated[float | None, Form()] = None,
) -> AnalysisResponse:
    if crop != "tomato":
        raise HTTPException(status_code=422, detail="AgroVision focuses on tomato. Upload a tomato leaf photo.")
    content = await file.read()
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image exceeds the local upload limit.")
    try:
        image = Image.open(io.BytesIO(content))
        image.verify()
        image = Image.open(io.BytesIO(content)).convert("RGB")
    except (UnidentifiedImageError, OSError):
        raise HTTPException(status_code=422, detail="Upload a supported image file.") from None
    if lat is not None and lon is not None:
        weather = weather_for_coords(lat, lon) or egypt_reference_weather()
    else:
        # No GPS: default to live Alexandria, Egypt weather; fall back to the labelled reference.
        weather = current_weather() or egypt_reference_weather()
    vision = vision_diagnose(image)
    result = analyze_image(image, file.filename or "upload", weather=weather, crop=crop, vision=vision)
    analyses[result.analysis_id] = result
    analysis_store.save_analysis(result, content, file.content_type or "image/jpeg")
    return result


@app.get("/api/analyses/{analysis_id}")
def get_analysis(analysis_id: str) -> AnalysisResponse:
    if analysis_id in analyses:
        return analyses[analysis_id]
    persisted = analysis_store.load_analysis(analysis_id)
    if persisted:
        analyses[analysis_id] = persisted
        return persisted
    raise HTTPException(status_code=404, detail="Analysis not found.")


@app.get("/api/analyses")
def list_analyses() -> list[AnalysisResponse]:
    persisted = analysis_store.list_analyses()
    combined = {item.analysis_id: item for item in [*persisted, *analyses.values()]}
    return list(combined.values())[-20:][::-1]


@app.get("/api/knowledge/tomato")
def tomato_knowledge(language: str = "en") -> dict[str, object]:
    return tomato_article("ar" if language == "ar" else "en")


@app.get("/api/market/tomato")
def tomato_market_price() -> MarketPriceResponse:
    return current_tomato_market_price()


@app.get("/api/treatments/tomato/{disease_key}")
def tomato_treatment_catalog(disease_key: str) -> dict[str, object]:
    info = disease_info(disease_key)
    if info.key == "unknown":
        raise HTTPException(status_code=404, detail="No reviewed tomato treatment catalog for this disease.")
    treatments = [
        treatment.model_copy(update={"price_sources": price_sources_for_treatment(treatment)}).model_dump()
        for treatment in info.treatments
    ]
    return {
        "disease_key": info.key,
        "disease_name_en": info.name_en,
        "disease_name_ar": info.name_ar,
        "crop": "tomato",
        "treatments": treatments,
        "availability": {
            "status_en": "Verify current Egyptian registration in APC, then confirm stock with a local pesticide dealer or agricultural association.",
            "status_ar": "أكّد التسجيل المصري الحالي في لجنة المبيدات، وبعدها أكّد التوفر من محل مبيدات أو جمعية زراعية محلية.",
            "apc_url": "https://www1.apc.gov.eg/en/search.aspx",
            "price_status_en": "No official live Egyptian pesticide retail-price API was found. Each product card now shows online retail/dealer price checks when a source can be read; treat them as market signals, not official prices.",
            "price_status_ar": "لا يوجد API رسمي موثوق لأسعار المبيدات لحظيًا في مصر. كل كارت منتج يعرض فحص أسعار أونلاين من تجار/أسواق عند قراءة المصدر؛ اعتبرها مؤشرات سوق وليست أسعار رسمية.",
        },
        "prevention": {
            "en": [
                "Start with certified clean seedlings and avoid moving soil/tools from infected fields.",
                "Scout twice weekly: lower leaves, underside of leaves, field edges, wet spots, and greenhouse corners.",
                "Keep foliage dry: drip irrigation, morning watering, wider spacing, pruning, and good ventilation.",
                "Remove infected leaf debris; never leave diseased leaves under plants.",
                "After rain, fog, or high humidity, tighten scouting and use only registered preventive products if an agronomist confirms risk.",
                "Rotate FRAC groups; never repeat one systemic group back-to-back.",
            ],
            "ar": [
                "ابدأ بشتلات نظيفة معتمدة وتجنب نقل تربة أو أدوات من أرض مصابة.",
                "اكشف مرتين في الأسبوع: الورق السفلي، ظهر الورق، حواف الحقل، الأماكن المبللة، وأركان الصوبة.",
                "خلّي الورق ناشف: ري تنقيط، ري الصبح، مسافات أوسع، تقليم وتهوية كويسة.",
                "شيل مخلفات الورق المصاب؛ ما تسيبش ورق مريض تحت النبات.",
                "بعد المطر أو الشبورة أو الرطوبة العالية، زوّد الكشف ولا تستخدم وقائي كيميائي إلا لو مهندس أكد الخطر والتسجيل.",
                "بدّل مجموعات FRAC؛ ما تكررش نفس المجموعة الجهازية ورا بعض.",
            ],
        },
    }


@app.post("/api/assistant")
def assistant(request: AssistantRequest) -> AssistantResponse:
    analysis = None
    if request.analysis_id:
        analysis = analyses.get(request.analysis_id) or analysis_store.load_analysis(request.analysis_id)
        if analysis:
            analyses[analysis.analysis_id] = analysis
    return answer_question(request.question, analysis, request.language, request.case_context)


@app.get("/api/reports/{analysis_id}.csv")
def csv_report(analysis_id: str) -> Response:
    analysis = get_analysis(analysis_id)
    content = analysis_csv(analysis)
    analysis_store.save_report(analysis_id, "csv", content, "text/csv")
    return Response(
        content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{analysis_id}.csv"'},
    )


@app.get("/api/reports/{analysis_id}.pdf")
def pdf_report(analysis_id: str) -> Response:
    analysis = get_analysis(analysis_id)
    content = analysis_pdf(analysis)
    analysis_store.save_report(analysis_id, "pdf", content, "application/pdf")
    return Response(
        content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{analysis_id}.pdf"'},
    )
