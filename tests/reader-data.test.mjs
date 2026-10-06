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
  assert.equal(summary.editorialCorrections, 55);
  assert.equal(summary.narratorCorrections, 437);
  assert.equal(summary.overcorrectionEdits, 28);
  assert.equal(summary.finalExcellenceEdits, 2006);
  assert.equal(summary.englishFullwidthSpaceCleanupLines, 18);
  assert.equal(summary.englishFullwidthSpaceCleanupOccurrences, 18);
  assert.equal(summary.mechanicalEditorialLines, 116);
  assert.equal(summary.mechanicalEditorialReplacements, 127);
  assert.equal(summary.englishDelimiterRepairLines, 42);
  assert.equal(summary.englishBreakRestorationLines, 3_471);
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
  assert.match(opening[36].english, /Should one laugh at a young man.*\?/);
  assert.match(opening[38].english, /their underwear/);
  assert.match(opening[53].english, /captain—the albino girl—/);
  assert.match(opening[60].english, /^For one instant he found himself on the verge of picturing/);
  assert.equal(json('5008.json').lines[113].english, '“I really did risk my life.”');
  assert.match(json('2010.json').lines[463].english, /^“Focus on his hands\.”$/);
  assert.match(json('2011.json').lines[191].english, /^\(What…!\? Her hair\'s changing color…\)$/);
  assert.match(json('4005.json').lines[261].english, /^Rui feels it\./);
  assert.match(json('4006.json').lines[25].english, /coupling with Rui/);
  assert.match(json('2010.json').lines[126].english, /Could Kuro feel something for him/);
  assert.doesNotMatch(json('2010.json').lines[126].english, /\bmy heart\b/i);
  assert.match(json('4010.json').lines[2].english, /Tomosato’s pronouncement/);
  assert.match(json('5007.json').lines[8].english, /the single-barreled gun that had burst/);
  assert.match(json('2008.json').lines[307].english, /a slender crimson thread ran down between her thighs/);
  assert.match(json('2003.json').lines[141].english, /landlubber/);
  assert.doesNotMatch(json('1002.json').lines[7].english, /affordable prostitute/);
});
