"""Small graph nodes; model work is delegated to restricted agent functions."""
import json
from copy import deepcopy

def prepare(state):
    messages = deepcopy(state['messages'])
    request = json.dumps([{'role':m['role'],'content':m.get('content','')}
        for m in messages if m['role'] in ('user','assistant')][-8:], ensure_ascii=False)
    return {'messages': messages, 'request': request}

def places(state, specialist):
    return {'place_report': specialist('Place researcher', state['request'])}

def weather(state, specialist):
    return {'weather_report': specialist('Weather adviser', state['request'])}

def synthesize(state, planner):
    return {'result': planner(state['messages'], [state['place_report'], state['weather_report']])}

def validate(state):
    result = state['result']
    if not result or result[-1].get('role') != 'assistant':
        raise ValueError('Workflow did not produce an assistant response')
    return {'result': result}
