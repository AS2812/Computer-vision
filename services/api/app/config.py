from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    app_name: str = "AgroVision Local API"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    cors_origin_regex: str | None = r"https?://(localhost|127\.0\.0\.1):51[0-9]{2}"
    max_upload_mb: int = 40
    tile_size: int = 512
    max_tile_workers: int = 2
    disease_confidence_threshold: float = 0.65
    disease_min_margin: float = 0.15
    disease_min_crop_probability_mass: float = 0.60
    disease_min_leaf_coverage: float = 0.04
    # Test-time augmentation: average the local ONNX model over a few deterministic
    # views (center + flip + tighter crop) for steadier real-field-photo predictions.
    disease_tta: bool = True
    # Honest confidence calibration. Temperature scaling is applied to the raw
    # logits; 1.0 is the identity (reported as "uncalibrated"). A real validation
    # set fitted by ml/training/evaluate_tomato.py writes the sidecar below and
    # flips calibration on. Never hand-tune these to inflate displayed confidence.
    disease_temperature: float = 1.0
    disease_calibration_path: Path = ROOT / "ml/models/plant_disease_mobilenetv2.calibration.json"
    # Confusion-group ("spot complex") rescue: when a Target-Spot-like top-1 splits
    # its score with its look-alikes, the COMBINED group mass must clear this bar
    # and beat everything outside the group by this margin to earn a "probable"
    # (medium) verdict instead of being dropped as "no reliable diagnosis".
    disease_group_mass_threshold: float = 0.55
    disease_group_margin_min: float = 0.08
    # Real hosted vision second opinion. The chat assistant model (deepseek) is
    # text-only and rejects images, so vision uses its own multimodal model on the
    # same OpenAI-compatible gateway / key. mimo-v2.5-free is reachable on the free tier.
    external_vision_enabled: bool = True
    external_vision_model: str = "mimo-v2.5-free"
    external_vision_timeout_seconds: float = 45.0
    external_vision_max_side_px: int = 1024
    # mimo is a reasoning model: it spends hidden reasoning tokens before the visible
    # JSON answer, so the budget must be generous or content comes back empty.
    external_vision_max_tokens: int = 2000
    disease_model_path: Path = ROOT / "ml/models/plant_disease_mobilenetv2.onnx"
    banana_disease_model_path: Path = ROOT / "ml/models/banana_cordana_vgg19_int8.onnx"
    model_manifest_path: Path = ROOT / "ml/models/manifest.json"
    weather_enabled: bool = True
    weather_latitude: float = 31.2001
    weather_longitude: float = 29.9187
    weather_timeout_seconds: float = 4.0
    supabase_url: str | None = None
    supabase_service_role_key: str | None = None
    supabase_demo_email: str = "demo@agrovision.local"
    supabase_demo_password: str = "agrovision-local-demo"
    supabase_timeout_seconds: float = 4.0
    external_llm_api_key: str | None = None
    external_llm_api_url: str | None = None
    external_llm_model: str = "deepseek-v4-flash-free"
    external_llm_timeout_seconds: float = 90.0
    # Budget covers hidden reasoning tokens plus the visible answer. Reasoning models
    # can spend a lot before answering, so keep this generous. The assistant also
    # retries with a larger budget if the first response comes back empty.
    external_llm_max_tokens: int = 2000
    # "low" keeps hidden reasoning small enough for the visible answer to fit.
    external_llm_reasoning_effort: str = "low"
    external_llm_temperature: float = 0.3

    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")


settings = Settings()
