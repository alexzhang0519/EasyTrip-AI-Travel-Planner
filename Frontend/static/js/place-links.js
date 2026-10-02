// Search Google Maps by place name and available address; never interpret model text as HTML.
export function mapUrl(place) {
  const name = typeof place.name === 'string' ? place.name.trim() : '';
  if (!name) return null;
  const address = typeof place.address === 'string' ? place.address.trim() : '';
  const location = typeof place.location === 'string' ? place.location.trim() : '';
  const query = [name, address, location].filter(Boolean).join(', ');
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(query)}`;
}
export function placeSegments(text, places = []) {
  const names = new Map();
  for (const place of places) {
    const name = typeof place.name === 'string' ? place.name.trim() : '';
    const url = mapUrl(place);
    if (!name || !url) continue;
    if (!names.has(name)) names.set(name, url);
    else if (names.get(name) !== url) names.set(name, null); // Multiple branches: do not guess.
  }
  const candidates = [...names].filter(([, url]) => url).sort((a, b) => b[0].length - a[0].length);
  const word = char => !!char && /[\p{L}\p{N}_]/u.test(char);
  const segments = [];
  let start = 0, pos = 0;
  while (pos < text.length) {
    const found = candidates.find(([name]) => text.startsWith(name, pos) &&
      !(word(name[0]) && word(text[pos - 1])) && !(word(name.at(-1)) && word(text[pos + name.length])));
    if (!found) { pos++; continue; }
    if (pos > start) segments.push({text: text.slice(start, pos)});
    segments.push({text: found[0], url: found[1]});
    pos += found[0].length; start = pos;
  }
  if (start < text.length) segments.push({text: text.slice(start)});
  return segments;
}
export function renderPlaceText(container, text, places) {
  for (const segment of placeSegments(text, places)) {
    if (!segment.url) { container.append(document.createTextNode(segment.text)); continue; }
    const link = document.createElement('a');
    link.textContent = segment.text;
    link.href = segment.url;
    link.className = 'itinerary-place-link';
    link.target = '_blank'; link.rel = 'noopener noreferrer';
    link.title = `Open ${segment.text} in Google Maps (new tab)`;
    container.append(link);
  }
}
