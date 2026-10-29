"""Execute the actual patched x86 layout with synthetic glyphs and line boxes."""
import json
import struct
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "outputs/cross-channel-retranslation/engineering/v1_1_patch/toolchain/pe-analysis"),
                str(ROOT / "outputs/albatross-patch/toolchain/pe-tests")]
import pefile
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import *
from stack_probes import entry_jump

EXE = ROOT / "outputs/albatross-patch/build/game/Albatross.exe"


def emulator():
    emu = Uc(UC_ARCH_X86, UC_MODE_32)
    emu.mem_map(0x400000, 0x100000)
    emu.mem_write(0x400000, pefile.PE(str(EXE)).get_memory_mapped_image())
    emu.mem_map(0x600000, 0xA0000)
    emu.mem_map(0x700000, 0x10000)
    emu.reg_write(UC_X86_REG_ESP, 0x708000)
    return emu


def layout(text, columns, size=18, height=10000, details=False):
    emu = emulator()
    obj, pointers, metadata, glyph_base = 0x600000, 0x610000, 0x620000, 0x800000
    emu.mem_map(glyph_base, 0x300000)
    vtable, render, end = 0x680000, 0x681000, 0x682000
    def write32(addr, value): emu.mem_write(addr, struct.pack("<I", value))
    write32(obj + 0x58, pointers)
    write32(obj + 0x5C, 0x690000)
    write32(obj + 0x198, metadata)
    write32(obj + 0x170, columns * (size // 2))
    write32(obj + 0x16C, height)
    write32(obj + 0x17C, size // 2)
    write32(obj + 0x180, 0)
    emu.mem_write(obj + 0x1A2, struct.pack("<H", size))
    write32(vtable + 4, 0)
    write32(vtable + 0xC4, render)
    emu.mem_write(render, bytes.fromhex("c2 08 00"))
    emu.mem_write(0x45F2C0, bytes.fromhex("c2 04 00"))
    chars = []
    hard_breaks = set()
    for ch in text:
        if ch == "\n":
            hard_breaks.add(len(chars))
        else:
            chars.append(ch)
    emu.mem_write(obj + 0x60, struct.pack("<H", len(chars)))
    for index, ch in enumerate(chars):
        glyph = glyph_base + index * 0x100
        write32(pointers + index * 4, glyph)
        write32(glyph, vtable)
        emu.mem_write(glyph + 0x70, struct.pack("<hh", size // 2, size))
        emu.mem_write(metadata + index * 6,
                      bytes([0, index in hard_breaks, 1 if ch in " ,.!?:;)'\"" else 0,
                             ch.encode("cp1252")[0], 0, 0]))
    write32(0x708000, end)
    emu.reg_write(UC_X86_REG_ECX, obj)
    positions = {}
    def observe(uc, address, size, _):
        if address == render:
            index = (uc.reg_read(UC_X86_REG_ECX) - glyph_base) // 0x100
            x, y = struct.unpack("<II", uc.mem_read(uc.reg_read(UC_X86_REG_ESP) + 4, 8))
            positions[index] = (x, y)
        elif address == end:
            uc.emu_stop()
    emu.hook_add(UC_HOOK_CODE, observe)
    emu.emu_start(0x455420, end, count=1000000)
    assert len(positions) == len(chars), (len(positions), len(chars))
    lines = {}
    for index, ch in enumerate(chars):
        lines.setdefault(positions[index][1], []).append(ch)
    rows = ["".join(value).rstrip() for _, value in sorted(lines.items())]
    if details:
        return rows, positions, emu.reg_read(UC_X86_REG_EAX)
    return rows


class Tests(unittest.TestCase):
    def test_story_presets_apply_font_cell_and_safe_area_together(self):
        from engine_layout import STORY_FONT_SIZES, STORY_WIDTH, STORY_HEIGHT
        for selection, size in enumerate(reversed(STORY_FONT_SIZES)):
            uc = emulator()
            scene, textbox, auxiliary = 0x600000, 0x601000, 0x602000
            uc.mem_write(scene + 0x68, struct.pack("<I", textbox))
            uc.mem_write(textbox + 0x5C, struct.pack("<I", auxiliary))
            uc.reg_write(UC_X86_REG_ESI, scene)
            uc.reg_write(UC_X86_REG_EDI, 0)
            uc.reg_write(UC_X86_REG_EAX, selection)
            uc.emu_start(0x43034D, 0x43042E, count=100)
            self.assertEqual(struct.unpack("<H", uc.mem_read(textbox + 0x1A2, 2))[0], size)
            self.assertEqual(struct.unpack("<I", uc.mem_read(textbox + 0x17C, 4))[0], size // 2)
            self.assertEqual(struct.unpack("<2I", uc.mem_read(textbox + 0x16C, 8)),
                             (STORY_HEIGHT, STORY_WIDTH))
            self.assertEqual(struct.unpack("<H", uc.mem_read(auxiliary + 0x68, 2))[0], size // 2)
            self.assertEqual(struct.unpack("<I", uc.mem_read(auxiliary + 0x74, 4))[0], size // 2)
            self.assertEqual(uc.reg_read(UC_X86_REG_ESP), 0x708000)

    def test_native_reveal_clock_normal_slow_and_instant(self):
        # Drive the native timer and its actual glyph reveal callback, not a
        # Python approximation of how many frames each interval takes.
        for delay, expected_frames in [(0, [1]), (2, [1, 3, 5, 7]),
                                       (4, [1, 5, 9, 13])]:
            uc = emulator()
            obj, vtable, pointers, metadata = 0x600000, 0x680000, 0x610000, 0x620000
            def put(address, value): uc.mem_write(address, struct.pack("<I", value))
            put(obj, vtable)
            put(obj + 0xC, 1)
            put(obj + 0x80, 1)
            put(obj + 0x54, pointers)
            put(obj + 0x198 - 4, metadata)
            uc.mem_write(obj + 0x5C, struct.pack("<H", 4))
            # Both virtual show operations are stubbed; timing, metadata and
            # native increment/countdown logic are executed unchanged.
            put(vtable + 0x34, 0x681000)
            put(vtable + 0x5C, 0x681000)
            uc.mem_write(0x681000, bytes.fromhex("c2 04 00"))
            put(vtable + 0xF4, 0x681100)
            uc.mem_write(0x681100, b"\xb9" + struct.pack("<I", obj + 0x1E8)
                         + b"\xe9" + struct.pack("<i", 0x453F80 - 0x68110A))
            uc.mem_write(0x448210, bytes.fromhex("c2 0c 00"))
            for index in range(4):
                glyph = 0x630000 + index * 0x100
                put(pointers + index * 4, glyph)
                put(glyph, vtable)
                uc.mem_write(metadata + index * 6, struct.pack("<4BH", 0, 0, 0, 65, delay))
            frames = []
            previous = 0
            for frame in range(1, 20):
                uc.reg_write(UC_X86_REG_ESP, 0x708000)
                put(0x708000, 0x682000)
                uc.reg_write(UC_X86_REG_ECX, obj)
                uc.emu_start(0x4403B0, 0x682000, count=1000)
                revealed = struct.unpack("<H", uc.mem_read(obj + 0x164, 2))[0]
                if revealed != previous:
                    frames.append(frame)
                    previous = revealed
                if revealed == 4:
                    break
            self.assertEqual(previous, 4)
            self.assertEqual(frames, expected_frames)

    def test_text_speed_settings_are_distinct_and_preserve_selection(self):
        # Execute the real settings route, including the live setter. The
        # legacy caller can leave unrelated bits in the upper half-register.
        for upper in [0, 0xCAFE0000]:
            for selection, expected in [(0, 0), (1, 1), (2, 2), (3, 4)]:
                for deferred in [0, 1]:
                    uc = emulator()
                    manager, scene, config, textbox = 0x600000, 0x601000, 0x602000, 0x603000
                    uc.mem_write(manager + 0xEC, struct.pack("<I", scene))
                    uc.mem_write(scene + 0x74, struct.pack("<I", config))
                    uc.mem_write(scene + 0x68, struct.pack("<I", textbox))
                    uc.mem_write(textbox + 0x1A0, struct.pack("<H", 99))
                    uc.mem_write(0x482216, struct.pack("<H", selection))
                    uc.mem_write(0x708000, struct.pack("<4I", 0x682000, 0,
                                                     upper | selection, deferred))
                    uc.reg_write(UC_X86_REG_ECX, manager)
                    uc.emu_start(0x42DEA0, 0x682000, count=100)
                    self.assertEqual(struct.unpack("<H", uc.mem_read(config + 0x2C, 2))[0], expected)
                    self.assertEqual(struct.unpack("<H", uc.mem_read(textbox + 0x1A0, 2))[0],
                                     99 if deferred else expected)
                    self.assertEqual(struct.unpack("<H", uc.mem_read(0x482216, 2))[0], selection)
                    self.assertEqual(uc.reg_read(UC_X86_REG_ESP), 0x708010)

    def test_fast_glyph_registration_keeps_native_stable_order(self):
        for count in [2, 3, 800, 8193]:
            uc = emulator()
            # The constructor first creates ruby (index 0, priority 1000),
            # then appends priority-0 glyphs. Before each insertion ruby is
            # next-to-last; the newly appended glyph is last.
            before = list(range(1, count - 1)) + [0, count - 1]
            uc.mem_write(0x600038, struct.pack("<H", count))
            uc.mem_write(0x60003C, struct.pack("<I", 0x610000))
            uc.mem_write(0x610000, struct.pack(f"<{count}H", *before))
            uc.mem_write(0x708000, struct.pack("<4I", 0x682000, 111, 222, 0x453BCA))
            uc.reg_write(UC_X86_REG_ECX, 0x600000)
            uc.reg_write(UC_X86_REG_ESI, 0x600000)
            uc.reg_write(UC_X86_REG_EAX, 123)
            uc.reg_write(UC_X86_REG_EDX, 456)
            uc.reg_write(UC_X86_REG_EBX, 789)
            uc.emu_start(0x472E90, 0x682000, count=100)
            self.assertEqual(struct.unpack(f"<{count}H", uc.mem_read(0x610000, count * 2)),
                             tuple(range(1, count)) + (0,))
            self.assertEqual([uc.reg_read(r) for r in (UC_X86_REG_EAX, UC_X86_REG_EDX,
                                                      UC_X86_REG_EBX, UC_X86_REG_ECX)],
                             [123, 456, 789, 0x600000])
        uc = emulator()
        uc.mem_write(0x70800C, struct.pack("<I", 0x123456))
        uc.emu_start(0x472E90, 0x43C6C0, count=10)
        self.assertEqual(uc.reg_read(UC_X86_REG_EIP), 0x43C6C0)

    def test_story_presets_have_fixed_safe_geometry(self):
        from engine_layout import STORY_WIDTH, STORY_HEIGHT, STORY_ORIGIN
        uc = emulator()
        for height_address, width_address in [(0x430376, 0x43037B),
                                               (0x4303A3, 0x4303A8),
                                               (0x4303F1, 0x4303F6)]:
            self.assertEqual(bytes(uc.mem_read(height_address, 5)),
                             b"\x68" + struct.pack("<I", STORY_HEIGHT))
            self.assertEqual(bytes(uc.mem_read(width_address, 5)),
                             b"\x68" + struct.pack("<I", STORY_WIDTH))
        uc.reg_write(UC_X86_REG_EAX, 0xFFFFFFFF)  # arbitrary saved snap index
        uc.emu_start(0x4307A5, 0x4307AF, count=20)
        self.assertEqual(struct.unpack("<II", uc.mem_read(0x707FF8, 8)),
                         (STORY_ORIGIN, STORY_ORIGIN))

    def test_twins_page_fits_and_reflows_at_every_size(self):
        from engine_layout import STORY_WIDTH, STORY_HEIGHT, STORY_ORIGIN
        text = ("Each deftly covered the other's blind spots; at times one even lent the other "
                "her shoulder for a gun rest, steadying her aim and making possible a precision "
                "scarcely credible from a handgun. The free sweep of their arms, the smooth "
                "play of their feet as they took position—nothing in their motion caught "
                "or faltered. They moved like a single living creature.\n"
                "Indeed, the two first mates—one to the right, one to the left—had identical "
                "faces down to the last detail. Naturally enough: they were twins. One fired; "
                "the other picked off a thug who had been aiming at her sister. One ran dry; "
                "the other instantly passed her a fresh cylinder. One moment they spun and "
                "wheeled in a dizzying blur; the next they stopped dead in a bold, theatrical pose.")
        row_counts = []
        from engine_layout import STORY_FONT_SIZES
        for size in STORY_FONT_SIZES:
            rows, positions, fits = layout(text, STORY_WIDTH // (size // 2),
                                          size, STORY_HEIGHT, details=True)
            row_counts.append(len(rows))
            self.assertEqual(fits, 1)
            self.assertEqual(" ".join(rows).split(), text.split())
            self.assertTrue(rows[-1].endswith("pose."))
            self.assertLessEqual(max(y + size for x, y in positions.values()), STORY_HEIGHT)
            visible = [pos for ch, pos in zip(text.replace("\n", ""), positions.values())
                       if ch != " "]  # the native kinsoku path permits hanging spaces
            self.assertLessEqual(max(x + size // 2 for x, y in visible), STORY_WIDTH)
            self.assertLess(STORY_ORIGIN + max(y + size for x, y in positions.values()), 560)
        self.assertLess(row_counts[0], row_counts[-1])

    def check_parser(self, entry, stack_return_offset, stack_text_offset,
                     text="—Once. “A”—…é", capacity=100):
        uc = emulator()
        uc.mem_write(0x600062, struct.pack("<H", capacity))
        uc.mem_write(0x600198, struct.pack("<I", 0x620000))
        uc.mem_write(0x640000, text.encode("cp1252") + b"\0")
        uc.mem_write(0x708000 + stack_return_offset, struct.pack("<I", 0x682000))
        uc.mem_write(0x708000 + stack_text_offset, struct.pack("<I", 0x640000))
        # Simulate a legacy CRT claiming every byte is a DBCS lead byte.
        uc.mem_write(0x462395, bytes.fromhex("b8 01 00 00 00 c3"))
        uc.mem_write(0x454FC0, bytes.fromhex("c2 14 00"))
        uc.reg_write(UC_X86_REG_ESI, 0x600000)
        decoded = []
        def observe(u, address, size, _):
            if address == 0x454FC0:
                value = struct.unpack("<I", u.mem_read(u.reg_read(UC_X86_REG_ESP) + 4, 4))[0]
                decoded.append(value & 0xFFFF)
                u.mem_write(0x600060, struct.pack("<H", len(decoded)))
            elif address == 0x682000:
                u.emu_stop()
        uc.hook_add(UC_HOOK_CODE, observe)
        uc.emu_start(entry, 0x682000, count=max(10000, len(text) * 200))
        self.assertEqual(decoded, list(text.encode("cp1252")))

    def test_parser_emits_each_english_byte_separately(self):
        self.check_parser(0x454BB1, 0x14, 0x18)

    def test_primary_parser_emits_unsigned_english_bytes(self):
        self.check_parser(0x454407, 0xEC, 0xF0)

    def test_long_english_page_is_not_cut_at_800_glyphs(self):
        from engine_layout import STORY_CAPACITY
        uc = emulator()
        self.assertEqual(bytes(uc.mem_read(0x42FC19, 5)),
                         b"\x68" + struct.pack("<I", STORY_CAPACITY))
        text = "An intact English sentence. " * 70 + "The final word survives."
        for args in [(0x454BB1, 0x14, 0x18), (0x454407, 0xEC, 0xF0)]:
            self.check_parser(*args, text=text, capacity=STORY_CAPACITY)

    def test_display_parser_never_combines_cp1252_pairs(self):
        for start, end in [(0x454BCD, 0x454C39), (0x454426, 0x4544AE)]:
            for flags in [0, 0x40]:
                uc = emulator()
                uc.reg_write(UC_X86_REG_EFLAGS, flags | 2)
                uc.emu_start(start, end, count=1)
                self.assertEqual(uc.reg_read(UC_X86_REG_EIP), end)

    def test_story_preprocessors_never_apply_locale_dbcs_pairing(self):
        from engine_layout import (ENGLISH_PREPROCESSOR_BUFFER,
                                   ENGLISH_PREPROCESSOR_DBCS_CALLS)
        expected = bytes.fromhex("83 c4 08 31 c0 90")
        uc = emulator()
        for address in ENGLISH_PREPROCESSOR_DBCS_CALLS:
            self.assertEqual(bytes(uc.mem_read(address, len(expected))), expected)
        self.assertEqual(bytes(uc.mem_read(0x41D7E4, 6)),
                         entry_jump(0x41D7E4))
        self.assertEqual(bytes(uc.mem_read(0x41D7F6, 7)),
                         bytes.fromhex("8b b4 24")
                         + struct.pack("<I", ENGLISH_PREPROCESSOR_BUFFER + 16))
        self.assertEqual(bytes(uc.mem_read(0x41D80E, 6)),
                         b"\x81\xc4" + struct.pack("<I", ENGLISH_PREPROCESSOR_BUFFER))

    def test_cp1252_punctuation_is_unsigned(self):
        for char in ["—", "–", "’", "“", "…", "é", "A"]:
            uc = emulator()
            uc.mem_write(0x600000, char.encode("cp1252"))
            uc.reg_write(UC_X86_REG_EAX, 0x600000)
            uc.reg_write(UC_X86_REG_ECX, 0xDEADBEEF)
            uc.emu_start(0x454EF3, 0x454EF7, count=1)
            self.assertEqual(uc.reg_read(UC_X86_REG_ECX) & 0xFFFF,
                             char.encode("cp1252")[0])
            uc.reg_write(UC_X86_REG_EDX, 0x600000)
            uc.reg_write(UC_X86_REG_EAX, 0xDEADBEEF)
            uc.emu_start(0x4549DC, 0x4549E0, count=1)
            self.assertEqual(uc.reg_read(UC_X86_REG_EAX) & 0xFFFF,
                             char.encode("cp1252")[0])

    def test_screenshot_regressions(self):
        for text in ["—A ship that sailed on through the cracks of a dark and chaotic age.",
                     "—To put it plainly, a ship whose very ability to float appeared to defy naval architecture and the laws of physics."]:
            for columns in [30, 40, 41, 42, 55, 71]:
                rows = layout(text, columns)
                self.assertEqual(" ".join(rows).split(), text.split())
                self.assertTrue(all(len(row) <= columns for row in rows))

    def test_authored_breaks(self):
        text = "Color.\nGorgeous.\nResplendent.\nGlittering.\nThe light draped across the sky tonight: an aurora in curtains."
        rows = layout(text, 42)
        self.assertEqual(rows[:4], text.splitlines()[:4])
        self.assertEqual(" ".join(rows).split(), text.split())

    def test_long_word_fallback(self):
        rows = layout("A " + "z" * 80, 30)
        self.assertEqual("".join(rows).replace(" ", ""), "A" + "z" * 80)

    def test_padding_capture(self):
        for ch in ["A", " ", "’", "—"]:
            uc = emulator()
            uc.mem_write(0x600060, struct.pack("<H", 7))
            uc.mem_write(0x600198, struct.pack("<I", 0x620000))
            uc.mem_write(0x6001A2, struct.pack("<H", 18))
            uc.mem_write(0x600058, struct.pack("<I", 0x610000))
            uc.mem_write(0x61001C, struct.pack("<I", 0x630000))
            uc.reg_write(UC_X86_REG_EDI, 0x600000)
            uc.reg_write(UC_X86_REG_ESI, ch.encode("cp1252")[0])
            uc.reg_write(UC_X86_REG_EAX, 123)
            uc.reg_write(UC_X86_REG_ECX, 456)
            uc.reg_write(UC_X86_REG_EDX, 789)
            uc.hook_add(UC_HOOK_CODE, lambda u, a, s, _: u.emu_stop()
                        if a in (0x4550CC, 0x455377) else None)
            uc.emu_start(0x472D80, 0x4550CC, count=100)
            self.assertEqual(bytes(uc.mem_read(0x620000 + 7 * 6 + 3, 1)), ch.encode("cp1252"))
            self.assertEqual([uc.reg_read(r) for r in (UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_EDX)],
                             [123, 456, 789])

    def test_extended_ansi_uses_single_mono_cell(self):
        for size in [14, 18, 24]:
            for char in ["—", "…", "’", "é", "A"]:
                uc = emulator()
                uc.mem_write(0x600060, struct.pack("<H", 0))
                uc.mem_write(0x600198, struct.pack("<I", 0x620000))
                uc.mem_write(0x6001A2, struct.pack("<H", size))
                uc.mem_write(0x600058, struct.pack("<I", 0x610000))
                uc.mem_write(0x610000, struct.pack("<I", 0x630000))
                width = size if ord(char) > 127 else size // 2
                uc.mem_write(0x630070, struct.pack("<HH", width, size))
                uc.reg_write(UC_X86_REG_EDI, 0x600000)
                uc.reg_write(UC_X86_REG_ESI, char.encode("cp1252")[0])
                uc.hook_add(UC_HOOK_CODE, lambda u, a, s, _: u.emu_stop()
                            if a in (0x4550CC, 0x455377) else None)
                uc.emu_start(0x472D80, 0x4550CC, count=100)
                self.assertEqual(struct.unpack("<HH", uc.mem_read(0x630070, 4)),
                                 (size // 2, size))

    def test_locked_callbacks(self):
        for address in [0x42E370, 0x42E3D0]:
            uc = emulator()
            uc.mem_write(0x708000, struct.pack("<III", 0x682000, 11, 22))
            uc.emu_start(address, 0x682000, count=100)
            self.assertEqual(uc.reg_read(UC_X86_REG_EAX), 1)
            self.assertEqual(uc.reg_read(UC_X86_REG_ESP), 0x70800C)

    def test_english_defaults_override_old_preferences(self):
        uc = emulator()
        uc.mem_write(0x482A5E, bytes.fromhex("00 00"))
        uc.mem_write(0x482A2A, b"Old Japanese Face\0".ljust(32, b"\0"))
        uc.reg_write(UC_X86_REG_ECX, 123)
        uc.emu_start(0x472D00, 0x4193B0, count=100)
        self.assertEqual(bytes(uc.mem_read(0x482A5E, 2)), b"\1\0")
        self.assertEqual(bytes(uc.mem_read(0x482A2A, 14)), b"IBM Plex Mono\0")
        self.assertEqual(uc.reg_read(UC_X86_REG_ECX), 123)
        self.assertEqual(struct.unpack("<I", uc.mem_read(0x707FFC, 4))[0], 0x472FA0)

    def test_every_native_fallback_uses_full_plex_family(self):
        uc = emulator()
        self.assertEqual(bytes(uc.mem_read(0x472FA0, 14)), b"IBM Plex Mono\0")
        for address in [0x4038BF, 0x449942, 0x45716B, 0x457E79, 0x44990F, 0x4571AA]:
            self.assertEqual(bytes(uc.mem_read(address, 5)), b"\x68" + struct.pack("<I", 0x472FA0))

    def test_font_creation_overrides_saved_face_only(self):
        from engine_layout import FONT_CREATION_CALLS, FONT_CREATION_HOOK
        from private_font import FONT_DATA
        uc = emulator()
        uc.mem_write(FONT_DATA, b'\x01')  # Already loaded on first font creation
        args = list(range(100, 114))
        uc.mem_write(0x708000, struct.pack("<15I", 0x682000, *args))
        uc.mem_write(0x473024, struct.pack("<I", 0x681000))
        uc.reg_write(UC_X86_REG_EAX, 77)
        uc.reg_write(UC_X86_REG_ECX, 88)
        uc.emu_start(FONT_CREATION_HOOK, 0x681000, count=100)
        self.assertEqual(struct.unpack("<15I", uc.mem_read(0x708000, 60)),
                         (0x682000, *args[:13], 0x472FA0))
        self.assertEqual(uc.reg_read(UC_X86_REG_EAX), 77)
        self.assertEqual(uc.reg_read(UC_X86_REG_ECX), 88)
        self.assertEqual(uc.reg_read(UC_X86_REG_ESP), 0x708000)
        for address in FONT_CREATION_CALLS:
            call = bytes(uc.mem_read(address, 6))
            self.assertEqual(call[0], 0xE8)
            self.assertEqual(address + 5 + struct.unpack("<i", call[1:5])[0], FONT_CREATION_HOOK)
            self.assertEqual(call[5], 0x90)

    def test_private_font_resolves_executable_directory_once(self):
        from private_font import FONT_LOADER, FONT_DATA, FONT_BUFFER
        for path in ['C:\\Games\\Albatross\\Albatross.exe',
                     'Z:/a folder/信天翁航海録/Albatross.exe']:
            uc = emulator()
            calls = []
            targets = [(0x47310C, 0x681100, 12), (0x4730E0, 0x681200, 4),
                       (0x4730B0, 0x681300, 8), (None, 0x681400, 12)]
            for iat, target, cleanup in targets:
                if iat and iat != 0x47310C: uc.mem_write(iat, struct.pack('<I', target))
                uc.mem_write(target, b'\xc2' + struct.pack('<H', cleanup))
            uc.mem_write(0x473024, struct.pack('<I', 0x681000))
            uc.mem_write(0x708000, struct.pack('<15I', 0x682000, *range(14)))
            uc.reg_write(UC_X86_REG_EAX, 77)
            uc.reg_write(UC_X86_REG_ECX, 88)
            def observe(u, address, size, _):
                esp = u.reg_read(UC_X86_REG_ESP)
                if address == 0x681100:
                    args = struct.unpack('<III', u.mem_read(esp + 4, 12))
                    self.assertEqual(args, (0, FONT_BUFFER, 1024))
                    u.mem_write(FONT_BUFFER, (path+'\0').encode('utf-16le'))
                    u.reg_write(UC_X86_REG_EAX, len(path))
                elif address == 0x681200:
                    u.reg_write(UC_X86_REG_EAX, 0x1234)
                elif address == 0x681300:
                    self.assertEqual(struct.unpack('<I', u.mem_read(esp + 4, 4))[0], 0x1234)
                    name_ptr = struct.unpack('<I', u.mem_read(esp + 8, 4))[0]
                    name = bytes(u.mem_read(name_ptr, 40)).split(b'\0')[0]
                    u.reg_write(UC_X86_REG_EAX, 0x681100 if name == b'GetModuleFileNameW' else 0x681400)
                elif address == 0x681400:
                    self.assertEqual(struct.unpack('<III', u.mem_read(esp + 4, 12)),
                                     (FONT_BUFFER, 0x10, 0))
                    actual = bytes(u.mem_read(FONT_BUFFER, 2048)).decode('utf-16le').split('\0')[0]
                    expected = path[:max(path.rfind('\\'), path.rfind('/')) + 1] + 'Fonts\\IBMPlexMono-Regular.ttf'
                    self.assertEqual(actual, expected)
                    calls.append(actual)
                    u.reg_write(UC_X86_REG_EAX, 1)
            uc.hook_add(UC_HOOK_CODE, observe)
            for _ in range(2):
                uc.emu_start(FONT_LOADER, 0x681000, count=10000)
                self.assertEqual(uc.reg_read(UC_X86_REG_ESP), 0x708000)
                self.assertEqual(uc.reg_read(UC_X86_REG_EAX), 77)
                self.assertEqual(uc.reg_read(UC_X86_REG_ECX), 88)
            self.assertEqual(len(calls), 1)
            self.assertEqual(bytes(uc.mem_read(FONT_DATA, 1)), b'\x01')

    def test_private_font_sections_have_separate_permissions(self):
        sections = pefile.PE(str(EXE)).sections
        self.assertEqual([s.Name.rstrip(b'\0') for s in sections[-2:]],
                         [b'.maofnt', b'.maodat'])
        self.assertFalse(sections[-2].Characteristics & 0x80000000)
        self.assertFalse(sections[-1].Characteristics & 0x20000000)


if __name__ == "__main__":
    unittest.main()
