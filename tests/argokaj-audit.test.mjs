import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read = path => JSON.parse(readFileSync(new URL('../public/audit-data/'+path,import.meta.url),'utf8'));
const data = read('comparison.json'), audit = read('dossiers.json');

test('both severities count as errors in the public total', () => {
  assert.equal(audit.summary.uniqueRetainedFindings,
    audit.summary.uniqueSeverity.material + audit.summary.uniqueSeverity.minor);
  const page=readFileSync(new URL('../app/audit/page.tsx',import.meta.url),'utf8');
  for(const label of ['Total errors','Material errors','Minor errors']) assert.ok(page.includes(label));
});

test('comparison preserves complete source groups and exact phrase evidence', () => {
  assert.equal(data.label,'Argokaj');
  assert.equal(data.scripts.length,84);
  const groups=data.scripts.flatMap(s=>s.groups);
  assert.equal(groups.length,5149);
  const sources=groups.flatMap(g=>g.source);
  assert.equal(sources.length,13128);
  assert.equal(new Set(sources.map(s=>s.ref)).size,13128);
  const targets=groups.flatMap(g=>g.target);
  assert.equal(targets.length,14017);
  assert.equal(new Set(targets.map(t=>t.id)).size,14017);
  const covered=new Set();
  let spans=0;
  for(const t of targets) {
    assert.doesNotMatch(t.text,/<\/?(?:ruby|rt)(?:\s|>)/i);
    for(const h of t.highlights) {
      assert.ok(h.start>=0 && h.end>h.start && h.end<=t.text.length);
      const finding=data.findings[h.findingId];
      assert.ok(finding);
      assert.ok(finding.occurrenceQuotes.includes(t.text.slice(h.start,h.end)),h.findingId);
      covered.add(h.findingId); spans++;
    }
  }
  assert.equal(spans,1147);
  assert.equal(covered.size,1137);
  assert.equal(Object.keys(data.findings).length,1137);
});

test('Fate-style dossiers separate full counts, curated examples, and counterexamples', () => {
  const dossiers=audit.groups.flatMap(g=>g.dossiers);
  assert.equal(dossiers.length,24);
  const ids=new Set(dossiers.map(d=>d.id));
  for(const d of dossiers) {
    assert.equal(d.retainedCount,new Set(d.findingIds).size);
    assert.equal(d.exampleCount,d.examples.length);
    assert.ok(d.examples.length<=8);
    assert.equal(d.counterexampleCount,d.counterexamples.length);
    for(const e of d.examples) {
      assert.ok(d.findingIds.includes(e.findingId));
      assert.deepEqual(e.context,data.refLocations[e.ref]);
      assert.equal(e.argokaj,data.findings[e.findingId].argokaj);
    }
    for(const e of d.counterexamples) assert.deepEqual(e.context,data.refLocations[e.ref]);
    for(const id of d.relatedDossiers||[]) assert.ok(ids.has(id));
  }
  assert.equal(audit.summary.uniqueRetainedFindings,1137);
  assert.equal(audit.summary.uniqueSeverity.material,103);
  assert.equal(audit.summary.uniqueSeverity.minor,1034);
  for(const f of Object.values(data.findings)) {
    assert.ok(f.dossiers.length);
    assert.ok(f.dossiers.every(id=>ids.has(id)));
  }
});

test('withdrawn and unsettled claims never become reader annotations', () => {
  for(const id of ['ALB-A-4017-006','ALB-A-1016-003','ALB-A-4002-004','ALB-A-4003-001','ALB-A-3001-002','ALB-A2-2013-006','ALB-A2-5005-010'])
    assert.equal(data.findings[id],undefined,id);
});
