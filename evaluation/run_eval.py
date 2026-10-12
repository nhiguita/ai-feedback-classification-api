"""Evaluate the classifier against the labeled dataset using the real LLM.

Usage:
    .venv/bin/python -m evaluation.run_eval --dataset dev
    .venv/bin/python -m evaluation.run_eval --dataset holdout --variant v1

Variants:
    v1, v2  Frozen prompts (evaluation/baselines/) where the LLM chooses the priority.
    v3      Current app: the LLM extracts facts and app/priority/rules.py computes the priority.

Datasets:
    dev  All comments used while developing prompts v1/v2 (including the former "test" split,
         which was used to compare v1 and v2 and is therefore no longer held out).
    holdout  Labeled following docs/ANNOTATION_GUIDELINES.md before the facts + rules approach was
             written. Report-only: never use its results to adjust prompts or rules.

Requires Ollama running with the configured model (see .env.example).
Writes evaluation/results/<variant>-<dataset>.json and docs/evaluation/<variant>-<dataset>.md.
"""

import argparse
import json
import statistics
import time
from datetime import date
from pathlib import Path

from collections.abc import Callable

from app.config import get_settings
from app.llm.errors import LLMError
from app.llm.factory import get_llm_client
from app.priority.rules import decide_priority
from app.prompts import PROMPT_VERSION
from app.schemas import Category, FeedbackClassification, Intent, Priority, Sentiment
from app.services.classifier import analyze_feedback, request_validated
from evaluation.baselines import prompt_v1, prompt_v2
from evaluation.metrics import FIELDS, accuracy, confusion_matrix, exact_match, macro_f1, per_label_scores

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "evaluation" / "data"
DATASETS = {"dev": DATA_DIR / "feedback_dev.jsonl", "holdout": DATA_DIR / "feedback_holdout.jsonl"}
RESULTS_DIR = ROOT / "evaluation" / "results"
REPORTS_DIR = ROOT / "docs" / "evaluation"

LABELS = {
    "sentiment": [s.value for s in Sentiment],
    "intent": [i.value for i in Intent],
    "category": [c.value for c in Category],
    "priority": [p.value for p in Priority],
}


Predictor = Callable[[str], dict]


def baseline_predictor(build_messages: Callable[[str], list[dict[str, str]]]) -> Predictor:
    def predict(text: str) -> dict:
        result = request_validated(get_llm_client(), build_messages(text), FeedbackClassification)
        return {"prediction": result.model_dump(mode="json")}

    return predict


def current_predictor(text: str) -> dict:
    # Same steps as classify_feedback, keeping the facts so errors can be traced to a fact or a rule.
    analysis = analyze_feedback(text)
    decision = decide_priority(analysis.facts)
    labels = analysis.model_dump(mode="json", exclude={"facts"})
    return {
        "prediction": labels | {"priority": decision.priority.value},
        "facts": analysis.facts.model_dump(),
        "priority_reasons": list(decision.reasons),
    }


VARIANTS: dict[str, Predictor] = {
    "v1": baseline_predictor(prompt_v1.build_messages),
    "v2": baseline_predictor(prompt_v2.build_messages),
    PROMPT_VERSION: current_predictor,
}


def load_dataset(name: str) -> list[dict[str, str]]:
    with DATASETS[name].open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def run_predictions(rows: list[dict[str, str]], predict: Predictor) -> list[dict]:
    predictions = []
    for i, row in enumerate(rows, start=1):
        start = time.perf_counter()
        try:
            output, error = predict(row["text"]), None
        except LLMError as exc:
            output, error = {"prediction": None}, f"{type(exc).__name__}: {exc}"
        elapsed = time.perf_counter() - start
        predictions.append({"id": row["id"], **output, "error": error, "seconds": round(elapsed, 2)})
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


def render_report(
    metrics: dict, rows: list[dict[str, str]], predictions: list[dict], model: str, dataset: str, variant: str
) -> str:
    lines = [
        f"# Evaluation — {variant}, {dataset} dataset",
        "",
        f"- Date: {date.today().isoformat()}",
        f"- Model: `{model}` via Ollama (temperature 0, thinking disabled)",
        f"- Dataset: `{DATASETS[dataset].relative_to(ROOT)}` ({metrics['n']} fictitious, hand-labeled comments)",
        f"- LLM errors: {metrics['errors']}",
        f"- Latency: median {metrics['latency']['median_seconds']:.2f}s, max {metrics['latency']['max_seconds']:.2f}s",
        "",
        f"Reproduce with `.venv/bin/python -m evaluation.run_eval --dataset {dataset} --variant {variant}`.",
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

    lines += [
        "",
        "## Misclassified items",
        "",
        "| ID | Text | Field | Expected | Predicted | Priority facts |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row, pred in zip(rows, predictions):
        p = pred["prediction"]
        if p is None:
            lines.append(f"| {row['id']} | {row['text']} | all | — | {pred['error']} | |")
            continue
        for field in FIELDS:
            if p[field] != row[field]:
                reasons = ", ".join(pred.get("priority_reasons", [])) or "—" if field == "priority" else ""
                lines.append(f"| {row['id']} | {row['text']} | {field} | {row[field]} | {p[field]} | {reasons} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dataset", choices=DATASETS, required=True, help="Dataset to evaluate.")
    parser.add_argument("--variant", choices=VARIANTS, default=PROMPT_VERSION, help="Classifier variant.")
    parser.add_argument("--limit", type=int, help="Evaluate only the first N items.")
    args = parser.parse_args()

    rows = load_dataset(args.dataset)[: args.limit]
    predictions = run_predictions(rows, VARIANTS[args.variant])
    metrics = compute_metrics(rows, predictions)
    model = get_settings().ollama_model

    name = f"{args.variant}-{args.dataset}"
    results_path, report_path = RESULTS_DIR / f"{name}.json", REPORTS_DIR / f"{name}.md"
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"model": model, "variant": args.variant, "dataset": args.dataset, "metrics": metrics}
    results_path.write_text(json.dumps({**payload, "predictions": predictions}, indent=2), encoding="utf-8")
    report_path.write_text(render_report(metrics, rows, predictions, model, args.dataset, args.variant), encoding="utf-8")

    print(f"\nExact match: {metrics['exact_match']:.1%}")
    for field in FIELDS:
        print(f"{field:>10}: {metrics['fields'][field]['accuracy']:.1%}")
    print(f"Report: {report_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
