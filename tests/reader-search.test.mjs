import test from 'node:test';
import assert from 'node:assert/strict';
import {matchesReaderText as matches, readerMatchRanges as ranges} from '../app/script/reader-search.mjs';

test('names are whole words, case-insensitive and width-normalized', () => {
  for (const text of ['Dora', 'DORA!', '“Dora,” she said.', "Dora’s hat", 'Dora-chan', 'Ｄｏｒａ']) assert.equal(matches(text, 'dora'), true, text);
  for (const text of ['adorable', 'Adoration', 'Pandora', 'Doral', '_Dora', 'Dora2', 'édora', 'Doraé']) assert.equal(matches(text, 'dora'), false, text);
  assert.equal(matches('adorable Dora', 'dora'), true);
});
test('phrases preserve word edges and whitespace, never compact English', () => {
  assert.equal(matches('The red\n  door.', 'red door'), true);
  assert.equal(matches('The red doorway.', 'red door'), false);
  assert.equal(matches('red door', 'reddoor'), false);
  assert.equal(matches('go in', 'gin'), false);
  assert.equal(matches('red\u0000door', 'red door'), false);
  assert.equal(matches('C++ and [x]', 'C++'), true);
  assert.equal(matches('anything', '   '), true);
});
test('Japanese retains unspaced, cross-line and width-normalized matching', () => {
  assert.equal(matches('私は彼女を見た', '彼女'), true);
  assert.equal(matches('彼\n女を見た', '彼女'), true);
  assert.equal(matches('ﾄﾞﾗに会った', 'ドラ'), true);
  assert.equal(matches('可愛い', 'dora'), false);
});
test('highlight ranges obey the same word rule and preserve original offsets', () => {
  assert.deepEqual(ranges('adorable Dora and DORA’s', 'dora'), [{start:9,end:13},{start:18,end:22}]);
  for (const [text,query] of [['Ｄｏｒａ','dora'],['cafe\u0301','café'],['oﬃce','office'],['彼\n女','彼女'],['red\n door','red door']]) {
    assert.equal(matches(text,query), true);
    assert.deepEqual(ranges(text,query), [{start:0,end:text.length}]);
  }
  assert.deepEqual(ranges('adorable','dora'), []);
  assert.deepEqual(ranges('😀 Dora','dora'), [{start:3,end:7}]);
});
