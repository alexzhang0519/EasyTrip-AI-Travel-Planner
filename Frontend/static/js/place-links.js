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
// Render only Google Maps search links; all other Markdown/HTML stays literal.
export function linkedSegments(text, places = []) {
  const output = [];
  const pattern = /\[([^\]\n]+)\]\((https:\/\/[^\s)]+)\)/g;
  let start = 0;
  for (const match of text.matchAll(pattern)) {
    let url;
    try { url = new URL(match[2]); } catch { continue; }
    if (url.origin !== 'https://www.google.com' || url.pathname !== '/maps/search/' ||
        url.username || url.password || url.searchParams.get('api') !== '1' || !url.searchParams.get('query')) continue;
    output.push(...placeSegments(text.slice(start, match.index), places));
    // Rebuild with only supported search parameters; never preserve redirects.
    const query = url.searchParams.get('query');
    const safeQuery = query.toLocaleLowerCase().includes(match[1].toLocaleLowerCase()) ? query : match[1];
    output.push({text: match[1], url: `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(safeQuery)}`});
    start = match.index + match[0].length;
  }
  output.push(...placeSegments(text.slice(start), places));
  return output;
}
export function renderPlaceText(container, text, places) {
  for (const segment of linkedSegments(text, places)) {
    if (!segment.url) { container.append(document.createTextNode(segment.text)); continue; }
    const link = document.createElement('a');
    link.textContent = segment.text;
    link.href = segment.url;
    link.className = 'itinerary-place-link';
    link.target = '_blank'; link.rel = 'noopener noreferrer';
    link.title = `Search for ${segment.text} in Google Maps (new tab)`;
    container.append(link);
  }
}
