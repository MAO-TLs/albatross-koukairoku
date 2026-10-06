#!/usr/bin/env python3
"""Regenerate English RScript UI sprites and preserve native archive topology.

Run with the bundled Python/Pillow runtime. No original file is modified.
The existing LiarsoftTool compiler runs in a disposable Alpine container;
only its runtime libraries are installed there, not on the user's Mac.
"""
from __future__ import annotations

import hashlib
import csv
import json
import shlex
import struct
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

ROOT = Path(__file__).resolve().parents[3]
PATCH = ROOT / "outputs/albatross-patch"
SOURCE = ROOT / "outputs/albatross-translation/source/disc/program files/raiL/信天翁航海録"
DECODED = PATCH / "work/ui-source"
STAGE = PATCH / "build/ui"
FONT = PATCH / "build/fonts/IBMPlexMono-Regular.ttf"
REGULAR = FONT
TOOL = PATCH / "toolchain/LiarsoftTool-master/build-linux/liarsofttool"
sys.path.insert(0, str(ROOT / "outputs/vn-translation-pilot"))
from vnrt.adapters.liar_xfl import parse_xfl, build_xfl

CHANGES: list[dict] = []
LABEL_BOUNDS: list[dict] = []
GROUP_SIZES: dict[str, int] = {}
CHAPTER_TITLES: list[dict] = []


def toggle_label(base: str) -> str:
    """Translate the Japanese sprite label, not its inverted internal suffix."""
    enabled = base.endswith("_on")
    # Retail vocst_on is なし and vocst_off is あり. Silent mode (bgr)
    # has the same inverted internal polarity. Keep native positions/callbacks.
    if base.startswith(("bgr_", "vocst_")):
        enabled = not enabled
    return "On" if enabled else "Off"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def label(draw, xy, text, size, fill="white", bold=True, anchor="lt", stroke=0):
    font = ImageFont.truetype(str(FONT if bold else REGULAR), size)
    draw.text(xy, text, font=font, fill=fill, anchor=anchor,
              stroke_width=stroke, stroke_fill="black")


def fit_label(draw, xy, text, size, right, group=None):
    """Keep raster text clear of neighboring native hit regions."""
    while size >= 6:
        f = ImageFont.truetype(str(FONT), size)
        box = draw.textbbox((0, 0), text, font=f, anchor="lt")
        width = max(draw.textlength(text, font=f), box[2])
        if xy[0] + width <= right:
            break
        size -= 1
    if size < 6:
        raise ValueError(f"Label cannot fit native geometry: {text}")
    label(draw, xy, text, size)
    LABEL_BOUNDS.append({"text": text, "x": xy[0], "y": xy[1], "group": group,
                         "font_size": size, "width": width,
                         "right_edge": xy[0] + width, "limit": right})


def shared_size(group, texts_and_widths, maximum, scale=1):
    """A peer group uses one size, chosen by its tightest label/region."""
    for size in range(maximum, 5, -1):
        f = ImageFont.truetype(str(FONT), size * scale)
        if all(max(f.getlength(text), f.getbbox(text)[2]) <= width * scale
               for text, width in texts_and_widths):
            GROUP_SIZES[group] = size
            return size
    raise ValueError(f"Group cannot fit native geometry: {group}")


def group_labels(draw, group, members, maximum):
    size = shared_size(group, [(text, right - xy[0]) for xy, text, right in members], maximum)
    for xy, text, right in members:
        fit_label(draw, xy, text, size, right, group)


def save_sprite(archive, name, image, english):
    path = STAGE / archive / (name + ".png")
    path.parent.mkdir(parents=True, exist_ok=True)
    original = Image.open(DECODED / archive / (name + ".png"))
    if image.size != original.size:
        raise ValueError(f"Geometry changed: {path}")
    image.save(path)
    CHANGES.append({"archive": archive, "sprite": name, "english": english,
                    "width": image.width, "height": image.height})


