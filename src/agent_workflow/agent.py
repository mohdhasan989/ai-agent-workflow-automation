from dataclasses import dataclass

from .llm import LLMClient
from .registry import WorkflowRegistry

SYSTEM_PROMPT = (
    "You are a workflow selector. Choose exactly one workflow from the list for the user request.\n"
    'Reply with JSON only: {"workflow_id": "...", "inputs": {...}, "rationale": "..."}\n'
    "Extract inputs from the request only when the user provided them; do not invent values.\n"
    "Available workflows:\n{manifest}"
)


class AgentError(Exception):
    pass


@dataclass(frozen=True)
class SelectionResult:
    workflow_id: str
    inputs: dict
    rationale: str


def build_workflow_manifest(workflows) -> str:
    lines = [
        f"- {workflow.workflow_id}: {workflow.workflow_name} | "
        f"Trigger: {workflow.trigger} | Inputs: {'; '.join(workflow.inputs)}"
        for workflow in workflows
    ]
    return "\n".join(lines)


class Agent:
    def __init__(self, registry: WorkflowRegistry, llm: LLMClient):
        self.registry = registry
        self.llm = llm

    def select_workflow(self, user_message: str) -> SelectionResult:
        manifest = build_workflow_manifest(self.registry.get_all_workflows())
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT.replace("{manifest}", manifest)},
            {"role": "user", "content": user_message},
        ]
        data = self.llm.complete_json(messages)
        workflow_id = data.get("workflow_id")
        if workflow_id not in self.registry.workflows:
            raise AgentError(f"LLM returned unknown workflow_id: {workflow_id}")
        inputs = data.get("inputs", {})
        if not isinstance(inputs, dict):
            raise AgentError("LLM returned inputs that are not an object")
        return SelectionResult(
            workflow_id=workflow_id,
            inputs=inputs,
            rationale=data.get("rationale", ""),
        )