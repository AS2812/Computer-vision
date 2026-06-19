from __future__ import annotations

from app.contracts.cases import CaseStatus


_TRANSITIONS: dict[CaseStatus, set[CaseStatus]] = {
    CaseStatus.DRAFT: {CaseStatus.COLLECTING_EVIDENCE, CaseStatus.FAILED},
    CaseStatus.COLLECTING_EVIDENCE: {
        CaseStatus.DIAGNOSIS_READY,
        CaseStatus.CONSULTING,
        CaseStatus.NEEDS_EXPERT,
        CaseStatus.FAILED,
    },
    CaseStatus.DIAGNOSIS_READY: {
        CaseStatus.CONSULTING,
        CaseStatus.PROTECTION_READY,
        CaseStatus.NEEDS_EXPERT,
        CaseStatus.FAILED,
    },
    CaseStatus.CONSULTING: {
        CaseStatus.DIAGNOSIS_READY,
        CaseStatus.PROTECTION_READY,
        CaseStatus.NEEDS_EXPERT,
        CaseStatus.FAILED,
    },
    CaseStatus.PROTECTION_READY: {
        CaseStatus.TREATMENT_READY,
        CaseStatus.ECONOMICS_READY,
        CaseStatus.NEEDS_EXPERT,
        CaseStatus.FAILED,
    },
    CaseStatus.TREATMENT_READY: {
        CaseStatus.ECONOMICS_READY,
        CaseStatus.PREDICTION_READY,
        CaseStatus.RECOMMENDATION_READY,
        CaseStatus.NEEDS_EXPERT,
        CaseStatus.FAILED,
    },
    CaseStatus.ECONOMICS_READY: {
        CaseStatus.PREDICTION_READY,
        CaseStatus.RECOMMENDATION_READY,
        CaseStatus.NEEDS_EXPERT,
        CaseStatus.FAILED,
    },
    CaseStatus.PREDICTION_READY: {
        CaseStatus.RECOMMENDATION_READY,
        CaseStatus.NEEDS_EXPERT,
        CaseStatus.FAILED,
    },
    CaseStatus.RECOMMENDATION_READY: {CaseStatus.REPORT_READY, CaseStatus.NEEDS_EXPERT, CaseStatus.FAILED},
    CaseStatus.REPORT_READY: {CaseStatus.CLOSED, CaseStatus.NEEDS_EXPERT, CaseStatus.FAILED},
    CaseStatus.NEEDS_EXPERT: {CaseStatus.COLLECTING_EVIDENCE, CaseStatus.CLOSED, CaseStatus.FAILED},
    CaseStatus.CLOSED: set(),
    CaseStatus.FAILED: {CaseStatus.COLLECTING_EVIDENCE},
}


def can_transition(current: CaseStatus, target: CaseStatus) -> bool:
    return current == target or target in _TRANSITIONS[current]


def require_transition(current: CaseStatus, target: CaseStatus) -> None:
    if not can_transition(current, target):
        raise ValueError(f"Invalid case status transition: {current} -> {target}")
