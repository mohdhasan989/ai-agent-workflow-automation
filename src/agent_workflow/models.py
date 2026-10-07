from dataclasses import dataclass


@dataclass(frozen=True)
class WorkflowDefinition:
    workflow_id: str
    workflow_name: str
    trigger: str
    inputs: list[str]
    steps: list[str]
    decision_logic: str
    tools_required: list[str]
    expected_output: str


@dataclass(frozen=True)
class TestQuestion:
    workflow_id: str
    test_request: str
    what_to_check: str
