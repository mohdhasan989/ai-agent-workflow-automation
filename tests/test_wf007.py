from agent_workflow.engine import WorkflowEngine
from agent_workflow.registry import WorkflowRegistry
from agent_workflow.service import AgentService
from agent_workflow.tools import build_default_registry
from tests.fakes import FakeLLM

registry = WorkflowRegistry().load()

INPUTS = {
    "goal": "Launch the new French Press collection",
    "products": "data/mock/campaign_products.csv",
    "audience": "Home coffee enthusiasts",
    "promotion": "20% launch discount",
    "dates": "2026-11-01 to 2026-11-30",
}

CONTENT = {
    "objective": "Drive pre-orders for the French Press collection.",
    "messaging": "Fresh brews start here.",
    "channels": ["social media", "email", "in-store"],
    "checklist": ["approve creative", "schedule emails", "launch landing page"],
}


def _engine():
    return WorkflowEngine(build_default_registry(FakeLLM(CONTENT)))


def test_wf007_complete_campaign_brief():
    result = _engine().execute(registry.get_workflow("WF007"), dict(INPUTS))
    assert result.status == "completed"
    brief = result.final_output
    for field in [
        "objective",
        "audience",
        "timeline",
        "product_count",
        "product_names",
        "messaging",
        "channels",
        "checklist",
        "goal",
        "promotion",
    ]:
        assert field in brief
    assert brief["product_count"] == 3
    assert brief["audience"] == "Home coffee enthusiasts"
    assert brief["timeline"] == "2026-11-01 to 2026-11-30"
    decision = [d for d in result.decision_results if d.name == "brief_complete"][0]
    assert decision.result is True
    assert decision.message == "campaign brief includes a checklist"


def test_wf007_missing_goal_requests_input():
    inputs = dict(INPUTS)
    inputs["goal"] = ""
    result = _engine().execute(registry.get_workflow("WF007"), inputs)
    assert result.status == "failed"
    assert result.error == "Missing required inputs: goal"
    assert result.steps[0].status == "failed"


def test_wf007_missing_dates_requests_input():
    inputs = dict(INPUTS)
    inputs["dates"] = ""
    result = _engine().execute(registry.get_workflow("WF007"), inputs)
    assert result.status == "failed"
    assert "dates" in result.error


def test_wf007_via_service_with_fake_llm():
    response = dict(CONTENT)
    response.update({"workflow_id": "WF007", "inputs": dict(INPUTS), "rationale": "campaign brief"})
    service = AgentService(llm=FakeLLM(response))
    body = service.run("Create a campaign brief for the new collection.")
    assert body["workflow_id"] == "WF007"
    assert body["status"] == "completed"
    assert body["final_output"]["product_count"] == 3
    assert body["final_output"]["objective"]
    assert len(body["decision_results"]) == 1