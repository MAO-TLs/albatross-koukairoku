#!/usr/bin/env python3
"""Build the English scr.xfl without changing RScript control bytecode."""

from __future__ import annotations

import hashlib
import json
import re
import struct
import sys
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PATCH_ROOT = ROOT / "outputs" / "albatross-patch"
SOURCE_ROOT = ROOT / "outputs" / "albatross-translation" / "source"
GAME_ROOT = (
    SOURCE_ROOT
    / "disc"
    / "program files"
    / "raiL"
    / "信天翁航海録"
)
SOURCE_ARCHIVE = GAME_ROOT / "scr.xfl"
CORPUS = SOURCE_ROOT / "extracted" / "corpus.jsonl"
READER_ROOT = (
    ROOT / "outputs" / "albatross-koukairoku-release" / "public" / "script-data"
)
OUTPUT_ARCHIVE = PATCH_ROOT / "build" / "game" / "scr.xfl"
REPORT = PATCH_ROOT / "reports" / "script-build.json"

sys.path.insert(0, str(ROOT / "outputs" / "vn-translation-pilot"))
from vnrt.adapters.liar_xfl import (  # noqa: E402
    assert_gsc_control_preserved,
    build_gsc,
    build_xfl,
    parse_gsc,
    parse_xfl,
    require_albatross_control_dialect,
)


SPEAKER_PREFIX = re.compile(r"^【[^】]+】\n?")
CHOICE_LAYOUT_PREFIX = re.compile(r"^<[0-9]{2}>")
BOX_DASH_RUN = re.compile(r"─+")
ELLIPSIS_STOP_LINE = re.compile(r"(?m)^(…+)。$")
RUBY_MARKUP = re.compile(
    r"\[R[^\]\n]*\^[^\]\n]*\]|\^[rR]|\((?:ruby|Ruby)\s*:"
)


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def source_body(text: str) -> str:
    stripped = text.strip(" \t\u3000\n")
    stripped = SPEAKER_PREFIX.sub("", stripped, count=1)
    return stripped.strip(" \t\u3000\n")


def runtime_normalize(ref: str, text: str, changes: list[dict]) -> str:
    """Apply only documented substitutions required by the ANSI renderer."""

    original = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = BOX_DASH_RUN.sub("—", original)
    normalized = normalized.replace("ō", "o").replace("Ō", "O")
    normalized = ELLIPSIS_STOP_LINE.sub(r"\1", normalized)

    # One passage discusses the written shape of the final kanji in Naomasa's
    # signature. The engine's CP1252 path cannot render that glyph, so retain
    # the meaning in prose instead of substituting a missing-glyph box.
    normalized = normalized.replace(
        "the last strokes of 正 wandered like the trail",
        "the last strokes of the final character wandered like the trail",
    )
    normalized = normalized.replace("。", ".")
    # ASCII brackets invoke the native ruby parser, rather than rendering as
    # literal brackets. Retain the two English bracketed asides as parentheses.
    normalized = normalized.replace("[", "(").replace("]", ")")

    if normalized != original:
        changes.append({"ref": ref, "before": original, "after": normalized})
    if "\x00" in normalized:
        raise ValueError(f"{ref}: NUL in English text")
    if "^n" in normalized or re.search(r"\^d\d", normalized):
        raise ValueError(f"{ref}: manuscript contains reserved RScript controls")
    if RUBY_MARKUP.search(normalized):
        raise ValueError(f"{ref}: ruby annotation leaked into English")
    try:
        normalized.encode("cp1252", errors="strict")
    except UnicodeEncodeError as error:
        problem = normalized[error.start : error.end]
        raise ValueError(f"{ref}: CP1252 cannot encode {problem!r}") from error
    return normalized


def attach_native_controls(source: dict, english: str) -> str:
    """Retain the two authored display-mode transitions without JP padding."""

    controls = [item for item in source["controls"] if item.startswith("^d")]
    if not controls:
        return english
    if source["ref"] == "albatross:1001:000001" and controls == ["^d0", "^d1"]:
        return f"^d0{english}^d1"
    if source["ref"] == "albatross:5011:000032" and controls == ["^d2", "^d4"]:
        marker = "The End"
        if marker not in english:
            raise ValueError(f"{source['ref']}: closing display marker is missing")
        before, after = english.rsplit(marker, 1)
        return f"^d2{before}^d4{marker}{after}"
    raise ValueError(f"{source['ref']}: unrecognized display-control arrangement")


def runtime_text(source: dict, reader: dict, changes: list[dict]) -> str:
    english = runtime_normalize(source["ref"], reader["english"], changes)
    speaker = runtime_normalize(
        source["ref"] + ":speaker", reader.get("speakerEn", ""), changes
    )
    if bool(source.get("source_speaker")) != bool(speaker):
        raise ValueError(
            f"{source['ref']}: source/English speaker presence differs "
            f"({source.get('source_speaker')!r} vs {speaker!r})"
        )
    body = english.replace("\n", "^n")
    if speaker:
        # [Speaker] would be interpreted as ruby for the preceding glyph.
        body = f"{speaker}:^n{body}"
    body = attach_native_controls(source, body)
    if any(item.get("kind") == "choice" for item in source.get("usages", [])):
        # <NN> chooses sel_aNN/sel_qNN artwork; it is not visible prose.
        # Without it the native menu defaults to 00, which this game lacks.
        prefix = CHOICE_LAYOUT_PREFIX.match(source["japanese_raw"])
        if not prefix or body.startswith("<") or speaker:
            raise ValueError(f"{source['ref']}: unrecognized choice layout/caption")
        body = prefix.group() + body
    return body


