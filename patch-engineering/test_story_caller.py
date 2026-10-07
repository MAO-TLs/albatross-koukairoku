"""Execute the story caller's real preprocessing destination and stack frame."""
import struct
import unittest

from build_script_patch import OUTPUT_ARCHIVE, parse_gsc, parse_xfl
from test_engine_layout import (emulator, UC_HOOK_CODE, UC_X86_REG_EAX,
                                UC_X86_REG_ECX, UC_X86_REG_EDI, UC_X86_REG_ESP)
from engine_layout import ENGLISH_TEXT_FRAME_PATCHES


def caller_trace(raw, legacy=False, rebuild=0):
    uc = emulator()
    if legacy:
        for address, original, _ in ENGLISH_TEXT_FRAME_PATCHES:
            uc.mem_write(address, bytes.fromhex(original))
    scene, config, source, stack = 0x600000, 0x601000, 0x640000, 0x708000
    uc.mem_write(scene + 0x100, struct.pack('<I', config))
    uc.mem_write(source, raw + b'\0')
    uc.mem_write(stack, struct.pack('<7I', 0x682000, 11, 22, 33, 44, 55, 66))
    expected = bytes(uc.mem_read(stack, 28))
    uc.reg_write(UC_X86_REG_ECX, scene)
    if rebuild:
        # Both rebuild routines obtain a saved script/string reference and
        # feed it through the same preprocessor before rendering it again.
        uc.mem_write(config + 0x19C, struct.pack('<H', 1))
        uc.mem_write(scene + 0xF0, struct.pack('<I', 0x602000))
        uc.mem_write(stack + 4, struct.pack('<I', 0))
        expected = bytes(uc.mem_read(stack, 28))
        for address in (0x430F30, 0x40DFA0, 0x4301B0, 0x42D200):
            uc.mem_write(address, b'\xc3')
        uc.mem_write(0x42C6E0, bytes.fromhex('31 c0 c3'))
        uc.mem_write(0x413C70, bytes.fromhex('b8 01 00 00 00 c2 04 00'))
    # Stub only scene setup and script-table lookup; execute both native copies.
    uc.mem_write(0x42DA20, bytes.fromhex('c2 0c 00'))
    uc.mem_write(0x413AC0, b'\xb8' + struct.pack('<I', source) + bytes.fromhex('c2 04 00'))
    captured = {}
    def observe(u, address, size, _):
        if address in (0x42D7EF, 0x42C378, 0x42C51F):
            esp = u.reg_read(UC_X86_REG_ESP)
            captured['destination'] = struct.unpack('<I', u.mem_read(esp, 4))[0]
    uc.hook_add(UC_HOOK_CODE, observe)
    start, stop = ((0x42C2E0, 0x42C37D) if rebuild == 1 else
                   (0x42C480, 0x42C524) if rebuild == 2 else
                   (0x42D790, 0x42D7FE))
    uc.emu_start(start, stop, count=2000000)
    # Unicorn stops before executing the until-address hook.
    captured['caller_frame_intact'] = bytes(uc.mem_read(stack, 28)) == expected
    captured['output_bytes'] = bytes(uc.mem_read(captured['destination'], 8192)).split(b'\0')[0]
    captured['capacity'] = stack - captured['destination']
    captured['setting_argument'] = uc.reg_read(UC_X86_REG_EDI)
    if not legacy:
        epilogue = 0x42C470 if rebuild == 1 else 0x42C6C6 if rebuild == 2 else 0x42D91D
        if rebuild:
            # These two stopping points precede cdecl argument cleanup.
            uc.reg_write(UC_X86_REG_ESP, uc.reg_read(UC_X86_REG_ESP) + 8)
        uc.emu_start(epilogue, 0x682000, count=100)
        captured['returned_stack'] = uc.reg_read(UC_X86_REG_ESP)
    return captured


class StoryCallerTests(unittest.TestCase):
    def test_long_records_do_not_overwrite_return_or_arguments(self):
        records = []
        for entry in parse_xfl(OUTPUT_ARCHIVE.read_bytes()).entries:
            if not entry.name.endswith('.gsc'):
                continue
            script = parse_gsc(entry.payload, script_id=entry.name[:4], encoding='cp1252')
            for index, string in enumerate(script.strings):
                if len(string.raw) >= 900:
                    records.append((entry.name, index, string.raw))
        self.assertEqual(sum(len(raw) >= 1024 for _, _, raw in records), 3)
        for name, index, raw in records:
            with self.subTest(script=name, index=index):
                for rebuild in (0, 1, 2):
                    result = caller_trace(raw, rebuild=rebuild)
                    self.assertEqual(result['capacity'], 8192)
                    self.assertEqual(result['output_bytes'], raw)
                    self.assertTrue(result['caller_frame_intact'])
                    self.assertEqual(result['returned_stack'],
                                     0x70801C if not rebuild else 0x708004 if rebuild == 1 else 0x708008)
                    if not rebuild:
                        self.assertEqual(result['setting_argument'], 55)

    def test_frame_patches_and_argument_loads_are_exact(self):
        uc = emulator()
        for address, _, replacement in ENGLISH_TEXT_FRAME_PATCHES:
            expected = bytes.fromhex(replacement)
            self.assertEqual(bytes(uc.mem_read(address, len(expected))), expected)

    def test_pre_v101_destination_corrupts_caller_for_long_text(self):
        for rebuild in (0, 1, 2):
            result = caller_trace(b'A' * 1066, legacy=True, rebuild=rebuild)
            self.assertEqual(result['capacity'], 1024)
            self.assertFalse(result['caller_frame_intact'])


if __name__ == '__main__':
    unittest.main()
