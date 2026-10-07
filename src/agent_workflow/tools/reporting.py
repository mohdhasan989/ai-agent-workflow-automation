from ..decisions import DecisionEvaluator
from .calc import calculate


def group_metrics(rows, group_field="workflow_id", status_field="status", success_value="success"):
    groups = {}
    order = []
    for row in rows:
        key = str(row.get(group_field, "")).strip()
        if not key:
            continue
        if key not in groups:
            groups[key] = {"workflow_id": key, "total": 0, "successful": 0, "failed": 0}
            order.append(key)
        groups[key]["total"] += 1
        if str(row.get(status_field, "")).strip() == success_value:
            groups[key]["successful"] += 1
        else:
            groups[key]["failed"] += 1
    result = []
    for key in order:
        record = groups[key]
        record["success_rate"] = round(record["successful"] / record["total"], 4) if record["total"] else 0.0
        record["failure_rate"] = round(record["failed"] / record["total"], 4) if record["total"] else 0.0
        result.append(record)
    return result


def with_averages(metrics, rows, group_field="workflow_id", time_field="execution_time_s"):
    values = {}
    for row in rows:
        key = str(row.get(group_field, "")).strip()
        if not key:
            continue
        try:
            value = float(row.get(time_field))
        except (TypeError, ValueError):
            continue
        values.setdefault(key, []).append(value)
    result = []
    for record in metrics:
        key = record["workflow_id"]
        times = values.get(key, [])
        updated = dict(record)
        updated["executions"] = len(times)
        updated["total_time_s"] = round(calculate("sum", *times), 4) if times else 0.0
        updated["average_time_s"] = round(calculate("average", *times), 4) if times else 0.0
        result.append(updated)
    return result


def frequent_errors(rows, error_field="error", min_count=2):
    counts = {}
    for row in rows:
        error = str(row.get(error_field, "")).strip()
        if not error:
            continue
        counts[error] = counts.get(error, 0) + 1
    items = [{"error": error, "count": count} for error, count in counts.items() if count >= min_count]
    items.sort(key=lambda item: item["count"], reverse=True)
    return items


def slow_steps(rows, step_field="slowest_step", time_field="execution_time_s", min_average=5.0):
    values = {}
    for row in rows:
        step = str(row.get(step_field, "")).strip()
        if not step:
            continue
        try:
            value = float(row.get(time_field))
        except (TypeError, ValueError):
            continue
        values.setdefault(step, []).append(value)
    items = []
    for step, times in values.items():
        average = calculate("average", *times)
        if average > min_average:
            items.append({"step": step, "executions": len(times), "average_time_s": round(average, 4)})
    items.sort(key=lambda item: item["average_time_s"], reverse=True)
    return items


def build_report(metrics, error_counts, slow_steps, rule, failure_threshold=0.10, time_threshold=10.0):
    evaluator = DecisionEvaluator()
    flagged = [record for record in metrics if evaluator.matches(rule, record)]
    recommendations = []
    for record in flagged:
        failure = float(record.get("failure_rate", 0.0) or 0.0)
        average = float(record.get("average_time_s", 0.0) or 0.0)
        if failure > failure_threshold:
            recommendations.append(
                f"Workflow {record['workflow_id']} failure rate ({failure:.0%}) "
                f"exceeds the threshold ({failure_threshold:.0%})"
            )
        if average > time_threshold:
            recommendations.append(
                f"Workflow {record['workflow_id']} average execution time "
                f"({average:g}s) exceeds the defined threshold ({time_threshold:g}s)"
            )
    for item in error_counts:
        recommendations.append(
            f"Fix frequent error '{item['error']}' which occurred {item['count']} times"
        )
    for item in slow_steps:
        recommendations.append(
            f"Optimize slow step '{item['step']}' with average {item['average_time_s']:g}s"
        )
    return {
        "metrics": metrics,
        "flagged_workflows": flagged,
        "frequent_errors": error_counts,
        "slow_steps": slow_steps,
        "recommendations": recommendations,
    }