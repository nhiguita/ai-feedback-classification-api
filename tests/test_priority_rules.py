import pytest

from app.priority.facts import PriorityFacts
from app.priority.rules import RULES, decide_priority
from app.schemas import Priority

FACT_NAMES = list(PriorityFacts.model_fields)


def facts(**true_facts: bool) -> PriorityFacts:
    return PriorityFacts(**{name: False for name in FACT_NAMES} | true_facts)


def test_no_facts_is_low():
    decision = decide_priority(facts())
    assert decision.priority == Priority.LOW
    assert decision.reasons == ()


@pytest.mark.parametrize(
    ("fact", "expected"),
    [
        ("service_down", Priority.CRITICAL),
        ("data_loss", Priority.CRITICAL),
        ("security_exposure", Priority.CRITICAL),
        ("blocked", Priority.HIGH),
        ("functional_problem", Priority.MEDIUM),
        ("price_or_support_complaint", Priority.MEDIUM),
        ("business_need", Priority.MEDIUM),
    ],
)
def test_each_fact_maps_to_its_level(fact, expected):
    decision = decide_priority(facts(**{fact: True}))
    assert decision.priority == expected
    assert decision.reasons == (fact,)


def test_most_severe_level_wins():
    decision = decide_priority(facts(blocked=True, functional_problem=True, data_loss=True))
    assert decision.priority == Priority.CRITICAL
    assert decision.reasons == ("data_loss",)


def test_blocked_beats_medium_facts():
    assert decide_priority(facts(blocked=True, business_need=True)).priority == Priority.HIGH


def test_all_critical_reasons_are_reported():
    decision = decide_priority(facts(service_down=True, security_exposure=True))
    assert decision.reasons == ("service_down", "security_exposure")


def test_every_fact_is_used_by_exactly_one_rule():
    used = [name for _, names in RULES for name in names]
    assert sorted(used) == sorted(FACT_NAMES)


def test_rules_are_ordered_by_severity():
    order = [Priority.CRITICAL, Priority.HIGH, Priority.MEDIUM]
    assert [priority for priority, _ in RULES] == order
