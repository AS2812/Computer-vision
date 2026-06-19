from __future__ import annotations

from dataclasses import dataclass

from app.contracts.cases import CropCase


@dataclass(frozen=True)
class Question:
    key: str
    text: str


QUESTIONS = (
    Question("affected_part", "Which part is affected: lower leaves, upper leaves, stem, roots, or fruit?"),
    Question("symptom_origin", "Where did the symptoms start on the plant?"),
    Question("spread_speed", "Is the problem spreading slowly, moderately, or quickly?"),
    Question("affected_plants_percent", "About how many plants out of every 100 show the same symptoms?"),
    Question("irrigation_method", "Do you use flood, drip, sprinkler, canal water, or another irrigation method?"),
    Question("recent_weather", "Was the recent weather unusually hot, humid, rainy, dusty, or windy?"),
    Question("previous_treatment", "What spray or fertilizer was used recently, and at what dose?"),
    Question("nearby_crop_symptoms", "Do nearby plants or crops show the same symptoms?"),
    Question("harvest_days_remaining", "About how many days remain before harvest?"),
    Question("extra_photos", "Please add a close leaf photo, leaf underside photo, and whole-plant photo."),
)


def next_questions(case: CropCase, limit: int = 3) -> list[Question]:
    bounded_limit = max(1, min(limit, 5))
    unavailable = set(case.asked_question_keys) | set(case.observations)
    return [question for question in QUESTIONS if question.key not in unavailable][:bounded_limit]
