# Development notes

[Back to README](../README.md)

Updated October 2, 2026.

## Setup and checks

Use a project `.venv` as described in the README. Do not depend on a previous developer's temporary environment.

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
node tests/test_frontend.mjs
```

The Python suite currently has 31 tests. It covers SDK tool-call serialization, place context across city changes, save/load, source extraction, session-isolated progress, safe failures, restaurant behavior, and optional embeddings with mocked HTTP. JS checks cover name/context map links, ambiguous names, day sections, and safe text rendering. No real API key is needed for these checks.

## Current implementation

- Flask serves an Instagram-inspired layout with desktop sidebar and mobile bottom navigation.
- OpenAI handles chat/tool selection; optional embeddings support Wikivoyage RAG. Model names are configurable in the environment.
- Map and restaurant searches remain free; no Yelp or paid Google Maps API is used.
- Each assistant answer preserves place/source metadata. Legacy snapshots attach shared locations to the last answer only.
- Google Maps links use place names, recorded addresses, and geocoded destination context, never coordinate-only queries.
- Transport preferences and prompt instructions encourage geographically sensible, less crowded days. Times are approximate suggestions.
- Errors preserve the previous conversation; progress corresponds to actual model/tool steps. Retry is manual.

## Known limitations and next work

- Personal testing is still needed for generated itinerary quality. Automated checks mock providers.
- Nearby-stop grouping is model guidance, not a route optimizer. There are no verified travel times, traffic data, transit schedules, ticket prices, or bookings.
- Common place names and legacy records without city context can lead to ambiguous Google Maps results.
- Source notes identify retrieved sources but do not provide sentence-level evidence verification.
- Public map data can be incomplete; shared services can fail or rate-limit requests. Follow their usage policies before scaling.
- The app has no user accounts; saved trips and feedback are shared on the local server. Production hosting would require authentication, authorization, a production server, and a deployment review.
- Dependency ranges are bounded but not fully locked; CI checks fresh installations.

## Working conventions

Keep page behavior, rendering, services, and API routes separate. Never overwrite `.env` or personal storage during updates. Preserve older snapshots. Never commit secrets, SQLite databases, backup folders, or downloaded runtime artifacts.

The obsolete Streamlit prototype, original handoff notes, and accumulated backup folders were moved outside this project into a dated local archive during repository preparation. They are not required to run EasyTrip.

## Attribution and licensing

The frontend flow was informed by a TravelMind reference project. No source-code license file was present in this EasyTrip folder or found in the available reference checkout during preparation. No license has been invented or applied. Confirm ownership and any upstream attribution/license requirements before choosing an open-source license or redistributing upstream code.

OpenStreetMap data attribution remains visible in the app. Wikivoyage is an optional external guide source; retain source attribution and review its terms for broader reuse.
