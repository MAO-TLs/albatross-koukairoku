#!/usr/bin/env python3
"""Finish the English patch of the exact retail Albatross executable."""

from __future__ import annotations

import hashlib
import json
import argparse
from dataclasses import replace
from dataclasses import dataclass
from pathlib import Path

from engine_layout import apply_layout_hooks, FONT_FACE_ADDRESS
from private_font import apply_private_font


ROOT = Path(__file__).resolve().parents[3]
PATCH_ROOT = ROOT / "outputs" / "albatross-patch"
ORIGINAL = PATCH_ROOT / "work" / "exe" / "albatross-original.exe"
CP1251_STAGE = PATCH_ROOT / "work" / "exe" / "albatross-original.cp1251.exe"
OUTPUT = PATCH_ROOT / "build" / "game" / "Albatross.exe"
REPORT = PATCH_ROOT / "reports" / "exe-build.json"

EXPECTED_ORIGINAL_SHA256 = (
    "f04c9729c0f60269f6ffdc63ea71c587a2431c501ade698e374978050fd156c4"
)
EXPECTED_CP1251_STAGE_SHA256 = (
    "417cf4f16eb8e920540688833317e9cdf77103012325ca27e115a56259bd2bb2"
)

# Immediate operands of the twelve PUSH SHIFTJIS_CHARSET instructions feeding
# CreateFontA in this exact executable. The upstream converter changes these
# from 0x80 to 0xCC; the English patch uses ANSI_CHARSET (0x00).
CHARSET_OFFSETS = (
    0x038CD,
    0x56D4A,
    0x57E83,
    0x5C61E,
    0x5C65F,
    0x5C9AB,
    0x5C9E9,
    0x5CCFE,
    0x5CD3F,
    0x5D0F3,
    0x5D42F,
    0x5D696,
)

# The original font picker enumerates only Shift-JIS, fixed-pitch, @vertical
# fonts. Use ordinary ANSI TrueType faces, including proportional families.
FONT_PICKER_PATCHES = (
    (0x576E9, bytes.fromhex("80"), bytes.fromhex("00"), "enumerate ANSI fonts"),
    (0x57732, bytes.fromhex("0f85a6000000"), b"\x90" * 6,
     "allow variable-pitch TrueType fonts"),
    (0x57740, bytes.fromhex("0f8598000000"), bytes.fromhex("0f8498000000"),
     "exclude @vertical aliases instead of ordinary faces"),
    (0x5774D, bytes.fromhex("1d"), bytes.fromhex("1c"),
     "retain the first character of ordinary face names"),
)


@dataclass(frozen=True)
class StringPatch:
    offset: int
    slot_size: int
    source_cp932: str
    english: str
    role: str


