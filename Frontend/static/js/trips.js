import {api, notice, element, setBusy} from './api.js';
const container = document.querySelector('#trips');
try {
  const {trips} = await api('/trips'); container.replaceChildren();
  if (!trips.length) {
    const empty = element('div', '', 'panel'); empty.append(element('h2', 'Your next adventure is still unwritten.'), element('p', 'Plan a trip with the assistant, then give it a name and save it.'));
    const link = element('a', 'Plan your first trip ↗', 'button'); link.href = '/planner'; empty.append(link); container.append(empty);
  }
  for (const trip of trips) {
    const card = element('article', '', 'panel'); card.append(element('p', 'SAVED ADVENTURE', 'eyebrow'), element('h2', trip.name), element('p', new Date(trip.saved_at).toLocaleString(), 'small'));
    const load = element('button', 'Open & continue ↗');
    load.addEventListener('click', async () => {
      load.disabled = true;
      try { await api(`/trips/${encodeURIComponent(trip.id)}/load`, {}); location.href = '/planner'; }
      catch (error) { notice(error.message, true); load.disabled = false; }
    });
    card.append(load);
    const form = element('form', '', 'feedback');
    const label = element('label', 'How was this trip?'); const input = element('textarea', ''); input.placeholder = 'What should the assistant keep in mind?'; input.maxLength = 1000; label.append(input); form.append(label);
    for (const [rating, caption] of [['up', 'Good trip'], ['down', 'Needs work']]) {
      const button = element('button', caption, 'secondary'); button.type = 'submit'; button.value = rating; form.append(button);
    }
    form.addEventListener('submit', async event => {
      event.preventDefault(); const rating = event.submitter.value; setBusy(form, true);
      try { await api(`/trips/${encodeURIComponent(trip.id)}/feedback`, {rating, comment: input.value}); notice('Feedback saved. Comments on “Needs work” help guide future plans.'); }
      catch (error) { notice(error.message, true); }
      finally { setBusy(form, false); }
    });
    card.append(form); container.append(card);
  }
} catch (error) { container.replaceChildren(); notice(error.message, true); }
