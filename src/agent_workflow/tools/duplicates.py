from .text import text_similarity
from .text import normalize_text


def find_duplicates(rows, key_fields, similarity_fields, threshold):
    threshold = float(threshold)
    key_groups = {}
    for row in rows:
        key = tuple(_row_key(row, key_fields))
        if not any(key):
            continue
        key_groups.setdefault(key, []).append(row)

    representatives = []
    for key, members in key_groups.items():
        representatives.append((key, members[0]))
    for row in rows:
        key = tuple(_row_key(row, key_fields))
        if not any(key):
            representatives.append((key, row))

    groups = []
    counter = 0
    for members in key_groups.values():
        if len(members) > 1:
            counter += 1
            groups.append(_duplicate_group(counter, "definite", members, list(key_fields), 1.0))

    clusters = []
    for index, (_, row) in enumerate(representatives):
        placed = False
        for cluster in clusters:
            for member_index in cluster:
                if (
                    _record_similarity(representatives[member_index][1], row, similarity_fields)
                    >= threshold
                ):
                    cluster.append(index)
                    placed = True
                    break
            if placed:
                break
        if not placed:
            clusters.append([index])

    for cluster in clusters:
        if len(cluster) > 1:
            counter += 1
            members = [representatives[index][1] for index in cluster]
            confidence = max(
                _record_similarity(representatives[i][1], representatives[j][1], similarity_fields)
                for i in cluster
                for j in cluster
                if i < j
            )
            groups.append(
                _duplicate_group(counter, "possible", members, list(similarity_fields), confidence)
            )

    for index, (_, row) in enumerate(representatives):
        cluster = next(c for c in clusters if index in c)
        if len(cluster) == 1:
            counter += 1
            groups.append(_duplicate_group(counter, "unique", [row], [], None))
    return groups


def _row_key(row, key_fields):
    return [normalize_text(str(row.get(field, "") or "")) for field in key_fields]


def _record_similarity(left, right, fields):
    a = " ".join(str(left.get(field, "") or "") for field in fields)
    b = " ".join(str(right.get(field, "") or "") for field in fields)
    if not a.strip() or not b.strip():
        return 0.0
    return text_similarity(a, b)


def _duplicate_group(group_id, group_type, members, matched_fields, confidence):
    return {
        "group_id": f"G{group_id}",
        "type": group_type,
        "members": members,
        "matched_fields": matched_fields,
        "confidence": confidence,
    }