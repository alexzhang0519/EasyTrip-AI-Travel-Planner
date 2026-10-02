import {api, notice, element, setBusy} from './api.js';
import {mapUrl} from './place-links.js?v=improvements-1';
const form = document.querySelector('#restaurant-form');
const results = document.querySelector('#restaurants');
let expiry;
form.addEventListener('submit', async event => {
  event.preventDefault(); setBusy(form, true); results.replaceChildren(); clearTimeout(expiry); notice('Finding your next favorite table…');
  try {
    const {restaurants} = await api('/restaurants', {city: document.querySelector('#city').value, cuisine: document.querySelector('#cuisine').value, radius: Number(document.querySelector('#radius').value)});
    notice(restaurants.length ? `${restaurants.length} places to try · OpenStreetMap · free search` : 'No mapped matches. Try a larger radius or remove the cuisine filter; missing tags can hide matches.');
    for (const place of restaurants) {
      const card = element('article', '', 'panel');
      card.append(element('p', place.detail, 'eyebrow'), element('h2', place.name), element('p', place.address || 'Address not recorded', 'small'));
      card.append(element('p', place.opening_hours ? `Recorded hours: ${place.opening_hours} (check with venue)` : 'Opening hours not recorded', 'small'));
      for (const diet of ['vegetarian', 'vegan']) {
        if (['yes', 'only'].includes(place[diet])) card.append(element('p', `${diet}: ${place[diet]} (community tagged)`, 'small'));
      }
      if (place.distance_m != null) card.append(element('p', `${(place.distance_m / 1000).toFixed(1)} km from search center`, 'small'));
      const url = mapUrl(place);
      if (url) { const link = element('a', 'View on Google Maps ↗'); link.href = url; link.target = '_blank'; link.rel = 'noopener noreferrer'; card.append(link); }
      results.append(card);
    }
    expiry = setTimeout(() => { results.replaceChildren(); notice('Results expired. Search again for current listings.'); }, 24 * 60 * 60 * 1000);
  } catch (error) { notice(error.message, true); }
  finally { setBusy(form, false); }
});