def button(archive, name, text, active=False, disabled=False, font_size=None):
    source = Image.open(DECODED / archive / (name + ".png"))
    w, h = source.size
    # Native hit regions are unchanged; regenerate the same rectangular UI.
    scale = 3
    background = "white" if active else "black"
    foreground = "black" if active else ("#777777" if disabled else "white")
    image = Image.new("RGBA", (w * scale, h * scale), background)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, w * scale - 1, h * scale - 1),
                   outline=foreground, width=max(1, scale))
    size = font_size if font_size is not None else min(27 if h >= 40 else 18, h - 5)
    while size > 6:
        f = ImageFont.truetype(str(FONT), size * scale)
        if draw.textlength(text, font=f) <= (w - 8) * scale:
            break
        if font_size is not None:
            raise ValueError(f"Shared font size does not fit: {name} {text}")
        size -= 1
    draw.text((w * scale / 2, h * scale / 2), text, font=f,
              fill=foreground, anchor="mm")
    image = image.resize((w, h), Image.Resampling.LANCZOS)
    save_sprite(archive, name, image, text)


def generate():
    main_size = shared_size("title_navigation", [(t, 160) for t in
                            ("New Game", "Load Game", "Settings", "Extras", "Quit")], 27, scale=3)
    extras_size = shared_size("extras_navigation", [(t, 160) for t in
                              ("CG Gallery", "Scene Gallery", "Music", "Back", "Stow Away")], 27, scale=3)
    for prefix in ("00", "01"):
        for index, text in enumerate(("New Game", "Load Game", "Settings", "Extras", "Quit"), 1):
            button("grpo", prefix + f"0{index}", text, active=prefix == "01", font_size=main_size)
        for index, text in enumerate(("CG Gallery", "Scene Gallery", "Music", "Back", "Stow Away"), 1):
            button("grpo", prefix + f"1{index}", text, active=prefix == "01", font_size=extras_size)

    config = DECODED / "grps/confscrn"
    labels = {"save": "Save", "load": "Load", "close": "Return to Game",
              "title": "Title Screen", "exit": "Quit", "scm_wnd": "Windowed",
              "scm_ful": "Full Screen", "msp_slw": "Slow", "msp_nom": "Normal",
              "msp_now": "Instant", "msk_on": "Stop at unread", "msk_off": "Skip unread"}
    on_off_size = shared_size("settings_on_off", [("On", 36), ("Off", 36)], 18, scale=3)
    speed_size = shared_size("settings_text_speed", [("Slow", 86), ("Normal", 60),
                             ("Instant", 122)], 18, scale=3)
    navigation_size = shared_size("settings_navigation", [(labels[k], 142) for k in
                                 ("save", "load", "close", "title", "exit")], 18, scale=3)
    display_size = shared_size("settings_display_buttons", [(labels[k], 134) for k in
                              ("scm_wnd", "scm_ful")], 18, scale=3)
    skip_size = shared_size("settings_skip_buttons", [(labels[k], 152) for k in
                           ("msk_on", "msk_off")], 18, scale=3)
    for path in config.glob("*.png"):
        name = path.stem
        base = name[:-2] if name.endswith(("_f", "_c")) else name
        text = labels.get(base)
        if text is None and base.endswith(("_on", "_off")):
            text = toggle_label(base)
        if text:
            size = (on_off_size if base.endswith(("_on", "_off")) and not base.startswith("msk_")
                    else speed_size if base.startswith("msp_")
                    else navigation_size if base in ("save", "load", "close", "title", "exit")
                    else display_size if base.startswith("scm_") else skip_size)
            button("grps/confscrn", name, text, active=name.endswith(("_f", "_c")), font_size=size)

    bg = Image.new("RGBA", (800, 600), (0, 0, 0, 255))
    d = ImageDraw.Draw(bg)
    label(d, (38, 20), "Settings", 34)
    d.line((0, 63, 799, 63), fill="white")
    group_labels(d, "settings_display_headings", [((45, 88), "Display Mode", 410),
                 ((418, 88), "Text Speed", 788)], 20)
    group_labels(d, "settings_behavior_headings", [((45, 164), "Effects", 161),
                 ((167, 164), "Stop Voice", 280), ((286, 164), "Silent", 410),
                 ((418, 164), "Skip Mode", 788)], 20)
    group_labels(d, "settings_audio_headings", [((45, 242), "Music", 136),
                 ((45, 281), "Voice", 136), ((418, 242), "Sound FX", 508),
                 ((418, 281), "Auto Delay", 646)], 20)
    label(d, (45, 336), "Character Voices", 20)
    for y in (245, 284):
        for x in (257, 630):
            label(d, (x, y), "Min", 11)
            label(d, (x + 125, y), "Max", 11)
            d.line((x + 28, y + 8, x + 117, y + 8), fill="white")
    # Left-align each column in its available gap, after the preceding column's
    # Off button. This allows all seven names to share a readable 14px face.
    group_labels(d, "settings_character_names", [((45, 375), "Captain Kuro", 150),
                 ((260, 375), "Navigator Sisam", 395), ((505, 375), "Navigator Kisara", 640),
                 ((45, 415), "Rui Irokuzu", 150), ((260, 415), "Stowaway", 395),
                 ((505, 415), "Junior Sailor", 640), ((45, 455), "Barmaid", 150)], 17)
    save_sprite("grps/confscrn", "bg", bg, "Settings panel labels and canonical character names")

    for name in ("exit", "exit_f"):
        button("grps/savescrn", name, "Back", active=name.endswith("_f"))
    page_size = shared_size("save_page_numbers", [(str(i), 32) for i in range(1, 11)], 27, scale=3)
    for index in range(1, 11):
        for suffix in ("", "_f"):
            button("grps/savescrn", f"{index:02d}{suffix}", str(index),
                   active=suffix == "_f", font_size=page_size)
    # Keep the original little albatross icon; replace only its NEW lettering.
    original_new = Image.open(DECODED / "grps/dat_new.png").convert("RGBA")
    new = original_new.copy()
    ImageDraw.Draw(new).rectangle((34, 54, 79, 79), fill=(0, 0, 0, 0))
    label(ImageDraw.Draw(new), (34, 56), "NEW", 14)
    GROUP_SIZES["save_new_indicator"] = 14
    save_sprite("grps", "dat_new", new, "NEW")
    # The decorative save/load background remains intact below its header;
    # a code-generated header panel replaces only the old Japanese heading.
    for name, text in (("bg_load", "Load Game"), ("bg_save", "Save Game")):
        bg = Image.open(DECODED / "grps/savescrn" / (name + ".png")).convert("RGBA")
        d = ImageDraw.Draw(bg)
        d.rectangle((0, 0, 799, 68), fill=(14, 26, 45, 255))
        d.line((0, 69, 799, 69), fill="white")
        label(d, (18, 15), text, 34)
        save_sprite("grps/savescrn", name, bg, text)

    for name in ("font_0", "font_0_f", "dir_0", "dir_0_f", "dir_1", "dir_1_f"):
        text = "F" if name.startswith("font") else "H"
        button("grps/excompane", name, text, disabled=True)
    for index, text in enumerate(("L", "M", "S")):
        for suffix in ("", "_f", "_c", "_l"):
            name = f"size_{index}{suffix}"
            button("grps/excompane", name, text, active=suffix in ("", "_l"))
    generate_chapter_titles()


