"""Real x86 execution with a one-page stack growth frontier, not a flat stack."""
import struct
import unittest
from unittest.mock import patch
from test_engine_layout import emulator
from unicorn import UC_HOOK_MEM_UNMAPPED, UcError
from unicorn.x86_const import *
from stack_probes import STACK_PROBES, ALLOCATION, build_probe
import test_story_caller

REGISTERS = (UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX,
             UC_X86_REG_EDX, UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_EBP)


def guarded_emulator():
    uc = emulator()
    uc.mem_unmap(0x700000, 0x8000)
    state = {'guard': 0x707000, 'grown': [], 'skipped': []}
    def grow(u, access, address, size, value, _):
        page = address & ~4095
        if page != state['guard']:
            state['skipped'].append(hex(address))
            return False
        u.mem_map(page, 4096)
        state['grown'].append(page)
        state['guard'] -= 4096
        return True
    uc.hook_add(UC_HOOK_MEM_UNMAPPED, grow)
    uc.stack_growth = state
    return uc


class StackProbeTests(unittest.TestCase):
    def test_shipping_unprobed_allocations_fault_but_fix_grows_in_order(self):
        for site in STACK_PROBES:
            for offset in (0, 4, 0x100, 0x400, 0x7FC, 0x800, 0xFFC):
                with self.subTest(site=hex(site), offset=offset):
                    broken = guarded_emulator()
                    broken.mem_write(site, ALLOCATION)
                    broken.reg_write(UC_X86_REG_ESP, 0x708000 + offset)
                    first_push_end = site + (11 if site == 0x41D7E4 else 7)
                    with self.assertRaises(UcError):
                        broken.emu_start(site, first_push_end, count=30)
                    self.assertTrue(broken.stack_growth['skipped'])
                    fixed = guarded_emulator()
                    fixed.reg_write(UC_X86_REG_ESP, 0x708000 + offset)
                    fixed.emu_start(site, first_push_end, count=30)
                    self.assertFalse(fixed.stack_growth['skipped'])
                    self.assertEqual(fixed.stack_growth['grown'][:2], [0x707000, 0x706000])
                    self.assertEqual(fixed.reg_read(UC_X86_REG_ESP), 0x706000 + offset - 4)

    def test_trampolines_preserve_registers_flags_memory_and_exact_allocation(self):
        for site, target in STACK_PROBES.items():
            for flags in (0x202, 0xAD7):
                expected, actual = emulator(), emulator()
                expected.mem_write(site, ALLOCATION)
                pattern = bytes(range(256)) * 256
                for u in (expected, actual):
                    u.mem_write(0x700000, pattern)
                    u.reg_write(UC_X86_REG_ESP, 0x708800)
                    u.reg_write(UC_X86_REG_EFLAGS, flags)
                    for index, reg in enumerate(REGISTERS):
                        u.reg_write(reg, 0x12340000 + index)
                    u.emu_start(site, site + 6, count=30)
                for reg in (*REGISTERS, UC_X86_REG_ESP, UC_X86_REG_EFLAGS):
                    self.assertEqual(actual.reg_read(reg), expected.reg_read(reg))
                self.assertEqual(bytes(actual.mem_read(0x700000, 0x10000)), pattern)
                code = build_probe(site)
                self.assertEqual(bytes(actual.mem_read(target, len(code))), code)

    def test_full_nested_copies_and_returns_with_guarded_stack(self):
        instances = []
        def make():
            u = guarded_emulator()
            instances.append(u)
            return u
        with patch.object(test_story_caller, 'emulator', make):
            for rebuild in (0, 1, 2):
                for length in (16, 1066, 4096, 8191):
                    result = test_story_caller.caller_trace(b'A' * length, rebuild=rebuild)
                    self.assertEqual(result['output_bytes'], b'A' * length)
                    self.assertTrue(result['caller_frame_intact'])
                    self.assertEqual(result['returned_stack'],
                                     0x70801C if not rebuild else 0x708004 if rebuild == 1 else 0x708008)
        for u in instances:
            self.assertFalse(u.stack_growth['skipped'])
            self.assertGreaterEqual(len(u.stack_growth['grown']), 4)


if __name__ == '__main__':
    unittest.main()
