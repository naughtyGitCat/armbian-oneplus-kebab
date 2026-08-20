#!/usr/bin/env python3
"""#57: PHY CMN LANE_CTRL1 = 0 (ABL), keep DSI CLKLN_HS_FORCE.

ABL (readable console): PHY CMN LANE_CTRL1 (0xa4) = 0
Linux #55 (snow):        0x60 = BIT(5)|BIT(6) from dsi_7nm_set_continuous_clock(true)

#20 set MIPI_DSI_CLOCK_NON_CONTINUOUS, which skipped the whole host
block: PHY bits *and* DSI CLKLN_HS_FORCE → black. Isolated here: clear
the PHY bits but still return true so dsi_host keeps FORCE (live
LANE_CTRL 0x10000000). Idempotent.
"""
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "/opt/kebab-kernel/linux")
p = root / "drivers/gpu/drm/msm/dsi/phy/dsi_phy_7nm.c"
text = p.read_text()

if "kebab #57: ABL LANE_CTRL1=0" in text:
    print("LANE_CTRL1 already 0 (ABL, FORCE kept)")
    raise SystemExit(0)

old = (
    "\tdata = readl(base + REG_DSI_7nm_PHY_CMN_LANE_CTRL1);\n"
    "\tif (enable)\n"
    "\t\tdata |= BIT(5) | BIT(6);\n"
    "\telse\n"
    "\t\tdata &= ~(BIT(5) | BIT(6));\n"
    "\twritel(data, base + REG_DSI_7nm_PHY_CMN_LANE_CTRL1);\n"
    "\n"
    "\treturn enable;\n"
)
new = (
    "\t/* kebab #57: ABL LANE_CTRL1=0. Linux ORs BIT(5)|BIT(6)=0x60.\n"
    "\t * Still return true so dsi_host keeps CLKLN_HS_FORCE (#20 dropped\n"
    "\t * both and blacked).\n"
    "\t */\n"
    "\t(void)enable;\n"
    "\tdata = readl(base + REG_DSI_7nm_PHY_CMN_LANE_CTRL1);\n"
    "\tdata &= ~(BIT(5) | BIT(6));\n"
    "\twritel(data, base + REG_DSI_7nm_PHY_CMN_LANE_CTRL1);\n"
    "\tpr_info_once(\"dsi 7nm LANE_CTRL1=%#x (ABL, FORCE kept)\\n\", data);\n"
    "\treturn true;\n"
)
if old not in text:
    raise SystemExit("no set_continuous_clock needle")
p.write_text(text.replace(old, new, 1))
print("patched dsi_phy_7nm.c LANE_CTRL1=0 (FORCE kept)")
