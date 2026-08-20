#!/usr/bin/env python3
"""#58: drop DSI CLKLN_HS_FORCE (ABL), keep PHY LANE_CTRL1=0.

ABL named dump of LANE_CTRL was off-by-4; Linux live xml 0xa8 is
0x10000000 (CLKLN_HS_FORCE). #20 set MIPI_DSI_CLOCK_NON_CONTINUOUS,
which skipped the whole host block (PHY bits AND FORCE AND clock-stop
around packets) and blacked. #57 cleared PHY LANE_CTRL1 only; still
snow, kickoff OK. Isolated: do not OR FORCE. Still call
set_continuous_clock (returns true, clears HS_REQ_SEL_PHY). Do NOT
set NON_CONTINUOUS. Idempotent.
"""
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "/opt/kebab-kernel/linux")
p = root / "drivers/gpu/drm/msm/dsi/dsi_host.c"
text = p.read_text()

if "kebab #58: no CLKLN_HS_FORCE" in text:
    print("CLKLN_HS_FORCE already dropped")
    raise SystemExit(0)

old = (
    "\t\tdsi_write(msm_host, REG_DSI_LANE_CTRL,\n"
    "\t\t\tlane_ctrl | DSI_LANE_CTRL_CLKLN_HS_FORCE_REQUEST);\n"
)
new = (
    "\t\t/* kebab #58: do not OR CLKLN_HS_FORCE. #20 dropped FORCE with\n"
    "\t\t * PHY LANE_CTRL1 and NON_CONTINUOUS and blacked. #57 cleared\n"
    "\t\t * PHY bits only. Isolated FORCE here.\n"
    "\t\t */\n"
    "\t\tdsi_write(msm_host, REG_DSI_LANE_CTRL, lane_ctrl);\n"
    "\t\tpr_info_once(\"dsi lane_ctrl=%#x (no FORCE)\\n\", lane_ctrl);\n"
)
if old not in text:
    raise SystemExit("no CLKLN_HS_FORCE write needle")
p.write_text(text.replace(old, new, 1))
print("patched dsi_host.c drop CLKLN_HS_FORCE")
