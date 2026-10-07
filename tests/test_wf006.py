from agent_workflow.engine import WorkflowEngine
from agent_workflow.registry import WorkflowRegistry
from agent_workflow.service import AgentService
from agent_workflow.tools import build_default_registry
from agent_workflow.tools.duplicates import find_duplicates
from tests.fakes import FakeLLM

registry = WorkflowRegistry().load()
engine = WorkflowEngine(build_default_registry())

CATALOG = [
    {"sku": "D-100", "name": "Wireless Mouse", "category": "Electronics", "brand": "Acme", "color": "Black", "size": "Standard"},
    {"sku": "D-100", "name": "Wireless Mouse", "category": "Electronics", "brand": "Acme", "color": "Black", "size": "Standard"},
    {"sku": "D-200", "name": "Wireless Mouse", "category": "Electronics", "brand": "Acme", "color": "Black", "size": "Standard"},
    {"sku": "E-300", "name": "Bluetooth Speaker", "category": "Audio", "brand": "SoundCo", "color": "Blue", "size": "Portable"},
    {"sku": "E-400", "name": "Bluetooth Speaker Pro", "category": "Audio", "brand": "SoundCo", "color": "Blue", "size": "Portable"},
    {"sku": "F-500", "name": "LED Desk Lamp", "category": "Lighting", "brand": "LitCo", "color": "White", "size": "Compact"},
]


def _group_types(groups):
    return {group["type"] for group in groups}


def test_find_duplicates_definite_possible_and_unique():
    groups = find_duplicates(CATALOG, ["sku"], ["name", "category", "brand", "color"], 0.7)
    assert _group_types(groups) == {"definite", "possible", "unique"}
    definite = [g for g in groups if g["type"] == "definite"]
    possible = [g for g in groups if g["type"] == "possible"]
    unique = [g for g in groups if g["type"] == "unique"]
    assert len(definite) == 1
    assert len(definite[0]["members"]) == 2
    assert definite[0]["confidence"] == 1.0
    assert definite[0]["matched_fields"] == ["sku"]
    assert len(possible) == 2
    assert all(g["confidence"] >= 0.7 for g in possible)
    assert len(unique) == 1


def test_similarity_threshold_is_configurable():
    strict = find_duplicates(CATALOG, ["sku"], ["name", "category", "brand", "color"], 0.99)
    strict_possible = [g for g in strict if g["type"] == "possible"]
    loose = find_duplicates(CATALOG, ["sku"], ["name", "category", "brand", "color"], 0.7)
    loose_possible = [g for g in loose if g["type"] == "possible"]
    assert len(strict_possible) == 1
    assert len(loose_possible) == 2


def test_wf006_end_to_end():
    result = engine.execute(registry.get_workflow("WF006"), {})
    assert result.status == "completed"
    groups = result.final_output
    assert len(groups) == 4
    assert _group_types(groups) == {"definite", "possible", "unique"}


def test_wf006_decisions():
    result = engine.execute(registry.get_workflow("WF006"), {})
    by_name = {d.name: d for d in result.decision_results}
    assert by_name["definite_duplicate_check"].result is True
    assert by_name["definite_duplicate_check"].message == "1 of 4 groups are definite duplicates"
    assert by_name["possible_duplicate_check"].result is True
    assert by_name["possible_duplicate_check"].message == "2 of 4 groups are possible duplicates"


def test_wf006_via_service_with_fake_llm():
    service = AgentService(
        llm=FakeLLM({"workflow_id": "WF006", "inputs": {}, "rationale": "selected"})
    )
    body = service.run("Find likely duplicate products in the catalog.")
    assert body["workflow_id"] == "WF006"
    assert body["status"] == "completed"
    assert len(body["final_output"]) == 4
    assert len(body["decision_results"]) == 2