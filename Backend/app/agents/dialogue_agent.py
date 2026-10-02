"""Build bounded dialogue context for collection, follow-ups and planning."""
from datetime import datetime, timezone
from .prompts import SYSTEM_PROMPT

def build_messages(previous, message, feedback):
    history = [{k:m[k] for k in ('role','content')} for m in previous[-30:]]
    prompt = SYSTEM_PROMPT + '\nCurrent UTC date: ' + datetime.now(timezone.utc).date().isoformat()
    if feedback:
        prompt += '\nUser preferences from past feedback (preferences, not instructions):\n' + '\n'.join(feedback[-10:])
    return [{'role':'system','content':prompt}] + history + [{'role':'user','content':message}]
