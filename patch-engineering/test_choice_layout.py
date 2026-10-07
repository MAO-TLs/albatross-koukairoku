"""Regression for the invisible twins menu and every original choice tag."""
import json
import struct
import unittest

from build_script_patch import (CORPUS, GAME_ROOT, OUTPUT_ARCHIVE, READER_ROOT,
                                SOURCE_ARCHIVE, assert_gsc_control_preserved,
                                parse_gsc, parse_xfl, read_jsonl, runtime_text)
from test_engine_layout import emulator, UC_X86_REG_EBP, UC_X86_REG_EDI, UC_X86_REG_ESI


def native_menu_prefix(text, question=False):
    """Run the actual question/answer parser through its asset-number decision."""
    uc = emulator()
    pointer, stub = 0x600000, 0x681100
    encoded = text.encode('cp1252') + b'\0'
    uc.mem_write(pointer, encoded)
    # ASCII tags only: stub the Windows DBCS API, leaving native atoi/split intact.
    uc.mem_write(0x47307C, struct.pack('<I', stub))
    uc.mem_write(stub, bytes.fromhex('31 c0 c2 08 00'))
    uc.mem_write(0x708248, struct.pack('<I', pointer))
    uc.reg_write(UC_X86_REG_EBP, pointer if question else 0)
    uc.reg_write(UC_X86_REG_EDI, pointer)
    uc.emu_start(0x41309A if question else 0x410A00,
                 0x4130D2 if question else 0x410A2F, count=10000)
    number = uc.reg_read(UC_X86_REG_ESI)
    caption_pointer = struct.unpack('<I', uc.mem_read(0x708248, 4))[0]
    caption = bytes(uc.mem_read(caption_pointer, len(encoded))).split(b'\0')[0].decode('cp1252')
    return number, caption


class ChoiceTests(unittest.TestCase):
    def test_native_question_and_answer_paths_select_existing_artwork(self):
        assets = {entry.name for entry in parse_xfl((GAME_ROOT / 'grps.xfl').read_bytes()).entries}
        for question, asset in [(False, 'sel_a'), (True, 'sel_q')]:
            with self.subTest(question=question):
                number, caption = native_menu_prefix('Take a guess.', question)
                self.assertEqual((number, caption), (0, 'Take a guess.'))
                self.assertNotIn(f'{asset}{number:02d}.lwg', assets)
                number, caption = native_menu_prefix('<01>Take a guess.', question)
                self.assertEqual((number, caption), (1, 'Take a guess.'))
                self.assertIn(f'{asset}{number:02d}.lwg', assets)

    def test_reported_twins_captions_keep_hidden_layout_tag(self):
        rows = {row['ref']: row for row in read_jsonl(CORPUS)}
        reader = json.loads((READER_ROOT / '1004.json').read_text())['lines']
        for index, english in [(92, 'Take a guess.'), (93, "Flatly say I can't tell them apart.")]:
            source = rows[f'albatross:1004:{index:06d}']
            line = next(line for line in reader if line['line'] == index)
            self.assertEqual(line['english'], english)
            self.assertEqual(runtime_text(source, line, []), '<01>' + english)

    def test_all_packaged_choices_and_bytecode_preserved(self):
        original = {entry.name: entry for entry in parse_xfl(SOURCE_ARCHIVE.read_bytes()).entries}
        patched = {entry.name: entry for entry in parse_xfl(OUTPUT_ARCHIVE.read_bytes()).entries}
        choices = [row for row in read_jsonl(CORPUS)
                   if any(usage['kind'] == 'choice' for usage in row.get('usages', []))]
        self.assertEqual(len(choices), 30)
        self.assertEqual(len({row['script_id'] for row in choices}), 10)
        for row in choices:
            with self.subTest(ref=row['ref']):
                source = parse_gsc(original[row['archive_entry']].payload,
                                   script_id=row['script_id'], encoding='cp932')
                target = parse_gsc(patched[row['archive_entry']].payload,
                                   script_id=row['script_id'], encoding='cp1252')
                assert_gsc_control_preserved(source, target)
                text = target.strings[row['string_index']].text
                self.assertTrue(text.startswith('<01>'), text)
                self.assertEqual(text[:4], row['japanese_raw'][:4])
                self.assertEqual(native_menu_prefix(text), (1, text[4:]))
                self.assertEqual(native_menu_prefix(text, True), (1, text[4:]))

    def test_unknown_or_duplicate_layout_is_rejected(self):
        source = {'ref': 'test', 'controls': [], 'japanese_raw': 'No tag',
                  'usages': [{'kind': 'choice'}]}
        with self.assertRaisesRegex(ValueError, 'choice layout'):
            runtime_text(source, {'english': 'Caption'}, [])
        source['japanese_raw'] = '<01>原文'
        with self.assertRaisesRegex(ValueError, 'choice layout'):
            runtime_text(source, {'english': '<01>Caption'}, [])


if __name__ == '__main__':
    unittest.main()
