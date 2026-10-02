# EasyTrip

A personal AI travel planner with a clean, responsive web interface. Plan a trip, refine it in chat, explore places and restaurants, and save itineraries on your computer.

## Features

- Optional collaborating place researcher, weather adviser, and coordinating planner powered by LangChain.
- Free personal-use Open-Meteo weather with travel dates and forecast coverage warnings.
- Validated structured itineraries and a LangGraph research workflow.
- Day-by-day sightseeing and meal plans with pace, interests, budget, transport, and dietary preferences.
- Clickable Google Maps searches using place names and available address/city context.
- Independent trip conversations and per-tab drafts, with saved itineraries you can reopen or delete.
- Separate location snapshots for each answer, retained when saving and reopening trips.
- Free OpenStreetMap restaurant search integrated into lunch and dinner planning, plus a standalone food search page.
- Planning progress, recoverable errors, and source notes.
- Optional Wikivoyage retrieval using OpenAI embeddings and local FAISS search.

OpenAI chat and embeddings use your separately billed API account. Map searches and Google Maps links need no paid Google or Yelp API. No local AI model or GPU is required.

## Quick start

Requires Python 3.10+ and an internet connection. From the project folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

On Windows, activate with `.venv\Scripts\activate` instead.

If `Backend/.env` does not already exist, copy `Backend/.env.example` to it. Add your key locally:

```dotenv
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4.1-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
FLASK_SECRET_KEY=your_random_session_secret
```

Generate a session secret with `python -c "import secrets; print(secrets.token_hex(32))"`. Keep this secret stable to preserve your browser session across restarts. Never put credentials in frontend files or commit `.env`.

```bash
python -m flask --app run:app run --host 127.0.0.1 --port 5001
```

Open [EasyTrip](http://127.0.0.1:5001/). Keep the terminal running; stop with Ctrl+C. Restart after changing `.env`. `python run.py` also works but uses port 5000, which may already be occupied on macOS.

Optional RAG dependencies:

```bash
python -m pip install -r requirements-rag.txt
```

## Project layout

```text
Backend/
  .env.example       # Blank configuration template; keep your .env local
  app/
    api/             # Flask application and routes
    agents/          # Planner and research specialists
    graph/           # LangGraph orchestration
    services/        # Places, food, weather, and itinerary formatting
    rag/             # Optional travel-guide retrieval
    memory/          # Conversation and saved-trip persistence
    models/          # Validated requests and structured plans
    middleware/      # Request IDs and error handling
Frontend/
  templates/         # Page layouts
  static/            # CSS and JavaScript
docs/               # Guides and interactive workflow
tests/              # Network-mocked backend and frontend checks
```

Older backend import paths remain as small compatibility shims. Runtime data,
credentials, environments, and local backups are excluded from Git.

## Documentation

- [User guide](docs/USER_GUIDE.md): planning, map links, saving, and troubleshooting.
- [Weather and agents](docs/WEATHER_AND_AGENTS.md): setup, costs, forecast limits, and team behavior.
- [Architecture](docs/ARCHITECTURE.md): project structure and data flow.
- [Development](docs/DEVELOPMENT.md): tests, implementation notes, and current limitations.
- [GitHub upload guide](docs/GITHUB.md): prepare and publish a clean repository.
- [Interactive workflow](docs/workflow.html): open this file in a browser to explore the workflow and input flow. GitHub's file view shows its source.

## Tests

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
node tests/test_frontend.mjs
```

Node.js 18+ is only needed for frontend tests, not to run the app. Tests mock external services; they do not spend OpenAI credits. GitHub Actions runs the same checks.

## Scope and data

EasyTrip is a local, single-user prototype. It has no authentication or booking system and is not configured for public hosting. Saved trips and feedback are shared by browsers accessing the same local server. Browser drafts are temporary and isolated per planner page; save before closing or refreshing. Saved trips live in `Backend/storage/itineraries/`. Legacy API conversations use `Backend/storage/conversations.sqlite3`. Runtime files are excluded from Git.

Plans and travel times are AI suggestions, not verified routes or schedules. Confirm venue hours, reservations, accessibility, and transport details before traveling. Public map services can be rate-limited or unavailable.

Place data: © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright). Optional travel guides: [Wikivoyage](https://en.wikivoyage.org/). The frontend flow was informed by a TravelMind reference project; see [development notes](docs/DEVELOPMENT.md#attribution-and-licensing) before choosing a distribution license.
