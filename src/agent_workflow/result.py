from dataclasses import dataclass, field


@dataclass
class StepResult:
    step: str
    status: str
    tool: str | None = None
    output: object = None
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "step": self.step,
            "status": self.status,
            "tool": self.tool,
            "output": self.output,
            "error": self.error,
        }


@dataclass
class DecisionResult:
    name: str
    rule: str
    values: dict
    result: bool
    message: str
    escalated: bool = False

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "rule": self.rule,
            "values": self.values,
            "result": self.result,
            "message": self.message,
            "escalated": self.escalated,
        }


@dataclass
class ExecutionResult:
    workflow_id: str
    workflow_name: str
    status: str
    steps: list
    final_output: object = None
    error: str | None = None
    decision_results: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "workflow_id": self.workflow_id,
            "workflow_name": self.workflow_name,
            "status": self.status,
            "steps": [step.to_dict() for step in self.steps],
            "final_output": self.final_output,
            "error": self.error,
            "decision_results": [decision.to_dict() for decision in self.decision_results],
        }