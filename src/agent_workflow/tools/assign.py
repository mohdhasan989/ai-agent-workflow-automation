from .io import read_csv


def require_fields(**fields):
    missing = [name for name, value in fields.items() if str(value or "").strip() == ""]
    if missing:
        raise ValueError(f"Missing required inputs: {', '.join(missing)}")
    return fields


def summarize_products(products, name_field="name"):
    rows = read_csv(products) if isinstance(products, str) else products
    return {
        "product_count": len(rows),
        "product_names": [str(row.get(name_field, "") or "") for row in rows],
    }


def match_skills(employees, required_skills, skill_field="skills", delimiter=";"):
    rows = read_csv(employees) if isinstance(employees, str) else employees
    required = [str(skill).strip().lower() for skill in (required_skills or [])]
    result = []
    for row in rows:
        skills = [
            skill.strip().lower()
            for skill in str(row.get(skill_field, "") or "").split(delimiter)
            if skill.strip()
        ]
        matched = [skill for skill in required if skill in skills]
        updated = dict(row)
        updated["skill_match_count"] = len(matched)
        updated["skill_match_fraction"] = round(len(matched) / len(required), 3) if required else 0.0
        result.append(updated)
    return result


def check_capacity(employees, workload_field="workload", capacity_field="capacity"):
    result = []
    for row in employees:
        updated = dict(row)
        updated["available_capacity"] = round(
            _number(row.get(capacity_field), 0.0) - _number(row.get(workload_field), 0.0), 3
        )
        result.append(updated)
    return result


def _number(value, default):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def select_best(ranked, skill_field="skill_match_fraction", capacity_field="available_capacity"):
    for entry in ranked:
        candidate = entry["candidate"]
        if (
            _number(candidate.get(skill_field), 0.0) > 0
            and _number(candidate.get(capacity_field), 0.0) > 0
        ):
            return {"recommended_employee": candidate, "score": entry.get("score")}
    raise ValueError("No suitable employee available; escalate for manual assignment")