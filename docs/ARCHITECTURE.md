# Architecture

[Back to README](../README.md)

```text
EasyTrip/
├── run.py                       Flask app entry point
├── requirements*.txt            Runtime, optional RAG, development dependencies
├── Backend/
│   ├── .env.example              Blank configuration template
│   ├── app.py                    App factory and request protections
│   ├── routes/                   HTML pages and JSON API routes
│   ├── Agent/                    Model loop, prompts, tool schemas
│   ├── Services/                 Maps, RAG, sources, progress, conversations
│   └── persistence.py            JSON trip snapshots and feedback
├── Frontend/
│   ├── templates/                Jinja page layouts
│   └── static/
│       ├── css/                  Responsive styling
│       └── js/                   API helper and page-specific behavior
├── docs/                         User, architecture, development, upload guides
├── tests/                        Mocked Python tests and JS rendering checks
└── .github/workflows/tests.yml   Continuous integration
```

## Request flow

The browser submits same-origin JSON to Flask. The backend validates it, rebuilds recent model context, runs the OpenAI tool loop, and stores the visible conversation in SQLite. Each assistant answer carries its own places and sources; these fields are stripped before sending history back to the model. Saving writes a new JSON snapshot including this metadata.

City lookup uses Nominatim. Place and restaurant search use Overpass/OpenStreetMap. Tool-derived names, addresses, and city context create Google Maps search URLs; Google is not called as a backend API. RAG optionally fetches Wikivoyage text, embeds it through OpenAI, and retrieves passages with FAISS.

`place-links.js` safely builds map links. `itinerary.js` recognizes day and time-of-day headings without rendering model HTML. `planner.js` manages conversation, progress, retries, places, and saving. Other pages have separate controllers.

## API

| Endpoint | Purpose |
| --- | --- |
| GET `/api/status` | Configuration availability, not upstream health |
| GET `/api/conversation` | Active session conversation |
| GET `/api/planning-status` | Current session's planning step |
| POST `/api/chat` | Generate or refine a plan |
| POST `/api/conversation/reset` | Reset active conversation |
| GET / POST `/api/trips` | List / save snapshots |
| POST `/api/trips/<id>/load` | Restore a snapshot |
| POST `/api/trips/<id>/feedback` | Record feedback |
| POST `/api/restaurants` | Independent free restaurant search |

Write requests require the `X-EasyTrip: 1` header and reject mismatched origins. A process lock serializes planning. Progress is held in a bounded, session-scoped in-memory store. This design is for one local server process, not multi-user production deployment.

## Private runtime files

`Backend/.env` contains credentials. `Backend/storage/` contains personal conversations, trip snapshots, and feedback. Both are local-only and ignored by Git. No browser-side API key is required.
