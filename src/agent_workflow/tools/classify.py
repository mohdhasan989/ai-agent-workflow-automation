from ..decisions import DecisionEvaluator

_EVALUATOR = DecisionEvaluator()


def classify_labels(rows, rules, output_field):
    return [{**row, output_field: _resolve_label(row, rules)} for row in rows]


def _resolve_label(row, rules):
    for rule in rules:
        if _conditions_met(row, rule.get("matches", [])):
            return rule["label"]
    return ""


def _conditions_met(row, conditions):
    if not conditions:
        return True
    for condition in conditions:
        value = str(row.get(condition["field"], "") or "").lower()
        pattern = str(condition.get("pattern", "")).lower()
        if pattern in value:
            return True
    return False


def tag_rows(rows, rule, output_field, true_value, false_value):
    return [
        {**row, output_field: true_value if _EVALUATOR.matches(rule, row) else false_value}
        for row in rows
    ]