# Weather and collaborating agents

[Back to README](../README.md)

## Try it

1. Install the updated dependencies in the project environment: `python -m pip install -r requirements.txt`.
2. Restart Flask and open **Create a trip**.
3. Enter a destination, duration, and optional start date. Leave **Use collaborating agents** selected to enable the team.
4. The place researcher and weather adviser run independently, then the planner combines their reports.
5. Read the itinerary, weather cards, coverage warnings, and expandable **Research from your planning team** notes.

Uncheck collaboration for a single agent with the same place and weather tools. Follow-up chat uses the current toggle. Retry retains the mode of the failed request. Forecasts and team reports are saved with their own answer and survive reloading.

## Cost and forecast limits

Weather uses [Open-Meteo](https://open-meteo.com/en/docs), without an API key. Its public endpoint is free for personal/noncommercial use, subject to rate limits and no uptime guarantee; see [provider terms and pricing](https://open-meteo.com/en/pricing). Public code on GitHub does not turn this into an unlimited commercial API license.

The forecast horizon is up to 16 days, using destination-local dates. Longer trips can have partial coverage. Past or far-future dates do not receive fabricated forecasts. With no trip date, the assistant uses a current outlook and must label it as such. Temperature is Celsius; precipitation is probability. Saved forecasts are snapshots, not live updates.

LangChain is a library, not an extra hosted subscription. The app uses its OpenAI integration with the existing `OPENAI_API_KEY`. Collaborating agents make additional billed OpenAI requests: up to four model turns for each of two specialists, then one synthesis turn (nine maximum, excluding SDK retries). The single-agent research has a ten-turn cap plus at most one final structured-formatting call. Actual cost depends on tokens and the configured model; collaboration is not guaranteed to cost less just because its cap is lower.

No LangSmith account or tracing configuration is required or enabled by the app. No Google Maps API or Yelp subscription was added.

## Implementation

- `Backend/app/agents/langchain_model.py`: ChatOpenAI configuration, tool binding, and sanitized message conversion.
- `Backend/app/agents/core.py`: bounded tool loop shared by all agents.
- `Backend/app/agents/collaboration.py`: parallel specialists with separate prompts and restricted tool sets, followed by planner synthesis. Specialists cannot delegate recursively.
- `Backend/app/services/weather.py`: validated Open-Meteo requests, bounded 15-minute cache, timezone-aware coverage handling.
- `Backend/app/services/evidence.py`: extract nested specialist evidence for place links, forecasts, and sources.
- `Frontend/static/js/weather.js`: safe forecast and research-report rendering.

Research agents are genuine separate model-driven tool loops, not just labels. They share the configured model but not a mutable conversation. The coordinator receives their reports and tool evidence. Specialist failure is reported; if both fail, the existing conversation remains unchanged. Tool data remains untrusted reference content.

Tests mock model and weather calls. A live API account is only needed for personal end-to-end planning trials. Model compliance (for example, exact tool usage and quality of rain alternatives) still needs hands-on evaluation.

References: [LangChain ChatOpenAI](https://docs.langchain.com/oss/python/integrations/chat/openai), [LangChain subagents](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents), [Open-Meteo forecast documentation](https://open-meteo.com/en/docs).

Collaboration now runs through the LangGraph workflow in `Backend/app/graph/`. No LangGraph cloud service or key is required. See [architecture](ARCHITECTURE.md).
