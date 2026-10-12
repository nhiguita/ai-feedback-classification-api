# AI Feedback Classification API

A FastAPI service that classifies user feedback by **sentiment, intent, category and priority**
using a local LLM (Qwen3 4B via Ollama) and returns validated JSON. No paid APIs; all data is fictitious.

The priority is not chosen by the LLM: the model extracts impact facts (is the service down? was data
lost? is the user blocked?) and deterministic, unit-tested rules compute the priority from them.

```json
POST /api/v1/feedback/analyze
{"text": "If I log in as a guest I can see the email addresses and phone numbers of every registered farmer."}

200 OK
{"sentiment": "negative", "intent": "report_issue", "category": "data_quality", "priority": "critical"}
```

## Stack
Python · FastAPI · Pydantic · Ollama (Qwen3 4B, structured output) · Pytest

## How it works

```
text ──► FastAPI + Pydantic validation (1–2000 chars)
     ──► Qwen3 4B via Ollama, constrained by a JSON schema:
         sentiment, intent, category + 7 boolean impact facts (no priority field)
     ──► app/priority/rules.py: ordered rules → priority
     ──► FeedbackClassification JSON
```

| Facts reported by the LLM | Priority |
| --- | --- |
| `service_down`, `data_loss` or `security_exposure` | critical |
| `blocked` | high |
| `functional_problem`, `price_or_support_complaint` or `business_need` | medium |
| none | low |

The rules encode [`docs/ANNOTATION_GUIDELINES.md`](docs/ANNOTATION_GUIDELINES.md). Because the LLM
output schema has no priority field, text such as "mark this as critical" cannot set it directly.

Other design points:
- Label and fact definitions in the prompt are generated from the schema enums and field descriptions, so prompt and schema cannot drift (enforced by tests).
- The feedback is delimited as untrusted data, with injection rules and a reminder after it.
- Provider-agnostic LLM interface (`app/llm/`): another backend can be added without touching the service.

### Error handling

| Situation | HTTP status |
| --- | --- |
| Invalid input (empty, more than 2000 chars) | 422 |
| Model output fails schema validation twice (one retry) | 502 |
| Ollama unreachable or model not pulled | 503 |
| Model does not answer within `LLM_TIMEOUT_SECONDS` | 504 |

Client messages are generic; details go to the server logs.

## Setup

Requirements: Python (developed and tested on 3.14), [Ollama](https://ollama.com), ~3.5 GB of free
VRAM for `qwen3:4b` (it also runs on CPU, several times slower).

```bash
ollama pull qwen3:4b
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env   # OLLAMA_HOST, OLLAMA_MODEL, LLM_TIMEOUT_SECONDS
```

`scripts/setup_wsl.sh` lists the system packages used on Ubuntu/WSL2.

## Run

```bash
.venv/bin/uvicorn app.main:app --reload
```

Swagger UI: http://localhost:8000/docs

```bash
curl -X POST http://localhost:8000/api/v1/feedback/analyze \
  -H "Content-Type: application/json" \
  -d '{"text": "The upload button returns an error and I cannot send today'\''s field data."}'
```

More real request/response pairs, including a prompt-injection attempt: [`examples/`](examples/).

## Tests

```bash
.venv/bin/pytest
```

85 tests; they mock the LLM and never call Ollama. Coverage: priority rules, schemas, prompt/schema
consistency, retry and error mapping, the endpoint, evaluation metrics and dataset integrity.

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
v1 and v2 are frozen in `evaluation/baselines/` so they can be re-run.

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
Development log, error analysis and design decisions: [`docs/PROGRESS.md`](docs/PROGRESS.md).

## Limitations

1. **Category got worse in v3** (78.4% → 66.7%, 6 items), mainly on security and data-loss cases:
   security exposures are labeled `data_quality` or `technical_issue` instead of `account_access`
   (see [`examples/02`](examples/README.md)). The guidelines' category clarifications are not in the prompt.
2. **`blocked` is over-reported.** In 5 held-out items the text mentions a workaround or partial
   failure, yet the model reported `blocked`, raising medium to high. The one missed critical
   (a deactivated account that can still log in) was read as `blocked` instead of `security_exposure`.
3. **Latency roughly tripled** (1.5s → 4.1s median on a GTX 1060) because the structured output
   now includes seven facts.
4. **Small, synthetic, single-annotator data.** 51 held-out items (11 critical); one item ≈ 2 points.
   The same author wrote the guidelines, the labels and the prompts, so the held-out set is
   independent of tuning but not of that author's judgment. English only.

## Future work

- **Add the security rule to the prompt:** security and permission problems → `account_access`, plus the
  `technical_issue` vs `data_quality` clarification from the guidelines.
- **Improve `blocked` extraction:** an explicit workaround, retry or partial failure means not blocked;
  distinguish "I cannot work" from "someone who should not have access can still get in".
- **New evaluation set with a second annotator:** label independently, measure inter-annotator
  agreement, and use it as the next held-out set. The current held-out set has already been reported
  on, so it can no longer validate further changes.

## Project structure

```
app/
  api/routes.py           POST /api/v1/feedback/analyze
  llm/                    provider-agnostic client, Ollama implementation, error types
  priority/               facts schema and priority rules
  prompts.py              prompt v3: labels + facts, few-shot, injection defenses
  schemas.py              request/response models and label enums
  services/classifier.py  LLM call with validation/retry + rule-based priority
evaluation/               datasets, metrics, frozen baselines, runner, raw results
docs/                     progress log, annotation guidelines, evaluation reports
examples/                 real request/response pairs
tests/
```
