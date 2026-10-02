import {element} from './api.js';

export function renderResearch(bubble, message) {
  for (const forecast of message.weather || []) {
    const section = element('section', '', 'weather-card');
    section.append(element('h3', 'Weather outlook'));
    if (forecast.location) section.append(element('p', forecast.location, 'small'));
    const range = forecast.requested_start_date && !forecast.outlook_only ? `From ${forecast.requested_start_date} · ${forecast.requested_days} day(s)` : 'Current outlook; travel dates not set';
    section.append(element('p', `${range} · ${forecast.timezone || 'Timezone unavailable'}`, 'small'));
    for (const warning of forecast.warnings || []) section.append(element('p', warning, 'weather-warning'));
    if (!forecast.daily?.length) section.append(element('p', 'No forecast is available for these dates.', 'small'));
    for (const day of forecast.daily || []) {
      const row = element('div', '', 'weather-day');
      row.append(element('strong', day.date), element('span', `${day.temperature_min_c}–${day.temperature_max_c} °C`),
        element('span', `Rain chance ${day.precipitation_probability_max}%`));
      section.append(row);
    }
    const attribution = element('a', 'Forecast data: Open-Meteo · CC BY 4.0');
    attribution.href = 'https://open-meteo.com/'; attribution.target = '_blank'; attribution.rel = 'noopener noreferrer';
    section.append(attribution);
    if (forecast.fetched_at) section.append(element('p', `Retrieved ${new Date(forecast.fetched_at).toLocaleString()}. Saved forecasts are snapshots; ask for an update before travel.`, 'small'));
    bubble.append(section);
  }
  if (message.agents?.length) {
    const notes = element('details', '', 'plan-sources'); notes.append(element('summary', 'Research from your planning team'));
    for (const agent of message.agents) {
      notes.append(element('h4', `${agent.agent} · ${agent.status === 'complete' ? 'Report ready' : 'Unavailable'}`),element('p', agent.summary, 'small'));
    }
    bubble.append(notes);
  }
}
