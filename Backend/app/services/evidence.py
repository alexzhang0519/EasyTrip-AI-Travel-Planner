"""Extract direct tools and the application's specialist evidence envelopes."""
import json

def tool_data(message):
    if message.get('role') != 'tool': return None
    try: return json.loads(message.get('content') or 'null')
    except (ValueError,TypeError): return None

def flatten_evidence(messages):
    result=[]
    for m in messages:
        result.append(m)
        data=tool_data(m)
        if isinstance(data,dict) and data.get('agent') in ('Place researcher','Weather adviser'):
            evidence=data.get('evidence',[])
            if isinstance(evidence,list): result.extend(e for e in evidence if isinstance(e,dict))
    return result

def weather_reports(messages):
    reports = []
    location = None
    for m in messages:
        data = tool_data(m)
        if isinstance(data, dict) and data.get('name') and 'lat' in data and 'lon' in data:
            location = data['name']
        if isinstance(data, dict) and data.get('source') == 'Open-Meteo' and 'daily' in data:
            reports.append(dict(data, location=location))
    return reports

def agent_reports(messages):
    return [{k:data[k] for k in ('agent','status','summary')} for m in messages
            if isinstance(data:=tool_data(m),dict) and data.get('agent') in ('Place researcher','Weather adviser')]
