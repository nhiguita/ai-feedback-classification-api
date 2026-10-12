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
A labeled set of 60 fictitious comments lives in `evaluation/data/feedback_labeled.jsonl`.
Run it against the real model (requires Ollama):
```bash
.venv/bin/python -m evaluation.run_eval
```
Baseline with `qwen3:4b` (GPU, median latency 1.2s): sentiment 88.3%, intent 90.0%,
category 76.7%, priority 68.3%, all four fields correct 41.7%.
Full report with per-label scores, confusion matrices and errors: [`docs/EVALUATION.md`](docs/EVALUATION.md).

## Tests
Tests mock the LLM and never call Ollama.
```bash
.venv/bin/pytest
```
