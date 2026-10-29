"""Probe every page of enlarged x86 text frames before moving ESP.

Jump trampolines preserve all registers and the original SUB's flags. No new
imports, saved stack words, or Windows-version-specific APIs are required.
"""
import struct
from engine_layout import Code, ENGLISH_PREPROCESSOR_BUFFER

STACK_PROBES = {site: 0x4CD200 + index * 32 for index, site in enumerate(
    (0x41D7E4, 0x42C2E0, 0x42C480, 0x42D790))}
ALLOCATION = b'\x81\xec' + struct.pack('<I', ENGLISH_PREPROCESSOR_BUFFER)


def entry_jump(site):
    return b'\xe9' + struct.pack('<i', STACK_PROBES[site] - site - 5) + b'\x90'


def build_probe(site):
    code = Code(STACK_PROBES[site])
    # Read each intervening page in order. TEST does not change its contents
    # or any register; the displaced SUB below supplies the final flags.
    for distance in range(4096, ENGLISH_PREPROCESSOR_BUFFER + 1, 4096):
        code.emit('f6 84 24')
        code.data.extend(struct.pack('<i', -distance))
        code.emit('00')
    code.data.extend(ALLOCATION)
    code.branch('e9', site + len(ALLOCATION))
    return code.finish()


def apply_stack_probes(image):
    pe = struct.unpack_from('<I', image, 0x3C)[0]
    headers = pe + 24 + struct.unpack_from('<H', image, pe + 20)[0]
    count = struct.unpack_from('<H', image, pe + 6)[0]
    matches = [headers + i * 40 for i in range(count)
               if image[headers+i*40:headers+i*40+8].rstrip(b'\0') == b'.maofnt']
    if len(matches) != 1:
        raise ValueError('Expected one private RX code section')
    header = matches[0]
    size, rva, raw_size, raw = struct.unpack_from('<IIII', image, header + 8)
    if rva != 0xCD000 or size > 0x200 or raw_size != 4096:
        raise ValueError('Stack-probe code space is not the expected unused tail')
    if struct.unpack_from('<I', image, header + 36)[0] != 0x60000020:
        raise ValueError('Stack-probe section must remain read/execute only')
    for site, target in STACK_PROBES.items():
        at = site - 0x400000
        if image[at:at+6] != ALLOCATION:
            raise ValueError(f'Unexpected allocation at {site:#x}')
        code = build_probe(site)
        offset = target - (0x400000 + rva)
        if len(code) > 32 or offset + len(code) > raw_size:
            raise ValueError('Stack-probe slot overflow')
        if any(image[raw+offset:raw+offset+len(code)]):
            raise ValueError('Stack-probe slot is occupied')
        image[raw+offset:raw+offset+len(code)] = code
        image[at:at+6] = entry_jump(site)
        size = max(size, offset + len(code))
    struct.pack_into('<I', image, header + 8, size)
    return {'role': 'probe each page before enlarged text stack allocations',
            'sites': STACK_PROBES, 'buffer_bytes': ENGLISH_PREPROCESSOR_BUFFER}
