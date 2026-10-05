import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

const json = path => JSON.parse(readFileSync(new URL('../public/script-data/'+path, import.meta.url), 'utf8'));

test('all 13,128 passages in 84 scripts are browsable and searchable exactly once', () => {
  const index = json('index.json'), corpus = json('concordance.json'), summary = json('summary.json');
  assert.equal(index.totalLines, 13_128);
  assert.equal(summary.totalScripts, 84);
  assert.equal(summary.pass3Lines, 10_840);
  assert.equal(summary.deeplLines, 2_288);
  assert.equal(index.version, corpus.version);
  assert.equal(index.version, summary.version);
  assert.equal(index.totalLines, corpus.totalLines);
  assert.equal(index.totalLines, summary.totalLines);
  const refs = new Set();
  let scripts = 0;
  for (const route of index.routes) {
    const searchableRoute = corpus.routes.find(item => item.id === route.id);
    assert.ok(searchableRoute);
    let routeCount = 0;
    for (const script of route.scripts) {
      scripts++;
      const payload = json(script.file);
      const searchableScript = searchableRoute.scripts.find(item => item.id === script.id);
      assert.ok(searchableScript);
      assert.equal(payload.route, route.id);
      assert.equal(payload.scriptId, script.id);
      assert.equal(payload.lines.length, script.lineCount);
      assert.equal(payload.lines.length, searchableScript.lines.length);
      routeCount += payload.lines.length;
      payload.lines.forEach((line, i) => {
        assert.ok(!refs.has(line.ref), line.ref);
        refs.add(line.ref);
        assert.equal(line.line, i+1);
        assert.ok(line.english.trim(), line.ref);
        assert.doesNotMatch(line.english, /\bruby\s*:/i, line.ref);
        assert.deepEqual(searchableScript.lines[i].slice(0,7), [line.ref,line.line,
          line.speakerJa,line.speakerEn,line.japanese,line.english,line.japaneseRuby]);
      });
    }
    assert.equal(routeCount, route.lineCount);
  }
  assert.equal(scripts, 84);
  assert.equal(refs.size, 13_128);
  assert.equal(json('1001.json').lines[1].english,
    'In the village where I was born,\nThere lived a sailor,\nAnd he told me of his days\nAboard a ship of fools.');
  assert.equal(json('3016.json').lines[2].english,
    'Color.\nGorgeous.\nResplendent.\nGlittering.\nThe light draped across the sky tonight: an aurora in curtains.');
  const opening = json('1002.json').lines;
  assert.match(opening[36].english, /Should one laugh at him\?/);
  assert.match(opening[38].english, /their underwear/);
  assert.match(opening[53].english, /captain—the albino girl—/);
  assert.match(opening[60].english, /^For a split second, he almost pictured/);
});
