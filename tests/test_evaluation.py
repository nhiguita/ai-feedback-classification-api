from unittest.mock import patch

import pytest

from app.llm.errors import LLMTimeoutError
from app.schemas import Category, FeedbackClassification, Intent, Priority, Sentiment
from evaluation.metrics import accuracy, confusion_matrix, exact_match, macro_f1, per_label_scores
from evaluation.run_eval import DATASET, LABELS, compute_metrics, load_dataset, render_report, run_predictions

GOLD = ["a", "a", "b", "c"]
PRED = ["a", "b", "b", "b"]


def test_accuracy():
    assert accuracy(GOLD, PRED) == 0.5
    assert accuracy([], []) == 0.0


def test_metrics_reject_length_mismatch():
    with pytest.raises(ValueError):
        accuracy(["a"], [])


def test_per_label_scores():
    scores = {s.label: s for s in per_label_scores(GOLD, PRED, ["a", "b", "c"])}
    assert scores["a"].precision == 1.0 and scores["a"].recall == 0.5
    assert scores["b"].precision == pytest.approx(1 / 3) and scores["b"].recall == 1.0
    assert scores["b"].f1 == pytest.approx(0.5)
    assert scores["c"].f1 == 0.0 and scores["c"].support == 1


def test_macro_f1_ignores_labels_without_support():
    scores = per_label_scores(["a", "a"], ["a", "a"], ["a", "unused"])
    assert macro_f1(scores) == 1.0


def test_confusion_matrix():
    matrix = confusion_matrix(GOLD, PRED, ["a", "b", "c"])
    assert matrix["a"] == {"a": 1, "b": 1, "c": 0}
    assert matrix["c"] == {"a": 0, "b": 1, "c": 0}


def test_exact_match():
    gold = [dict(sentiment="x", intent="y", category="z", priority="w")] * 2
    pred = [gold[0], {**gold[0], "priority": "other"}]
    assert exact_match(gold, pred) == 0.5


def test_dataset_is_valid_and_covers_every_label():
    rows = load_dataset(DATASET)
    assert len({r["id"] for r in rows}) == len(rows)
    for row in rows:
        FeedbackClassification.model_validate({k: v for k, v in row.items() if k not in ("id", "text")})
    for field, labels in LABELS.items():
        assert {r[field] for r in rows} == set(labels), f"{field} does not cover every label"


def test_dataset_does_not_reuse_few_shot_examples():
    from app.prompts import FEW_SHOT_EXAMPLES

    few_shot_texts = {text for text, _ in FEW_SHOT_EXAMPLES}
    assert not few_shot_texts & {r["text"] for r in load_dataset(DATASET)}


def test_run_predictions_and_report_with_mocked_classifier():
    rows = load_dataset(DATASET)[:2]
    correct = FeedbackClassification(**{k: rows[0][k] for k in ("sentiment", "intent", "category", "priority")})
    with patch("evaluation.run_eval.classify_feedback", side_effect=[correct, LLMTimeoutError("slow")]):
        predictions = run_predictions(rows)

    assert predictions[0]["error"] is None
    assert predictions[1]["prediction"] is None and "LLMTimeoutError" in predictions[1]["error"]

    metrics = compute_metrics(rows, predictions)
    assert metrics["errors"] == 1
    assert metrics["exact_match"] == 0.5

    report = render_report(metrics, rows, predictions, "qwen3:4b")
    assert "| sentiment | 50.0% |" in report
    assert rows[1]["id"] in report  # Failed item is listed under misclassified.


def test_labels_match_schema_enums():
    assert LABELS["sentiment"] == [s.value for s in Sentiment]
    assert LABELS["intent"] == [i.value for i in Intent]
    assert LABELS["category"] == [c.value for c in Category]
    assert LABELS["priority"] == [p.value for p in Priority]
