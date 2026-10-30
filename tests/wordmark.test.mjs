import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read = p => readFileSync(new URL('../'+p,import.meta.url),'utf8');
test('brand never wraps; navigation yields instead',()=>{
 const css=read('app/wordmark.css');
 assert.match(css,/\.nav\.shell \.wordmark, \.masthead \.brand \{ max-width: none; white-space: nowrap; flex-shrink: 0; \}/);
 assert.match(css,/\.nav\.shell, \.masthead \{ flex-wrap: wrap;/);
 assert.match(css,/\.nav\.shell \.nav-links, \.masthead nav \{ flex-wrap: wrap;/);
 assert.ok(read('app/layout.tsx').includes('wordmark.css'));
});
