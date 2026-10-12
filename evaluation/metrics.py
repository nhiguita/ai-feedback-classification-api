"""Pure metric functions for comparing predicted labels with gold labels."""

from collections import Counter
from dataclasses import dataclass

FIELDS = ("sentiment", "intent", "category", "priority")


@dataclass(frozen=True)
class LabelScore:
    label: str
    precision: float
    recall: float
    f1: float
    support: int


def accuracy(gold: list[str], pred: list[str]) -> float:
    _check_lengths(gold, pred)
    if not gold:
        return 0.0
    return sum(g == p for g, p in zip(gold, pred)) / len(gold)


def per_label_scores(gold: list[str], pred: list[str], labels: list[str]) -> list[LabelScore]:
    _check_lengths(gold, pred)
    scores = []
    for label in labels:
        tp = sum(g == label and p == label for g, p in zip(gold, pred))
        predicted = sum(p == label for p in pred)
        support = sum(g == label for g in gold)
        precision = tp / predicted if predicted else 0.0
        recall = tp / support if support else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        scores.append(LabelScore(label, precision, recall, f1, support))
    return scores


def macro_f1(scores: list[LabelScore]) -> float:
    # Only labels present in the gold set count, so unused labels do not drag the average to zero.
    present = [s.f1 for s in scores if s.support]
    return sum(present) / len(present) if present else 0.0


def confusion_matrix(gold: list[str], pred: list[str], labels: list[str]) -> dict[str, dict[str, int]]:
    """Rows are gold labels, columns are predicted labels."""
    _check_lengths(gold, pred)
    counts = Counter(zip(gold, pred))
    return {g: {p: counts[(g, p)] for p in labels} for g in labels}


def exact_match(gold_rows: list[dict[str, str]], pred_rows: list[dict[str, str]]) -> float:
    """Share of items where all four fields are correct."""
    _check_lengths(gold_rows, pred_rows)
    if not gold_rows:
        return 0.0
    hits = sum(all(g[f] == p[f] for f in FIELDS) for g, p in zip(gold_rows, pred_rows))
    return hits / len(gold_rows)


def _check_lengths(gold: list, pred: list) -> None:
    if len(gold) != len(pred):
        raise ValueError(f"gold and pred lengths differ: {len(gold)} != {len(pred)}")
