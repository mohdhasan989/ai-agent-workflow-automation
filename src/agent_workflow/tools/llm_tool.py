import json

from ..llm import LLMClient


def build_llm_tools(client=None):
    if client is None:
        client = LLMClient()
    return {
        "llm_generate": _make_generate(client),
        "generate_report": _make_report(client),
    }


def _make_generate(client):
    def llm_generate(system, user, fields, **attributes):
        missing = [name for name, value in attributes.items() if str(value or "").strip() == ""]
        if missing:
            user = (
                f"{user}\nThe following attributes are missing and must not be invented: "
                f"{', '.join(missing)}. Mark each as missing in the output."
            )
        if attributes:
            user = f"{user}\nProduct information: {json.dumps(attributes, ensure_ascii=False)}"
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        data = client.complete_json(messages)
        result = {}
        for field in fields:
            value = data.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                value = "Information missing."
            result[field] = value
        return result

    return llm_generate


def _make_report(client):
    _generate = _make_generate(client)

    def generate_report(system, user, fields, **context):
        messages = [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": f"{user}\nContext: {json.dumps(context, ensure_ascii=False, default=str)}",
            },
        ]
        data = client.complete_json(messages)
        result = {}
        for field in fields:
            value = data.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                value = "Information missing."
            result[field] = value
        for key, value in context.items():
            if isinstance(value, dict):
                result.update(value)
            else:
                result.setdefault(key, value)
        return result

    return generate_report