def generate_chapter_titles():
    rows = list(csv.DictReader((PATCH / "tools/chapter_titles.tsv").open(), delimiter="\t"))
    expected = {p.stem.removeprefix("dt2_") for p in (DECODED / "grps").glob("dt2_*.png")}
    actual = {r["script_id"] for r in rows}
    if len(rows) != 84 or len(actual) != 84 or actual != expected:
        raise ValueError("Chapter title manifest does not cover exactly the 84 native sprites")
    # Regenerate the decorative ship from the clean save background silhouette,
    # not from title sprites with Japanese glyphs baked into their pixels.
    # This changes UI labels only; story backgrounds/CG archives are untouched.
    bg = Image.open(DECODED / "grps/savescrn/bg_save.png").convert("RGB")
    crop = bg.crop((34, 84, 384, 164))
    channels = [c.point(lambda v: 255 if v == 0 else 0) for c in crop.split()]
    mask = ImageChops.multiply(ImageChops.multiply(channels[0], channels[1]), channels[2])
    outline = mask.filter(ImageFilter.MaxFilter(5))
    ship = Image.new("RGBA", (350, 80), (255, 255, 255, 0))
    ship.putalpha(outline)
    ship.paste((0, 0, 0, 255), (0, 0, 350, 80), mask)
    scale = 3
    font_size = 14
    GROUP_SIZES["save_chapter_titles"] = font_size
    f = ImageFont.truetype(str(FONT), font_size * scale)
    for row in rows:
        title = row["english"]
        lines = []
        current = ""
        for word in title.split():
            candidate = (current + " " + word).strip()
            if f.getlength(candidate) > 320 * scale and current:
                lines.append(current)
                current = word
            else:
                current = candidate
        lines.append(current)
        if len(lines) > 2 or any(f.getlength(line) > 320 * scale for line in lines):
            raise ValueError(f"Chapter title does not fit native region: {row}")
        image = ship.resize((350 * scale, 80 * scale), Image.Resampling.NEAREST)
        draw = ImageDraw.Draw(image)
        for index, line in enumerate(lines):
            draw.text((16 * scale, (12 + index * 18) * scale), line, font=f,
                      anchor="lt", fill="white", stroke_width=scale, stroke_fill="black")
        image = image.resize((350, 80), Image.Resampling.LANCZOS)
        name = "dt2_" + row["script_id"]
        save_sprite("grps", name, image, title)
        CHAPTER_TITLES.append({**row, "sprite": name + ".wcg",
                              "source_sprite_sha256": digest((DECODED / "grps" / (name + ".wcg")).read_bytes()),
                              "font_size": font_size, "rendered_lines": lines})