def main() -> None:
    source_rows = read_jsonl(CORPUS)
    by_script: dict[str, list[dict]] = defaultdict(list)
    for row in source_rows:
        by_script[row["script_id"]].append(row)

    reader_by_script: dict[str, list[dict]] = {}
    for path in sorted(READER_ROOT.glob("[0-9][0-9][0-9][0-9].json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        script_id = str(data["scriptId"])
        if script_id in reader_by_script:
            raise ValueError(f"duplicate reader script: {script_id}")
        reader_by_script[script_id] = data["lines"]

    if set(reader_by_script) != set(by_script):
        missing = sorted(set(by_script) - set(reader_by_script))
        extra = sorted(set(reader_by_script) - set(by_script))
        raise ValueError(f"reader/source script sets differ; missing={missing}, extra={extra}")

    archive_bytes = SOURCE_ARCHIVE.read_bytes()
    archive = parse_xfl(archive_bytes, encoding="cp932")
    entries = {entry.name: entry for entry in archive.entries}
    replacements: dict[str, bytes] = {}
    normalization_changes: list[dict] = []
    mismatch_count = 0
    passage_count = 0
    ruby_source_rows = 0
    scripts_report: list[dict] = []

    for script_id in sorted(by_script):
        source_script_rows = by_script[script_id]
        reader_rows = reader_by_script[script_id]
        if len(source_script_rows) != len(reader_rows):
            raise ValueError(
                f"{script_id}: source has {len(source_script_rows)} rows, "
                f"reader has {len(reader_rows)}"
            )
        entry_name = source_script_rows[0]["archive_entry"]
        entry = entries[entry_name]
        script = parse_gsc(entry.payload, script_id=script_id, encoding="cp932")
        # The shared adapter's original pilot guard predates the twelve
        # Albatross scripts using the game's third observed table layout.
        # Accept that exact layout here; every control byte is still copied and
        # compared verbatim after the text-table rebuild.
        header_words = struct.unpack("<IIII", script.header)
        if header_words == (4, 1, 8, 8):
            if not script.code:
                raise ValueError(f"{script_id}: empty RScript bytecode")
        else:
            require_albatross_control_dialect(script)
        string_replacements: dict[str, str] = {}

        for source, reader in zip(source_script_rows, reader_rows, strict=True):
            if source_body(source["japanese_plain"]) != source_body(reader["japanese"]):
                mismatch_count += 1
                raise ValueError(
                    f"{source['ref']}: public manuscript no longer matches source Japanese"
                )
            if source["ruby"]:
                ruby_source_rows += 1
            string_ref = f"gsc:{script_id}:{source['string_index']:06d}"
            string_replacements[string_ref] = runtime_text(
                source, reader, normalization_changes
            )
            passage_count += 1

        rebuilt_bytes = build_gsc(
            script, string_replacements, encoding="cp1252"
        )
        rebuilt = parse_gsc(rebuilt_bytes, script_id=script_id, encoding="cp1252")
        assert_gsc_control_preserved(script, rebuilt)
        replacements[entry_name] = rebuilt_bytes
        scripts_report.append(
            {
                "script_id": script_id,
                "archive_entry": entry_name,
                "passages": len(source_script_rows),
                "source_sha256": entry.sha256,
                "patched_sha256": sha256(rebuilt_bytes),
                "control_sha256": script.control_sha256,
                "bytecode_preserved": script.code == rebuilt.code,
                "string_count_preserved": len(script.strings) == len(rebuilt.strings),
            }
        )

    output = build_xfl(archive, replacements)
    reparsed_archive = parse_xfl(output, encoding="cp932")
    reparsed_entries = {entry.name: entry for entry in reparsed_archive.entries}
    unchanged_entries = 0
    for entry in archive.entries:
        if entry.name not in replacements:
            if reparsed_entries[entry.name].payload != entry.payload:
                raise ValueError(f"{entry.name}: supposedly untouched payload changed")
            unchanged_entries += 1

    OUTPUT_ARCHIVE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_ARCHIVE.write_bytes(output)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "schema": "albatross-script-patch-report/1",
        "source_archive": str(SOURCE_ARCHIVE.relative_to(ROOT)),
        "output_archive": str(OUTPUT_ARCHIVE.relative_to(ROOT)),
        "source_sha256": sha256(archive_bytes),
        "output_sha256": sha256(output),
        "archive_entry_count": len(archive.entries),
        "patched_script_count": len(replacements),
        "untouched_entry_count": unchanged_entries,
        "passage_count": passage_count,
        "source_reader_mismatch_count": mismatch_count,
        "source_rows_with_ruby": ruby_source_rows,
        "english_ruby_markup_count": 0,
        "choice_layout_tags_preserved": sum(
            any(item.get("kind") == "choice" for item in row.get("usages", []))
            for row in source_rows
        ),
        "target_encoding": "cp1252",
        "runtime_normalization_count": len(normalization_changes),
        "runtime_normalizations": normalization_changes,
        "scripts": scripts_report,
    }
    REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({key: report[key] for key in (
        "output_sha256",
        "patched_script_count",
        "passage_count",
        "source_reader_mismatch_count",
        "source_rows_with_ruby",
        "english_ruby_markup_count",
        "runtime_normalization_count",
    )}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