STRING_PATCHES = (
    StringPatch(0x7E100, 8, "次へ", "Next", "next-button label"),
    StringPatch(0x7E150, 16, "ＭＳ ゴシック", "Literata", "sans font fallback"),
    StringPatch(0x7E454, 8, "確認", "Confirm", "confirmation dialog title"),
    StringPatch(
        0x7E45C,
        44,
        "タイトル画面に戻ります。\nよろしいですか？",
        "Return to the title screen?\nAre you sure?",
        "return-to-title confirmation",
    ),
    StringPatch(
        0x7E488,
        48,
        "セーブデータを上書きします。\nよろしいですか？",
        "Overwrite this save data?\nAre you sure?",
        "save overwrite confirmation",
    ),
    StringPatch(
        0x7E4B8,
        48,
        "セーブデータをロードします。\nよろしいですか？",
        "Load this save data?\nAre you sure?",
        "load confirmation",
    ),
    StringPatch(0x7E58E, 13, "信天翁航海録", "Albatross", "program/window title"),
    StringPatch(0x7E6DC, 10, "ＭＳ 明朝", "Literata", "serif font fallback"),
    StringPatch(
        0x7E79C,
        116,
        "このゲームは32Bitカラーモードで最適化されています。\n"
        "カラーモードを変更していただくとより一層お楽しみになれます。",
        "This game is optimized for 32-bit color.\n"
        "Switch to 32-bit color for the best experience.",
        "display-mode notice",
    ),
    StringPatch(0x7E810, 12, "お知らせ", "Notice", "notice dialog title"),
    StringPatch(0x7E8FC, 20, "コンパイルエラー", "Compile error", "compile error"),
    StringPatch(
        0x7E910,
        32,
        "スクリプトネストオーバーフロー",
        "Script nesting overflow",
        "script nesting overflow",
    ),
    StringPatch(
        0x7E930,
        32,
        "スクリプトネストアンダーフロー",
        "Script nesting underflow",
        "script nesting underflow",
    ),
    StringPatch(0x7E950, 20, "レイヤー指定違反", "Invalid layer", "layer error"),
    StringPatch(
        0x7E970,
        28,
        "テキストフォーマットエラー",
        "Text format error",
        "text format error",
    ),
    StringPatch(0x7E9AE, 52, "図書室での一夜、初めての",
                "A Night in the Library: The First Time", "scene gallery caption 1"),
    StringPatch(0x7E9E8, 52, "蛍舞い、振袖乱れる",
                "Fireflies Dance, Long Sleeves in Disarray", "scene gallery caption 2"),
    StringPatch(0x7EA22, 52, "忘れられた納戸で、何度も",
                "Again and Again in a Forgotten Storeroom", "scene gallery caption 3"),
    StringPatch(0x7EA5C, 52, "蔵。暗がり。朱唇がぬめる",
                "A Storehouse. Darkness. Slick Crimson Lips.", "scene gallery caption 4"),
    StringPatch(0x7EA96, 52, "お手伝いさん達だって弾けたい",
                "Even the Maids Want to Let Loose", "scene gallery caption 5"),
    StringPatch(0x7EAD0, 52, "板壁白く、乳房はたわむ",
                "White-planked Walls, Yielding Breasts", "scene gallery caption 6"),
    StringPatch(0x7EB0A, 52, "一つに溶け合う、血と精と",
                "Blood and Seed, Melting into One", "scene gallery caption 7"),
    StringPatch(0x7EB44, 52, "法師が鳴らす、初めての音色",
                "The Monk's First Melody", "scene gallery caption 8"),
    StringPatch(0x7EB7E, 52, "悦びに、薫り高まって",
                "Fragrance Deepening in Delight", "scene gallery caption 9"),
    StringPatch(0x7EBB8, 52, "可愛い娘ね。遊びましょう",
                "What a Pretty Girl. Let's Play.", "scene gallery caption 10"),
    StringPatch(0x7EBF2, 52, "指がはやまって、ついに",
                "Impatient Fingers, at Last", "scene gallery caption 11"),
    StringPatch(0x7EC2C, 52, "闇の奥底に、結ばれる二人",
                "Two United in the Depths of Darkness", "scene gallery caption 12"),
    StringPatch(0x7EFD4, 12, "ＭＳ 明朝", "Literata", "system font fallback"),
    StringPatch(0x7EFF8, 12, "終了確認", "Quit Game", "quit dialog title"),
    StringPatch(
        0x7F004,
        32,
        "本当にゲームを終了しますか？",
        "Are you sure you want to quit?",
        "quit confirmation",
    ),
)


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def patch_slot(image: bytearray, patch: StringPatch) -> dict:
    source = patch.source_cp932.encode("cp932") + b"\x00"
    actual = bytes(image[patch.offset : patch.offset + len(source)])
    if actual != source:
        raise ValueError(
            f"{patch.role} at 0x{patch.offset:x}: source bytes do not match exact retail EXE"
        )
    target = patch.english.encode("cp1252") + b"\x00"
    if len(target) > patch.slot_size:
        raise ValueError(
            f"{patch.role}: {len(target)} bytes will not fit {patch.slot_size}-byte slot"
        )
    slot_end = patch.offset + patch.slot_size
    source_tail = bytes(image[patch.offset + len(source) : slot_end])
    if any(source_tail):
        raise ValueError(f"{patch.role}: nonzero data in declared string padding")
    image[patch.offset:slot_end] = target.ljust(patch.slot_size, b"\x00")
    return {
        "role": patch.role,
        "offset": patch.offset,
        "slot_size": patch.slot_size,
        "source": patch.source_cp932,
        "english": patch.english,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--font", default="IBM Plex Mono")
    args = parser.parse_args()
    original = ORIGINAL.read_bytes()
    if sha256(original) != EXPECTED_ORIGINAL_SHA256:
        raise ValueError("original executable hash does not match the supported retail build")
    stage = CP1251_STAGE.read_bytes()
    if sha256(stage) != EXPECTED_CP1251_STAGE_SHA256:
        raise ValueError("upstream CP1251 conversion does not match the audited tool output")
    if len(original) != len(stage):
        raise ValueError("upstream converter changed executable size")

    image = bytearray(stage)
    charset_changes = []
    for offset in CHARSET_OFFSETS:
        if original[offset] != 0x80 or image[offset] != 0xCC:
            raise ValueError(f"charset site 0x{offset:x} does not match expected transition")
        image[offset] = 0x00
        charset_changes.append({"offset": offset, "from": 0xCC, "to": 0x00})

    font_picker_changes = []
    for offset, source, target, role in FONT_PICKER_PATCHES:
        if bytes(image[offset:offset + len(source)]) != source:
            raise ValueError(f"{role}: exact font-picker instructions do not match")
        if len(source) != len(target):
            raise ValueError(f"{role}: instruction patch would change image size")
        image[offset:offset + len(source)] = target
        font_picker_changes.append({"offset": offset, "role": role,
                                    "source_hex": source.hex(), "target_hex": target.hex()})
    string_changes = []
    for patch in STRING_PATCHES:
        if "font fallback" in patch.role:
            source = patch.source_cp932.encode("cp932") + b"\0"
            if bytes(image[patch.offset:patch.offset + len(source)]) != source:
                raise ValueError(f"{patch.role}: original fallback string differs")
            string_changes.append({"role": patch.role, "offset": patch.offset,
                                   "english": args.font, "source": patch.source_cp932,
                                   "relocated_family_address": FONT_FACE_ADDRESS})
            continue
        elif patch.role.startswith("scene gallery caption"):
            patch = replace(patch, source_cp932=f"「{patch.source_cp932}」",
                            english=f"“{patch.english}”")
        string_changes.append(patch_slot(image, patch))
    layout_changes = apply_layout_hooks(image, args.font)
    layout_changes.append(apply_private_font(image))
    output = bytes(image)
    if len(output) != len(original) + 8192:
        raise ValueError("unexpected size after adding private font code/data sections")
    if any(output[offset] != 0x00 for offset in CHARSET_OFFSETS):
        raise ValueError("not every CreateFontA charset operand is ANSI_CHARSET")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_bytes(output)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "schema": "albatross-exe-patch-report/1",
        "supported_original_sha256": EXPECTED_ORIGINAL_SHA256,
        "upstream_cp1251_stage_sha256": EXPECTED_CP1251_STAGE_SHA256,
        "output_sha256": sha256(output),
        "output_size": len(output),
        "font_face": args.font,
        "text_encoding": "cp1252",
        "font_charset": "ANSI_CHARSET",
        "upstream_stage": {
            "tool": "LiarsoftTool",
            "mode": "cp1251",
            "purpose": "font call discovery and Windows punctuation line-break tables",
        },
        "charset_changes": charset_changes,
        "font_picker_changes": font_picker_changes,
        "layout_changes": layout_changes,
        "string_changes": string_changes,
    }
    REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "output_sha256": report["output_sha256"],
        "output_size": report["output_size"],
        "charset_site_count": len(charset_changes),
        "translated_native_string_count": len(string_changes),
        "font_face": report["font_face"],
    }, indent=2))


if __name__ == "__main__":
    main()
