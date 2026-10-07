def validate_required(data, required_fields: list) -> dict:
    records = data if isinstance(data, list) else [data]
    issues = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            issues.append({"index": index, "missing": list(required_fields)})
            continue
        missing = [
            field
            for field in required_fields
            if str(record.get(field, "")).strip() == ""
        ]
        if missing:
            issues.append({"index": index, "missing": missing})
    return {"valid": not issues, "issues": issues}