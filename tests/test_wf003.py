from openpyxl import Workbook

from agent_workflow.engine import WorkflowEngine
from agent_workflow.registry import WorkflowRegistry
from agent_workflow.service import AgentService
from agent_workflow.tools import build_default_registry
from agent_workflow.tools.table import read_table
from tests.fakes import FakeLLM

registry = WorkflowRegistry().load()
engine = WorkflowEngine(build_default_registry())


def test_read_table_supports_xlsx(tmp_path):
    path = tmp_path / "vendor_data.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "VendorData"
    sheet.append(["SKU Code", "Product Name", "List Price"])
    sheet.append(["V-001", "Espresso Maker", 50])
    sheet.append(["V-002", "Tea Kettle", 22])
    workbook.save(path)
    rows = read_table(str(path))
    assert rows == [
        {"SKU Code": "V-001", "Product Name": "Espresso Maker", "List Price": 50},
        {"SKU Code": "V-002", "Product Name": "Tea Kettle", "List Price": 22},
    ]


def test_wf003_cleans_and_reports_invalid_rows():
    result = engine.execute(registry.get_workflow("WF003"), {})
    assert result.status == "completed"
    payload = result.final_output
    assert payload["summary"] == {"total": 7, "valid": 4, "invalid": 3}
    cleaned = payload["cleaned_rows"]
    invalid = payload["invalid_rows"]
    assert {row["sku"] for row in cleaned} == {"V-101", "V-102", "V-105", "V-106"}
    assert len(invalid) == 3


def test_wf003_missing_sku_or_name_flagged_invalid():
    result = engine.execute(registry.get_workflow("WF003"), {})
    payload = result.final_output
    invalid = payload["invalid_rows"]
    missing_sku_only = [row for row in invalid if not row["sku"] and row["name"]]
    missing_name_only = [row for row in invalid if row["sku"] and not row["name"]]
    missing_both = [row for row in invalid if not row["sku"] and not row["name"]]
    assert len(missing_sku_only) == 1
    assert len(missing_name_only) == 1
    assert len(missing_both) == 1


def test_wf003_invalid_rows_decision():
    result = engine.execute(registry.get_workflow("WF003"), {})
    decision = [d for d in result.decision_results if d.name == "invalid_rows_check"][0]
    assert decision.result is True
    assert decision.rule == "or"
    assert decision.message == "3 of 7 rows missing SKU or product name"


def test_wf003_all_steps_executed():
    result = engine.execute(registry.get_workflow("WF003"), {})
    assert [step.step for step in result.steps] == [
        "Read file",
        "detect columns",
        "normalize column names",
        "validate required fields",
        "identify invalid rows",
        "produce cleaned dataset",
    ]
    assert all(step.status == "executed" for step in result.steps)


def test_wf003_via_service_with_fake_llm():
    service = AgentService(
        llm=FakeLLM({"workflow_id": "WF003", "inputs": {}, "rationale": "selected"})
    )
    body = service.run("Process this vendor spreadsheet and show invalid rows.")
    assert body["workflow_id"] == "WF003"
    assert body["status"] == "completed"
    assert body["final_output"]["summary"]["invalid"] == 3
    assert len(body["decision_results"]) == 1