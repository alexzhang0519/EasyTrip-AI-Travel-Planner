# Using EasyTrip

[Back to README](../README.md)

## Plan and refine

1. Open **Create a trip** and enter a city and country, days, pace, interests, transport preference, and budget.
2. Optionally set your start date and choose **Use collaborating agents**. The team uses extra OpenAI calls; uncheck it for one agent. Click **Create trip**. The status message reports the current planning/tool step; slow public services can take several minutes.
3. Read the day cards. New plans are requested with morning, afternoon, and evening sections. Older plans may have fewer headings.
4. Click an underlined place name to search Google Maps. Available address and destination context are included; common names can still return several results.
5. Ask a follow-up such as “Make day two less busy” or “Prefer minimal walking.”
6. Expand **Sources & things to check** for source links and limitations.

The **Places to explore** panel shows the latest search results, which may contain places not used in the itinerary. Individual answers retain their own location lists. Legacy saved plans lack some context; their shared places are attached only to the latest answer.

## Save and reopen

Enter a name under **Save for later**, then click **Save trip**. Under **Saved trips**, select **Open & continue**. Saving again creates another snapshot. **Needs work** feedback comments become preferences in future requests.

**Start a new conversation** clears the active chat after confirmation. Saved snapshots stay on disk. Changing the session secret can start a new browser session but does not delete saved snapshots.

## Find food

Choose **Find food**, enter city/country, optionally a cuisine or name, and a search radius. Listings use community map tags and may lack addresses or opening hours. Dietary filters depend on those tags. There are no Yelp ratings or price filters.

Results cover up to 300 mapped venues and return up to 10 matches. Distances are straight-line estimates from the search center, not walking distances. Restaurant searches are separate from saved trip conversations.

## Troubleshooting

- **Missing OpenAI key:** edit the hidden file `Backend/.env`, then restart the server. In macOS Finder, Cmd+Shift+. toggles hidden files.
- **Key rejected:** check the key and API configuration. Never paste the key into chat or a GitHub issue.
- **Rate limit or unavailable API balance:** check your OpenAI API account's usage/billing, then use **Retry last request**. Retrying may incur normal API usage.
- **Free map service unavailable:** retry later or use a more specific city. There is no paid fallback.
- **Port occupied:** use port 5001 as shown in the README, or choose another unused port.
- **RAG unavailable:** install `requirements-rag.txt` in the active environment and restart. Ordinary place-based planning does not require FAISS.

On planning errors the previous conversation is preserved. Inputs stay available; retry is manual.

## Weather

Forecast cards show the provider dates, destination timezone, retrieval time, temperature in Celsius, and precipitation probability. Forecasts extend at most 16 days; partial or unavailable dates are explicitly labeled. With no date, weather is a current outlook, not a forecast for an unspecified future trip. Ask for an update before travel; saved weather does not refresh automatically. See [weather and agents](WEATHER_AND_AGENTS.md).


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
