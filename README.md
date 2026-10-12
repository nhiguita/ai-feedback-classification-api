# AI Feedback Classification API

A FastAPI service that classifies user feedback by sentiment, intent, category and priority
using a local LLM (Qwen3 4B via Ollama) and returns validated JSON.

> Work in progress. See `docs/PROGRESS.md`.

## Stack
Python · FastAPI · Pydantic · Ollama (Qwen3 4B) · Pytest

## Setup
```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
```

## Run
```bash
.venv/bin/uvicorn app.main:app --reload
```
Swagger UI: http://localhost:8000/docs

## Example
```bash
curl -X POST http://localhost:8000/api/v1/feedback/analyze \
  -H "Content-Type: application/json" \
  -d '{"text": "The application crashes when I upload reports."}'
```

## Evaluation
63 fictitious, hand-labeled comments in `evaluation/data/feedback_dev.jsonl` (development set).
Run against the real model (requires Ollama):
```bash
.venv/bin/python -m evaluation.run_eval --dataset dev
```

Historical results on the former **test** split (33 of those comments; now part of the
development set because it was used to compare v1 and v2) with `qwen3:4b` (GPU, median latency ~1.4s):

| Field | Prompt v1 | Prompt v2 |
| --- | --- | --- |
| sentiment | 81.8% | 90.9% |
| intent | 87.9% | 90.9% |
| category | 78.8% | 72.7% |
| priority | 63.6% | 69.7% |
| all four fields | 42.4% | 45.5% |
| injection attempts that raised priority | 3/3 | 0/3 |

Per-label scores, confusion matrices and errors: [`docs/evaluation/`](docs/evaluation/).
Error analysis and design decisions: [`docs/PROGRESS.md`](docs/PROGRESS.md).

## Tests
Tests mock the LLM and never call Ollama.
```bash
.venv/bin/pytest
```
