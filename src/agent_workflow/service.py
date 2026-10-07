from .agent import Agent
from .engine import WorkflowEngine
from .llm import LLMClient
from .registry import WorkflowRegistry
from .tools import build_default_registry


class AgentService:
    def __init__(self, registry=None, tools=None, engine=None, llm=None):
        self.registry = registry if registry is not None else WorkflowRegistry().load()
        self.llm = llm if llm is not None else LLMClient()
        self.tools = tools if tools is not None else build_default_registry(self.llm)
        self.engine = engine if engine is not None else WorkflowEngine(self.tools)

    def run(self, user_message: str) -> dict:
        selection = Agent(self.registry, self.llm).select_workflow(user_message)
        definition = self.registry.get_workflow(selection.workflow_id)
        execution = self.engine.execute(definition, selection.inputs)
        body = execution.to_dict()
        body["rationale"] = selection.rationale
        body["extracted_inputs"] = selection.inputs
        return body