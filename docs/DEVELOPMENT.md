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

The Python suite covers the core app plus LangChain serialization, collaboration, and weather edge cases. It covers SDK tool-call serialization, place context across city changes, save/load, source extraction, session-isolated progress, safe failures, restaurant behavior, and optional embeddings with mocked HTTP. JS checks cover name/context map links, ambiguous names, day sections, and safe text rendering. No real API key is needed for these checks.

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

## Weather / LangChain update

Added optional collaborating specialists, the LangChain OpenAI adapter, forecast service, trip dates, and weather/research cards. Use a real isolated `.venv`: global packages (notably multiple OpenMP runtimes from torch and FAISS) can crash optional RAG tests. See [implementation and provider limits](WEATHER_AND_AGENTS.md).

Map-link discoverability: the planner now has a top-level Map links shortcut with the result count, and new replies scroll to the start of the itinerary rather than past it to weather/research notes.

Inline Maps: structured responses provide named place objects; the server and frontend build Google Maps search links. Legacy Markdown links remain supported. The renderer safely supports only Google Maps search URLs and retains automatic links for tool-returned names. Search links do not certify a venue or recommendation. Weather reports must not supply unverified venue recommendations to the coordinator.


## Architecture migration

Canonical backend code now lives under `Backend/app/`; see [architecture](ARCHITECTURE.md). Legacy imports are shims. Existing `.env`, SQLite table, and JSON snapshots remain at their original locations. No user data migration is required. JSON writes are now atomic.

Planner responses use native structured output and Pydantic validation. Older saved answers remain supported. Invalid structured output returns an error before overwriting the active conversation. The collaborating workflow uses LangGraph's parallel branches and explicit join; each specialist still has four model turns and synthesis one. Single-agent planning may use one additional final-formatting call after research (at most eleven model requests, excluding SDK retries).

No API key, saved data, or existing uncommitted change was discarded. Source backups are in the ignored `.backup-before-architecture/` folder. The temporary import shims can be removed in a later compatibility-breaking release after consumers migrate.

Current verification: 91 Python tests pass, including real LangGraph execution, structured-output SDK serialization, structured snapshot save/load, fresh direct plans, and request-ID errors. Frontend checks cover structured place links independently of description text and literal rendering of HTML-like strings. Dependency validation passes. No live paid planning request was used for this refactor.


### Integrated sightseeing and meals

The main planner now researches restaurants with the same free OpenStreetMap
service used by Find food. Both single-agent and collaborating-agent modes can
call `search_restaurants` near researched sights. The Place researcher handles
sightseeing and food together; no additional specialist or paid provider is added.
Full-day plans request Lunch and Dinner activities with named Google Maps links.
The main form has Food & dietary needs; the direct planning API accepts optional
`food_preferences` (up to 300 characters). Saved plans retain meal activities.
If evidence is missing, the assistant should keep an unnamed meal break and
explain the gap. Dietary tags are incomplete: confirm restrictions, allergens and
opening hours with the venue. Existing saved itineraries are not rewritten;
generate a new plan or ask to add nearby meals to your current plan.


### Unsaved chats

Each planner page has a unique in-memory draft identifier. New tabs and refreshes
start empty; opening one tab cannot reset another tab's plan or prevent saving.
Browser drafts stay in server memory, not SQLite. Save before navigating away
or closing the planner. Saved trips → Open & continue loads a saved snapshot
into a new draft. A trip name is optional in the UI (defaults to My trip).

On page exit the browser sends a keepalive close request, which drops the draft
content and blocks late AI writes. Browsers cannot guarantee delivery after a
crash or network loss. Abandoned drafts expire after 30 minutes without activity,
with cleanup running every minute, and all drafts disappear on server restart.
Visible planner pages refresh their draft lifetime every minute. Switching to
a Maps tab does not delete the original planner; opening another planner gets
an independent empty draft. Saved JSON trips persist until explicitly deleted.
Legacy API clients without a draft header retain cookie-scoped SQLite behavior.

### Saving and deleting trips

Generate a plan, enter a trip name, and select **Save trip**. In **Saved trips**,
use **Open & continue** to restore it, or **Delete trip** and confirm to remove
that saved snapshot and its feedback permanently. Other saved trips are kept.
Deleting a snapshot does not clear an already open working chat; reopening the
planner clears that draft as described above. The protected deletion endpoint
is `POST /api/trips/<trip_id>/delete`.


### One conversation per trip

Create trip starts fresh, while chat messages refine the current trip. Retrying
a failed Create trip request keeps that fresh-trip behavior. A failed request
preserves the previous draft. Saved trips contain the current trip and its
follow-ups. Older snapshots containing multiple recognizable form submissions
are opened from the latest trip request; their original files are not rewritten
on load. Free-text trip boundaries in older snapshots cannot be inferred reliably.
