#!/usr/bin/env python3
"""#59: DSI TEST_PATTERN_GEN_CTRL = 0 (ABL).

Safe-DTB ABL vs Linux #58 DSI raw (xml+4): remaining programmed deltas
are HS_TIMER, ERR_INT_MASK0, xml 0x1f4, and TEST_PATTERN_GEN_CTRL
0x158 ABL 0 vs Linux 4 (DSI_TEST_PATTERN_GEN_CTRL_TPG_DMA_FIFO_MODE).

Mainline never writes this register on the normal path; reset leftover
0x4 selects TPG DMA FIFO mode. Isolated: write 0. Idempotent.
"""
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "/opt/kebab-kernel/linux")
p = root / "drivers/gpu/drm/msm/dsi/dsi_host.c"
text = p.read_text()

if "kebab #59: ABL TPG_CTRL=0" in text:
    print("TPG_CTRL already 0 (ABL)")
    raise SystemExit(0)

old = (
    "\tdata = 0;\n"
    "\tdsi_write(msm_host, REG_DSI_CLKOUT_TIMING_CTRL, data);\n"
    "\tpr_info_once(\"dsi clkout_timing=0 (ABL)\\n\");\n"
)
new = (
    "\tdata = 0;\n"
    "\tdsi_write(msm_host, REG_DSI_CLKOUT_TIMING_CTRL, data);\n"
    "\tpr_info_once(\"dsi clkout_timing=0 (ABL)\\n\");\n"
    "\t/* kebab #59: ABL TPG_CTRL=0. Linux reset leftover 0x4 is\n"
    "\t * TPG_DMA_FIFO_MODE. Can scramble MDP pixels into snow.\n"
    "\t */\n"
    "\tdsi_write(msm_host, REG_DSI_TEST_PATTERN_GEN_CTRL, 0);\n"
    "\tpr_info_once(\"dsi tpg_ctrl=0 (ABL)\\n\");\n"
)
if old not in text:
    raise SystemExit("no CLKOUT needle for TPG insert")
p.write_text(text.replace(old, new, 1))
print("patched dsi_host.c TPG_CTRL=0 (ABL)")
