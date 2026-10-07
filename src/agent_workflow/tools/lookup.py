from .io import read_csv


def require_any(**fields):
    provided = {name: value for name, value in fields.items() if str(value or "").strip()}
    if not provided:
        raise ValueError(
            f"Missing required inputs: at least one of {', '.join(fields)} must be provided"
        )
    return provided


def find_rows(rows, **criteria):
    records = read_csv(rows) if isinstance(rows, str) else rows
    result = []
    for row in records:
        matches = True
        for name, value in criteria.items():
            if str(value or "").strip() == "":
                continue
            if str(row.get(name, "") or "").strip().lower() != str(value).strip().lower():
                matches = False
                break
        if matches:
            result.append(row)
    return result


def first_record(rows, not_found_message="No matching record found"):
    if not rows:
        raise ValueError(not_found_message)
    return rows[0]


def attach_lookup(rows, source, left_on="id", right_on="id"):
    records = rows if isinstance(rows, list) else [rows]
    lookup_rows = read_csv(source) if isinstance(source, str) else source
    lookup = {str(row.get(right_on)): row for row in lookup_rows}
    output = []
    for row in records:
        match = lookup.get(str(row.get(left_on)))
        updated = dict(row)
        if match is not None:
            for key, value in match.items():
                if key != right_on:
                    updated[key] = value
        output.append(updated)
    return output if isinstance(rows, list) else output[0]


def summarize_record(record, required_fields, optional_fields=None):
    result = {}
    for field in required_fields:
        result[field] = record.get(field)
    for field in optional_fields or []:
        value = record.get(field)
        if value is not None and str(value).strip():
            result[field] = value
    return result