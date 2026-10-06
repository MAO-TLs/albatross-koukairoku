import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync, existsSync} from 'node:fs';
import {createHash} from 'node:crypto';
const read = p => readFileSync(new URL('../'+p, import.meta.url), 'utf8');
const sha = p => createHash('sha256').update(read(p)).digest('hex');
test('canonical MAO publication and reader styles remain exact copies', () => {
  assert.equal(sha('app/mao-publication-template.css'), 'ba5e364b91a96297549ae7c552769af9cff01ae044b15c658e770fd2a55e6d7a');
  assert.equal(sha('app/mao-reader-template.css'), '24728a1a18fa4eec57cc653f3a0911221e07b6fa69368b822789677d739c4b7f');
});
test('steel theme changes colors only, not layout or typography', () => {
  assert.doesNotMatch(read('app/theme.css'), /[;{]\s*(?:font-size|width|height|margin|padding|display|grid-template|gap|line-height|letter-spacing)\s*:/);
  assert.equal(sha('app/globals.css'), '1b8125a7bea0d401c9a20bea7077f83f7ddaa9fbf97e36ab272a27f9eeabed5e');
  assert.match(read('app/theme.css'), /--paper:#f7f8f9/);
});
test('landing keeps MAO section structure and credits', () => {
  const page = read('app/page.tsx');
  for (const s of ['hero-grid shell', 'hero-copy', 'hero-actions', 'compatibility', 'release-strip', 'shell release-grid', 'section-heading', 'install-section', 'install-heading', 'credits-section', 'Project Lead', 'MAO', 'Translator', 'GPT-6 Astra', 'Special Thanks', 'gambs']) assert.ok(page.includes(s), s);
  assert.doesNotMatch(page, /chapter-grid|box-art/);
  assert.ok(page.indexOf('Open the script browser') > page.indexOf('Browse the complete script'));
  assert.match(page, /Download complete release/);
  assert.match(page, /Version<\/span><strong>\{patch.version\}/);
  assert.match(page, /Status<\/span><strong className="release-status">Released/);
  assert.match(page, /Main game/);
  assert.match(page, /MB · <a href=\{patch.releaseUrl\}>Release notes/);
  assert.match(page, /Windows \+ Wine · Japanese DVD retail edition required/);
  assert.match(page, /className="install-steps"/);
  assert.equal((page.match(/<li><span>0[123]<\/span>/g) || []).length, 3);
  assert.equal((page.match(/className="hero-actions"/g) || []).length, 1);
  assert.equal((page.match(/className="install-warning"/g) || []).length, 2);
  assert.match(page, /bilingual script is available now\.<\/p>\s*<\/div>\s*<a className="text-link"/);
  assert.match(page, /<code>Install English Patch\.cmd<\/code>/);
  assert.doesNotMatch(page, /<code>\s|\s<\/code>/);
  assert.match(page, /unabridged/);
});
test('public script has no audit or unsupported release claims', () => {
  assert.equal(existsSync(new URL('../app/audit',import.meta.url)), false);
  assert.doesNotMatch(read('app/SiteNav.tsx'), /Audit/);
  assert.match(read('app/layout.tsx'), /index: true, follow: true/);
  assert.match(read('public/robots.txt'), /Allow: \//);
  assert.doesNotMatch(read('app/page.tsx'), /Patch coming soon|46,618|18\.1 MB|v1\.1/);
  const patch = JSON.parse(read('public/patch-release.json'));
  assert.equal(patch.version, '1.0.0');
  assert.match(patch.downloadUrl, /^https:\/\/github.com\/MAO-TLs\/albatross-koukairoku\/releases\/download\/v1\.0\.0\/Albatross-Koukairoku-English-v1\.0\.0\.zip$/);
  assert.equal(patch.sha256, '6920c784ea3373865a068877afe00d718ac9306343b40b2066bd89a5e35b4008');
  assert.equal(patch.revision, '2026-10-07-stop-voice-hotfix');
  assert.equal(patch.exeSha256, '92649ab3facdf7f7026de735bdd928b45a54cc55b1a4f4a2cfee2c07edd8bd54');
  assert.equal(patch.size, 3550347);
  assert.equal(patch.requiresOriginalGame, true);
  assert.equal(patch.standaloneMacApp, false);
  assert.match(read('public/patch-installation.txt'), /MAO-original-backup|--uninstall/);
  assert.equal(existsSync(new URL('../.github/workflows/pages.yml',import.meta.url)), true);
});
test('hero and title are Albatross-specific', () => {
  assert.match(read('app/page.tsx'), /ALBATROSS<br \/>KOUKAIROKU/);
  assert.match(read('app/page.tsx'), /moonlit-sail-hero\.png/);
  assert.match(read('app/page.tsx'), /Mareni’s uncompromising prose/);
  assert.doesNotMatch(read('app/page.tsx') + read('app/SiteFooter.tsx') + read('app/script/page.tsx'), /Saihate|WHITE ALBUM|Farthest2015/);
});
test('complete reader is mounted through the existing MAO engine', () => {
  assert.match(read('app/script/page.tsx'), /<ScriptBrowser \/>/);
  assert.match(read('app/script/page.tsx'), /Complete script/);
  assert.doesNotMatch(read('app/script/page.tsx'), /will be available|Coming soon/);
  assert.match(read('app/script/ScriptBrowser.tsx'), /albatross-public-concordance/);
  assert.match(read('app/script/ScriptBrowser.tsx'), /className="reader-controls"/);
});
