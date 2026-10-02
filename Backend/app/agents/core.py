"""Bounded LangChain tool loop shared by the planner and specialists."""
import os
import json
import logging
from inspect import signature
from openai import OpenAIError
from Backend.app.agents.tools import TOOLS, TOOL_FUNCTIONS
from Backend.app.agents.langchain_model import make_model, invoke_model
from Backend.app.services.progress import report
logger = logging.getLogger(__name__)
client = None
MODEL = os.getenv('OPENAI_MODEL', 'gpt-4.1-mini')
MAX_TURNS = 10

def _finish(messages, content):
    messages.append({'role':'assistant','content':content,'error':True})
    return messages

def _execute_tool(call, functions, agent_name):
    function = call.get('function', {})
    name = function.get('name')
    if name not in functions:
        return json.dumps({'error':'Unknown tool. Choose an available tool.'})
    try:
        args = json.loads(function.get('arguments', '{}'))
        if not isinstance(args, dict): raise ValueError('Expected an object')
        func = functions[name]
        signature(func).bind(**args)
    except (ValueError, TypeError):
        return json.dumps({'error':'Invalid tool arguments. Check the schema and retry.'})
    try:
        action = {'geocode_city':'finding the destination','search_pois':'finding real places',
                  'search_restaurants':'finding meal stops near your sights',
                  'get_weather':'checking the forecast','lookup_travel_info':'reading travel guides'}.get(name,'checking information')
        report(f'{agent_name}: {action}…')
        return json.dumps(func(**args), ensure_ascii=False)
    except Exception as exc:
        logger.warning('Tool %s failed (%s)', name, type(exc).__name__)
        return json.dumps({'error':'Tool unavailable. Do not invent results; explain missing information.'})

def run_loop(messages, *, tools=None, functions=None, max_turns=MAX_TURNS, agent_name='Planner', structured=False):
    global client
    schemas = TOOLS if tools is None else tools
    functions = TOOL_FUNCTIONS if functions is None else functions
    if client is None:
        if not os.getenv('OPENAI_API_KEY','').strip():
            return _finish(messages,'Trip planning needs OPENAI_API_KEY in Backend/.env.')
        try:
            client = make_model()
        except (OpenAIError, ValueError) as exc:
            logger.warning('Model initialization failed (%s)',type(exc).__name__)
            return _finish(messages,'API configuration could not be initialized. Check Backend/.env and restart.')
    for _ in range(max_turns):
        try:
            report(f'{agent_name}: preparing its response…')
            if structured and not schemas:
                from Backend.app.models.schemas import PlannerResponse
                message = invoke_model(client, messages, schemas, response_schema=PlannerResponse.model_json_schema())
            else:
                message = invoke_model(client, messages, schemas)
        except OpenAIError as exc:
            logger.warning('Model request failed (%s)',type(exc).__name__)
            hint = {401:'API configuration: the OpenAI key was rejected. Check Backend/.env and restart.',
                    429:'OpenAI is rate-limited or your API balance is unavailable. Check usage and billing, then retry.'}.get(
                getattr(exc,'status_code',None),'OpenAI could not respond. Check your connection and retry. Your previous plan is unchanged.')
            return _finish(messages,hint)
        if not message.get('tool_calls'):
            if not message.get('content'):
                return _finish(messages,'The planning service returned no answer. Please retry.')
            if structured:
                from Backend.app.services.itinerary import normalize_plan
                from Backend.app.models.schemas import PlannerResponse
                try:
                    if schemas:
                        # Separate final formatting from non-strict optional tool schemas.
                        message = invoke_model(client, messages, [], response_schema=PlannerResponse.model_json_schema())
                    message['content'], message['itinerary'] = normalize_plan(message['content'])
                except (ValueError, OpenAIError):
                    return _finish(messages, 'The plan format was incomplete. Please retry; your previous trip is unchanged.')
            messages.append(message)
            return messages
        messages.append(message)
        if len(message['tool_calls']) > 8:
            return _finish(messages,'Too many searches requested. Please try a smaller trip.')
        for call in message['tool_calls']:
            messages.append({'role':'tool','tool_call_id':call['id'],'content':_execute_tool(call,functions,agent_name)})
    return _finish(messages,'Planning reached its step limit. Try a shorter or more specific request.')

def run_agent(messages):
    return run_loop(messages, structured=True)
