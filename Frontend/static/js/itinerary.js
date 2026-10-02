import {renderPlaceText} from './place-links.js?v=improvements-1';

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
