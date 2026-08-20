#!/usr/bin/env python3
"""#54: DSI CLKOUT_TIMING_CTRL = 0 (ABL picture).

ABL (readable console): REG_DSI_CLKOUT_TIMING_CTRL = 0
Linux #53 (snow):        0x1a1e = T_CLK_POST(0x1a) | T_CLK_PRE(0x1e)

Those bytes are the PHY shared clk_post/clk_pre also programmed into
7nm TIMING_CTRL_12/13. The DSI controller copy is for clock-lane
HS entry/exit around LP transitions. ABL leaves the controller
register 0 (clock lane stays in HS; CLKLN_HS_FORCE is also 0 on ABL
but #20 dropping FORCE blacks the panel). Isolated: zero clkout only.
Idempotent.
"""
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "/opt/kebab-kernel/linux")
p = root / "drivers/gpu/drm/msm/dsi/dsi_host.c"
text = p.read_text()

if "kebab #54: ABL CLKOUT_TIMING=0" in text:
    print("CLKOUT_TIMING already 0 (ABL)")
    raise SystemExit(0)

old = (
    "\tdata = DSI_CLKOUT_TIMING_CTRL_T_CLK_POST(phy_shared_timings->clk_post) |\n"
    "\t\tDSI_CLKOUT_TIMING_CTRL_T_CLK_PRE(phy_shared_timings->clk_pre);\n"
    "\tdsi_write(msm_host, REG_DSI_CLKOUT_TIMING_CTRL, data);\n"
)
new = (
    "\t/* kebab #54: ABL CLKOUT_TIMING=0. Linux wrote T_CLK_POST/PRE\n"
    "\t * from PHY shared timings (live 0x1a1e). Controller clkout is\n"
    "\t * unused when the clock lane stays in HS.\n"
    "\t */\n"
    "\tdata = 0;\n"
    "\tdsi_write(msm_host, REG_DSI_CLKOUT_TIMING_CTRL, data);\n"
    "\tpr_info_once(\"dsi clkout_timing=0 (ABL)\\n\");\n"
)
if old not in text:
    raise SystemExit("no CLKOUT_TIMING write needle")
p.write_text(text.replace(old, new, 1))
print("patched dsi_host.c CLKOUT_TIMING=0 (ABL)")
