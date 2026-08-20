#!/usr/bin/env python3
"""Command DSC COMP: write STREAM0 only, drop STREAM1 leftover.

ABL COMP=0x3901 COMP2=0x21c. Linux RMW-ORs STREAM0 into the low 16 bits
and keeps STREAM1=0x3901 (live 0x39003901). Idempotent.
"""
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "/opt/kebab-kernel/linux")
p = root / "drivers/gpu/drm/msm/dsi/dsi_host.c"
text = p.read_text()

if "ABL COMP=0x3901" in text:
    print("CMD COMP already written clean")
    raise SystemExit(0)

old = (
    "\t\treg_ctrl = dsi_read(msm_host, REG_DSI_COMMAND_COMPRESSION_MODE_CTRL);\n"
    "\t\treg_ctrl2 = dsi_read(msm_host, REG_DSI_COMMAND_COMPRESSION_MODE_CTRL2);\n"
    "\n"
    "\t\treg_ctrl &= ~0xffff;\n"
    "\t\treg_ctrl |= reg;\n"
    "\n"
    "\t\treg_ctrl2 &= ~DSI_COMMAND_COMPRESSION_MODE_CTRL2_STREAM0_SLICE_WIDTH__MASK;\n"
    "\t\treg_ctrl2 |= DSI_COMMAND_COMPRESSION_MODE_CTRL2_STREAM0_SLICE_WIDTH(dsc->slice_chunk_size);\n"
)
new = (
    "\t\t/* ABL COMP=0x3901 COMP2=0x21c. Do not keep STREAM1 leftover. */\n"
    "\t\treg_ctrl = reg;\n"
    "\t\treg_ctrl2 = DSI_COMMAND_COMPRESSION_MODE_CTRL2_STREAM0_SLICE_WIDTH(\n"
    "\t\t\tdsc->slice_chunk_size);\n"
)

if old not in text:
    raise SystemExit("no CMD COMP RMW needle")
p.write_text(text.replace(old, new, 1))
print("patched CMD COMP write-clean")
