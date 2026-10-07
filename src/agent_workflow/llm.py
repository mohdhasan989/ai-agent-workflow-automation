import json
import os

import httpx

DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_TIMEOUT = 60


class LLMError(Exception):
    pass


class LLMClient:
    def __init__(
        self,
        api_key: str = None,
        model: str = None,
        base_url: str = None,
        timeout: float = None,
    ):
        self.api_key = (
            api_key if api_key is not None else os.getenv("GROQ_API_KEY") or os.getenv("LLM_API_KEY")
        )
        self.model = model if model is not None else os.getenv("LLM_MODEL") or DEFAULT_MODEL
        self.base_url = (
            (base_url if base_url is not None else os.getenv("LLM_BASE_URL") or DEFAULT_BASE_URL)
        ).rstrip("/")
        timeout_value = timeout if timeout is not None else os.getenv("LLM_TIMEOUT")
        self.timeout = float(timeout_value or DEFAULT_TIMEOUT)

    def complete(self, messages: list) -> str:
        if not self.api_key:
            raise LLMError("LLM API key is not set")
        payload = json.dumps({"model": self.model, "messages": messages}).encode("utf-8")
        try:
            response = httpx.post(
                f"{self.base_url}/chat/completions",
                content=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
                timeout=self.timeout,
            )
        except httpx.HTTPError as error:
            raise LLMError(f"LLM request failed: {error}") from None
        if response.status_code != 200:
            raise LLMError(f"LLM request failed: {response.status_code} {response.text}") from None
        try:
            body = response.json()
            return body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, ValueError):
            raise LLMError("LLM response missing expected content") from None

    def complete_json(self, messages: list) -> dict:
        content = self.complete(messages)
        try:
            return json.loads(content)
        except json.JSONDecodeError as error:
            raise LLMError(f"LLM returned invalid JSON: {error}") from None