import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { SITE_BASE_PATH } from '../site-target.mjs';

const read = path => readFileSync(new URL('../' + path, import.meta.url));
const pngSize = bytes => {
  assert.equal(bytes.subarray(0, 8).toString('hex'), '89504e470d0a1a0a');
  return [bytes.readUInt32BE(16), bytes.readUInt32BE(20)];
};
test('site-wide icons use the title-specific mount, including nested reader routes', () => {
  const layout = read('app/layout.tsx').toString();
  assert.match(layout, /import \{ SITE_BASE_PATH \} from "\.\.\/site-target\.mjs"/);
  for (const file of ['favicon.svg', 'favicon.png', 'favicon.ico', 'apple-touch-icon.png']) {
    assert.ok(layout.includes('${SITE_BASE_PATH}/' + file), file);
    for (const page of [`https://mao-tls.github.io${SITE_BASE_PATH}/`, `https://mao-tls.github.io${SITE_BASE_PATH}/script/`]) {
      assert.equal(new URL(SITE_BASE_PATH + '/' + file, page).pathname, SITE_BASE_PATH + '/' + file);
    }
  }
});
test('favicon SVG is a self-contained, spoiler-free mark', () => {
  const svg = read('public/favicon.svg').toString();
  assert.match(svg, /viewBox="0 0 64 64"/);
  assert.doesNotMatch(svg, /<(?:script|image|text|foreignObject)\b|(?:href|onload)=/i);
});
test('PNG fallback and touch icon have the declared dimensions', () => {
  assert.deepEqual(pngSize(read('public/favicon.png')), [32, 32]);
  assert.deepEqual(pngSize(read('public/apple-touch-icon.png')), [180, 180]);
});
test('ICO contains three valid PNG frames at native tab sizes', () => {
  const ico = read('public/favicon.ico');
  assert.equal(ico.readUInt16LE(0), 0);
  assert.equal(ico.readUInt16LE(2), 1);
  assert.equal(ico.readUInt16LE(4), 3);
  for (const [i, size] of [16, 32, 48].entries()) {
    const entry = 6 + i * 16;
    assert.equal(ico[entry], size);
    assert.equal(ico[entry + 1], size);
    const length = ico.readUInt32LE(entry + 8);
    const offset = ico.readUInt32LE(entry + 12);
    assert.ok(offset >= 54 && offset + length <= ico.length);
    assert.deepEqual(pngSize(ico.subarray(offset, offset + length)), [size, size]);
  }
});

