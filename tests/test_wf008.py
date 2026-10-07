from agent_workflow.engine import WorkflowEngine
from agent_workflow.decisions import DecisionEvaluator
from agent_workflow.registry import WorkflowRegistry
from agent_workflow.service import AgentService
from agent_workflow.tools import build_default_registry
from agent_workflow.tools.classify import classify_labels, tag_rows
from agent_workflow.tools.rows import dedupe_rows
from tests.fakes import FakeLLM

registry = WorkflowRegistry().load()
engine = WorkflowEngine(build_default_registry())

INTENT_RULES = [
    {"label": "transactional", "matches": [{"field": "keyword", "pattern": "buy"}]},
    {"label": "navigational", "matches": [{"field": "keyword", "pattern": "near"}]},
    {"label": "commercial", "matches": [{"field": "keyword", "pattern": "best"}]},
    {"label": "informational", "matches": []},
]

KEYWORDS = [
    {"keyword": "buy espresso beans", "category": "espresso"},
    {"keyword": "coffee shop near me", "category": "shops"},
    {"keyword": "best coffee maker", "category": "machines"},
    {"keyword": "how to brew coffee", "category": "coffee"},
]


def test_dedupe_rows_removes_duplicate_keywords():
    rows = [
        {"keyword": "best coffee maker", "search_volume": "2400"},
        {"keyword": "best coffee maker", "search_volume": "2400"},
        {"keyword": "coffee grinder", "search_volume": "650"},
    ]
    deduped = dedupe_rows(rows, "keyword")
    assert [r["keyword"] for r in deduped] == ["best coffee maker", "coffee grinder"]


def test_classify_labels_assigns_from_config_rules():
    classified = classify_labels(KEYWORDS, INTENT_RULES, "intent")
    by_keyword = {row["keyword"]: row["intent"] for row in classified}
    assert by_keyword["buy espresso beans"] == "transactional"
    assert by_keyword["coffee shop near me"] == "navigational"
    assert by_keyword["best coffee maker"] == "commercial"
    assert by_keyword["how to brew coffee"] == "informational"


def test_tag_rows_uses_decision_evaluator_rules():
    rows = [
        {"sku": "A", "stock": "5"},
        {"sku": "B", "stock": "20"},
    ]
    rule = {"op": "lt", "left": {"field": "stock"}, "right": {"value": 10}}
    tagged = tag_rows(rows, rule, "status", "low", "ok")
    assert [row["status"] for row in tagged] == ["low", "ok"]


def test_decision_evaluator_in_operator():
    evaluator = DecisionEvaluator()
    assert evaluator.matches(
        {"op": "in", "left": {"field": "intent"}, "values": ["informational", "commercial"]},
        {"intent": "commercial"},
    )
    assert not evaluator.matches(
        {"op": "in", "left": {"field": "intent"}, "values": ["informational"]},
        {"intent": "transactional"},
    )


def test_wf008_end_to_end():
    result = engine.execute(registry.get_workflow("WF008"), {})
    assert result.status == "completed"
    report = result.final_output
    assert len(report) == 7
    intents = {row["intent"] for row in report}
    assert intents == {"informational", "commercial", "transactional", "navigational"}
    assert all(row["category"] in {"Espresso", "Coffee Machines", "Coffee Shops", "Order Support", "Coffee"} for row in report)
    assert all(row["target_page"].startswith("/") for row in report)
    assert {row["keyword"] for row in report} == {
        "how to clean espresso machine",
        "best coffee maker under 200",
        "buy espresso beans online",
        "local coffee shop near me",
        "coffee grinder",
        "cheap espresso machine review",
        "track my order",
    }


def test_wf008_priority_and_intent_decision():
    result = engine.execute(registry.get_workflow("WF008"), {})
    report = result.final_output
    high = [row for row in report if row["priority"] == "high"]
    normal = [row for row in report if row["priority"] == "normal"]
    assert len(high) == 4
    assert len(normal) == 3
    decision = [d for d in result.decision_results if d.name == "intent_coverage"][0]
    assert decision.result is True
    assert decision.message == "7 of 7 keywords classified into a recognized intent"
    assert decision.rule == "in"


def test_wf008_via_service_with_fake_llm():
    service = AgentService(
        llm=FakeLLM({"workflow_id": "WF008", "inputs": {}, "rationale": "selected"})
    )
    body = service.run("Classify these keywords and map them to pages.")
    assert body["workflow_id"] == "WF008"
    assert body["status"] == "completed"
    assert len(body["final_output"]) == 7
    assert len(body["decision_results"]) == 1