import {readFileSync} from 'node:fs';
import assert from 'node:assert/strict';
const root = new URL('../Frontend/static/js/', import.meta.url);
const moduleURL = source => 'data:text/javascript;base64,' + Buffer.from(source).toString('base64');
const linksURL = moduleURL(readFileSync(new URL('place-links.js', root), 'utf8'));
const {mapUrl, placeSegments, renderPlaceText, linkedSegments} = await import(linksURL);
const itinerarySource = readFileSync(new URL('itinerary.js', root), 'utf8').replace('./place-links.js?v=inline-maps-2', linksURL);
const {splitDays, activityMapUrl, renderStructuredItinerary} = await import(moduleURL(itinerarySource));
const kyoto={name:'City Museum',location:'Kyoto, Japan'};
const paris={name:'City Museum',location:'Paris, France'};
assert.equal(new URL(mapUrl(kyoto)).searchParams.get('query'),'City Museum, Kyoto, Japan');
assert.notEqual(mapUrl(kyoto),mapUrl(paris));
assert.equal(mapUrl({name:' '}),null);
assert.equal(placeSegments('City Museums',[kyoto]).some(s=>s.url),false);
assert.equal(placeSegments('City Museum',[kyoto,paris]).some(s=>s.url),false);
assert.equal(placeSegments('City Museum Annex',[kyoto,{name:'City Museum Annex'}])[0].text,'City Museum Annex');
const blocks=splitDays('Welcome!\nDay 1: Gardens\nMorning: City Museum\nDay 2: Art\nAfternoon: Gallery');
assert.equal(blocks.length,3);
assert.equal(blocks[2].title,'Day 2: Art');
assert.equal(blocks.map(b=>[b.title,...b.lines].filter(Boolean).join('\n')).join('\n'),'Welcome!\nDay 1: Gardens\nMorning: City Museum\nDay 2: Art\nAfternoon: Gallery');
assert.equal(splitDays('Just a normal reply.')[0].title,'');
// A minimal DOM verifies rendering creates text nodes, never HTML from the model.
globalThis.document={createTextNode:text=>({text}),createElement:tag=>({tag})};
const children=[];
renderPlaceText({append:child=>children.push(child)},'<script>alert(1)</script> City Museum',[kyoto]);
assert.equal(children[0].text,'<script>alert(1)</script> ');
assert.equal(children[1].tag,'a');
assert.equal(children[1].href,mapUrl(kyoto));
assert.equal(children[1].rel,'noopener noreferrer');
console.log('Frontend checks passed: name/context links, ambiguity, day sections, safe text rendering.');

const inline = linkedSegments('Visit [Central Park](https://www.google.com/maps/search/?api=1&query=Central%20Park%2C%20New%20York).', []);
assert.equal(inline[1].text, 'Central Park');
assert.equal(new URL(inline[1].url).searchParams.get('query'), 'Central Park, New York');
assert.equal(linkedSegments('[Bad](https://evil.example/)').some(s=>s.url), false);
assert.equal(linkedSegments('[Bad](javascript:alert(1))').some(s=>s.url), false);
assert.equal(linkedSegments('[Bad](https://www.google.com.evil.example/maps/search/?api=1&query=Bad)').some(s=>s.url), false);
assert.equal(linkedSegments('Visit [City Museum](https://www.google.com/maps/search/?api=1&query=City%20Museum%2C%20Kyoto) and City Museum.', [kyoto]).filter(s=>s.url).length, 2);

assert.equal(new URL(activityMapUrl({description:'A quiet afternoon',place:{name:'City Museum',city:'Kyoto, Japan',address:null}})).searchParams.get('query'),'City Museum, Kyoto, Japan');
assert.equal(activityMapUrl({description:'Lunch break',place:null}),null);

class TestNode {
  constructor(tag) { this.tag=tag; this.children=[]; this.classList={add(){}}; }
  append(...children) { this.children.push(...children); }
}
globalThis.document={createElement:tag=>new TestNode(tag),createTextNode:text=>({text})};
const structuredContainer=new TestNode('div');
renderStructuredItinerary(structuredContainer,{summary:'A trip',days:[{day:1,title:'Museums',activities:[{period:'Morning',description:'<img src=x onerror=alert(1)>',place:{name:'City Museum',city:'Kyoto, Japan',address:null}}]}],warnings:['Check hours']});
const section=structuredContainer.children.find(n=>n.tag==='section');
assert.equal(section.children.find(n=>n.tag==='a').textContent,'City Museum');
assert.equal(section.children.find(n=>n.tag==='p').textContent,'<img src=x onerror=alert(1)>');
assert.equal(new URL(section.children.find(n=>n.tag==='a').href).searchParams.get('query'),'City Museum, Kyoto, Japan');

