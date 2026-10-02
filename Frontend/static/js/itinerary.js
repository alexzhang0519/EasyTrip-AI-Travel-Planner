import {renderPlaceText, mapUrl} from './place-links.js?v=inline-maps-2';

// Only recognize itinerary headings. All other model text remains literal text.
export function splitDays(text) {
  const blocks = [];
  let current = {title: '', lines: []};
  for (const line of text.split('\n')) {
    const heading = line.trim().replace(/^#{1,4}\s*/, '').replace(/^\*\*(.*?)\*\*:?$/, '$1');
    if (/^Day\s+\d+\b[^\n]*$/i.test(heading)) {
      if (current.title || current.lines.length) blocks.push(current);
      current = {title: heading, lines: []};
    } else current.lines.push(line);
  }
  if (current.title || current.lines.length) blocks.push(current);
  return blocks;
}
export function renderItinerary(container, text, places) {
  const blocks = splitDays(text);
  if (!blocks.some(b => b.title)) { renderPlaceText(container, text, places); return; }
  container.classList.add('itinerary');
  for (const block of blocks) {
    const section = document.createElement(block.title ? 'section' : 'div');
    section.className = block.title ? 'day-card' : 'plan-intro';
    if (block.title) {
      const heading = document.createElement('h3'); heading.textContent = block.title; section.append(heading);
    }
    for (const line of block.lines) {
      if (!line.trim()) continue;
      const period = line.trim().replace(/^\*\*(.*?)\*\*:?$/, '$1').match(/^(Morning|Afternoon|Evening)\s*:\s*(.*)$/i);
      if (period) {
        const label = document.createElement('h4'); label.textContent = period[1]; section.append(label);
        if (!period[2]) continue;
        const activity = document.createElement('p'); renderPlaceText(activity, period[2], places); section.append(activity);
      } else {
        const activity = document.createElement('p'); renderPlaceText(activity, line, places); section.append(activity);
      }
    }
    container.append(section);
  }
}

// New plans use explicit place fields, independent of names in the description.
export function activityMapUrl(activity) {
  return activity.place ? mapUrl({...activity.place, location: activity.place.city || ''}) : null;
}
export function renderStructuredItinerary(container, plan) {
  container.classList.add('itinerary');
  const summary = document.createElement('p'); summary.textContent = plan.summary || ''; container.append(summary);
  for (const day of plan.days || []) {
    const section = document.createElement('section'); section.className = 'day-card';
    const heading = document.createElement('h3'); heading.textContent = `Day ${day.day}: ${day.title}`; section.append(heading);
    for (const activity of day.activities || []) {
      const period = document.createElement('h4'); period.textContent = activity.period; section.append(period);
      const url = activityMapUrl(activity);
      if (url) {
        const link = document.createElement('a'); link.textContent = activity.place.name;
        link.href = url; link.className = 'itinerary-place-link'; link.target = '_blank'; link.rel = 'noopener noreferrer';
        section.append(link);
      }
      const description = document.createElement('p'); description.textContent = activity.description; section.append(description);
    }
    container.append(section);
  }
  for (const warning of plan.warnings || []) {
    const note = document.createElement('p'); note.textContent = warning; note.className = 'small'; container.append(note);
  }
}
