def _pct_diff(a, b):
    if b == 0:
        raise ValueError("pct_diff reference value cannot be zero")
    return (a - b) / b * 100


def calculate(operation: str, *values):
    if operation in ("add", "subtract", "multiply", "divide"):
        if len(values) != 2:
            raise ValueError(f"{operation} requires exactly 2 values")
    if operation == "add":
        return values[0] + values[1]
    if operation == "subtract":
        return values[0] - values[1]
    if operation == "multiply":
        return values[0] * values[1]
    if operation == "divide":
        if values[1] == 0:
            raise ValueError("divide requires a nonzero divisor")
        return values[0] / values[1]
    if operation == "sum":
        return sum(values)
    if operation == "average":
        if not values:
            raise ValueError("average requires at least one value")
        return sum(values) / len(values)
    if operation == "pct_diff":
        if len(values) != 2:
            raise ValueError("pct_diff requires exactly 2 values")
        return _pct_diff(values[0], values[1])
    raise ValueError(f"Unknown calculation: {operation}")