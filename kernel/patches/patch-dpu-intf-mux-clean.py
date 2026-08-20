#!/usr/bin/env python3
"""INTF_MUX: write PP index, do not RMW leftover bits 16-19.

ABL live MUX=0 (PP0). Linux RMW keeps reset/ABL 0x000f0000 in the
upper nibble while low nibble is already PP0. #24 set PINGPONG_NONE
(low nibble 0xf) and starved; this only drops the leftover. Idempotent.
"""
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "/opt/kebab-kernel/linux")
p = root / "drivers/gpu/drm/msm/disp/dpu1/dpu_hw_intf.c"
text = p.read_text()

if "ABL live MUX=0" in text:
    print("INTF_MUX already written clean")
    raise SystemExit(0)

old = (
    "\tmux_cfg = DPU_REG_READ(c, INTF_MUX);\n"
    "\tmux_cfg &= ~0xf;\n"
    "\n"
    "\tif (pp)\n"
    "\t\tmux_cfg |= (pp - PINGPONG_0) & 0x7;\n"
    "\telse\n"
    "\t\tmux_cfg |= 0xf;\n"
    "\n"
    "\tDPU_REG_WRITE(c, INTF_MUX, mux_cfg);\n"
)
new = (
    "\t/* ABL live MUX=0 (PP0). Do not RMW leftover 0xf0000. */\n"
    "\tif (pp)\n"
    "\t\tmux_cfg = (pp - PINGPONG_0) & 0x7;\n"
    "\telse\n"
    "\t\tmux_cfg = 0xf;\n"
    "\n"
    "\tDPU_REG_WRITE(c, INTF_MUX, mux_cfg);\n"
)

if old not in text:
    raise SystemExit("no INTF_MUX RMW needle")
p.write_text(text.replace(old, new, 1))
print("patched INTF_MUX write-clean")
