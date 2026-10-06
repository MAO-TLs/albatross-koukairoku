"""Source-bound settings label polarity and native placement regressions."""
from pathlib import Path
import struct
import unittest
from build_ui_patch import toggle_label, DECODED, PATCH, parse_xfl


class SettingsLabels(unittest.TestCase):
    def test_stop_voice_japanese_polarity(self):
        # Spot-read originals: vocst_off = あり, vocst_on = なし.
        self.assertEqual(toggle_label('vocst_off'), 'On')
        self.assertEqual(toggle_label('vocst_on'), 'Off')

    def test_other_toggle_polarities_are_unchanged(self):
        for prefix in ('gef', 'bgm', 'voc', 'sef', 'pv00', 'pv01', 'pv06'):
            self.assertEqual(toggle_label(prefix+'_on'), 'On')
            self.assertEqual(toggle_label(prefix+'_off'), 'Off')
        self.assertEqual(toggle_label('bgr_off'), 'On')
        self.assertEqual(toggle_label('bgr_on'), 'Off')

    def test_native_stop_voice_left_on_right_off(self):
        raw = (DECODED/'grps/confscrn.lwg').read_bytes()
        pos = 24
        positions = {}
        for _ in range(struct.unpack_from('<I', raw, 12)[0]):
            length = raw[pos+17]
            name = raw[pos+18:pos+18+length].decode('cp932')
            positions[name] = struct.unpack_from('<ii', raw, pos)
            pos += 18+length
        for suffix in ('', '_f', '_c'):
            self.assertEqual(positions['vocst_off'+suffix], (169,195))
            self.assertEqual(positions['vocst_on'+suffix], (223,195))

    def test_hotfix_changes_only_six_stop_voice_layers(self):
        old = parse_xfl((PATCH/'reports/pre-hotfix-v1.0.0/grps.xfl').read_bytes())
        new = parse_xfl((PATCH/'build/game/grps.xfl').read_bytes())
        self.assertEqual([e.name_field for e in old.entries], [e.name_field for e in new.entries])
        changed = [a.name for a,b in zip(old.entries,new.entries) if a.payload != b.payload]
        self.assertEqual(changed, ['confscrn.lwg'])
        def layers(raw):
            pos, result = 24, {}
            data_start = 28+struct.unpack_from('<I',raw,20)[0]
            for _ in range(struct.unpack_from('<I',raw,12)[0]):
                offset,size = struct.unpack_from('<II',raw,pos+9)
                length = raw[pos+17]
                name = raw[pos+18:pos+18+length]
                result[name] = (raw[pos:pos+9], raw[data_start+offset:data_start+offset+size])
                pos += 18+length
            return result
        before = layers(next(e.payload for e in old.entries if e.name == 'confscrn.lwg'))
        after = layers(next(e.payload for e in new.entries if e.name == 'confscrn.lwg'))
        self.assertEqual(list(before), list(after))
        expected = {('vocst_'+state+suffix).encode() for state in ('on','off') for suffix in ('','_f','_c')}
        self.assertEqual({name for name in before if before[name][1] != after[name][1]}, expected)
        for name in before:
            self.assertEqual(before[name][0], after[name][0])
        for suffix in ('','_f','_c'):
            self.assertEqual(after[('vocst_off'+suffix).encode()][1], before[('vocst_on'+suffix).encode()][1])
            self.assertEqual(after[('vocst_on'+suffix).encode()][1], before[('vocst_off'+suffix).encode()][1])


if __name__ == '__main__': unittest.main()
