#!/usr/bin/env python3
"""Command-mode DSI: keep PHY/byte at the mode clock, snap pixel_clk to bit/N.

Mainline scales both pclk and byteclk by compressed_bpp/24, which drops
AMB655X from 1.1 Gbps to ~400 Mbps. The panel FFC is written for 1100 Mbps.

Command-mode porches are transfer overhead, not video blanking — downstream
keeps clockrate=1100 with DSC. Unscaling *pixel_clk* as well (#8) made
STREAM0 (hdisp=360, wc=1081) drain the MDP FIFO at 24bpp-line rate and
flooded dsi_err_worker with status=0xc (FIFO|MDP_FIFO_UNDERFLOW).

7nm dsiclk is an integer divider from bit (or bit/2). dispcc pclk0 uses
clk_pixel 1/1 and only accepts |pclk - parent| < 100 kHz. Raw DSC-scaled
78858050 is 331 kHz off bit/14, so #9's clk_set_rate returned -22 and the
panel never initialized. Snap pclk to bit/N (N=1..15). Idempotent.
"""
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "/opt/kebab-kernel/linux")
p = root / "drivers/gpu/drm/msm/dsi/dsi_host.c"
text = p.read_text()
changed = False

old_byte = (
    "\tunsigned long pclk_rate = dsi_get_pclk_rate(mode, msm_host->dsc, is_bonded_dsi);\n"
)
new_byte = (
    "\tconst struct drm_dsc_config *clk_dsc = msm_host->dsc;\n"
    "\tunsigned long pclk_rate;\n"
    "\n"
    "\t/* CMD mode: do not scale HS by DSC bpp. AMB655X FFC is 1100 Mbps. */\n"
    "\tif (!(msm_host->mode_flags & MIPI_DSI_MODE_VIDEO))\n"
    "\t\tclk_dsc = NULL;\n"
    "\tpclk_rate = dsi_get_pclk_rate(mode, clk_dsc, is_bonded_dsi);\n"
)
if "CMD mode: do not scale HS by DSC bpp" in text:
    print("byte_clk cmd-HS already patched")
elif old_byte not in text:
    raise SystemExit("no dsi_byte_clk_get_rate pclk needle")
else:
    text = text.replace(old_byte, new_byte, 1)
    changed = True
    print("patched dsi_byte_clk_get_rate")

snap = (
    "\t/* CMD+DSC: keep byte/PHY at 1.1G (FFC). Snap pixel_clk to bit/N so\n"
    "\t * clk_pixel 1/1 accepts it (|pclk-parent|<100 kHz). STREAM0 hdisp=360\n"
    "\t * then matches the slower pclk and does not underrun the MDP FIFO.\n"
    "\t */\n"
    "\tif (!(msm_host->mode_flags & MIPI_DSI_MODE_VIDEO) && msm_host->dsc &&\n"
    "\t    msm_host->byte_clk_rate && msm_host->pixel_clk_rate) {\n"
    "\t\tunsigned long bit = msm_host->byte_clk_rate * 8;\n"
    "\t\tunsigned int div = DIV_ROUND_CLOSEST(bit, msm_host->pixel_clk_rate);\n"
    "\n"
    "\t\tif (div < 1)\n"
    "\t\t\tdiv = 1;\n"
    "\t\telse if (div > 15)\n"
    "\t\t\tdiv = 15;\n"
    "\t\tmsm_host->pixel_clk_rate = bit / div;\n"
    "\t}\n"
    "\n"
    "\tpr_info_once(\"dsi clk pclk=%lu byte=%lu dsc=%d cmd=%d\\n\",\n"
    "\t\tmsm_host->pixel_clk_rate, msm_host->byte_clk_rate,\n"
    "\t\t!!msm_host->dsc, !(msm_host->mode_flags & MIPI_DSI_MODE_VIDEO));\n"
)

old_snap9 = (
    "\t/* CMD: byte/PHY stay at mode clock (FFC). pixel_clk stays DSC-scaled\n"
    "\t * so STREAM0 hdisp=360 does not underrun the MDP FIFO. 7nm pix_div\n"
    "\t * has no CLK_SET_RATE_PARENT, so the two rates split.\n"
    "\t */\n"
    "\tpr_info_once(\"dsi clk pclk=%lu byte=%lu dsc=%d cmd=%d\\n\",\n"
    "\t\tmsm_host->pixel_clk_rate, msm_host->byte_clk_rate,\n"
    "\t\t!!msm_host->dsc, !(msm_host->mode_flags & MIPI_DSI_MODE_VIDEO));\n"
)
old_unscale = (
    "\t/* Command-mode pixel_clk must match the unscaled HS rate too. */\n"
    "\tif (!(msm_host->mode_flags & MIPI_DSI_MODE_VIDEO))\n"
    "\t\tmsm_host->pixel_clk_rate = dsi_get_pclk_rate(\n"
    "\t\t\tmsm_host->mode, NULL, is_bonded_dsi);\n"
    "\n"
    "\tpr_info_once(\"dsi clk pclk=%lu byte=%lu dsc=%d cmd=%d\\n\",\n"
    "\t\tmsm_host->pixel_clk_rate, msm_host->byte_clk_rate,\n"
    "\t\t!!msm_host->dsc, !(msm_host->mode_flags & MIPI_DSI_MODE_VIDEO));\n"
)
old_dbg = (
    "\tDBG(\"pclk=%lu, bclk=%lu\", msm_host->pixel_clk_rate,\n"
    "\t\t\t\tmsm_host->byte_clk_rate);\n"
)

if "Snap pixel_clk to bit/N" in text:
    print("dsi_calc_pclk already snaps pclk to bit/N")
elif old_snap9 in text:
    text = text.replace(old_snap9, snap, 1)
    changed = True
    print("patched dsi_calc_pclk (snap pclk to bit/N)")
elif old_unscale in text:
    text = text.replace(old_unscale, snap, 1)
    changed = True
    print("patched dsi_calc_pclk (from pixel unscale)")
elif old_dbg in text:
    text = text.replace(old_dbg, snap, 1)
    changed = True
    print("patched dsi_calc_pclk (from vanilla DBG)")
elif "dsi clk pclk=" in text:
    print("dsi_calc_pclk log present, leaving rates")
else:
    raise SystemExit("no dsi_calc_pclk needle")

if changed:
    p.write_text(text)
    print("patched dsi_host.c (cmd HS keep, pclk snapped)")
else:
    print("dsi_host.c clock path unchanged")
