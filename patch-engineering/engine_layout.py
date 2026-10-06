"""Exact-build x86 hooks for English layout; no manuscript pre-wrapping.

The original renderer has six-byte per-glyph records: voice, hard break,
kinsoku, padding, and a two-byte delay. We use the padding byte to retain the
ANSI character, then move an overflowing line end back to a preceding space.
Glyph order, hard breaks, timing, and page control remain native.
"""

import struct

FONT_FACE_ADDRESS = 0x472FA0
FONT_CREATION_HOOK = 0x472FC0
STORY_WIDTH = 720
STORY_HEIGHT = 530
STORY_ORIGIN = 20
STORY_CAPACITY = 8192
ENGLISH_PREPROCESSOR_DBCS_CALLS = (0x41D623, 0x41D6F8)
ENGLISH_PREPROCESSOR_BUFFER = 8192
FONT_CREATION_CALLS = (0x4038EF, 0x456D5E, 0x457E96, 0x45C63D,
                       0x45C670, 0x45C9CA, 0x45C9FA, 0x45CD1D,
                       0x45CD50, 0x45D10C, 0x45D448, 0x45D6B4)


class Code:
    def __init__(self, address):
        self.address = address
        self.data = bytearray()
        self.labels = {}
        self.fixups = []

    def emit(self, value):
        self.data.extend(bytes.fromhex(value))

    def label(self, name):
        self.labels[name] = self.address + len(self.data)

    def branch(self, opcode, target):
        self.emit(opcode)
        self.fixups.append((len(self.data), target))
        self.data.extend(b"\0" * 4)

    def finish(self):
        for offset, target in self.fixups:
            dest = self.labels[target] if isinstance(target, str) else target
            self.data[offset:offset + 4] = struct.pack(
                "<i", dest - (self.address + offset + 4))
        return bytes(self.data)


def build_hooks(font_face="IBM Plex Mono"):
    startup = Code(0x472D00)
    # Force the saved direction to horizontal; preserve size and placement.
    startup.emit("66 c7 05 5e 2a 48 00 01 00")
    # Set the persisted face as well as the face supplied to the font object.
    font_bytes = font_face.encode("ascii") + b"\0"
    if len(font_bytes) > 32:
        raise ValueError("Font face exceeds the native LF_FACESIZE field")
    startup.emit("60 be")
    startup.data.extend(struct.pack("<I", FONT_FACE_ADDRESS))
    startup.emit("bf 2a 2a 48 00 b9")
    startup.data.extend(struct.pack("<I", len(font_bytes)))
    startup.emit("f3 a4 61 68")
    startup.data.extend(struct.pack("<I", FONT_FACE_ADDRESS))
    startup.branch("e9", 0x4193B0)

    capture = Code(0x472D80)
    capture.emit("50 51 52")                 # preserve EAX/ECX/EDX
    capture.emit("0f b7 47 60")             # current glyph index
    capture.emit("8d 0c 40")                # index * 3
    capture.emit("8b 97 98 01 00 00")       # six-byte metadata records
    capture.emit("89 f0 88 44 4a 03")       # retain low byte of SI
    # Extended ANSI punctuation otherwise retains a full Japanese cell while
    # its monospaced bitmap occupies the same half cell as ASCII. Correct the
    # advance only; leave the bitmap, timing and glyph order unchanged.
    capture.emit("66 81 fe 80 00")
    capture.branch("0f82", "captured")
    capture.emit("66 81 fe ff 00")
    capture.branch("0f87", "captured")
    capture.emit("0f b7 87 a2 01 00 00 d1 e8")  # half current text size
    capture.emit("8b 4f 58 0f b7 57 60 8b 0c 91 66 89 41 70")
    capture.label("captured")
    capture.emit("5a 59 58 66 83 fe 20")    # restore and displaced CMP
    capture.branch("0f84", 0x455377)        # original space classification
    capture.branch("e9", 0x4550CC)

    wrap = Code(0x472E00)
    wrap.emit("8b 96 98 01 00 00")          # displaced metadata load
    wrap.emit("50 51")
    wrap.emit("0f b7 c5")                   # scan from overflowing index BP
    wrap.label("scan")
    wrap.emit("66 3b c7")                   # never go before line start DI
    wrap.branch("0f86", "fallback")
    wrap.emit("8d 0c 40")
    wrap.emit("80 7c 4a fd 20")             # preceding glyph was a space?
    wrap.branch("0f84", "found")
    wrap.emit("48")
    wrap.branch("e9", "scan")
    wrap.label("found")
    wrap.emit("66 89 c5")                   # break after that space
    wrap.emit("89 6c 24 24")                # original [ESP+1C], two pushes
    wrap.emit("59 58")
    wrap.branch("e9", 0x455521)
    wrap.label("fallback")
    # A word longer than an entire line must retain character-wrap fallback.
    wrap.emit("59 58")
    wrap.branch("e9", 0x455506)

    # Retail registration re-sorts the complete child list with bubble sort
    # after EACH glyph allocation (cubic startup cost). The story constructor
    # creates one priority-1000 ruby child, then identical priority-0 glyphs.
    # For that exact caller only, inserting the new glyph before the final
    # ruby child is the same stable order, without repeatedly sorting it.
    insert = Code(0x472E90)
    insert.emit("81 7c 24 0c ca 3b 45 00")  # caller of registration, beyond hook return
    insert.branch("0f85", 0x43C6C0)          # every other caller uses native sort
    insert.emit("50 52 53 0f b7 41 38 8b 51 3c")
    insert.emit("66 8b 4c 42 fc 66 8b 5c 42 fe")
    insert.emit("66 89 4c 42 fe 66 89 5c 42 fc")
    # ECX must remain the parent for the registration epilogue.
    insert.emit("89 f1 5b 5a 58 c3")
    return {"horizontal_and_font_defaults": startup,
            "retain_ANSI_glyph_in_padding": capture,
            "word_boundary_wrap": wrap,
            "stable_fast_story_glyph_registration": insert}


