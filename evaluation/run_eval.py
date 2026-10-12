"""Evaluate the classifier against the labeled dataset using the real LLM.

Usage:
    .venv/bin/python -m evaluation.run_eval --split dev
    .venv/bin/python -m evaluation.run_eval --split test

Tune the prompt on the dev split only; run the test split once per prompt version.
Requires Ollama running with the configured model (see .env.example).
Writes evaluation/results/<prompt version>-<split>.json and docs/evaluation/<prompt version>-<split>.md.
"""

import argparse
import json
import statistics
import time
from datetime import date
from pathlib import Path

from app.config import get_settings
from app.llm.errors import LLMError
from app.prompts import PROMPT_VERSION
from app.schemas import Category, Intent, Priority, Sentiment
from app.services.classifier import classify_feedback
from evaluation.metrics import FIELDS, accuracy, confusion_matrix, exact_match, macro_f1, per_label_scores

ROOT = Path(__file__).resolve().parent.parent
DATASET = ROOT / "evaluation" / "data" / "feedback_labeled.jsonl"
RESULTS_DIR = ROOT / "evaluation" / "results"
REPORTS_DIR = ROOT / "docs" / "evaluation"
SPLITS = ("dev", "test", "all")

LABELS = {
    "sentiment": [s.value for s in Sentiment],
    "intent": [i.value for i in Intent],
    "category": [c.value for c in Category],
    "priority": [p.value for p in Priority],
}


def load_dataset(path: Path, split: str = "all") -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]
    return rows if split == "all" else [r for r in rows if r["split"] == split]


def run_predictions(rows: list[dict[str, str]]) -> list[dict]:
    predictions = []
    for i, row in enumerate(rows, start=1):
        start = time.perf_counter()
        try:
            pred = classify_feedback(row["text"]).model_dump(mode="json")
            error = None
        except LLMError as exc:
            pred, error = None, f"{type(exc).__name__}: {exc}"
        elapsed = time.perf_counter() - start
        predictions.append({"id": row["id"], "prediction": pred, "error": error, "seconds": round(elapsed, 2)})
        status = "ERROR" if error else "ok"
        print(f"[{i}/{len(rows)}] {row['id']} {status} {elapsed:.1f}s")
    return predictions


def compute_metrics(rows: list[dict[str, str]], predictions: list[dict]) -> dict:
    # Failed calls count as wrong answers so errors are visible in the scores.
    pred_rows = [p["prediction"] or {f: "<error>" for f in FIELDS} for p in predictions]
    fields = {}
    for field in FIELDS:
        gold = [r[field] for r in rows]
        pred = [p[field] for p in pred_rows]
        scores = per_label_scores(gold, pred, LABELS[field])
        fields[field] = {
            "accuracy": accuracy(gold, pred),
            "macro_f1": macro_f1(scores),
            "per_label": [s.__dict__ for s in scores],
            "confusion": confusion_matrix(gold, pred, LABELS[field]),
        }
    seconds = [p["seconds"] for p in predictions]
    return {
        "n": len(rows),
        "errors": sum(p["error"] is not None for p in predictions),
        "exact_match": exact_match(rows, pred_rows),
        "fields": fields,
        "latency": {
            "median_seconds": statistics.median(seconds),
            "max_seconds": max(seconds),
            "total_seconds": round(sum(seconds), 1),
        },
    }


def render_report(metrics: dict, rows: list[dict[str, str]], predictions: list[dict], model: str, split: str) -> str:
    lines = [
        f"# Evaluation — prompt {PROMPT_VERSION}, {split} split",
        "",
        f"- Date: {date.today().isoformat()}",
        f"- Model: `{model}` via Ollama (temperature 0, thinking disabled)",
        f"- Dataset: `evaluation/data/feedback_labeled.jsonl`, split `{split}` ({metrics['n']} fictitious, hand-labeled comments)",
        f"- LLM errors: {metrics['errors']}",
        f"- Latency: median {metrics['latency']['median_seconds']:.2f}s, max {metrics['latency']['max_seconds']:.2f}s",
        "",
        f"Reproduce with `.venv/bin/python -m evaluation.run_eval --split {split}`.",
        "",
        "## Summary",
        "",
        "| Field | Accuracy | Macro F1 |",
        "| --- | --- | --- |",
    ]
    for field in FIELDS:
        m = metrics["fields"][field]
        lines.append(f"| {field} | {m['accuracy']:.1%} | {m['macro_f1']:.2f} |")
    lines.append(f"| **all four fields (exact match)** | **{metrics['exact_match']:.1%}** | — |")

    for field in FIELDS:
        m = metrics["fields"][field]
        labels = LABELS[field]
        lines += ["", f"## {field}", "", "| Label | Precision | Recall | F1 | Support |", "| --- | --- | --- | --- | --- |"]
        for s in m["per_label"]:
            lines.append(f"| {s['label']} | {s['precision']:.2f} | {s['recall']:.2f} | {s['f1']:.2f} | {s['support']} |")
        lines += ["", "Confusion matrix (rows = expected, columns = predicted):", ""]
        lines.append("| | " + " | ".join(labels) + " |")
        lines.append("| --- " * (len(labels) + 1) + "|")
        for gold_label in labels:
            cells = [str(m["confusion"][gold_label][p]) for p in labels]
            lines.append(f"| **{gold_label}** | " + " | ".join(cells) + " |")

    lines += ["", "## Misclassified items", "", "| ID | Text | Field | Expected | Predicted |", "| --- | --- | --- | --- | --- |"]
    for row, pred in zip(rows, predictions):
        p = pred["prediction"]
        if p is None:
            lines.append(f"| {row['id']} | {row['text']} | all | — | {pred['error']} |")
            continue
        for field in FIELDS:
            if p[field] != row[field]:
                lines.append(f"| {row['id']} | {row['text']} | {field} | {row[field]} | {p[field]} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--split", choices=SPLITS, required=True, help="Dataset split to evaluate.")
    parser.add_argument("--limit", type=int, help="Evaluate only the first N items.")
    args = parser.parse_args()

    rows = load_dataset(DATASET, args.split)[: args.limit]
    predictions = run_predictions(rows)
    metrics = compute_metrics(rows, predictions)
    model = get_settings().ollama_model

    name = f"{PROMPT_VERSION}-{args.split}"
    results_path, report_path = RESULTS_DIR / f"{name}.json", REPORTS_DIR / f"{name}.md"
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"model": model, "prompt_version": PROMPT_VERSION, "split": args.split, "metrics": metrics}
    results_path.write_text(json.dumps({**payload, "predictions": predictions}, indent=2), encoding="utf-8")
    report_path.write_text(render_report(metrics, rows, predictions, model, args.split), encoding="utf-8")

    print(f"\nExact match: {metrics['exact_match']:.1%}")
    for field in FIELDS:
        print(f"{field:>10}: {metrics['fields'][field]['accuracy']:.1%}")
    print(f"Report: {report_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
