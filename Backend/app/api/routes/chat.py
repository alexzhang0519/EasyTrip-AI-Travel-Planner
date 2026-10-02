"""API boundary: validate requests and connect UI actions to existing services."""
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from flask import Blueprint, current_app, jsonify, request, session
from Backend.app.memory import trips as persistence
from Backend.app.services import progress
from Backend.app.agents.core import run_agent
from Backend.app.agents.collaboration import run_collaboration
from Backend.app.services.evidence import flatten_evidence, weather_reports, agent_reports
from Backend.app.agents.prompts import SYSTEM_PROMPT
from Backend.app.memory import conversations
from Backend.app.services.places import extract_pois
from Backend.app.services.plan_sources import collect_sources
from Backend.app.services.geocoding import geocode_city
from Backend.app.services.restaurants import search_restaurants

from . import api
from .common import planning_lock, payload, text_field, trip_path, visible

@api.get('/status')
def status():
    return jsonify(ai_ready=bool(os.getenv('OPENAI_API_KEY', '').strip()),
                   restaurant_provider='openstreetmap', restaurants_ready=True)

@api.get('/conversation')
def conversation():
    return jsonify(visible(conversations.read()))

@api.get('/planning-status')
def planning_status():
    return jsonify(stage=progress.read(session.get('conversation_id')))

@api.post('/conversation/reset')
def reset():
    with planning_lock:
        conversations.write({'messages': [], 'pois': []})
    return jsonify(ok=True)

@api.post('/chat')
def chat():
    from Backend.app.models.schemas import ChatRequest
    body = ChatRequest.model_validate(payload())
    return plan_message(body.message.strip(), body.collaborate)

def plan_message(message, collaborate=False, fresh=False):
    if not message:
        raise ValueError('Message cannot be blank.')
    if not os.getenv('OPENAI_API_KEY', '').strip():
        return jsonify(error='Add OPENAI_API_KEY to Backend/.env and restart EasyTrip to enable the AI assistant.'), 503
    with planning_lock:
        data = conversations.read()
        if fresh:
            data = {'messages': [], 'pois': []}
        # Rebuild a bounded visible history; never truncate midway through tool calls.
        previous = visible(data)['messages']
        from Backend.app.agents.dialogue_agent import build_messages
        messages = build_messages(previous, message, persistence.collect_feedback_notes())
        start = len(messages)
        key = session['conversation_id']
        progress.update(key, 'Preparing your request…')
        token = progress.callback.set(lambda stage: progress.update(key, stage))
        try:
            result = run_collaboration(messages) if collaborate else run_agent(messages)
        except Exception:
            current_app.logger.exception('Planning failed')
            return jsonify(error='Planning is unavailable. Your previous plan is unchanged. Please retry or check the server configuration.'), 502
        finally:
            progress.callback.reset(token)
            progress.update(key, 'idle')
        if result and isinstance(result[-1], dict) and result[-1].get('error'):
            return jsonify(error=result[-1]['content']), 502
        serialized = [m if isinstance(m, dict) else m.model_dump(exclude_none=True) for m in result]
        evidence = flatten_evidence(serialized[start:])
        places = extract_pois(evidence)
        fresh = persistence._clean_messages(serialized[start:])
        # No new search means a refinement can reuse the previous answer's places.
        searched = any(m.get('role') == 'tool' and (m.get('content') or '').lstrip().startswith('[') for m in evidence) or any(c.get('function', {}).get('name') in ('geocode_city', 'search_pois', 'search_restaurants') for m in evidence for c in m.get('tool_calls', []))
        current_places = places if searched else data['pois']
        for m in fresh:
            if m['role'] == 'assistant':
                m['places'] = current_places
                m['sources'] = collect_sources(evidence, current_places)
                m['weather'] = weather_reports(evidence)
                m['agents'] = agent_reports(serialized[start:])
        data = {'messages': previous + [{'role': 'user', 'content': message}] + fresh, 'pois': current_places}
        conversations.write(data)
    return jsonify(visible(data))

