#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import struct
import unittest


source = Path(__file__).with_name("audit_kernel_module_abi.py")
spec = importlib.util.spec_from_file_location("kernel_module_abi", source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class KernelModuleAbiTests(unittest.TestCase):
    def test_versions_and_modinfo_parsers(self):
        blob = b"".join((
            module.VERSION_RECORD.pack(0x12345678, b"module_layout"),
            module.VERSION_RECORD.pack(0xABCDEF01, b"cnss2_symbol"),
        ))
        self.assertEqual(module.parse_versions_blob(blob), {
            "module_layout": 0x12345678,
            "cnss2_symbol": 0xABCDEF01,
        })
        self.assertEqual(
            module.parse_modinfo_blob(
                b"vermagic=5.4.274-test SMP\0depends=cnss2,cnss_nl\0"
            ),
            {"vermagic": "5.4.274-test SMP", "depends": "cnss2,cnss_nl"},
        )

    def test_symvers_audit_reports_missing_and_mismatched(self):
        exports = module.parse_symvers_text(
            "0x12345678\tmodule_layout\tvmlinux\tEXPORT_SYMBOL\t\n"
            "0x00000002\tpresent\tvmlinux\tEXPORT_SYMBOL_GPL\t\n"
        )
        missing, mismatched = module.audit(
            {"module_layout": 0x12345678, "present": 3, "absent": 4},
            exports,
        )
        self.assertEqual(missing, ["absent"])
        self.assertEqual(mismatched, ["present"])

    def test_elf_section_reader_is_read_only_and_finds_sections(self):
        names = b"\0.shstrtab\0__versions\0.modinfo\0"
        version = module.VERSION_RECORD.pack(0x12345678, b"module_layout")
        modinfo = b"vermagic=test SMP\0"
        header_size = module.ELF_HEADER.size
        strings_offset = header_size
        versions_offset = strings_offset + len(names)
        modinfo_offset = versions_offset + len(version)
        section_offset = modinfo_offset + len(modinfo)
        ident = b"\x7fELF" + bytes([2, 1, 1]) + bytes(9)
        header = module.ELF_HEADER.pack(
            ident, 1, 183, 1, 0, 0, section_offset, 0,
            header_size, 0, 0, module.SECTION_HEADER.size, 4, 1,
        )
        null = module.SECTION_HEADER.pack(*([0] * 10))
        shstr = module.SECTION_HEADER.pack(
            1, 3, 0, 0, strings_offset, len(names), 0, 0, 1, 0
        )
        versions = module.SECTION_HEADER.pack(
            names.index(b"__versions"), 1, 0, 0, versions_offset,
            len(version), 0, 0, 8, module.VERSION_RECORD.size,
        )
        info = module.SECTION_HEADER.pack(
            names.index(b".modinfo"), 1, 0, 0, modinfo_offset,
            len(modinfo), 0, 0, 1, 0,
        )
        data = header + names + version + modinfo + null + shstr + versions + info
        sections = module.elf_sections(data)
        self.assertEqual(module.parse_versions_blob(sections["__versions"]), {
            "module_layout": 0x12345678,
        })
        self.assertEqual(module.parse_modinfo_blob(sections[".modinfo"])["vermagic"],
                         "test SMP")

    def test_bad_version_blob_is_rejected(self):
        with self.assertRaises(ValueError):
            module.parse_versions_blob(b"short")
        bad = struct.pack("<Q56s", 1 << 40, b"symbol")
        with self.assertRaises(ValueError):
            module.parse_versions_blob(bad)

    def test_nobits_section_needs_no_file_payload(self):
        names = b"\0.shstrtab\0.bss\0"
        header_size = module.ELF_HEADER.size
        section_offset = header_size + len(names)
        ident = b"\x7fELF" + bytes([2, 1, 1]) + bytes(9)
        header = module.ELF_HEADER.pack(
            ident, 1, 183, 1, 0, 0, section_offset, 0,
            header_size, 0, 0, module.SECTION_HEADER.size, 3, 1,
        )
        null = module.SECTION_HEADER.pack(*([0] * 10))
        shstr = module.SECTION_HEADER.pack(
            1, 3, 0, 0, header_size, len(names), 0, 0, 1, 0
        )
        bss = module.SECTION_HEADER.pack(
            names.index(b".bss"), 8, 0, 0, 10_000_000, 4096, 0, 0, 8, 0
        )
        sections = module.elf_sections(header + names + null + shstr + bss)
        self.assertEqual(sections[".bss"], b"")


if __name__ == "__main__":
    unittest.main()
