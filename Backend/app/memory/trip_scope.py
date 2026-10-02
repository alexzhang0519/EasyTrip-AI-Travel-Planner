"""Keep one trip and its follow-ups when opening older combined snapshots."""
import re

# Only recognize the old UI-generated form format, not arbitrary destination text.
LEGACY_START = re.compile(r'^Plan a \d+-day trip to .+\. Start date: .+\. Pace: .+\. Getting around: .+\. Interests: .+\. Budget and preferences:', re.DOTALL)

def current_trip_messages(messages):
    marked = [i for i, m in enumerate(messages)
              if m.get('role') == 'user' and m.get('trip_start') is True]
    if marked:
        return messages[marked[-1]:]
    starts = [i for i, m in enumerate(messages)
              if m.get('role') == 'user' and LEGACY_START.match(m.get('content') or '')]
    return messages[starts[-1]:] if starts else messages
