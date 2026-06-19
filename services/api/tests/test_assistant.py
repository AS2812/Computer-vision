import httpx

from app import assistant, diseases
from app.config import settings
from app.schemas import AnalysisResponse, FeatureResult, LocalizedText, ValidationLevel


def make_analysis(crop: str = "banana") -> AnalysisResponse:
    disease = FeatureResult(
        feature="disease",
        title="Disease detection",
        title_ar="كشف الأمراض",
        level=ValidationLevel.EXPERIMENTAL,
        score=0.8,
        value="Cordana leaf spot",
        value_ar="تبقّع كوردانا",
        confidence=0.8,
        evidence=[],
        disease_info=diseases.disease_info("cordana_leaf_spot"),
    )
    return AnalysisResponse(
        analysis_id="test-analysis",
        filename="field.png",
        crop=crop,
        width=10,
        height=10,
        processing_ms=5,
        peak_memory_mb=10.0,
        provider="test-runtime",
        results=[disease],
        # Bilingual alerts must not break the external grounding builder.
        alerts=[LocalizedText(en="Leaf yellowing detected.", ar="رُصد اصفرار في الأوراق.")],
        recommendations=[LocalizedText(en="Inspect the field.", ar="افحص الحقل.")],
    )


def _ok_response(url, content):
    return httpx.Response(
        200,
        json={"choices": [{"message": {"content": content}, "finish_reason": "stop"}]},
        request=httpx.Request("POST", url),
    )


def test_external_assistant_returns_grounded_answer(monkeypatch):
    captured = {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured["payload"] = kwargs["json"]
        return _ok_response(url, "Cordana leaf spot is a minor fungal banana disease.")

    monkeypatch.setattr(settings, "external_llm_api_key", "test-key")
    monkeypatch.setattr(settings, "external_llm_api_url", "https://opencode.ai/zen/v1/chat/completions")
    monkeypatch.setattr(assistant.httpx, "post", fake_post)

    result = assistant.answer_question("What is this disease?", make_analysis(), "en")

    assert result.mode == "external-grounded-assistant"
    assert "Cordana" in result.answer
    assert captured["url"] == "https://opencode.ai/zen/v1/chat/completions"
    assert captured["payload"]["model"] == "deepseek-v4-flash-free"
    assert captured["payload"]["reasoning_effort"] == "low"
    assert captured["payload"]["messages"][0]["content"] == assistant.SYSTEM_PROMPTS["en"]
    assert "DETECTED CONDITION" in captured["payload"]["messages"][1]["content"]
    # The bilingual alert must be rendered as its English string, not an object repr.
    assert "Leaf yellowing detected." in captured["payload"]["messages"][1]["content"]


def test_external_uses_arabic_system_prompt_when_arabic(monkeypatch):
    captured = {}

    def fake_post(url, **kwargs):
        captured["payload"] = kwargs["json"]
        return _ok_response(url, "تبقّع كوردانا مرض فطري بسيط.")

    monkeypatch.setattr(settings, "external_llm_api_key", "test-key")
    monkeypatch.setattr(settings, "external_llm_api_url", "https://x")
    monkeypatch.setattr(assistant.httpx, "post", fake_post)

    result = assistant.answer_question("ما هذا المرض؟", make_analysis(), "ar")

    assert result.mode == "external-grounded-assistant"
    assert captured["payload"]["messages"][0]["content"] == assistant.SYSTEM_PROMPTS["ar"]
    assert "المرض المكتشف" in captured["payload"]["messages"][1]["content"]
    assert "رُصد اصفرار في الأوراق." in captured["payload"]["messages"][1]["content"]


def test_empty_external_content_falls_back_offline(monkeypatch):
    def fake_post(url, **kwargs):
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "", "reasoning_content": "..."}, "finish_reason": "length"}]},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(settings, "external_llm_api_key", "test-key")
    monkeypatch.setattr(settings, "external_llm_api_url", "https://x")
    monkeypatch.setattr(assistant.httpx, "post", fake_post)

    result = assistant.answer_question("What is this disease?", make_analysis(), "en")

    assert result.mode == "grounded-case-answer"
    assert "Cordana leaf spot" in result.answer


def test_external_retries_with_lean_prompt_when_first_response_empty(monkeypatch):
    calls = {"n": 0}

    def fake_post(url, **kwargs):
        calls["n"] += 1
        content = "" if calls["n"] == 1 else "Cordana leaf spot is a minor fungal disease."
        return _ok_response(url, content)

    monkeypatch.setattr(settings, "external_llm_api_key", "test-key")
    monkeypatch.setattr(settings, "external_llm_api_url", "https://x")
    monkeypatch.setattr(assistant.httpx, "post", fake_post)

    result = assistant.answer_question("What is this disease?", make_analysis(), "en")

    assert calls["n"] == 2
    assert result.mode == "external-grounded-assistant"
    assert "Cordana" in result.answer


