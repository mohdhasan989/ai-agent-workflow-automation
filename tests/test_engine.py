import pytest

import agent_workflow.engine as engine_module
from agent_workflow.engine import WorkflowEngine
from agent_workflow.models import WorkflowDefinition
from agent_workflow.registry import WorkflowRegistry
from agent_workflow.tools import ToolRegistry, build_default_registry

registry = WorkflowRegistry().load()
tools = build_default_registry()


def _definition(workflow_id="WFD", steps=("one", "two", "three")):
    return WorkflowDefinition(
        workflow_id=workflow_id,
        workflow_name="Definition",
        trigger="trigger",
        inputs=[],
        steps=list(steps),
        decision_logic="",
        tools_required=[],
        expected_output="",
    )


def test_executes_steps_in_defined_order():
    calls = []

    def probe(value):
        calls.append(value)
        return value

    custom = ToolRegistry()
    custom.register("probe", probe)
    definition = _definition(steps=("first", "second", "third"))
    engine = WorkflowEngine(
        custom,
        {
            "bindings": [
                {"workflow_id": "WFD", "step": "first", "tool": "probe", "params": {"args": [1]}},
                {"workflow_id": "WFD", "step": "second", "tool": "probe", "params": {"args": [2]}},
                {"workflow_id": "WFD", "step": "third", "tool": "probe", "params": {"args": [3]}},
            ]
        },
    )
    result = engine.execute(definition, {})
    assert result.status == "completed"
    assert [step.step for step in result.steps] == ["first", "second", "third"]
    assert calls == [1, 2, 3]


def test_step_outputs_passed_through_context():
    def add10(value):
        return value + 10

    custom = ToolRegistry()
    custom.register("add10", add10)
    definition = _definition(steps=("seed", "increment", "summarize"))
    engine = WorkflowEngine(
        custom,
        {
            "bindings": [
                {"workflow_id": "WFD", "step": "seed", "tool": "add10", "params": {"args": [5]}, "output": "first"},
                {"workflow_id": "WFD", "step": "increment", "tool": "add10", "params": {"args": ["$first"]}, "output": "second"},
                {"workflow_id": "WFD", "step": "summarize", "tool": "add10", "params": {"args": ["$second"]}, "output": "third"},
            ]
        },
    )
    result = engine.execute(definition, {})
    assert result.status == "completed"
    assert result.steps[0].output == 15
    assert result.steps[1].output == 25
    assert result.steps[2].output == 35
    assert result.final_output == 35


def test_tools_resolved_through_registry():
    calls = []

    def probe(value):
        calls.append(value)
        return value * 2

    custom = ToolRegistry()
    custom.register("probe", probe)
    definition = _definition(steps=("double it",))
    engine = WorkflowEngine(
        custom,
        {"bindings": [{"workflow_id": "WFD", "step": "double it", "tool": "probe", "params": {"args": [21]}}]},
    )
    result = engine.execute(definition, {})
    assert result.status == "completed"
    assert calls == [21]
    assert result.steps[0].output == 42


def test_tool_failure_produces_failed_result():
    def boom():
        raise RuntimeError("kaboom")

    custom = ToolRegistry()
    custom.register("boom", boom)
    definition = _definition(steps=("explode", "unreached"))
    engine = WorkflowEngine(
        custom,
        {
            "bindings": [
                {
                    "workflow_id": "WFD",
                    "step": "explode",
                    "tool": "boom",
                }
            ]
        },
    )
    result = engine.execute(definition, {})
    assert result.status == "failed"
    assert result.error == "kaboom"
    assert result.steps[0].status == "failed"
    assert result.steps[0].error == "kaboom"
    assert len(result.steps) == 1


def test_unknown_tool_produces_controlled_error():
    definition = _definition(steps=("call missing",))
    engine = WorkflowEngine(
        tools,
        {
            "bindings": [
                {"workflow_id": "WFD", "step": "call missing", "tool": "nope"}
            ]
        },
    )
    result = engine.execute(definition, {})
    assert result.status == "failed"
    assert "nope" in result.steps[0].error
    assert result.steps[0].status == "failed"


def test_missing_binding_marks_step_skipped():
    definition = _definition(steps=("do something",))
    engine = WorkflowEngine(
        tools,
        {"bindings": []},
    )
    result = engine.execute(definition, {})
    assert result.status == "completed"
    assert result.steps[0].status == "skipped"


def test_engine_has_no_workflow_id_branches():
    source = engine_module.__file__
    text = open(source, encoding="utf-8").read()
    assert "WF001" not in text
    assert "WF002" not in text
    assert "workflow_id ==" not in text