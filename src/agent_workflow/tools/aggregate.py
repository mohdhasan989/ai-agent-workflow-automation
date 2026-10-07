def group_rows(rows, field):
    groups = {}
    order = []
    for row in rows:
        key = str(row.get(field, "") or "").strip()
        if not key:
            continue
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(row)
    return [{"key": key, "rows": groups[key]} for key in order]


def count_groups(groups):
    items = [{"key": group["key"], "count": len(group["rows"])} for group in groups]
    items.sort(key=lambda item: item["count"], reverse=True)
    return items


def report_counts(counts):
    return {
        "counts": counts,
        "total_groups": len(counts),
        "empty": not counts,
        "message": "No rows found in the provided source." if not counts else None,
    }