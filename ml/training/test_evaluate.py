from evaluate import Evaluation, passes_release_gate


def test_release_gate_rejects_weak_model():
    assert not passes_release_gate(Evaluation(0.89, 0.9, 0.01, 0.5, 1000))


def test_release_gate_accepts_model_meeting_every_limit():
    assert passes_release_gate(Evaluation(0.92, 0.84, 0.01, 0.8, 1200))

