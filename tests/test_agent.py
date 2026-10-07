import pytest

from agent_workflow.agent import Agent, AgentError
from agent_workflow.llm import LLMClient, LLMError
from agent_workflow.registry import WorkflowRegistry
from tests.fakes import FakeLLM

registry = WorkflowRegistry().load()


def test_agent_selects_wf001_from_request():
    fake = FakeLLM(
        {
            "workflow_id": "WF001",
            "inputs": {"minimum_stock": 5},
            "rationale": "User asked about restocking",
        }
    )
    agent = Agent(registry, fake)
    selection = agent.select_workflow("Which products need restocking?")
    assert selection.workflow_id == "WF001"
    assert selection.inputs == {"minimum_stock": 5}
    assert selection.rationale == "User asked about restocking"
    assert fake.messages[-1]["content"] == "Which products need restocking?"


def test_agent_selects_wf002_from_request():
    fake = FakeLLM(
        {
            "workflow_id": "WF002",
            "inputs": {"internal_price": 120, "vendor_price": 100},
            "rationale": "Price comparison requested",
        }
    )
    agent = Agent(registry, fake)
    selection = agent.select_workflow("Find products where vendor price differs by more than 10%.")
    assert selection.workflow_id == "WF002"
    assert selection.inputs == {"internal_price": 120, "vendor_price": 100}


def test_manifest_contains_workflow_candidates_from_excel():
    fake = FakeLLM({"workflow_id": "WF001", "inputs": {}, "rationale": ""})
    Agent(registry, fake).select_workflow("Which products need restocking?")
    system_content = fake.messages[0]["content"]
    assert "WF001: Inventory Restock Check" in system_content
    assert "User asks which products need restocking" in system_content
    assert "Product inventory CSV; minimum stock threshold" in system_content
    assert "WF002: Product Price Validation" in system_content
    assert "WF010: Workflow Performance Report" in system_content


def test_returned_workflow_id_is_validated_against_registry():
    fake = FakeLLM({"workflow_id": "WF001", "inputs": {}, "rationale": ""})
    selection = Agent(registry, fake).select_workflow("anything")
    assert selection.workflow_id in registry.workflows


def test_invalid_workflow_id_raises_controlled_error():
    fake = FakeLLM({"workflow_id": "WF999", "inputs": {}, "rationale": ""})
    agent = Agent(registry, fake)
    with pytest.raises(AgentError):
        agent.select_workflow("anything")


def test_missing_workflow_id_raises_controlled_error():
    fake = FakeLLM({"inputs": {}, "rationale": ""})
    agent = Agent(registry, fake)
    with pytest.raises(AgentError):
        agent.select_workflow("anything")


def test_non_object_inputs_raises_controlled_error():
    fake = FakeLLM({"workflow_id": "WF001", "inputs": "bad", "rationale": ""})
    agent = Agent(registry, fake)
    with pytest.raises(AgentError):
        agent.select_workflow("anything")


def test_llm_client_config_loaded_from_environment(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    monkeypatch.setenv("LLM_BASE_URL", "https://example.test/v1/")
    client = LLMClient()
    assert client.api_key == "test-key"
    assert client.model == "test-model"
    assert client.base_url == "https://example.test/v1"


def test_llm_client_missing_api_key_raises_before_network(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    client = LLMClient(api_key="", model="m", base_url="https://example.test/v1")
    with pytest.raises(LLMError):
        client.complete([{"role": "user", "content": "hello"}])