// New visits discard drafts; explicit saved-trip entries load exactly once.
const {openPlanner} = await import(moduleURL(readFileSync(new URL('planner-session.js', root), 'utf8')));
const startupCalls = [];
const fakeHistory = {replaceState(...args) { startupCalls.push(['history', ...args]); }};
const savedData = {messages: [{role:'assistant', content:'Saved trip'}], pois: []};
const startupApi = async (path, body) => { startupCalls.push([path, body]); return savedData; };
assert.deepEqual(await openPlanner(startupApi, new URL('http://localhost/planner'), fakeHistory), {messages:[], pois:[]});
assert.deepEqual(startupCalls, [['/conversation/start', {}]]);
startupCalls.length = 0;
assert.equal(await openPlanner(startupApi, new URL('http://localhost/planner?trip=saved.json&inspiration=Art'), fakeHistory), savedData);
assert.deepEqual(startupCalls, [['/conversation/start', {}], ['/trips/saved.json/load', {}], ['history', null, '', '/planner?inspiration=Art']]);
startupCalls.length = 0;
await openPlanner(startupApi, new URL('http://localhost/planner?inspiration=Art'), fakeHistory);
assert.deepEqual(startupCalls, [['/conversation/start', {}]]);
await assert.rejects(openPlanner(async () => { throw new Error('Offline'); }, new URL('http://localhost/planner'), fakeHistory), /Offline/);
console.log('Draft lifecycle checks passed: new visit, saved trip, refresh, and startup failure.');

// Exercise actual saved-trip page handlers with a small DOM and mocked HTTP boundary.
class TripNode {
  constructor(tag, text = '') { this.tag = tag; this.textContent = text; this.children = []; this.handlers = {}; }
  append(...nodes) { for (const node of nodes) { node.parent = this; this.children.push(node); } }
  replaceChildren(...nodes) { this.children = []; this.append(...nodes); }
  addEventListener(name, handler) { this.handlers[name] = handler; }
  remove() { this.parent.children = this.parent.children.filter(node => node !== this); }
}
const tripContainer = new TripNode('section');
const pageCalls = [];
let failDelete = false;
globalThis.__tripTest = {
  api: async (path, body) => {
    pageCalls.push([path, body]);
    if (body === undefined) return {trips:[{id:'sample.json', name:'Kyoto', saved_at:'2026-10-02'}]};
    if (failDelete) throw new Error('Deletion unavailable');
    return {ok:true};
  },
  notice: () => {},
  element: (tag, text) => new TripNode(tag, text),
  setBusy: (node, busy) => { node.busy = busy; }
};
globalThis.document = {querySelector: () => tripContainer};
const mockPageApi = moduleURL('export const {api, notice, element, setBusy} = globalThis.__tripTest;');
await import(moduleURL(readFileSync(new URL('trips.js', root), 'utf8').replace('./api.js?v=tab-drafts-1', mockPageApi)));
const tripCard = tripContainer.children[0];
const deleteButton = tripCard.children.find(node => node.textContent === 'Delete trip');
assert.ok(deleteButton);
globalThis.confirm = () => false;
await deleteButton.handlers.click();
assert.equal(pageCalls.length, 1); // No mutation when confirmation is canceled.
assert.equal(tripContainer.children[0], tripCard);
globalThis.confirm = () => true;
failDelete = true;
await deleteButton.handlers.click();
assert.equal(tripContainer.children[0], tripCard);
assert.equal(tripCard.busy, false);
failDelete = false;
await deleteButton.handlers.click();
assert.deepEqual(pageCalls.at(-1), ['/trips/sample.json/delete', {}]);
assert.notEqual(tripContainer.children[0], tripCard);
assert.equal(tripContainer.children[0].children[0].textContent, 'Your next adventure is still unwritten.');
delete globalThis.__tripTest;
console.log('Saved-trip deletion UI checks passed: cancel, failure, success, and empty list.');

// The real API adapter uses a stable per-page ID and a keepalive close request.
const fetchRequests = [];
globalThis.fetch = async (url, options) => {
  fetchRequests.push([url, options]);
  return {ok: true, json: async () => ({ok:true})};
};
const apiSource = readFileSync(new URL('api.js', root), 'utf8');
const firstPage = await import(moduleURL(apiSource + '\n// test page one'));
const secondPage = await import(moduleURL(apiSource + '\n// test page two'));
await firstPage.api('/conversation/start', {});
await firstPage.api('/chat', {message:'Kyoto'});
await firstPage.api('/trips', {name:'My trip'});
await secondPage.api('/conversation/start', {});
await firstPage.closeDraft();
const pageId = fetchRequests[0][1].headers['X-EasyTrip-Draft'];
assert.ok(pageId);
assert.equal(fetchRequests[1][1].headers['X-EasyTrip-Draft'], pageId);
assert.equal(fetchRequests[2][1].headers['X-EasyTrip-Draft'], pageId);
assert.notEqual(fetchRequests[3][1].headers['X-EasyTrip-Draft'], pageId);
assert.equal(fetchRequests[4][0], '/api/conversation/close');
assert.equal(fetchRequests[4][1].headers['X-EasyTrip-Draft'], pageId);
assert.equal(fetchRequests[4][1].keepalive, true);
console.log('Tab API checks passed: isolated identity, save identity, and close cleanup.');
