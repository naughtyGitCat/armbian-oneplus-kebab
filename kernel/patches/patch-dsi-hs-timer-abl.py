#!/usr/bin/env python3
"""#60: DSI HS_TIMER_CTRL = 0x4ea60 (ABL).

Safe-DTB ABL vs Linux #59 DSI raw: Linux never writes REG_DSI_HS_TIMER_CTRL
so it stays reset 0xffff (HS_TX_TO max, TIMER_RESOLUTION 0). ABL 0x4ea60.
Isolated from TPG=0 (kept, structure change). Idempotent.
"""
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "/opt/kebab-kernel/linux")
p = root / "drivers/gpu/drm/msm/dsi/dsi_host.c"
text = p.read_text()

if "kebab #60: ABL HS_TIMER=0x4ea60" in text:
    print("HS_TIMER already 0x4ea60 (ABL)")
    raise SystemExit(0)

old = (
    "\tdsi_write(msm_host, REG_DSI_TEST_PATTERN_GEN_CTRL, 0);\n"
    "\tpr_info_once(\"dsi tpg_ctrl=0 (ABL)\\n\");\n"
)
new = (
    "\tdsi_write(msm_host, REG_DSI_TEST_PATTERN_GEN_CTRL, 0);\n"
    "\tpr_info_once(\"dsi tpg_ctrl=0 (ABL)\\n\");\n"
    "\t/* kebab #60: ABL HS_TIMER=0x4ea60. Linux left reset 0xffff. */\n"
    "\tdsi_write(msm_host, REG_DSI_HS_TIMER_CTRL, 0x4ea60);\n"
    "\tpr_info_once(\"dsi hs_timer=0x4ea60 (ABL)\\n\");\n"
)
if old not in text:
    raise SystemExit("no TPG needle for HS_TIMER insert")
p.write_text(text.replace(old, new, 1))
print("patched dsi_host.c HS_TIMER=0x4ea60 (ABL)")
