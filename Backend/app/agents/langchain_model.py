"""LangChain boundary for serializable conversations and OpenAI tool schemas."""
import json
import os


def make_model():
    """Initialize lazily, so missing configuration does not prevent startup."""
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("OPENAI_API_KEY is required")
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(api_key=api_key, model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
                      base_url="https://api.openai.com/v1", timeout=60.0,
                      max_retries=2, use_responses_api=False)


def _as_dict(value):
    return value if isinstance(value, dict) else value.model_dump(exclude_none=True)


def _function_call(call):
    """Preserve raw invalid JSON so execution can produce a matching tool error."""
    call = _as_dict(call)
    if "function" in call:
        function = _as_dict(call["function"])
        name, arguments = function["name"], function.get("arguments", "{}")
    else:
        name, arguments = call["name"], call.get("args", {})
    if not isinstance(arguments, str):
        arguments = json.dumps(arguments, ensure_ascii=False)
    if not call.get("id"):
        raise ValueError("Tool call is missing its result correlation ID")
    return {"id": call["id"], "type": "function",
            "function": {"name": name, "arguments": arguments}}


def _request_message(message):
    """Exclude presentation context and local error flags from model requests."""
    data = _as_dict(message)
    role = data.get("role")
    if role not in {"system", "developer", "user", "assistant", "tool"}:
        raise ValueError("Unsupported conversation role")
    clean = {"role": role, "content": data.get("content") or ""}
    if role == "assistant" and data.get("tool_calls"):
        clean["tool_calls"] = [_function_call(call) for call in data["tool_calls"]]
    if role == "tool":
        clean["tool_call_id"] = data["tool_call_id"]
    return clean


def _text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            block if isinstance(block, str) else block["text"]
            for block in content
            if isinstance(block, str) or (
                isinstance(block, dict) and block.get("type") in {"text", "output_text"}
                and isinstance(block.get("text"), str)))
    return ""


def invoke_model(model, messages, tools, response_schema=None):
    """Use LangChain tool binding and normalize its AIMessage for persistence."""
    options = {}
    if response_schema is not None:
        options['response_format'] = {'type': 'json_schema', 'json_schema': {
            'name': 'easytrip_plan', 'strict': True, 'schema': response_schema}}
    runnable = model.bind_tools(tools, **options) if tools else (model.bind(**options) if options else model)
    answer = runnable.invoke([_request_message(message) for message in messages])
    calls = list(getattr(answer, "tool_calls", None) or [])
    calls.extend(getattr(answer, "invalid_tool_calls", None) or [])
    return {"role": "assistant", "content": _text(answer.content),
            "tool_calls": [_function_call(call) for call in calls]}
