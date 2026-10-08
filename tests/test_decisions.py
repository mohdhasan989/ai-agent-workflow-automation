import pytest

from agent_workflow.decisions import DecisionEvaluator
from agent_workflow.engine import WorkflowEngine
from agent_workflow.registry import WorkflowRegistry
from agent_workflow.tools import build_default_registry

registry = WorkflowRegistry().load()
tools = build_default_registry()
engine = WorkflowEngine(tools)
evaluator = DecisionEvaluator()


def _rows():
    return [{"item": "A", "value": 4}, {"item": "B", "value": 7}, {"item": "C", "value": 12}]


def test_less_than_threshold():
    outcome = evaluator.evaluate({"op": "lt", "left": {"field": "value"}, "right": {"value": 10}}, _rows())
    assert outcome["result"] is True
    assert outcome["matched_count"] == 2
    assert outcome["total"] == 3


def test_greater_than_threshold():
    outcome = evaluator.evaluate({"op": "gt", "left": {"field": "value"}, "right": {"value": 6}}, _rows())
    assert outcome["result"] is True
    assert outcome["matched_count"] == 2


def test_equality_numeric_and_string():
    assert evaluator.evaluate({"op": "eq", "left": {"field": "value"}, "right": {"value": "7"}}, {"value": 7})["result"]
    assert evaluator.evaluate({"op": "eq", "left": {"field": "code"}, "right": {"value": "SKU-A"}}, {"code": "SKU-A"})["result"]
    assert not evaluator.evaluate({"op": "eq", "left": {"field": "code"}, "right": {"value": "SKU-B"}}, {"code": "SKU-A"})["result"]


def test_and_operator():
    rule = {
        "op": "and",
        "rules": [
            {"op": "gt", "left": {"field": "value"}, "right": {"value": 5}},
            {"op": "lt", "left": {"field": "value"}, "right": {"value": 20}},
        ],
    }
    assert evaluator.evaluate(rule, {"value": 10})["result"]
    assert not evaluator.evaluate(rule, {"value": 25})["result"]


def test_or_operator():
    rule = {
        "op": "or",
        "rules": [
            {"op": "lt", "left": {"field": "value"}, "right": {"value": 5}},
            {"op": "gt", "left": {"field": "value"}, "right": {"value": 15}},
        ],
    }
    assert evaluator.evaluate(rule, {"value": 2})["result"]
    assert evaluator.evaluate(rule, {"value": 20})["result"]
    assert not evaluator.evaluate(rule, {"value": 10})["result"]


def test_missing_value_primitive():
    assert evaluator.evaluate({"op": "missing", "left": {"field": "sku"}}, {"name": "Widget"})["result"]
    assert evaluator.evaluate({"op": "missing", "left": {"field": "sku"}}, {"sku": ""})["result"]
    assert not evaluator.evaluate({"op": "missing", "left": {"field": "sku"}}, {"sku": "A1"})["result"]


def test_exists_not_found():
    assert evaluator.evaluate({"op": "exists", "left": {"field": "order"}}, {"order": "ORD-1001"})["result"]
    assert not evaluator.evaluate({"op": "exists", "left": {"field": "order"}}, {})["result"]


def test_classification_in_category():
    rule = {"op": "in", "left": {"field": "intent"}, "values": ["informational", "commercial"]}
    assert evaluator.evaluate(rule, {"intent": "commercial"})["result"]
    assert not evaluator.evaluate(rule, {"intent": "navigational"})["result"]


def test_escalation_primitive():
    rule = {
        "op": "escalate",
        "rule": {"op": "eq", "left": {"field": "available"}, "right": {"value": 0}},
    }
    outcome = evaluator.evaluate(rule, {"available": 0})
    assert outcome["result"] is True
    assert outcome["escalated"] is True
    assert not evaluator.evaluate(rule, {"available": 2})["result"]


def test_unknown_operator_raises():
    with pytest.raises(ValueError):
        evaluator.evaluate({"op": "bogus", "left": {"field": "value"}, "right": {"value": 1}}, {"value": 2})


def test_wf001_decision_evaluated_by_engine():
    result = engine.execute(registry.get_workflow("WF001"), {"minimum_stock": 10})
    assert result.status == "completed"
    assert len(result.decision_results) == 1
    decision = result.decision_results[0]
    assert decision.name == "restock_check"
    assert decision.rule == "lt"
    assert decision.result is True
    assert decision.message == "2 of 4 products marked for restock"
    assert decision.values == {"left": -5.0, "right": 0}


def test_wf002_decision_evaluated_by_engine():
    result = engine.execute(registry.get_workflow("WF002"), {})
    assert result.status == "completed"
    assert len(result.decision_results) == 1
    decision = result.decision_results[0]
    assert decision.name == "exception_check"
    assert decision.rule == "gt"
    assert decision.result is True
    assert decision.message == "2 of 4 products flagged as price exceptions"
    assert decision.values["left"] > decision.values["right"]


def test_values_come_from_matching_record():
    rows = [{"value": 4}, {"value": 12}]
    outcome = evaluator.evaluate({"op": "gt", "left": {"field": "value"}, "right": {"value": 10}}, rows)
    assert outcome["result"] is True
    assert outcome["values"] == {"left": 12, "right": 10}


def test_invalid_decision_operator_fails_step():
    invalid = {
        "decisions": [
            {
                "workflow_id": "WF001",
                "step": "identify low-stock products",
                "name": "bad",
                "rule": {"op": "bogus", "left": {"field": "stock_diff"}, "right": {"value": 0}},
                "data": "$compared",
                "message": "bad",
            }
        ]
    }
    custom = WorkflowEngine(tools, decisions=invalid)
    result = custom.execute(registry.get_workflow("WF001"), {})
    assert result.status == "failed"
    failed_steps = [step for step in result.steps if step.status == "failed"]
    assert failed_steps and "Decision evaluation failed" in failed_steps[0].error


def test_decision_config_missing_rule_raises():
    with pytest.raises(ValueError):
        WorkflowEngine(
            tools,
            decisions={
                "decisions": [
                    {"workflow_id": "X", "step": "s", "name": "n"}
                ]
            },
        )