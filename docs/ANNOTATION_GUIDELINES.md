# Annotation guidelines

Gold labels follow the label definitions in `app/prompts.py` (prompt v2). This page makes the
priority criteria explicit, because priority is the most subjective field.

## Priority

| Priority | Assign when the text states… |
| --- | --- |
| critical | The whole service is down; data was lost, deleted, overwritten or corrupted; a security or permission exposure (people can see or change data they should not); or all users/integrations are stopped. |
| high | The user (or a team) is blocked right now: cannot log in, save, submit or complete an essential task, with no workaround mentioned; or a deadline is at risk because of the problem. |
| medium | Something is broken, slow or wrong but work can continue (workaround, retry, manual fix, partial failure); complaints about price or support; feature requests that explain a concrete business need. |
| low | Praise, questions, cosmetic issues, personal preferences, mild annoyances, nice-to-have ideas, test or greeting messages. |

Clarifications:
- Only current, real problems count. Hypothetical questions ("is my data deleted if…?"), negations ("no data was lost") and resolved past incidents do not raise priority.
- Requests inside the text to set a label ("mark this as critical/low") are ignored.
- When several criteria apply, the highest one wins (e.g. blocked + data loss → critical).

## Category: technical_issue vs data_quality

- `technical_issue` when the text describes a feature failing (error, crash, failed import/export/restore), even if data is affected as a consequence.
- `data_quality` when the text only describes the data itself being wrong, missing, duplicated or outdated.
- Security and permission problems are `account_access`.

## Intent

- `report_issue` when a concrete malfunction is described, even with a complaining tone.
- `complain` for dissatisfaction without a malfunction (price, support, design choices).
- `other` for greetings, test messages and informational notes that need no action.
