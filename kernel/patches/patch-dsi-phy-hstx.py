#!/usr/bin/env python3
"""Keep SM8250 7nm V4.1 D-PHY HSTX at the generic 0x88.

#30 forced 0x66 (pre-v4.1 <1.5G drive). Live ABL scanout uses 0x88 and
pictures; 0x66 still snowed. Drop the override, keep the once-log.
Idempotent: vanilla V4.1 D-PHY has no glbl_hstx_str_ctrl_0 in that
branch (0x88 comes from the generic D-PHY default).
"""
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "/opt/kebab-kernel/linux")
p = root / "drivers/gpu/drm/msm/dsi/phy/dsi_phy_7nm.c"
text = p.read_text()

forced_66 = (
    "\t\t} else {\n"
    "\t\t\t/* Pre-v4.1 <1.5G drive. 0x88 snows HS pixels. */\n"
    "\t\t\tglbl_hstx_str_ctrl_0 = 0x66;\n"
    "\t\t\tglbl_rescode_top_ctrl = less_than_1500_mhz ? 0x3d :  0x00;\n"
    "\t\t\tglbl_rescode_bot_ctrl = less_than_1500_mhz ? 0x39 :  0x3c;\n"
    "\t\t}\n"
)
reverted = (
    "\t\t} else {\n"
    "\t\t\tglbl_rescode_top_ctrl = less_than_1500_mhz ? 0x3d :  0x00;\n"
    "\t\t\tglbl_rescode_bot_ctrl = less_than_1500_mhz ? 0x39 :  0x3c;\n"
    "\t\t}\n"
)

if forced_66 in text:
    text = text.replace(forced_66, reverted, 1)
    p.write_text(text)
    print("reverted V4.1 D-PHY HSTX 0x66 -> generic 0x88")
    raise SystemExit(0)

if "glbl_hstx_str_ctrl_0 = 0x66;" in text.split("DSI_PHY_7NM_QUIRK_V4_1")[1].split("} else {")[0] if "DSI_PHY_7NM_QUIRK_V4_1" in text else "":
    raise SystemExit("V4.1 still has an unexpected 0x66")

if "dsi 7nm hstx=" in text:
    print("V4.1 HSTX already generic 0x88 (log kept)")
    raise SystemExit(0)

# Vanilla: add the once-log after the V4.1 quirk block so live dumps
# still print hstx/rescode without changing drive.
old = (
    "\t} else if (phy->cfg->quirks & DSI_PHY_7NM_QUIRK_V4_1) {\n"
    "\t\tif (phy->cphy_mode) {\n"
    "\t\t\tglbl_hstx_str_ctrl_0 = 0x88;\n"
    "\t\t\tglbl_rescode_top_ctrl = 0x00;\n"
    "\t\t\tglbl_rescode_bot_ctrl = 0x3c;\n"
    "\t\t} else {\n"
    "\t\t\tglbl_rescode_top_ctrl = less_than_1500_mhz ? 0x3d :  0x00;\n"
    "\t\t\tglbl_rescode_bot_ctrl = less_than_1500_mhz ? 0x39 :  0x3c;\n"
    "\t\t}\n"
)
new = old + (
    "\t\tpr_info_once(\"dsi 7nm hstx=%#x res_top=%#x res_bot=%#x cphy=%d\\n\",\n"
    "\t\t\t     glbl_hstx_str_ctrl_0, glbl_rescode_top_ctrl,\n"
    "\t\t\t     glbl_rescode_bot_ctrl, phy->cphy_mode);\n"
)
if old not in text:
    raise SystemExit("no V4.1 HSTX needle")
p.write_text(text.replace(old, new, 1))
print("kept V4.1 D-PHY HSTX=0x88, added once-log")
