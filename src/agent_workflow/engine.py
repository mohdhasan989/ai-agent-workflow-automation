import json
from pathlib import Path

from .decisions import DecisionEvaluator
from .models import WorkflowDefinition
from .result import DecisionResult, ExecutionResult, StepResult

DEFAULT_BINDINGS = Path(__file__).resolve().parents[2] / "config" / "bindings.json"
DEFAULT_DECISIONS = Path(__file__).resolve().parents[2] / "config" / "decisions.json"


class WorkflowEngine:
    def __init__(self, tools, bindings=None, decisions=None):
        self.tools = tools
        if bindings is None:
            bindings = json.loads(DEFAULT_BINDINGS.read_text(encoding="utf-8"))
        elif isinstance(bindings, (str, Path)):
            bindings = json.loads(Path(bindings).read_text(encoding="utf-8"))
        self._bindings = {
            f"{binding['workflow_id']}|{binding['step']}": binding
            for binding in bindings["bindings"]
        }
        if decisions is None:
            decisions = json.loads(DEFAULT_DECISIONS.read_text(encoding="utf-8"))
        elif isinstance(decisions, (str, Path)):
            decisions = json.loads(Path(decisions).read_text(encoding="utf-8"))
        self._decisions = {}
        for decision in decisions.get("decisions", []):
            for key in ("workflow_id", "step", "name", "rule"):
                if key not in decision:
                    raise ValueError(f"Decision is missing '{key}'")
            self._decisions.setdefault(
                f"{decision['workflow_id']}|{decision['step']}", []
            ).append(decision)
        self._evaluator = DecisionEvaluator()

    def execute(self, definition: WorkflowDefinition, inputs: dict) -> ExecutionResult:
        context = dict(inputs)
        steps = []
        decision_results = []
        for step_name in definition.steps:
            binding = self._bindings.get(f"{definition.workflow_id}|{step_name}")
            if binding is None:
                steps.append(StepResult(step=step_name, status="skipped"))
                continue
            try:
                tool = self.tools.get(binding["tool"])
                params = binding.get("params", {})
                output = tool(
                    *self._resolve(params.get("args", []), context),
                    **self._resolve(params.get("kwargs", {}), context),
                )
            except Exception as error:
                steps.append(
                    StepResult(
                        step=step_name,
                        status="failed",
                        tool=binding["tool"],
                        error=str(error),
                    )
                )
                break
            context[binding.get("output", step_name)] = output
            try:
                for decision in self._decisions.get(
                    f"{definition.workflow_id}|{step_name}", []
                ):
                    outcome = self._evaluator.evaluate(
                        decision["rule"], self._resolve(decision.get("data"), context)
                    )
                    message = decision.get("message", "")
                    message = message.format(
                        count=outcome["matched_count"], total=outcome["total"]
                    )
                    decision_results.append(
                        DecisionResult(
                            name=decision["name"],
                            rule=decision["rule"]["op"],
                            values=outcome["values"],
                            result=outcome["result"],
                            message=message,
                            escalated=outcome["escalated"],
                        )
                    )
            except Exception as error:
                steps.append(
                    StepResult(
                        step=step_name,
                        status="failed",
                        tool=binding["tool"],
                        error=f"Decision evaluation failed: {error}",
                    )
                )
                break
            steps.append(
                StepResult(
                    step=step_name,
                    status="executed",
                    tool=binding["tool"],
                    output=output,
                )
            )
        failed = any(step.status == "failed" for step in steps)
        status = "failed" if failed else "completed"
        last_executed = next(
            (step for step in reversed(steps) if step.status == "executed"), None
        )
        return ExecutionResult(
            workflow_id=definition.workflow_id,
            workflow_name=definition.workflow_name,
            status=status,
            steps=steps,
            final_output=last_executed.output if last_executed else None,
            error=steps[-1].error if failed and steps else None,
            decision_results=decision_results,
        )

    def _resolve(self, value, context):
        if isinstance(value, list):
            return [self._resolve(item, context) for item in value]
        if isinstance(value, dict):
            return {key: self._resolve(item, context) for key, item in value.items()}
        if isinstance(value, str) and value.startswith("$"):
            key = value[1:]
            return context.get(key, "")
        return value