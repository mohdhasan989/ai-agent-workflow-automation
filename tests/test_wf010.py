import pytest

from agent_workflow.engine import WorkflowEngine
from agent_workflow.registry import WorkflowRegistry
from agent_workflow.service import AgentService
from agent_workflow.tools import build_default_registry
from tests.fakes import FakeLLM

registry = WorkflowRegistry().load()

LOGS = "data/mock/execution_logs.csv"


def _engine():
    return WorkflowEngine(build_default_registry())


def _run(logs_path=LOGS):
    return _engine().execute(registry.get_workflow("WF010"), {"logs_path": logs_path})


def test_wf010_workflow_below_threshold_not_flagged():
    result = _run()
    assert result.status == "completed"
    report = result.final_output
    wf001 = [w for w in report["flagged_workflows"] if w["workflow_id"] == "WF001"]
    assert wf001 == []
    metrics = {m["workflow_id"]: m for m in report["metrics"]}
    assert metrics["WF001"]["total"] == 3
    assert metrics["WF001"]["successful"] == 3
    assert metrics["WF001"]["failed"] == 0
    assert metrics["WF001"]["failure_rate"] == 0.0
    assert metrics["WF001"]["average_time_s"] == 3.0


def test_wf010_workflow_above_failure_threshold_flagged():
    result = _run()
    report = result.final_output
    flagged = {w["workflow_id"]: w for w in report["flagged_workflows"]}
    assert "WF002" in flagged and "WF003" in flagged
    assert flagged["WF003"]["failure_rate"] == pytest.approx(0.3333)
    assert not any(("WF001") == w["workflow_id"] for w in report["flagged_workflows"])


def test_wf010_workflow_above_time_threshold_flagged():
    result = _run()
    report = result.final_output
    flagged = {w["workflow_id"]: w for w in report["flagged_workflows"]}
    assert "WF004" in flagged
    assert flagged["WF004"]["failure_rate"] == 0.0
    assert flagged["WF004"]["average_time_s"] == pytest.approx(10.9)


def test_wf010_workflow_satisfying_both_conditions():
    result = _run()
    report = result.final_output
    flagged = {w["workflow_id"]: w for w in report["flagged_workflows"]}
    assert flagged["WF002"]["failure_rate"] == pytest.approx(0.6667)
    assert flagged["WF002"]["average_time_s"] == pytest.approx(15.2333)
    failure_rec = next(
        r for r in report["recommendations"] if r.startswith("Workflow WF002 failure rate")
    )
    time_rec = next(
        r for r in report["recommendations"] if r.startswith("Workflow WF002 average execution time")
    )
    assert "67%" in failure_rec
    assert "15.2333s" in time_rec


def test_wf010_frequent_error_detection():
    result = _run()
    report = result.final_output
    by_error = {item["error"]: item["count"] for item in report["frequent_errors"]}
    assert by_error == {"TimeoutError": 2}


def test_wf010_slow_step_detection():
    result = _run()
    report = result.final_output
    steps = [item["step"] for item in report["slow_steps"]]
    assert "compare internal and vendor prices" in steps
    assert "normalize column names" in steps
    assert steps[0] == "compare internal and vendor prices"


def test_wf010_report_contains_required_sections():
    result = _run()
    report = result.final_output
    assert set(report) == {"metrics", "flagged_workflows", "frequent_errors", "slow_steps", "recommendations"}
    assert len(report["recommendations"]) > 0


def test_wf010_flag_decision_covers_all_workflows():
    result = _run()
    decision = [d for d in result.decision_results if d.name == "workflow_flag"][0]
    assert decision.result is True
    assert decision.rule == "or"
    assert decision.message == "3 of 4 workflows flagged for review"


def test_wf010_works_with_different_log_data(tmp_path):
    logs = tmp_path / "logs.csv"
    logs.write_text(
        "workflow_id,status,execution_time_s,slowest_step,error\n"
        "X1,success,2.0,step a,\n"
        "X1,failure,3.0,step a,OopsError\n"
        "Y1,success,1.5,step b,\n",
        encoding="utf-8",
    )
    result = _engine().execute(registry.get_workflow("WF010"), {"logs_path": str(logs)})
    assert result.status == "completed"
    report = result.final_output
    metrics = {m["workflow_id"]: m for m in report["metrics"]}
    assert set(metrics) == {"X1", "Y1"}
    assert metrics["X1"]["failed"] == 1
    assert metrics["Y1"]["failure_rate"] == 0.0
    assert metrics["Y1"]["average_time_s"] == 1.5
    assert all(w["workflow_id"] == "X1" for w in report["flagged_workflows"])


def test_wf010_via_service_with_fake_llm():
    service = AgentService(
        llm=FakeLLM(
            {
                "workflow_id": "WF010",
                "inputs": {"logs_path": LOGS},
                "rationale": "aggregate execution logs",
            }
        )
    )
    body = service.run("Which workflows are failing most often?")
    assert body["workflow_id"] == "WF010"
    assert body["status"] == "completed"
    assert set(body["final_output"]) == {
        "metrics",
        "flagged_workflows",
        "frequent_errors",
        "slow_steps",
        "recommendations",
    }
    assert len(body["decision_results"]) == 1