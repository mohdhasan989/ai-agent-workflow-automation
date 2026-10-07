import pytest

from agent_workflow.engine import WorkflowEngine
from agent_workflow.registry import WorkflowRegistry
from agent_workflow.service import AgentService
from agent_workflow.tools import build_default_registry
from tests.fakes import FakeLLM

registry = WorkflowRegistry().load()

COMPLETE = {
    "name": "Steel Pour-Over Kettle",
    "category": "Coffee Equipment",
    "attributes": "gooseneck spout, 1 liter capacity",
    "material": "stainless steel",
    "color": "Matte Black",
    "target_audience": "Home baristas",
}

CONTENT = {
    "product_description": "A precise gooseneck kettle for pour-over brewing.",
    "short_description": "Precision pour-over kettle.",
    "seo_title": "Steel Pour-Over Kettle | Coffee Equipment",
    "meta_description": "A precise gooseneck kettle for the home barista.",
}


def _engine(response=None):
    response = response if response is not None else CONTENT
    return WorkflowEngine(build_default_registry(FakeLLM(response)))


def test_wf004_complete_product_information():
    result = _engine().execute(registry.get_workflow("WF004"), dict(COMPLETE))
    assert result.status == "completed"
    payload = result.final_output
    for field in ["product_description", "short_description", "seo_title", "meta_description"]:
        assert field in payload
        assert payload[field]
    decision = [d for d in result.decision_results if d.name == "content_complete"][0]
    assert decision.result is False
    assert decision.message == "0 of 1 content fields marked as missing"


def test_wf004_missing_required_attribute_blocks_workflow():
    inputs = dict(COMPLETE)
    inputs["name"] = ""
    result = _engine().execute(registry.get_workflow("WF004"), inputs)
    assert result.status == "failed"
    assert result.error == "Missing required inputs: name"
    assert result.steps[0].status == "failed"


def test_wf004_marks_missing_attribute_in_llm_prompt():
    fake = FakeLLM(CONTENT)
    inputs = dict(COMPLETE)
    inputs["material"] = ""
    engine = WorkflowEngine(build_default_registry(fake))
    result = engine.execute(registry.get_workflow("WF004"), inputs)
    assert result.status == "completed"
    flat = " ".join(message["content"] for call in fake.all_messages for message in call)
    assert "material" in flat
    assert "must not be invented" in flat


def test_wf004_marks_missing_llm_field_as_information_missing():
    response = dict(CONTENT)
    response["product_description"] = ""
    result = _engine(response).execute(registry.get_workflow("WF004"), dict(COMPLETE))
    assert result.status == "completed"
    assert result.final_output["product_description"] == "Information missing."
    decision = [d for d in result.decision_results if d.name == "content_complete"][0]
    assert decision.result is True
    assert decision.message == "1 of 1 content fields marked as missing"


def test_wf004_via_service_with_fake_llm():
    response = dict(CONTENT)
    response.update(
        {"workflow_id": "WF004", "inputs": dict(COMPLETE), "rationale": "product copy needed"}
    )
    service = AgentService(llm=FakeLLM(response))
    body = service.run("Generate SEO content for this product.")
    assert body["workflow_id"] == "WF004"
    assert body["status"] == "completed"
    for field in ["product_description", "short_description", "seo_title", "meta_description"]:
        assert body["final_output"][field]
    assert len(body["decision_results"]) == 1