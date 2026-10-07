from .calc import calculate
from .io import read_csv
from .text import normalize_text
from .validation import validate_required


def _to_number(value):
    if isinstance(value, str):
        value = value.strip()
    return float(value)


def transform_rows(rows, output_field, operation, fields):
    result = []
    for row in rows:
        values = [_to_number(row.get(field)) for field in fields]
        computed = calculate(operation, *values)
        updated = dict(row)
        updated[output_field] = computed
        result.append(updated)
    return result


_COMPARATORS = {
    "lt": lambda a, b: a < b,
    "le": lambda a, b: a <= b,
    "gt": lambda a, b: a > b,
    "ge": lambda a, b: a >= b,
    "eq": lambda a, b: a == b,
    "ne": lambda a, b: a != b,
    "outside": lambda a, b: abs(a) > b,
}


def filter_rows(rows, field, operator, value):
    if operator not in _COMPARATORS:
        raise ValueError(f"Unknown filter operator: {operator}")
    compare = _COMPARATORS[operator]
    matched = []
    for row in rows:
        raw = row.get(field)
        if raw is None:
            continue
        try:
            left = float(raw)
            right = float(value)
            operands = (left, right)
        except (TypeError, ValueError):
            operands = (str(raw), str(value))
        if compare(*operands):
            matched.append(row)
    return matched


def select_columns(rows, columns):
    return [{column: row[column] for column in columns} for row in rows]


def normalize_fields(rows, fields):
    result = []
    for row in rows:
        updated = dict(row)
        for field in fields:
            if field in updated:
                updated[field] = normalize_text(updated[field])
        result.append(updated)
    return result


def partition_rows(rows, required_fields):
    validation = validate_required(rows, required_fields)
    invalid_indexes = {issue["index"] for issue in validation["issues"]}
    cleaned_rows = [row for index, row in enumerate(rows) if index not in invalid_indexes]
    invalid_rows = [row for index, row in enumerate(rows) if index in invalid_indexes]
    return {
        "cleaned_rows": cleaned_rows,
        "invalid_rows": invalid_rows,
        "summary": {
            "total": len(rows),
            "valid": len(cleaned_rows),
            "invalid": len(invalid_rows),
        },
    }


def dedupe_rows(rows, key_field):
    seen = set()
    result = []
    for row in rows:
        key = str(row.get(key_field, "")).strip()
        if key in seen:
            continue
        seen.add(key)
        result.append(row)
    return result


def join_rows(left, right, left_on, right_on):
    right_rows = read_csv(right) if isinstance(right, str) else right
    lookup = {str(row.get(right_on)): row for row in right_rows}
    joined = []
    for row in left:
        match = lookup.get(str(row.get(left_on)))
        if match is None:
            continue
        combined = dict(row)
        for key, value in match.items():
            if key != right_on:
                combined[key] = value
        joined.append(combined)
    return joined