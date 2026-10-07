import pytest

from agent_workflow.engine import WorkflowEngine
from agent_workflow.registry import WorkflowRegistry
from agent_workflow.service import AgentService
from agent_workflow.tools import build_default_registry
from tests.fakes import FakeLLM

registry = WorkflowRegistry().load()
engine = WorkflowEngine(build_default_registry())

MOCK = "data/mock/products_categories.csv"


def test_wf011_is_loaded_from_workbook():
    definition = registry.get_workflow("WF011")
    assert definition.workflow_id == "WF011"
    assert definition.workflow_name == "Product Category Count"
    assert definition.steps == [
        "Load products",
        "Group products by category",
        "Count products in each category",
        "Generate category count report",
    ]


def test_wf011_executes_successfully():
    result = engine.execute(registry.get_workflow("WF011"), {"products_path": MOCK})
    assert result.status == "completed"
    assert [step.status for step in result.steps] == ["executed"] * 4


def test_wf011_category_counts_are_correct():
    result = engine.execute(registry.get_workflow("WF011"), {"products_path": MOCK})
    report = result.final_output
    by_category = {item["key"]: item["count"] for item in report["counts"]}
    assert by_category == {"Espresso": 3, "Drip Coffee": 3, "Coffee Beans": 3}
    assert report["total_groups"] == 3
    assert report["empty"] is False
    decision = [d for d in result.decision_results if d.name == "products_loaded"][0]
    assert decision.result is True
    assert decision.message == "9 of 9 products loaded"


def test_wf011_empty_product_file_returns_empty_data_result(tmp_path):
    products = tmp_path / "products.csv"
    products.write_text("product_id,name,category,price\n", encoding="utf-8")
    result = engine.execute(registry.get_workflow("WF011"), {"products_path": str(products)})
    assert result.status == "completed"
    report = result.final_output
    assert report["empty"] is True
    assert report["counts"] == []
    assert report["total_groups"] == 0
    assert "No rows" in report["message"]
    decision = [d for d in result.decision_results if d.name == "products_loaded"][0]
    assert decision.result is False
    assert decision.message == "0 of 0 products loaded"


def test_wf011_via_service_with_fake_llm():
    service = AgentService(
        llm=FakeLLM(
            {
                "workflow_id": "WF011",
                "inputs": {"products_path": MOCK},
                "rationale": "count products per category",
            }
        )
    )
    body = service.run("How many products are in each category?")
    assert body["workflow_id"] == "WF011"
    assert body["status"] == "completed"
    by_category = {item["key"]: item["count"] for item in body["final_output"]["counts"]}
    assert by_category["Espresso"] == 3
    assert len(body["decision_results"]) == 1