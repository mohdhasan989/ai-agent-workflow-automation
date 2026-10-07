import pytest

from agent_workflow.agent import AgentError
from agent_workflow.engine import WorkflowEngine
from agent_workflow.service import AgentService
from agent_workflow.tools import ToolRegistry
from tests.fakes import FakeLLM


def _selection(workflow_id, inputs=None, rationale="selected"):
    return {"workflow_id": workflow_id, "inputs": inputs or {}, "rationale": rationale}


def test_wf001_end_to_end_via_service():
    service = AgentService(llm=FakeLLM(_selection("WF001", {"minimum_stock": 10})))
    body = service.run("Which products need restocking?")
    assert body["workflow_id"] == "WF001"
    assert body["workflow_name"] == "Inventory Restock Check"
    assert body["status"] == "completed"
    assert body["error"] is None
    assert [step["step"] for step in body["steps"]] == [
        "Load inventory",
        "compare current stock with minimum threshold",
        "identify low-stock products",
        "calculate reorder quantity",
        "generate restock list",
    ]
    assert all(step["status"] == "executed" for step in body["steps"])
    assert len(body["decision_results"]) == 1
    assert body["decision_results"][0]["name"] == "restock_check"
    assert body["decision_results"][0]["message"] == "2 of 4 products marked for restock"
    restock = body["final_output"]
    assert [row["sku"] for row in restock] == ["SKU-101", "SKU-103"]
    assert restock[0]["reorder_qty"] == 5.0
    assert restock[1]["reorder_qty"] == 2.0


def test_wf002_end_to_end_via_service():
    service = AgentService(llm=FakeLLM(_selection("WF002")))
    body = service.run("Find products where vendor price differs by more than 10%.")
    assert body["workflow_id"] == "WF002"
    assert body["workflow_name"] == "Product Price Validation"
    assert body["status"] == "completed"
    assert [step["step"] for step in body["steps"]] == [
        "Load product prices",
        "match products by SKU",
        "compare internal and vendor prices",
        "calculate percentage difference",
        "flag exceptions",
    ]
    assert len(body["decision_results"]) == 1
    assert body["decision_results"][0]["name"] == "exception_check"
    assert body["decision_results"][0]["message"] == "2 of 4 products flagged as price exceptions"
    exceptions = body["final_output"]
    skus = {row["sku"] for row in exceptions}
    assert skus == {"P-202", "P-204"}


def test_tool_failure_returns_failed_result():
    custom_tools = ToolRegistry()
    engine = WorkflowEngine(custom_tools)
    service = AgentService(
        tools=custom_tools,
        engine=engine,
        llm=FakeLLM(_selection("WF001", {}, "")),
    )
    body = service.run("Which products need restocking?")
    assert body["status"] == "failed"
    assert body["steps"][0]["status"] == "failed"
    assert "read_csv" in body["steps"][0]["error"]


def test_unknown_workflow_raises_controlled_error():
    service = AgentService(llm=FakeLLM(_selection("WF999", {}, "")))
    with pytest.raises(AgentError):
        service.run("anything")