def test_external_failure_falls_back_offline_in_arabic(monkeypatch):
    def fail(*args, **kwargs):
        raise httpx.ConnectError("offline")

    monkeypatch.setattr(settings, "external_llm_api_key", "test-key")
    monkeypatch.setattr(settings, "external_llm_api_url", "https://x")
    monkeypatch.setattr(assistant.httpx, "post", fail)

    result = assistant.answer_question("ما هذا المرض؟", make_analysis(), "ar")

    assert result.mode == "grounded-case-answer"
    assert "كوردانا" in result.answer


def test_language_autodetect_from_arabic_question(monkeypatch):
    monkeypatch.setattr(settings, "external_llm_api_key", None)

    result = assistant.answer_question("كيف أقرأ النتيجة؟", make_analysis(), None)

    assert result.mode == "grounded-case-answer"
    assert any("؀" <= ch <= "ۿ" for ch in result.answer)


def test_offline_water_question_answers_in_english(monkeypatch):
    monkeypatch.setattr(settings, "external_llm_api_key", None)

    result = assistant.answer_question("How is the water stress here?", make_analysis(), "en")

    assert result.mode == "grounded-case-answer"
    assert "irrigation" in result.answer.lower()
    assert "Banana irrigation scheme" in result.answer


def test_offline_treatment_question_returns_products_for_detected_case(monkeypatch):
    monkeypatch.setattr(settings, "external_llm_api_key", None)

    result = assistant.answer_question("Give me the treatment plan", make_analysis(), "en")

    assert "TREATMENT PROGRAM" in result.answer
    assert "Mancozeb" in result.answer
    assert "Dose:" in result.answer


def test_offline_tomato_varieties_are_useful_without_analysis(monkeypatch):
    monkeypatch.setattr(settings, "external_llm_api_key", None)

    result = assistant.answer_question("List resistant tomato varieties", None, "en")

    assert result.mode == "grounded-case-answer"
    assert "Iron Lady" in result.answer
    assert "Mountain Merit F1" in result.answer
    assert any(source.startswith("https://") for source in result.sources)


def test_offline_greenhouse_answer_explains_both_risk_directions(monkeypatch):
    monkeypatch.setattr(settings, "external_llm_api_key", None)

    result = assistant.answer_question("Will a greenhouse reduce tomato infection?", None, "en")

    assert "lower some tomato disease risk" in result.answer
    assert "Poor ventilation" in result.answer
    assert "does not guarantee" in result.answer


def test_online_general_tomato_question_uses_grounding_without_analysis(monkeypatch):
    captured = {}

    def fake_post(url, **kwargs):
        captured["payload"] = kwargs["json"]
        return _ok_response(url, "Use a resistant variety and manage greenhouse humidity.")

    monkeypatch.setattr(settings, "external_llm_api_key", "test-key")
    monkeypatch.setattr(settings, "external_llm_api_url", "https://x")
    monkeypatch.setattr(assistant.httpx, "post", fake_post)

    result = assistant.answer_question("Does a greenhouse reduce tomato infection risk?", None, "en")

    assert result.mode == "external-grounded-assistant"
    assert "Poor ventilation" in captured["payload"]["messages"][1]["content"]
    assert any(source.startswith("https://") for source in result.sources)


def test_online_named_tomato_disease_without_analysis_gets_treatment_program(monkeypatch):
    captured = {}

    def fake_post(url, **kwargs):
        captured["payload"] = kwargs["json"]
        return _ok_response(url, "Use the reviewed late blight treatment program and confirm labels.")

    monkeypatch.setattr(settings, "external_llm_api_key", "test-key")
    monkeypatch.setattr(settings, "external_llm_api_url", "https://x")
    monkeypatch.setattr(assistant.httpx, "post", fake_post)
    monkeypatch.setattr(assistant, "price_sources_for_treatment", lambda treatment: [])

    result = assistant.answer_question("Give tomato_late_blight products doses and prices", None, "en")

    prompt = captured["payload"]["messages"][1]["content"]
    assert result.mode == "external-grounded-assistant"
    assert "TREATMENT PROGRAM" in prompt
    assert "Mandipropamid" in prompt
    assert "Dose:" in prompt
