#!/usr/bin/env python3
"""Build a patch-only delta package: untouched artwork stays in the retail copy."""
import difflib
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import sys
import zipfile
from build_script_patch import ROOT, PATCH_ROOT, GAME_ROOT, parse_xfl
from install_patch import FILES, FONT, install, file_hash

VERSION = '1.0.1'
RELEASE = PATCH_ROOT / 'release' / ('v' + VERSION)
PACKAGE = RELEASE / ('Albatross-Koukairoku-English-v' + VERSION)


def main():
    PACKAGE.mkdir(parents=True, exist_ok=True)
    payload = bytearray()
    manifest = {'schema':'mao-albatross-delta/1','version':VERSION,
                'edition':'2010-07-23 Japanese DVD retail, exact file hashes',
                'files':[]}
    for name in FILES:
        source_path = PATCH_ROOT / 'work/exe/albatross-original.exe' if name == 'Albatross.exe' else GAME_ROOT / name
        source = source_path.read_bytes()
        target = (PATCH_ROOT / 'build/game' / name).read_bytes()
        operations = []
        def literal(content):
            if content:
                operations.append(['payload',len(payload),len(content)])
                payload.extend(content)
        if name.endswith('.xfl'):
            src, dst = parse_xfl(source), parse_xfl(target)
            src_base = 12 + 40 * len(src.entries)
            dst_base = 12 + 40 * len(dst.entries)
            originals = {e.name:e for e in src.entries}
            literal(target[:dst_base])
            for entry in dst.entries:
                old = originals.get(entry.name)
                if old is not None and old.payload == entry.payload:
                    operations.append(['source',src_base+old.relative_offset,len(old.payload)])
                elif name == 'scr.xfl' and old is not None:
                    # The script header/control block is copied from retail.
                    # Changed English string tables are the only literal data.
                    common = 0
                    while common < min(len(old.payload),len(entry.payload)) and old.payload[common] == entry.payload[common]:
                        common += 1
                    if common:
                        operations.append(['source',src_base+old.relative_offset,common])
                    literal(entry.payload[common:])
                else:
                    literal(entry.payload)
        else:
            # Executable runs at unchanged offsets; keep every exact byte run
            # of at least 16 bytes in the user's original rather than shipping it.
            start, at = 0, 0
            while at < min(len(source),len(target)):
                if source[at:at+16] == target[at:at+16] and at+16 <= len(source):
                    literal(target[start:at])
                    end = at+16
                    while end < min(len(source),len(target)) and source[end] == target[end]: end += 1
                    operations.append(['source',at,end-at])
                    at, start = end, end
                else:
                    at += 1
            literal(target[start:])
        manifest['files'].append({'name':name,'source_sha256':hashlib.sha256(source).hexdigest(),
                                  'output_sha256':hashlib.sha256(target).hexdigest(),
                                  'output_size':len(target),'operations':operations})
    compressed = gzip.compress(bytes(payload), compresslevel=9, mtime=0)
    (PACKAGE / 'patch.dat.gz').write_bytes(compressed)
    manifest['payload_sha256'] = hashlib.sha256(compressed).hexdigest()
    (PACKAGE / 'Fonts').mkdir(exist_ok=True)
    for name in [FONT,'IBMPlexMono-OFL.txt']:
        shutil.copy2(PATCH_ROOT / 'build/fonts' / name, PACKAGE / 'Fonts' / name)
    manifest['font_sha256'] = file_hash(PACKAGE / 'Fonts' / FONT)
    (PACKAGE / 'patch.json').write_text(json.dumps(manifest,indent=2)+'\n')
    shutil.copy2(Path(__file__).with_name('install_patch.py'), PACKAGE / 'install_patch.py')
    shutil.copy2(Path(__file__).with_name('RELEASE_README.txt'), PACKAGE / 'README.txt')
    shutil.copy2(Path(__file__).with_name('Install English Patch.cmd'), PACKAGE / 'Install English Patch.cmd')
    archive = RELEASE / (PACKAGE.name + '.zip')
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as stream:
        for path in sorted(PACKAGE.rglob('*')):
            if path.is_file(): stream.write(path,path.relative_to(RELEASE))
    report = {'version':VERSION,'zip':str(archive),'size':archive.stat().st_size,
              'sha256':file_hash(archive),'literal_bytes':len(payload),
              'files':[{k:v for k,v in row.items() if k!='operations'} for row in manifest['files']]}
    (PATCH_ROOT/'reports/release-package.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__ == '__main__': main()
