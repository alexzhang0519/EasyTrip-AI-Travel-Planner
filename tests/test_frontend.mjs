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
