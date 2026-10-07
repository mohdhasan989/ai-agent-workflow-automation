from agent_workflow.engine import WorkflowEngine
from agent_workflow.registry import WorkflowRegistry
from agent_workflow.service import AgentService
from agent_workflow.tools import build_default_registry
from tests.fakes import FakeLLM

registry = WorkflowRegistry().load()
engine = WorkflowEngine(build_default_registry())


def test_wf005_valid_order_id():
    result = engine.execute(registry.get_workflow("WF005"), {"order_id": "ORD-1001"})
    assert result.status == "completed"
    status = result.final_output
    assert status["order_id"] == "ORD-1001"
    assert status["items"] == "Ceramic Mug; Pour-Over Kettle"
    assert status["order_status"] == "shipped"
    assert status["shipment_status"] == "delivered"
    assert status["tracking_number"] == "TRACK-9F8Z7Q"
    decision = [d for d in result.decision_results if d.name == "order_match"][0]
    assert decision.result is True
    assert decision.message == "1 of 1 orders matched the provided identifier"


def test_wf005_valid_customer_email():
    result = engine.execute(registry.get_workflow("WF005"), {"customer_email": "bob@example.com"})
    assert result.status == "completed"
    status = result.final_output
    assert status["order_id"] == "ORD-1002"
    assert status["order_status"] == "processing"
    assert status["shipment_status"] == "in transit"


def test_wf005_shipment_information_available():
    result = engine.execute(registry.get_workflow("WF005"), {"order_id": "ORD-1002"})
    assert result.status == "completed"
    assert result.final_output["tracking_number"] == "TRACK-3A2B1C"


def test_wf005_tracking_information_unavailable():
    result = engine.execute(registry.get_workflow("WF005"), {"order_id": "ORD-1003"})
    assert result.status == "completed"
    status = result.final_output
    assert status["order_status"] == "pending"
    assert status["shipment_status"] == "label created"
    assert "tracking_number" not in status


def test_wf005_order_not_found_asks_for_another_identifier():
    result = engine.execute(registry.get_workflow("WF005"), {"order_id": "ORD-9999"})
    assert result.status == "failed"
    assert "No order found" in result.error
    assert "another order ID or customer email" in result.error
    decision = [d for d in result.decision_results if d.name == "order_match"][0]
    assert decision.result is False
    assert decision.message == "0 of 0 orders matched the provided identifier"


def test_wf005_missing_identifier_fails():
    result = engine.execute(registry.get_workflow("WF005"), {"order_id": "", "customer_email": ""})
    assert result.status == "failed"
    assert "at least one of order_id, customer_email" in result.error
    assert result.steps[0].status == "failed"


def test_wf005_all_steps_executed_on_success():
    result = engine.execute(registry.get_workflow("WF005"), {"order_id": "ORD-1001"})
    assert [step.step for step in result.steps] == [
        "Validate identifier",
        "search order data",
        "retrieve order status",
        "retrieve shipment information",
        "summarize current status",
    ]
    assert all(step.status == "executed" for step in result.steps)


def test_wf005_via_service_with_fake_llm():
    service = AgentService(
        llm=FakeLLM(
            {
                "workflow_id": "WF005",
                "inputs": {"order_id": "ORD-1002"},
                "rationale": "order status lookup",
            }
        )
    )
    body = service.run("Where is my order?")
    assert body["workflow_id"] == "WF005"
    assert body["status"] == "completed"
    assert body["final_output"]["order_id"] == "ORD-1002"
    assert body["final_output"]["tracking_number"] == "TRACK-3A2B1C"
    assert len(body["decision_results"]) == 1