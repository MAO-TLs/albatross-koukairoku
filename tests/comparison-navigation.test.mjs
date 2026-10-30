import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {parseReaderLocation} from '../app/script/location.mjs';
const index=JSON.parse(readFileSync(new URL('../public/script-data/index.json',import.meta.url)));
const parse=path=>parseReaderLocation('https://example.test/script/'+path,index);

test('comparison uses the same reader controls, not a second toolbar',()=>{
  const entry=readFileSync(new URL('../app/script/Reader.tsx',import.meta.url),'utf8');
  const view=readFileSync(new URL('../app/script/ArgokajReader.tsx',import.meta.url),'utf8');
  assert.match(entry,/<ScriptBrowser/);
  assert.doesNotMatch(entry,/ArgokajReader/);
  assert.doesNotMatch(view,/className="reader-controls"|<select|pushState|replaceState/);
  assert.match(view,/s\.japanese\.trim\(\)/);
});
test('audit group links select their script without a route parameter',()=>{
  const state=parse('?script=1008&compare=argokaj&errors=argokaj#albatross-argokaj:1008:run:00019');
  assert.equal(state.scriptId,'1008');
  assert.equal(state.pendingRef,'albatross-argokaj:1008:run:00019');
  assert.equal(state.argokaj,true); assert.equal(state.argokajErrors,true);
  assert.equal(state.searchScope,'script');
});
test('script-only links, source anchors, queries and corpus filters survive reload',()=>{
  assert.equal(parse('?script=1008').scriptId,'1008');
  const state=parse('?script=1008&q=sailor&compare=argokaj');
  assert.equal(state.scriptQuery,'sailor');
  const source=parse('#albatross:1008:000001');
  assert.equal(source.scriptId,'1008');
  assert.equal(source.pendingRef,`albatross:${source.routeId}:1008:000001`);
  const corpus=parse('?scope=all&q=sailor&section=section-1&compare=argokaj');
  assert.equal(corpus.searchScope,'corpus'); assert.equal(corpus.corpusQuery,'sailor');
  assert.equal(corpus.corpusRouteId,'section-1');
  assert.equal(parse('?compare=argokaj#%invalid').pendingRef,'');
});
