#!/usr/bin/env python3
"""Command-mode CMD_CFG0 INTERLEAVE_MAX=1, matching live ABL 0x100008.

ABL CFG0=0x100008 (DST_FORMAT RGB888 + INTERLEAVE_MAX=1). Mainline writes
only DST_FORMAT=8 (live 0x8). Dual-slice command DSC (spp=2) is the
case interleave is for. Idempotent.
"""
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "/opt/kebab-kernel/linux")
p = root / "drivers/gpu/drm/msm/dsi/dsi_host.c"
text = p.read_text()

if "ABL CFG0=0x100008" in text:
    print("CMD_CFG0 INTERLEAVE_MAX already 1")
    raise SystemExit(0)

old = (
    "\t\tdata = DSI_CMD_CFG0_RGB_SWAP(SWAP_RGB);\n"
    "\t\tdata |= DSI_CMD_CFG0_DST_FORMAT(dsi_get_cmd_fmt(mipi_fmt));\n"
    "\t\tdsi_write(msm_host, REG_DSI_CMD_CFG0, data);\n"
)
new = (
    "\t\tdata = DSI_CMD_CFG0_RGB_SWAP(SWAP_RGB);\n"
    "\t\tdata |= DSI_CMD_CFG0_DST_FORMAT(dsi_get_cmd_fmt(mipi_fmt));\n"
    "\t\t/* ABL CFG0=0x100008: INTERLEAVE_MAX=1 with RGB888. */\n"
    "\t\tdata |= DSI_CMD_CFG0_INTERLEAVE_MAX(1);\n"
    "\t\tdsi_write(msm_host, REG_DSI_CMD_CFG0, data);\n"
)

if old not in text:
    raise SystemExit("no CMD_CFG0 write needle")
p.write_text(text.replace(old, new, 1))
print("patched CMD_CFG0 INTERLEAVE_MAX=1")