def apply_layout_hooks(image, font_face="IBM Plex Mono"):
    changes = []

    def patch(address, source, target, role):
        # This supported retail image uses identical RVA/file offsets in text.
        offset = address - 0x400000
        if image[offset:offset + len(source)] != source:
            raise ValueError(f"{role}: exact engine bytes differ at {address:#x}")
        if len(source) != len(target):
            raise ValueError(f"{role}: patch length differs")
        image[offset:offset + len(target)] = target
        changes.append({"role": role, "address": address, "offset": offset,
                        "source_hex": source.hex(), "target_hex": target.hex()})

    def jump(address, source_hex, destination, role):
        source = bytes.fromhex(source_hex)
        target = b"\xe9" + struct.pack("<i", destination - address - 5)
        patch(address, source, target.ljust(len(source), b"\x90"), role)

    # Full family names do not fit every original Japanese fallback slot.
    # Store one intact name in the audited alignment tail and redirect all
    # six verified PUSH operands, instead of truncating or renaming the font.
    font_bytes = font_face.encode("ascii") + b"\0"
    if len(font_bytes) > 32:
        raise ValueError("Font face exceeds the native LF_FACESIZE field")
    patch(FONT_FACE_ADDRESS, b"\0" * 32, font_bytes.ljust(32, b"\0"),
          "full English font family name")
    for address, old in [(0x4038BF, 0x47E150), (0x449942, 0x47E150),
                         (0x45716B, 0x47E150), (0x457E79, 0x47E150),
                         (0x44990F, 0x47EFD4), (0x4571AA, 0x47EFD4)]:
        patch(address, b"\x68" + struct.pack("<I", old),
              b"\x68" + struct.pack("<I", FONT_FACE_ADDRESS),
              "use locked English family for native font fallback")

    # Save files can restore another face after startup. At the actual
    # CreateFontA boundary replace only argument 14 (the family pointer),
    # preserving size, weight, style, return address and stdcall cleanup.
    font_hook = (bytes.fromhex("c7 44 24 38")
                 + struct.pack("<I", FONT_FACE_ADDRESS)
                 + bytes.fromhex("ff 25 24 30 47 00"))
    patch(FONT_CREATION_HOOK, b"\0" * len(font_hook), font_hook,
          "lock font family across saved-state restoration")
    for address in FONT_CREATION_CALLS:
        target = b"\xe8" + struct.pack("<i", FONT_CREATION_HOOK - address - 5) + b"\x90"
        patch(address, bytes.fromhex("ff 15 24 30 47 00"), target,
              "create all native text fonts through locked family hook")

    for role, hook in build_hooks(font_face).items():
        code = hook.finish()
        patch(hook.address, b"\0" * len(code), code, role)
    jump(0x4193AB, "68 2a 2a 48 00", 0x472D00, "force English defaults after preferences load")
    jump(0x4550C2, "66 83 fe 20 0f 84 ab 02 00 00", 0x472D80,
         "retain glyph character without changing classification")
    jump(0x455500, "8b 96 98 01 00 00", 0x472E00,
         "wrap overflowing horizontal lines at spaces")
    patch(0x43C679, bytes.fromhex("e8 42 00 00 00"),
          b"\xe8" + struct.pack("<i", 0x472E90 - 0x43C679 - 5),
          "avoid cubic sorting while allocating the English story glyph pool")

    # The retail horizontal presets scale both box dimensions with the font:
    # 240x342 / 320x456 / 360x513. That keeps almost the same character count
    # at every size, and translated pages run behind the bottom toolbar.
    # Change only the three story presets, not the generic text-box setter
    # used by menus/gallery. Native layout now reflows each selected size in
    # a fixed area, with room for the advance symbol and bottom controls.
    for height_address, old_height, width_address, old_width in [
        (0x430376, 342, 0x43037B, 240),
        (0x4303A3, 456, 0x4303A8, 320),
        (0x4303F1, 513, 0x4303F6, 360),
    ]:
        for address, old, new, role in [
            (height_address, old_height, STORY_HEIGHT, "fixed safe English story height"),
            (width_address, old_width, STORY_WIDTH, "reflow English story at fixed width"),
        ]:
            patch(address, b"\x68" + struct.pack("<I", old),
                  b"\x68" + struct.pack("<I", new), role)
    # The old snap positions were calculated for the small Japanese box.
    # Anchor the enlarged English box at the same safe top-left origin for
    # all sizes/saved snap preferences. Preserve the native position call.
    patch(0x4307A5, bytes.fromhex("8b 74 04 2c 8b 44 04 08 56 50"),
          bytes([0x6A, STORY_ORIGIN, 0x6A, STORY_ORIGIN]) + b"\x90" * 6,
          "anchor English story area clear of the toolbar")
    # This constructor argument sizes BOTH the pointer array and six-byte
    # metadata allocation, and creates the matching number of glyph objects.
    # Increase the allocation, not merely the parser's bounds check. English
    # pages containing several appended records exceeded the retail 800 cap.
    patch(0x42FC19, bytes.fromhex("68 20 03 00 00"),
          b"\x68" + struct.pack("<I", STORY_CAPACITY),
          "allocate enough story glyphs to prevent silent English truncation")

    # Plain CP1252 bytes must be unsigned character codes. The Japanese
    # single-byte path sign-extends punctuation (e.g. 97 -> FF97), sending an
    # invalid double-byte glyph to GetGlyphOutlineA instead of the em dash.
    patch(0x454EF3, bytes.fromhex("66 0f be 08"),
          bytes.fromhex("66 0f b6 08"), "decode CP1252 glyph bytes unsigned")
    patch(0x4549DC, bytes.fromhex("66 0f be 02"),
          bytes.fromhex("66 0f b6 02"), "decode CP1252 bytes unsigned in primary parser")
    # The engine's CRT still classifies e.g. 97 + 41 as a Shift-JIS pair.
    # Every English display byte must go through the single-byte/control path;
    # otherwise an em dash consumes the following letter as one wide glyph.
    jump(0x454BCD, "74 6a 8b 44 24 18", 0x454C39,
         "never combine English display bytes as Shift-JIS pairs")
    jump(0x454426, "0f 84 82 00 00 00", 0x4544AE,
         "never combine English bytes in primary parser as Shift-JIS pairs")

    # Before text reaches either display parser, the script handler expands it
    # through two older string-copy passes. Both ask IsDBCSLeadByteEx(CP_ACP)
    # whether each byte begins a Shift-JIS pair. On a Japanese system, ordinary
    # CP1252 punctuation such as a closing curly quote (0x94) is classified as
    # a lead byte. When that quote is the final visible byte, the copier skips
    # its NUL terminator and continues into later strings, overflowing its
    # 1,024-byte stack buffer. English script text is deliberately single-byte,
    # so consume the two pushed API arguments and return false at these two
    # story preprocessing call sites. Other engine/asset string paths retain
    # their locale-aware behavior.
    for address in ENGLISH_PREPROCESSOR_DBCS_CALLS:
        patch(address, bytes.fromhex("ff 15 7c 30 47 00"),
              bytes.fromhex("83 c4 08 31 c0 90"),
              "treat English story preprocessing as single-byte")
    # Three legitimate English records are slightly larger than the retail
    # routine's 1,024-byte temporary buffer even without the locale bug. Keep
    # the formatter and its substitutions intact, but enlarge only this local
    # story-text frame to the same audited bound as the story glyph pool.
    patch(0x41D7E4, bytes.fromhex("81 ec 00 04 00 00"),
          b"\x81\xec" + struct.pack("<I", ENGLISH_PREPROCESSOR_BUFFER),
          "enlarge English story preprocessing buffer")
    patch(0x41D7F6, bytes.fromhex("8b b4 24 10 04 00 00"),
          bytes.fromhex("8b b4 24") + struct.pack("<I", ENGLISH_PREPROCESSOR_BUFFER + 16),
          "address caller argument beyond enlarged story buffer")
    patch(0x41D80E, bytes.fromhex("81 c4 00 04 00 00"),
          b"\x81\xc4" + struct.pack("<I", ENGLISH_PREPROCESSOR_BUFFER),
          "release enlarged English story preprocessing buffer")

    # These are distinct callbacks: 42E390 is SIZE, not direction.
    for address, tail, role in [
        (0x42E370, "e8 fd fd ff ff", "disable font chooser button"),
        (0x42E3D0, "e8 7d fe ff ff", "disable vertical/horizontal button"),
    ]:
        source = (bytes.fromhex("8b 4c 24 04")
                  + bytes.fromhex("e8 77 1a 01 00" if address == 0x42E370 else "e8 17 1a 01 00")
                  + bytes.fromhex("8b 4c 24 08 50 " + tail + " b8 01 00 00 00 c2 08 00"))
        patch(address, source, bytes.fromhex("b8 01 00 00 00 c2 08 00").ljust(len(source), b"\x90"), role)

    # Preferences and loaded saves can restore the old vertical value after
    # startup. Redirect every audited direction read to an immutable one in
    # the mapped alignment tail; leave the serialized preferences untouched.
    horizontal_direction = 0x472F80
    patch(horizontal_direction, b"\0" * 4, struct.pack("<I", 1), "immutable horizontal direction")
    for operand in [0x42BE47, 0x42C168, 0x42C733, 0x42C753,
                    0x42C77D, 0x42C7B7, 0x42C96D, 0x42CF7D,
                    0x42D140, 0x430282, 0x430433, 0x430767,
                    0x430D14, 0x430E04]:
        patch(operand, struct.pack("<I", 0x482A5E),
              struct.pack("<I", horizontal_direction), "read locked horizontal direction")

    # Extend .text's declared virtual size over its existing zero-filled raw
    # alignment tail. No new section, image growth, or changed import is needed.
    pe = struct.unpack_from("<I", image, 0x3C)[0]
    optional_size = struct.unpack_from("<H", image, pe + 20)[0]
    section_header = pe + 24 + optional_size
    if image[section_header:section_header + 8] != b".text\0\0\0":
        raise ValueError("first section is not the supported .text section")
    old_size, rva, raw_size, file_offset = struct.unpack_from("<IIII", image, section_header + 8)
    if (old_size, rva, raw_size, file_offset) != (465954, 4096, 466944, 4096):
        raise ValueError("supported .text section layout differs")
    struct.pack_into("<I", image, section_header + 8, raw_size)
    changes.append({"role": "map audited executable alignment tail",
                    "offset": section_header + 8, "from": old_size, "to": raw_size})
    return changes
