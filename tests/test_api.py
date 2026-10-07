from fastapi.testclient import TestClient

from agent_workflow.api import app, get_service
from agent_workflow.service import AgentService
from tests.fakes import FakeLLM

client = TestClient(app)


def _selection(workflow_id, inputs=None, rationale="selected"):
    return {"workflow_id": workflow_id, "inputs": inputs or {}, "rationale": rationale}


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_agent_run_wf001_end_to_end():
    app.dependency_overrides[get_service] = lambda: AgentService(
        llm=FakeLLM(_selection("WF001", {"minimum_stock": 10}))
    )
    try:
        response = client.post("/agent/run", json={"message": "Which products need restocking?"})
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    body = response.json()
    assert body["workflow_id"] == "WF001"
    assert body["workflow_name"] == "Inventory Restock Check"
    assert body["status"] == "completed"
    assert body["error"] is None
    assert body["rationale"] == "selected"
    assert len(body["decision_results"]) == 1
    assert body["decision_results"][0]["name"] == "restock_check"
    assert body["decision_results"][0]["result"] is True
    assert len(body["steps"]) == 5
    assert all(step["status"] == "executed" for step in body["steps"])
    skus = [row["sku"] for row in body["final_output"]]
    assert skus == ["SKU-101", "SKU-103"]


def test_agent_run_wf002_end_to_end():
    app.dependency_overrides[get_service] = lambda: AgentService(
        llm=FakeLLM(_selection("WF002", {"internal_price": 80, "vendor_price": 72}))
    )
    try:
        response = client.post(
            "/agent/run",
            json={"message": "Find products where vendor price differs by more than 10%."},
        )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    body = response.json()
    assert body["workflow_id"] == "WF002"
    assert body["workflow_name"] == "Product Price Validation"
    assert body["status"] == "completed"
    assert len(body["steps"]) == 5
    assert len(body["decision_results"]) == 1
    assert body["decision_results"][0]["name"] == "exception_check"
    assert body["decision_results"][0]["result"] is True
    skus = [row["sku"] for row in body["final_output"]]
    assert skus == ["P-202", "P-204"]


def test_agent_run_unknown_workflow_returns_400():
    app.dependency_overrides[get_service] = lambda: AgentService(
        llm=FakeLLM(_selection("WF999", {}, ""))
    )
    try:
        response = client.post("/agent/run", json={"message": "anything"})
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 400
    assert "WF999" in response.json()["detail"]


def test_agent_run_empty_message():
    response = client.post("/agent/run", json={"message": ""})
    assert response.status_code == 422


def test_agent_run_blank_message():
    response = client.post("/agent/run", json={"message": "   "})
    assert response.status_code == 422


def test_agent_run_missing_body():
    response = client.post("/agent/run", json={})
    assert response.status_code == 422