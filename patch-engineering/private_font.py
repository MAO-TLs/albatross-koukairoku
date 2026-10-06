"""Load the bundled font privately, before the first native CreateFontA.

The font path is relative to the executable, not the process working directory.
Code and mutable data have separate RX/RW sections; no global font registration.
"""
import struct
from engine_layout import Code, FONT_CREATION_HOOK, FONT_FACE_ADDRESS

FONT_LOADER = 0x4CD000
FONT_DATA = 0x4CE000
FONT_BUFFER = FONT_DATA + 0x100
FONT_SUFFIX = FONT_DATA + 0x10
GDI_NAME = FONT_DATA + 0x50
ADD_FONT_NAME = FONT_DATA + 0x60
KERNEL_NAME = FONT_DATA + 0x80
MODULE_FILE_NAME = FONT_DATA + 0xA0


def build_font_loader():
    code = Code(FONT_LOADER)
    def imm(value): code.data.extend(struct.pack('<I', value))
    code.emit('60 80 3d'); imm(FONT_DATA); code.emit('01')
    code.branch('0f84', 'ready')
    code.emit('c6 05'); imm(FONT_DATA); code.emit('01')
    code.emit('68'); imm(KERNEL_NAME)
    code.emit('ff 15 e0 30 47 00')
    code.emit('85 c0'); code.branch('0f84', 'ready')
    code.emit('68'); imm(MODULE_FILE_NAME)
    code.emit('50 ff 15 b0 30 47 00')
    code.emit('85 c0'); code.branch('0f84', 'ready')
    code.emit('68'); imm(1024)
    code.emit('68'); imm(FONT_BUFFER)
    code.emit('6a 00 ff d0')  # GetModuleFileNameW, including Japanese folder names
    code.emit('85 c0'); code.branch('0f84', 'ready')
    code.emit('3d'); imm(960); code.branch('0f83', 'ready')
    code.emit('bf'); imm(FONT_BUFFER); code.emit('8d 3c 47')
    code.label('scan')
    code.emit('81 ff'); imm(FONT_BUFFER)
    code.branch('0f86', 'ready')
    code.emit('83 ef 02 66 83 3f 5c'); code.branch('0f84', 'path')
    code.emit('66 83 3f 2f'); code.branch('0f85', 'scan')
    code.label('path')
    code.emit('83 c7 02 be'); imm(FONT_SUFFIX)
    code.emit('b9'); imm(len('Fonts\\IBMPlexMono-Regular.ttf\0'.encode('utf-16le')))
    code.emit('fc f3 a4 68'); imm(GDI_NAME)
    code.emit('ff 15 e0 30 47 00')  # GetModuleHandleA
    code.emit('85 c0'); code.branch('0f84', 'ready')
    code.emit('68'); imm(ADD_FONT_NAME)
    code.emit('50 ff 15 b0 30 47 00')  # GetProcAddress
    code.emit('85 c0'); code.branch('0f84', 'ready')
    code.emit('6a 00 6a 10 68'); imm(FONT_BUFFER)
    code.emit('ff d0')  # AddFontResourceExW(path, FR_PRIVATE, NULL)
    code.label('ready')
    code.emit('61 c7 44 24 38'); imm(FONT_FACE_ADDRESS)
    code.emit('ff 25 24 30 47 00')  # Native CreateFontA, stdcall untouched
    return code.finish()


def apply_private_font(image):
    pe = struct.unpack_from('<I', image, 0x3c)[0]
    count = struct.unpack_from('<H', image, pe + 6)[0]
    optional = pe + 24
    headers = optional + struct.unpack_from('<H', image, pe + 20)[0]
    if count != 4 or len(image) != 552960:
        raise ValueError('Private font loader requires the supported four-section image')
    if struct.unpack_from('<III', image, optional + 32)[:2] != (4096, 4096):
        raise ValueError('Unexpected PE section/file alignment')
    if struct.unpack_from('<I', image, optional + 56)[0] != 0xcd000:
        raise ValueError('Unexpected original image size')
    new_headers = headers + count * 40
    if any(image[new_headers:new_headers + 80]):
        raise ValueError('New PE section headers would overwrite existing data')
    old = bytes.fromhex('c7 44 24 38') + struct.pack('<I', FONT_FACE_ADDRESS) + bytes.fromhex('ff 25 24 30 47 00')
    offset = FONT_CREATION_HOOK - 0x400000
    if image[offset:offset + len(old)] != old:
        raise ValueError('Expected locked CreateFontA wrapper is absent')
    image[offset:offset + len(old)] = (b'\xe9' + struct.pack('<i', FONT_LOADER - FONT_CREATION_HOOK - 5)).ljust(len(old), b'\x90')
    code = build_font_loader()
    data = bytearray(4096)
    for address, value in [(FONT_SUFFIX, 'Fonts\\IBMPlexMono-Regular.ttf\0'.encode('utf-16le')),
                           (GDI_NAME, b'gdi32.dll\0'),
                           (ADD_FONT_NAME, b'AddFontResourceExW\0'),
                           (KERNEL_NAME, b'kernel32.dll\0'),
                           (MODULE_FILE_NAME, b'GetModuleFileNameW\0')]:
        at = address - FONT_DATA
        data[at:at + len(value)] = value
    raw = len(image)
    for index, (name, rva, content, flags) in enumerate([
        (b'.maofnt', 0xcd000, code, 0x60000020),
        (b'.maodat', 0xce000, data, 0xc0000040),
    ]):
        header = struct.pack('<8sIIIIIIHHI', name, len(content), rva,
                             4096, raw + index * 4096, 0, 0, 0, 0, flags)
        image[new_headers + index * 40:new_headers + (index + 1) * 40] = header
        image.extend(bytes(content).ljust(4096, b'\0'))
    struct.pack_into('<H', image, pe + 6, 6)
    struct.pack_into('<I', image, optional + 56, 0xcf000)
    for at in [optional + 4, optional + 8]:
        struct.pack_into('<I', image, at, struct.unpack_from('<I', image, at)[0] + 4096)
    struct.pack_into('<I', image, optional + 64, 0)  # No stale PE checksum
    return {'role': 'privately load bundled IBM Plex Mono beside executable',
            'loader_address': FONT_LOADER, 'data_address': FONT_DATA,
            'font_path': 'Fonts/IBMPlexMono-Regular.ttf',
            'registration': 'FR_PRIVATE, per-process only',
            'section_permissions': ['read/execute', 'read/write']}
