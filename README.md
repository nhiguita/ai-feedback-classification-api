# AI Feedback Classification API

A FastAPI service that classifies user feedback by sentiment, intent, category and priority
using a local LLM (Qwen3 4B via Ollama) and returns validated JSON.

> Work in progress. See `docs/PROGRESS.md`.

## Stack
Python · FastAPI · Pydantic · Ollama (Qwen3 4B) · Pytest

## How it works
1. The request text is validated (1–2000 chars) and sent to Qwen3 with a JSON schema (Ollama structured output).
2. The LLM returns `sentiment`, `intent`, `category` and seven boolean **impact facts**
   (`service_down`, `data_loss`, `security_exposure`, `blocked`, `functional_problem`,
   `price_or_support_complaint`, `business_need`). It never chooses the priority.
3. `app/priority/rules.py` computes the priority from the facts with ordered, unit-tested rules
   (critical → high → medium → low), following [`docs/ANNOTATION_GUIDELINES.md`](docs/ANNOTATION_GUIDELINES.md).
4. Invalid model output is retried once (then 502); Ollama down → 503; timeout → 504.

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
Two fictitious, hand-labeled datasets:

| Dataset | Items | Use |
| --- | --- | --- |
| `evaluation/data/feedback_dev.jsonl` | 63 | Development: used while designing prompts v1 and v2 |
| `evaluation/data/feedback_holdout.jsonl` | 51 | Held out: written before v3 existed, report-only, never used to adjust prompts or rules |

```bash
.venv/bin/python -m evaluation.run_eval --dataset holdout --variant v3   # v1 | v2 | v3
```

Variants: **v1** first prompt, LLM chooses priority · **v2** calibrated prompt + injection defenses,
LLM chooses priority · **v3** (current) LLM extracts facts, code computes priority.

### Results on the held-out set (`qwen3:4b`, GTX 1060 6 GB)

| Metric | v1 | v2 | v3 |
| --- | --- | --- | --- |
| sentiment | 80.4% | 78.4% | 78.4% |
| intent | 86.3% | 88.2% | 90.2% |
| category | 78.4% | 72.5% | 66.7% |
| **priority** | 60.8% | 74.5% | **86.3%** |
| all four fields correct | 37.3% | 41.2% | 43.1% |
| critical issues detected (of 11) | 6 | 5 | 10 |
| false `critical` | 4 | 1 | 0 |
| priority off by 2+ levels | 3 | 3 | 0 |
| injection attempts that changed priority (of 3) | 2 | 1 | 0 |
| median latency per request | 1.3s | 1.5s | 4.1s |

v3 makes priority the most reliable field and catches the costly cases (security exposure,
data loss) that v1 and v2 rated as high or medium. Per-label scores, confusion matrices and
every error (with the facts that triggered each priority): [`docs/evaluation/`](docs/evaluation/).
Error analysis and design decisions: [`docs/PROGRESS.md`](docs/PROGRESS.md).

### Limitations
- **Small, synthetic data.** 51 held-out items (11 critical): one item ≈ 2 points. The priority
  gain is well beyond that; sentiment differences are 1 item, while the category drop (6 items) is real.
- **Single annotator.** The same author wrote the guidelines, the labels and the prompts. The
  held-out set is independent of tuning, not of that author's judgment; no inter-annotator agreement was measured.
- **Category got worse in v3** (78.4% → 66.7%), mainly on security and data-loss items. The
  guidelines' category clarifications (security → `account_access`, described failure →
  `technical_issue`) are not in the prompt yet.
- **Fact errors remain:** `blocked` is over-reported when a workaround is mentioned (medium → high),
  and `functional_problem` fires on cosmetic issues (low → medium).
- **Latency tripled** in v3 because of the larger structured output (~4s per request on a GTX 1060).
- **English only**, fictitious comments; real feedback is noisier and may be multilingual.
- **Injection resistance is empirical,** tested on a handful of attempts; it is not a guarantee.
  Rules limit the damage (text cannot set the priority directly) but a crafted text can still
  claim facts such as "the service is down".
- The held-out set has now been reported on. Any further tuning needs new held-out data.

## Tests
Tests mock the LLM and never call Ollama.
```bash
.venv/bin/pytest
```
