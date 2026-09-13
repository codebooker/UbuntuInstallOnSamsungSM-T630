"""Read-only disassembly of the extracted stock SM-T630 ABL."""
import re
import sys
from pathlib import Path
import pefile
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM

path = next(Path('/tmp/t630-boot-audit.J5LCRu/unpacked').rglob(
    'file-f536d559-459f-48fa-8bbc-43b554ecae8d/section1.pe'))
pe = pefile.PE(str(path))
base = pe.OPTIONAL_HEADER.ImageBase
data = pe.get_memory_mapped_image()
md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
md.detail = True

def show(insns):
    for ins in insns:
        print(hex(ins.address), ins.mnemonic, ins.op_str)

if sys.argv[1] == 'range':
    a, b = (int(v, 16) for v in sys.argv[2:4])
    show(md.disasm(data[a-base:b-base], a))
else:
    targets = {}
    if sys.argv[1] == 'xref':
        for m in re.finditer(rb'[\x09\x0a\x0d\x20-\x7e]{3,}\x00', data):
            if re.search(sys.argv[2], m.group().decode(), re.I):
                targets[base + m.start()] = m.group().decode()
                print(hex(base + m.start()), repr(m.group()))
    for sec in pe.sections:
        if not sec.Characteristics & 0x20000000:
            continue
        insns = list(md.disasm(sec.get_data(), base + sec.VirtualAddress))
        for i, ins in enumerate(insns):
            if sys.argv[1] == 'calls':
                if (ins.mnemonic in ('bl', 'b', 'cbz', 'cbnz', 'tbz', 'tbnz') or ins.mnemonic.startswith('b.')) and ins.operands[-1].type == 2 and ins.operands[-1].imm == int(sys.argv[2], 16):
                    print('CALL', hex(ins.address))
                    show(insns[max(0, i-8):i+10])
            elif ins.mnemonic == 'adrp':
                reg, page = ins.operands[0].reg, ins.operands[1].imm
                for nxt in insns[i+1:i+5]:
                    if nxt.mnemonic == 'add' and len(nxt.operands) >= 3 and nxt.operands[1].reg == reg and nxt.operands[2].type == 2:
                        address = page + nxt.operands[2].imm
                        if address in targets:
                            print('XREF', hex(ins.address), repr(targets[address]))
                            show(insns[max(0, i-12):i+20])
                        break
