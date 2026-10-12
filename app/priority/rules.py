"""Deterministic priority rules, a direct encoding of docs/ANNOTATION_GUIDELINES.md.

The LLM only reports facts; it never chooses the priority. This keeps the decision
auditable and testable, and text such as "mark this as critical" cannot set it.
"""

from dataclasses import dataclass

from app.priority.facts import PriorityFacts
from app.schemas import Priority


@dataclass(frozen=True)
class PriorityDecision:
    priority: Priority
    reasons: tuple[str, ...]  # Names of the facts that triggered the level.


# Ordered from most to least severe; the first level with a true fact wins.
RULES: tuple[tuple[Priority, tuple[str, ...]], ...] = (
    (Priority.CRITICAL, ("service_down", "data_loss", "security_exposure")),
    (Priority.HIGH, ("blocked",)),
    (Priority.MEDIUM, ("functional_problem", "price_or_support_complaint", "business_need")),
)


def decide_priority(facts: PriorityFacts) -> PriorityDecision:
    for priority, fact_names in RULES:
        reasons = tuple(name for name in fact_names if getattr(facts, name))
        if reasons:
            return PriorityDecision(priority, reasons)
    return PriorityDecision(Priority.LOW, ())