def lwg_replace(source: bytes, replacements: dict[bytes, bytes]) -> bytes:
    """Change payloads only; preserve raw layer names, geometry, flags/order.

    This avoids roundtripping legacy extraction's mojibake metadata names.
    """
    if source[:4] != b"LG\x01\x00":
        raise ValueError("Not an LWG")
    count = struct.unpack_from("<I", source, 12)[0]
    table_size = struct.unpack_from("<I", source, 20)[0]
    data_start = 28 + table_size
    header = bytearray(source[:data_start])
    data = bytearray()
    pos = 24
    seen = set()
    for _ in range(count):
        offset, size = struct.unpack_from("<II", source, pos + 9)
        name_len = source[pos + 17]
        name = source[pos + 18:pos + 18 + name_len]
        original = source[data_start + offset:data_start + offset + size]
        payload = replacements.get(name, original)
        if name in replacements:
            if original[:2] != b"WG" or payload[:2] != b"WG":
                raise ValueError(f"Non-WCG replacement {name!r}")
            if original[8:16] != payload[8:16]:
                raise ValueError(f"Changed WCG geometry {name!r}")
            seen.add(name)
        struct.pack_into("<II", header, pos + 9, len(data), len(payload))
        data.extend(payload)
        pos += 18 + name_len
    if seen != set(replacements):
        raise ValueError(f"Unknown LWG names: {set(replacements)-seen}")
    if pos != 24 + table_size:
        raise ValueError("Unexpected LWG table layout")
    return bytes(header + data)


