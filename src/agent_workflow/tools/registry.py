class ToolNotFoundError(KeyError):
    pass


class ToolRegistry:
    def __init__(self):
        self._tools = {}

    def register(self, name: str, function):
        self._tools[name] = function

    def get(self, name: str):
        if name not in self._tools:
            raise ToolNotFoundError(f"Unknown tool: {name}")
        return self._tools[name]

    def all(self) -> dict:
        return dict(self._tools)

    def names(self) -> list:
        return list(self._tools)