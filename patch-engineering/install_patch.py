#!/usr/bin/env python3
"""Exact-edition, staged, reversible Albatross English patch installation."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

FILES = ('Albatross.exe', 'scr.xfl', 'grpo.xfl', 'grps.xfl')
FONT = 'IBMPlexMono-Regular.ttf'
BACKUP = 'MAO-original-backup'
PREVIOUS_OUTPUTS = {
    # v1.0.0 before the locale-sensitive story preprocessing crash fix.
    'Albatross.exe': ('92649ab3facdf7f7026de735bdd928b45a54cc55b1a4f4a2cfee2c07edd8bd54',),
    # Initial v1.0.0 UI archive; the hotfix changes only Stop Voice labels.
    'grps.xfl': ('905908febd79f621e72f95bb546b6dc680e4b1c2eb9db41ee07bca63b658325f',),
}


def digest(data): return hashlib.sha256(data).hexdigest()
def file_hash(path): return digest(path.read_bytes())


def install(package, game, uninstall=False):
    package, game = Path(package).resolve(), Path(game).resolve()
    if not game.is_dir(): raise ValueError('Select the installed Japanese game folder, not the disc image.')
    manifest = json.loads((package / 'patch.json').read_text(encoding='utf-8'))
    if manifest['schema'] != 'mao-albatross-delta/1' or tuple(f['name'] for f in manifest['files']) != FILES:
        raise ValueError('Unsupported patch manifest')
    compressed = (package / 'patch.dat.gz').read_bytes()
    if digest(compressed) != manifest['payload_sha256']: raise ValueError('Damaged patch data')
    payload = gzip.decompress(compressed)
    font = package / 'Fonts' / FONT
    if file_hash(font) != manifest['font_sha256']: raise ValueError('Damaged bundled font')
    backup = game / BACKUP
    font_target = game / 'Fonts' / FONT
    targets = {}
    for name in FILES:
        matches = [path for path in game.iterdir() if path.name.casefold() == name.casefold()]
        if len(matches) != 1: raise ValueError(f'Missing or ambiguous {name}. No files changed.')
        targets[name] = matches[0]
    for path in [backup, game/'Fonts', font_target, *targets.values()]:
        if path.is_symlink(): raise ValueError(f'Symbolic links are not supported: {path.name}')
    current = {}
    for row in manifest['files']:
        target, saved = targets[row['name']], backup / row['name']
        if not target.is_file(): raise ValueError(f"Missing {row['name']}. No files changed.")
        actual = file_hash(target)
        if actual not in (row['source_sha256'], row['output_sha256'], *PREVIOUS_OUTPUTS.get(row['name'], ())):
            raise ValueError(f"{row['name']} is not the supported Japanese retail edition or this patch. No files changed.")
        if saved.exists() and (saved.is_symlink() or file_hash(saved) != row['source_sha256']):
            raise ValueError(f"Conflicting original backup for {row['name']}. No files changed.")
        if actual != row['source_sha256'] and not saved.is_file():
            raise ValueError(f"Original backup missing for {row['name']}. No files changed.")
        current[row['name']] = actual
    if font_target.exists() and file_hash(font_target) != manifest['font_sha256']:
        raise ValueError('An unrelated font occupies the bundled-font path. No files changed.')
    pending = []
    with tempfile.TemporaryDirectory(prefix='mao-albatross-stage-', dir=game) as temp:
        stage = Path(temp)
        for row in manifest['files']:
            name = row['name']
            desired = row['source_sha256'] if uninstall else row['output_sha256']
            if current[name] == desired: continue
            source_path = targets[name] if current[name] == row['source_sha256'] else backup / name
            source = source_path.read_bytes()
            if uninstall:
                result = source
            else:
                result = bytearray()
                for kind, offset, size in row['operations']:
                    origin = source if kind == 'source' else payload if kind == 'payload' else None
                    if origin is None or offset < 0 or size < 0 or offset+size > len(origin):
                        raise ValueError('Invalid delta operation. No files changed.')
                    result.extend(origin[offset:offset+size])
                if len(result) != row['output_size']: raise ValueError('Output size check failed')
            if digest(result) != desired: raise ValueError('Output checksum check failed. No files changed.')
            (stage / name).write_bytes(result)
            shutil.copy2(targets[name], stage / ('rollback-' + name))
            pending.append(name)
        if not uninstall:
            shutil.copy2(font, stage / FONT)
        # All outputs and all existing backups have passed preflight first.
        backup.mkdir(exist_ok=True)
        for row in manifest['files']:
            saved = backup / row['name']
            if not saved.exists() and current[row['name']] == row['source_sha256']:
                shutil.copy2(targets[row['name']], saved)
        replaced = []
        font_created = False
        try:
            for name in pending:
                os.replace(stage / name, targets[name])
                replaced.append(name)
            if not uninstall and not font_target.exists():
                font_target.parent.mkdir(exist_ok=True)
                os.replace(stage / FONT, font_target)
                font_created = True
            elif uninstall and font_target.exists():
                # Keep the font recoverable beside the original game backups.
                saved_font = backup / FONT
                if saved_font.exists() and file_hash(saved_font) != manifest['font_sha256']:
                    raise ValueError('Conflicting backed-up font')
                shutil.copy2(font_target, saved_font)
                font_target.unlink()
        except Exception:
            for name in replaced:
                shutil.copy2(stage / ('rollback-' + name), targets[name])
            if font_created and font_target.exists(): font_target.unlink()
            raise
    return 'Japanese originals restored; saves untouched.' if uninstall else 'English v1.0.0 installed. Original files and saves are preserved.'


def main():
    parser = argparse.ArgumentParser(description='Albatross English v1.0.0. Close the game before installing.')
    parser.add_argument('game_folder', type=Path)
    parser.add_argument('--uninstall', action='store_true')
    args = parser.parse_args()
    print(install(Path(__file__).resolve().parent, args.game_folder, args.uninstall))


if __name__ == '__main__':
    try: main()
    except Exception as error:
        print('Installation stopped: ' + str(error), file=sys.stderr)
        sys.exit(1)