def compile_assets():
    pngs = sorted((STAGE / "grpo").glob("*.png"))
    pngs += sorted((STAGE / "grps").glob("*.png"))
    pngs += sorted((STAGE / "grps").glob("*/*.png"))
    relative = [str(p.relative_to(ROOT)) for p in pngs]
    tool = str(TOOL.relative_to(ROOT))
    command = "apk add --no-cache libstdc++ >/dev/null && " + tool
    # Paths and labels are fixed internal filenames, not untrusted shell input.
    command += " " + " ".join(relative)
    # Decode built sprites through the upstream codec for pixel-level QA.
    qa = STAGE / "roundtrip"
    qa.mkdir(exist_ok=True)
    for png in pngs:
        output = qa / png.relative_to(STAGE)
        output.parent.mkdir(parents=True, exist_ok=True)
        command += " && " + tool + " " + shlex.quote(str(png.with_suffix(".wcg").relative_to(ROOT)))
        command += " " + shlex.quote(str(output.relative_to(ROOT)))
    with (PATCH / "reports/ui-compiler.log").open("w") as log:
        subprocess.run(["docker", "run", "--rm", "-v", f"{ROOT}:/work", "-w", "/work",
                        "alpine:3.22", "sh", "-c", command], check=True,
                       stdout=log, stderr=subprocess.STDOUT)
    for png in pngs:
        rebuilt = Image.open(qa / png.relative_to(STAGE)).convert("RGBA")
        expected = Image.open(png).convert("RGBA")
        if rebuilt.size != expected.size or rebuilt.tobytes() != expected.tobytes():
            raise ValueError(f"WCG pixel roundtrip differs: {png}")


def build():
    archive_reports = []
    for archive_name in ("grpo", "grps"):
        source = (SOURCE / (archive_name + ".xfl")).read_bytes()
        archive = parse_xfl(source)
        if build_xfl(archive) != source:
            raise ValueError("No-op XFL not identical")
        replacements = {}
        if archive_name == "grpo":
            replacements = {p.name: p.read_bytes() for p in (STAGE / "grpo").glob("*.wcg")}
        else:
            original = {e.name: e.payload for e in archive.entries}
            for path in (STAGE / "grps").glob("*.wcg"):
                rebuilt = path.read_bytes()
                if original[path.name][:2] != b"WG" or rebuilt[:2] != b"WG":
                    raise ValueError(f"Non-WCG sprite replacement: {path.name}")
                if original[path.name][8:16] != rebuilt[8:16]:
                    raise ValueError(f"Changed native sprite geometry: {path.name}")
                replacements[path.name] = rebuilt
            for group in ("confscrn", "savescrn", "excompane"):
                layers = {p.stem.encode("ascii"): p.read_bytes()
                          for p in (STAGE / "grps" / group).glob("*.wcg")}
                rebuilt = lwg_replace(original[group + ".lwg"], layers)
                # A no-op payload rebuild must retain all original bytes exactly.
                if lwg_replace(original[group + ".lwg"], {}) != original[group + ".lwg"]:
                    raise ValueError(f"LWG no-op differs: {group}")
                replacements[group + ".lwg"] = rebuilt
        result = build_xfl(archive, replacements)
        verified = parse_xfl(result)
        assert [e.name_field for e in archive.entries] == [e.name_field for e in verified.entries]
        assert all(a.payload == b.payload for a, b in zip(archive.entries, verified.entries)
                   if a.name not in replacements)
        out = PATCH / "build/game" / (archive_name + ".xfl")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(result)
        archive_reports.append({"archive": archive_name, "original_sha256": digest(source),
                                "built_sha256": digest(result), "entries": len(archive.entries),
                                "replaced_entries": sorted(replacements)})
    report = {"sprites": CHANGES, "sprite_count": len(CHANGES), "archives": archive_reports,
              "font": {"family": "IBM Plex Mono", "style": "Regular",
                       "path": str(FONT.relative_to(ROOT)), "sha256": digest(FONT.read_bytes())},
              "settings_label_bounds": LABEL_BOUNDS,
              "shared_group_font_sizes": GROUP_SIZES,
              "chapter_titles": CHAPTER_TITLES,
              "chapter_title_coverage": {"translated": len(CHAPTER_TITLES), "expected": 84},
              "structural_validation": f"passed; unchanged entry bytes, raw layer metadata and image dimensions preserved; all {len(CHANGES)} sprites pixel-identical after WCG roundtrip",
              "runtime_validation": "pending", "untranslated_remaining": [
                  "Native executable tooltip/program strings outside this asset build",
                  "Extras scene/CG gallery dynamic captions, if present"]}
    (PATCH / "reports/ui-build.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"sprites": len(CHANGES), "archives": archive_reports}, indent=2))


if __name__ == "__main__":
    generate()
    compile_assets()
    build()
