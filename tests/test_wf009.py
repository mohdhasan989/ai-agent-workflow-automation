from agent_workflow.engine import WorkflowEngine
from agent_workflow.registry import WorkflowRegistry
from agent_workflow.service import AgentService
from agent_workflow.tools import build_default_registry
from tests.fakes import FakeLLM

registry = WorkflowRegistry().load()

INPUTS = {
    "task": "Build the inventory ETL pipeline",
    "employees": "data/mock/employees.csv",
    "required_skills": ["Python", "SQL"],
    "priority": "high",
    "deadline": "2026-11-15",
}

BUSY_INPUTS = {
    "task": "Build the inventory ETL pipeline",
    "employees": "data/mock/employees_busy.csv",
    "required_skills": ["Python", "SQL"],
    "priority": "high",
    "deadline": "2026-11-15",
}

CONTENT = {
    "task_summary": "Assign the inventory ETL pipeline build to the recommended developer.",
    "reasoning": "Matches required skills and has available capacity.",
}


def _engine():
    return WorkflowEngine(build_default_registry(FakeLLM(CONTENT)))


def test_wf009_assigns_best_available_employee():
    result = _engine().execute(registry.get_workflow("WF009"), dict(INPUTS))
    assert result.status == "completed"
    summary = result.final_output
    assert summary["task"] == "Build the inventory ETL pipeline"
    assert summary["priority"] == "high"
    assert summary["deadline"] == "2026-11-15"
    assert summary["recommended_employee"]["name"] == "Ana"
    assert summary["score"] == 12.0
    assert "task_summary" in summary
    assert "reasoning" in summary
    decision = [d for d in result.decision_results if d.name == "candidate_fit"][0]
    assert decision.result is True
    assert decision.message == "4 of 5 candidates fit the assignment"
    assert decision.rule == "gt"


def test_wf009_ranking_order_prefers_skills_then_capacity():
    result = _engine().execute(registry.get_workflow("WF009"), dict(INPUTS))
    assert result.status == "completed"
    ranked_step = [s for s in result.steps if s.step == "rank candidates"][0]
    names = [entry["candidate"]["name"] for entry in ranked_step.output]
    assert names == ["Ana", "Cara", "Eve", "Bob", "Dan"]
    scores = [entry["score"] for entry in ranked_step.output]
    assert all(scores[i] >= scores[i + 1] for i in range(len(scores) - 1))


def test_wf009_escalates_when_no_suitable_employee():
    result = _engine().execute(registry.get_workflow("WF009"), dict(BUSY_INPUTS))
    assert result.status == "failed"
    assert "escalate for manual assignment" in result.error
    select_step = [s for s in result.steps if s.step == "select employee"][0]
    assert select_step.status == "failed"


def test_wf009_missing_task_blocks_workflow():
    inputs = dict(INPUTS)
    inputs["task"] = ""
    result = _engine().execute(registry.get_workflow("WF009"), inputs)
    assert result.status == "failed"
    assert result.error == "Missing required inputs: task"


def test_wf009_via_service_with_fake_llm():
    response = dict(CONTENT)
    response.update({"workflow_id": "WF009", "inputs": dict(INPUTS), "rationale": "best effort assignment"})
    service = AgentService(llm=FakeLLM(response))
    body = service.run("Assign this urgent task to the best available developer.")
    assert body["workflow_id"] == "WF009"
    assert body["status"] == "completed"
    assert body["final_output"]["recommended_employee"]["name"] == "Ana"
    assert len(body["decision_results"]) == 1