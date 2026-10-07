def rank(candidates: list, criteria: list) -> list:
    def score(item):
        return sum(c["weight"] * float(item.get(c["field"], 0)) for c in criteria)

    results = [{"candidate": item, "score": score(item)} for item in candidates]
    results.sort(key=lambda result: result["score"], reverse=True)
    return results