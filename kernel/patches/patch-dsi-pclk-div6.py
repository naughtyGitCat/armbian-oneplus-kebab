#!/usr/bin/env python3
"""#64: command-mode DSC pclk = bit/6 (ABL CLK_CFG0/CFG1 ratio).

Linux CLK_CFG0=0xE1 (pix_div=14, DSICLK_SEL=0) → pclk=bit/14=78.5 MHz.
ABL CLK_CFG0=0x31 CLK_CFG1=0x31 (pix_div=3, DSICLK_SEL=1) → pclk=bit/6.

HS FIFO_STATUS Linux 0x99991310 (EMPTY|UNDERFLOW on all 4 lanes) vs
ABL 0x11111310 (EMPTY only). PHY byteclk 137 MHz drains faster than
pclk 78.5 MHz fills. #8 unscaled pclk to 183 MHz (this same bit/6)
without raising MDP and MDP-FIFO under-ran. Pair with #64 MDP 460 MHz.
Idempotent.
"""
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "/opt/kebab-kernel/linux")
p = root / "drivers/gpu/drm/msm/dsi/dsi_host.c"
text = p.read_text()

if "kebab #64: pclk=bit/6" in text:
    print("pclk already snapped to bit/6")
    raise SystemExit(0)

old = (
    "\t\tunsigned long bit = msm_host->byte_clk_rate * 8;\n"
    "\t\tunsigned int div = DIV_ROUND_CLOSEST(bit, msm_host->pixel_clk_rate);\n"
    "\n"
    "\t\tif (div < 1)\n"
    "\t\t\tdiv = 1;\n"
    "\t\telse if (div > 15)\n"
    "\t\t\tdiv = 15;\n"
    "\t\tmsm_host->pixel_clk_rate = bit / div;\n"
)
new = (
    "\t\tunsigned long bit = msm_host->byte_clk_rate * 8;\n"
    "\t\t/* kebab #64: pclk=bit/6 (ABL). #10 used DIV_ROUND_CLOSEST → 14. */\n"
    "\t\tunsigned int div = 6;\n"
    "\n"
    "\t\tmsm_host->pixel_clk_rate = bit / div;\n"
    "\t\tpr_info_once(\"dsi pclk forced bit/6 %lu (ABL ratio)\\n\",\n"
    "\t\t\tmsm_host->pixel_clk_rate);\n"
)
if old not in text:
    raise SystemExit("no pclk snap needle for bit/6")
p.write_text(text.replace(old, new, 1))
print("patched dsi_host.c pclk=bit/6")
