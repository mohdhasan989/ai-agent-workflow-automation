_CMP_OPERATORS = {
    "lt": lambda a, b: a < b,
    "le": lambda a, b: a <= b,
    "gt": lambda a, b: a > b,
    "ge": lambda a, b: a >= b,
}


def _to_number(value):
    if isinstance(value, bool):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _is_missing(value) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


class DecisionEvaluator:
    def evaluate(self, rule, data):
        op = rule.get("op")
        if op not in _CMP_OPERATORS and op not in ("and", "or", "escalate", "missing", "exists", "in", "eq", "ne"):
            raise ValueError(f"Unknown decision operator: {op}")
        if data is None:
            records = []
        elif isinstance(data, dict):
            records = [data]
        elif isinstance(data, list):
            records = data
        else:
            raise ValueError("Decision data must be a dict or a list of dicts")
        matched = []
        values = {}
        for record in records:
            record = record if isinstance(record, dict) else {}
            is_match, record_values = self._matches(rule, record)
            if not is_match:
                continue
            matched.append(record)
            if not values:
                values = record_values
        return {
            "result": bool(matched),
            "matched": matched,
            "matched_count": len(matched),
            "total": len(records),
            "values": values,
            "escalated": rule.get("op") == "escalate" and bool(matched),
        }

    def matches(self, rule, record):
        return self._matches(rule, record)[0]

    def _resolve(self, ref, record):
        if not isinstance(ref, dict):
            return ref
        if "field" in ref:
            return record.get(ref["field"])
        if "value" in ref:
            return ref["value"]
        return None

    def _matches(self, rule, record):
        op = rule.get("op")
        if op == "and":
            outcomes = [self._matches(sub, record) for sub in rule.get("rules", [])]
            return all(outcome[0] for outcome in outcomes), outcomes[0][1] if outcomes else {}
        if op == "or":
            outcomes = [self._matches(sub, record) for sub in rule.get("rules", [])]
            winner = next((outcome for outcome in outcomes if outcome[0]), None)
            if winner is None:
                return False, outcomes[0][1] if outcomes else {}
            return True, winner[1]
        if op == "escalate":
            is_match, record_values = self._matches(rule["rule"], record)
            return is_match, record_values
        if op == "missing":
            value = self._resolve(rule["left"], record)
            return _is_missing(value), {"field": rule["left"].get("field"), "value": value}
        if op == "exists":
            value = self._resolve(rule["left"], record)
            return not _is_missing(value), {"field": rule["left"].get("field"), "value": value}
        if op == "in":
            value = self._resolve(rule["left"], record)
            return str(value) in [str(item) for item in rule.get("values", [])], {
                "field": rule["left"].get("field"),
                "value": value,
            }
        left = self._resolve(rule.get("left"), record)
        right = self._resolve(rule.get("right"), record)
        values = {"left": left, "right": right}
        if op in _CMP_OPERATORS:
            left_number = _to_number(left)
            right_number = _to_number(right)
            if left_number is not None and right_number is not None:
                return _CMP_OPERATORS[op](left_number, right_number), values
            return _CMP_OPERATORS[op](str(left), str(right)), values
        if op == "eq":
            left_number = _to_number(left)
            right_number = _to_number(right)
            if left_number is not None and right_number is not None:
                return left_number == right_number, values
            return str(left) == str(right), values
        if op == "ne":
            return not self._matches({"op": "eq", "left": rule["left"], "right": rule["right"]}, record)[0], values
        raise ValueError(f"Unknown decision operator: {op}")