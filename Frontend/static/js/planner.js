import {api, notice, element, setBusy} from './api.js';
import {mapUrl} from './place-links.js?v=improvements-1';
import {renderItinerary} from './itinerary.js?v=improvements-1';
const messages = document.querySelector('#messages');
const planningForms = [document.querySelector('#plan-form'), document.querySelector('#chat-form'), document.querySelector('#save-form')];
let busy = false;
let lastRequest = '';
const retry = document.querySelector('#retry-plan');
retry.addEventListener('click', () => { if (lastRequest) send(lastRequest); });
function render(data) {
  messages.replaceChildren();
  if (!data.messages.length) messages.append(element('p', 'Tell me where you want to go, and we’ll start exploring.', 'empty'));
  for (const message of data.messages) {
    const bubble = element('article', '', `message ${message.role}`);
    const content = element('div', '');
    if (message.role === 'assistant') renderItinerary(content, message.content || '', message.places || []);
    else content.textContent = message.content || '';
    bubble.append(element('span', message.role === 'user' ? 'YOU' : 'EASYTRIP', 'eyebrow'), content);
    if (message.role === 'assistant' && ((message.places || []).length || (message.sources || []).length)) {
      const sources = element('details', '', 'plan-sources');
      sources.append(element('summary', 'Sources & things to check'));
      sources.append(element('p', 'Places: community-maintained map listings. Schedule and travel times: AI suggestions. Confirm opening hours, bookings, accessibility, and travel time before you go.', 'small'));
      for (const source of message.sources || [{label:'OpenStreetMap place listings',url:'https://www.openstreetmap.org/copyright'}]) {
        // Only known reference domains may become source links.
        let url; try { url = new URL(source.url); } catch { continue; }
        if (url.protocol !== 'https:' || !['www.openstreetmap.org','en.wikivoyage.org'].includes(url.hostname)) continue;
        const link = element('a', source.label); link.href = url.href;
        link.target = '_blank'; link.rel = 'noopener noreferrer'; sources.append(link);
      }
      bubble.append(sources);
    }
    messages.append(bubble);
  }
  messages.scrollTop = messages.scrollHeight;
  const places = document.querySelector('#places'); places.replaceChildren();
  if (!data.pois.length) places.append(element('p', 'Places with map links will appear after a search.', 'muted'));
  data.pois.forEach((place, i) => {
    const card = element('article', '', 'place');
    card.append(element('span', String(i + 1).padStart(2, '0'), 'place-number'), element('h3', place.name), element('p', place.detail || place.kind, 'small'));
    if (place.location) card.append(element('p', place.location, 'small'));
    const link = element('a', 'View on Google Maps ↗');
    const url = mapUrl(place);
    if (!url) { places.append(card); return; }
    link.href = url;
    link.target = '_blank'; link.rel = 'noopener noreferrer'; card.append(link); places.append(card);
  });
}
async function send(message) {
  if (busy) return false;
  busy = true; planningForms.forEach(form => setBusy(form, true)); document.querySelector('#reset').disabled = true;
  lastRequest = message; retry.hidden = true;
  messages.setAttribute('aria-busy', 'true');
  notice('Preparing your request… This can take a few minutes.');
  let done = false;
  let polling = false;
  const poll = setInterval(async () => {
    if (polling) return;
    polling = true;
    try {
      const {stage} = await api('/planning-status');
      if (!done && stage !== 'idle') notice(stage);
    } catch { /* Progress failure must not cancel the plan request. */ }
    finally { polling = false; }
  }, 1500);
  try { render(await api('/chat', {message})); notice(''); return true; }
  catch (error) { notice(error.message, true); retry.hidden = false; return false; }
  finally { done = true; clearInterval(poll); messages.setAttribute('aria-busy', 'false'); busy = false; planningForms.forEach(form => setBusy(form, false)); document.querySelector('#reset').disabled = false; }
}
document.querySelector('#plan-form').addEventListener('submit', async event => {
  event.preventDefault();
  const destination = document.querySelector('#destination').value.trim();
  const message = `Plan a ${document.querySelector('#days').value}-day trip to ${destination}. Pace: ${document.querySelector('#pace').value}. Getting around: ${document.querySelector('#transport').value}. Interests: ${document.querySelector('#interests').value || 'local highlights'}. Budget and preferences: ${document.querySelector('#budget').value || 'flexible'}.`;
  if (await send(message)) document.querySelector('#trip-name').value = `${destination} adventure`.slice(0, 100);
});
document.querySelector('#chat-form').addEventListener('submit', async event => {
  event.preventDefault(); const input = document.querySelector('#message'); const message = input.value.trim();
  if (message && await send(message)) input.value = '';
});
document.querySelector('#save-form').addEventListener('submit', async event => {
  event.preventDefault(); setBusy(event.currentTarget, true);
  try { await api('/trips', {name: document.querySelector('#trip-name').value}); notice('Trip saved. Find it in Saved trips.'); }
  catch (error) { notice(error.message, true); }
  finally { setBusy(document.querySelector('#save-form'), false); }
});
document.querySelector('#reset').addEventListener('click', async () => {
  if (busy || !confirm('Start fresh? Save your current trip first if you want to keep it.')) return;
  try { await api('/conversation/reset', {}); render({messages: [], pois: []}); notice('Ready for a new adventure.'); }
  catch (error) { notice(error.message, true); }
});
try {
  render(await api('/conversation'));
  const status = await api('/status');
  if (!status.ai_ready) notice('One-time setup: add OPENAI_API_KEY to Backend/.env and restart EasyTrip. See README.md for steps.');
} catch (error) { notice(error.message, true); }

// Inspiration links fill a preference only; they never submit an AI request.
const inspiration = new URLSearchParams(window.location.search).get('inspiration');
if (['Slow days', 'City walks', 'Good food', 'Fresh air', 'Art & culture'].includes(inspiration)) {
  document.querySelector('#interests').value = inspiration;
}
