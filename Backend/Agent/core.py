import os
import json
import logging
from inspect import signature
from dotenv import load_dotenv
from openai import OpenAI, OpenAIError

from Backend.Agent.tools import TOOLS, TOOL_FUNCTIONS
from Backend.Agent.prompts import SYSTEM_PROMPT
from Backend.Services.progress import report

load_dotenv()

logger = logging.getLogger(__name__)
# Initialize on the first request so a missing key does not prevent app startup.
client = None
MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
MAX_TURNS = 10


def _finish(messages: list, content: str) -> list:
    """Keep the return type consistent on all handled failure paths."""
    messages.append({"role": "assistant", "content": content, "error": True})
    return messages


def _execute_tool(tool_call) -> str:
    """Return JSON text for every tool call, including failed calls."""
    name = tool_call.function.name
    if name not in TOOL_FUNCTIONS:
        return json.dumps({"error": "Unknown tool. Choose one of the available tools."})
    try:
        args = json.loads(tool_call.function.arguments)
        if not isinstance(args, dict):
            raise ValueError("Tool arguments must be an object")
        func = TOOL_FUNCTIONS[name]
        signature(func).bind(**args)
    except (ValueError, TypeError):
        return json.dumps({"error": "Invalid tool arguments. Check the tool schema and try again."})

    try:
        report({'geocode_city': 'Finding your destination…', 'search_pois': 'Searching free place listings…', 'lookup_travel_info': 'Reading the travel guide…'}.get(name, 'Checking travel information…'))
        result = func(**args)
        return json.dumps(result, ensure_ascii=False)
    except Exception as exc:
        # External tools may raise different exception types. Do not expose
        # credentials, request URLs, or service internals to the model or UI.
        logger.warning("Tool %s failed (%s)", name, type(exc).__name__)
        return json.dumps({"error": "Tool execution failed. Do not invent results; retry or explain the failure."})


def run_agent(messages: list) -> list:
    """Run the tool loop and always return updated conversation history."""
    global client
    if client is None:
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            return _finish(messages, "Trip planning needs a OPENAI_API_KEY. Please configure it and try again.")
        try:
            client = OpenAI(
                api_key=api_key,
                base_url="https://api.openai.com/v1",
                timeout=60.0,
                max_retries=2,
            )
        except (OpenAIError, ValueError) as exc:
            logger.warning("Model client initialization failed (%s)", type(exc).__name__)
            return _finish(messages, "Could not initialize trip planning. Please check the API configuration.")

    for _ in range(MAX_TURNS):
        try:
            report('Preparing the next planning step…')
            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=TOOLS,
            )
        except OpenAIError as exc:
            logger.warning("Model request failed (%s)", type(exc).__name__)
            code = getattr(exc, 'status_code', None)
            hint = {
                401: 'API configuration: the OpenAI key was rejected. Check Backend/.env and restart EasyTrip.',
                429: 'OpenAI is rate-limited or your API balance is unavailable. Check your API usage and billing, then retry.',
            }.get(code, 'OpenAI could not respond. Check your connection and try again. Your previous plan is unchanged.')
            return _finish(messages, hint)

        if not response.choices or response.choices[0].message is None:
            return _finish(messages, "The planning service returned no answer. Please try again.")
        msg = response.choices[0].message
        if not msg.tool_calls:
            if not msg.content:
                return _finish(messages, "The planning service returned an empty answer. Please try again.")
            messages.append(msg)
            return messages

        messages.append(msg)
        for tool_call in msg.tool_calls:
            # Even failures need a matching result so subsequent requests have
            # no unanswered tool calls, including when this is the final turn.
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": _execute_tool(tool_call),
            })

    return _finish(messages, "Sorry, I couldn't finish within the allowed number of steps.")


if __name__ == "__main__":
    conversation = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "Plan me a short afternoon in Kyoto."},
    ]
    conversation = run_agent(conversation)
    print("\n=== ITINERARY ===")
    reply = conversation[-1]
    print(reply["content"] if isinstance(reply, dict) else reply.content)
