#!/usr/bin/env python3
"""#44: revert software ABL byteclk force.

#40/#42/#43 software byte=103167334 made clk_pixel 1/1 return -22 and
left the 7nm PLL at DEC=0. Analog 825 M is now forced in dsi_pll_commit
(patch-dsi-pll-abl-vco.py). CCF must stay on the working 1.1G snap so
link clocks actually enable. Idempotent: #42 force → 1.1G snap; 1.1G
snap already present is a no-op.
"""
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "/opt/kebab-kernel/linux")
p = root / "drivers/gpu/drm/msm/dsi/dsi_host.c"
text = p.read_text()

SNAP_11G = (
    "	/* CMD+DSC: keep byte/PHY at 1.1G (FFC). Snap pixel_clk to bit/N so\n"
    "	 * clk_pixel 1/1 accepts it (|pclk-parent|<100 kHz). STREAM0 hdisp=360\n"
    "	 * then matches the slower pclk and does not underrun the MDP FIFO.\n"
    "	 */\n"
    "	if (!(msm_host->mode_flags & MIPI_DSI_MODE_VIDEO) && msm_host->dsc &&\n"
    "	    msm_host->byte_clk_rate && msm_host->pixel_clk_rate) {\n"
)

if "kebab #42: ABL VCO" not in text and "kebab #40: ABL VCO" not in text:
    if SNAP_11G in text:
        print("software byteclk already 1.1G snap")
        raise SystemExit(0)
    raise SystemExit("no #42/#40 force and no 1.1G snap")

# Replace the #42 (or #40) force + the if (0 && leftover) header with the
# original 1.1G snap header. The DIV_ROUND_CLOSEST body is reused.
old_42 = (
    "	/* kebab #42: ABL VCO=825.338672 MHz, bit_div=1, byte=VCO/8.\n"
    "	 * #40 auto-snapped pclk to bit/10 and stalled. Keep the #39 ratio.\n"
    "	 */\n"
    "	if (!(msm_host->mode_flags & MIPI_DSI_MODE_VIDEO)) {\n"
    "		msm_host->byte_clk_rate = 103167334;\n"
    "		pr_info_once(\"dsi byte forced ABL 103167334\\n\");\n"
    "	}\n"
    "	if (!(msm_host->mode_flags & MIPI_DSI_MODE_VIDEO) && msm_host->dsc &&\n"
    "	    msm_host->byte_clk_rate) {\n"
    "		unsigned long bit = msm_host->byte_clk_rate * 8;\n"
    "		msm_host->pixel_clk_rate = bit / 14;\n"
    "		pr_info_once(\"dsi pclk forced bit/14 %lu\\n\",\n"
    "			     msm_host->pixel_clk_rate);\n"
    "	}\n"
    "\n"
    "	/* leftover snap kept as a no-op guard if the force above is removed */\n"
    "	if (0 && !(msm_host->mode_flags & MIPI_DSI_MODE_VIDEO) && msm_host->dsc &&\n"
    "	    msm_host->byte_clk_rate && msm_host->pixel_clk_rate) {\n"
)
old_40 = (
    "	/* kebab #40: ABL VCO=825.338672 MHz, bit_div=1, byte=VCO/8. */\n"
    "	if (!(msm_host->mode_flags & MIPI_DSI_MODE_VIDEO)) {\n"
    "		msm_host->byte_clk_rate = 103167334;\n"
    "		pr_info_once(\"dsi byte forced ABL 103167334\\n\");\n"
    "	}\n"
    "\n"
    "	/* CMD+DSC: keep byte/PHY at ABL HS. Snap pixel_clk to bit/N so\n"
    "	 * clk_pixel 1/1 accepts it (|pclk-parent|<100 kHz). STREAM0 hdisp=360\n"
    "	 * then matches the slower pclk and does not underrun the MDP FIFO.\n"
    "	 */\n"
    "	if (!(msm_host->mode_flags & MIPI_DSI_MODE_VIDEO) && msm_host->dsc &&\n"
    "	    msm_host->byte_clk_rate && msm_host->pixel_clk_rate) {\n"
)

if old_42 in text:
    text = text.replace(old_42, SNAP_11G, 1)
elif old_40 in text:
    text = text.replace(old_40, SNAP_11G, 1)
else:
    raise SystemExit("force header not found")

p.write_text(text)
print("reverted software ABL byteclk; CCF 1.1G snap restored")
