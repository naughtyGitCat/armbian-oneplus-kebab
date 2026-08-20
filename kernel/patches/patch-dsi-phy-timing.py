#!/usr/bin/env python3
"""Force Lineage 7nm D-PHY timings (1.1G HS).

Analog is CCF 1.1 G again (#49+). ABL 825 M UI counts at 1.1 G bitclock
(#42–#51) are the wrong pairing. #41 ran Lineage timings at 1.1 G *before*
mixer/CTL/solid-fill/FFC were matched. #52 is that combo for the first time.

00 24 0A 0A 26 25 09 0A 06 02 04 00 1E 1A
Idempotent: ABL/#42 force is rewritten in place; vanilla calc-fail needle
is patched if absent.
"""
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "/opt/kebab-kernel/linux")
p = root / "drivers/gpu/drm/msm/dsi/phy/dsi_phy_7nm.c"
text = p.read_text()

LINEAGE_BLOCK = (
    "\tif (!phy->cphy_mode) {\n"
    "\t\tpr_info(\"dsi 7nm phy calc clk_z=%u clk_prep=%u clk_tr=%u "
    "hs_ex=%u hs_z=%u hs_prep=%u hs_tr=%u hs_rq=%u clk_pre=%u clk_post=%u\\n\",\n"
    "\t\t\ttiming->clk_zero, timing->clk_prepare, timing->clk_trail,\n"
    "\t\t\ttiming->hs_exit, timing->hs_zero, timing->hs_prepare,\n"
    "\t\t\ttiming->hs_trail, timing->hs_rqst,\n"
    "\t\t\ttiming->shared_timings.clk_pre,\n"
    "\t\t\ttiming->shared_timings.clk_post);\n"
    "\t\t/* kebab #52: Lineage 1.1G phy-timings:\n"
    "\t\t * 00 24 0A 0A 26 25 09 0A 06 02 04 00 1E 1A\n"
    "\t\t * Analog is 1.1 G; ABL 825 M UI counts were the wrong pairing.\n"
    "\t\t */\n"
    "\t\ttiming->clk_zero = 0x24;\n"
    "\t\ttiming->clk_prepare = 0x0a;\n"
    "\t\ttiming->clk_trail = 0x0a;\n"
    "\t\ttiming->hs_exit = 0x26;\n"
    "\t\ttiming->hs_zero = 0x25;\n"
    "\t\ttiming->hs_prepare = 0x09;\n"
    "\t\ttiming->hs_trail = 0x0a;\n"
    "\t\ttiming->hs_rqst = 0x06;\n"
    "\t\ttiming->shared_timings.clk_pre = 0x1e;\n"
    "\t\ttiming->shared_timings.clk_post = 0x1a;\n"
    "\t\tpr_info(\"dsi 7nm phy force Lineage 1.1G timings\\n\");\n"
    "\t}\n"
)

if "kebab #52: Lineage 1.1G phy-timings" in text:
    print("7nm PHY timings already Lineage 1.1G")
    raise SystemExit(0)

force_start = text.find("\tif (!phy->cphy_mode) {\n\t\tpr_info(\"dsi 7nm phy calc")
if force_start >= 0:
    end = text.find("\t}\n", force_start)
    if end < 0:
        raise SystemExit("phy force block unterminated")
    end = end + len("\t}\n")
    text = text[:force_start] + LINEAGE_BLOCK + text[end:]
    p.write_text(text)
    print("rewrote 7nm PHY timings to Lineage 1.1G")
    raise SystemExit(0)

old = (
    "\tif (ret) {\n"
    "\t\tDRM_DEV_ERROR(&phy->pdev->dev,\n"
    "\t\t\t      \"%s: PHY timing calculation failed\\n\", __func__);\n"
    "\t\treturn -EINVAL;\n"
    "\t}\n"
)
new = (
    "\tif (ret) {\n"
    "\t\tDRM_DEV_ERROR(&phy->pdev->dev,\n"
    "\t\t\t      \"%s: PHY timing calculation failed\\n\", __func__);\n"
    "\t\treturn -EINVAL;\n"
    "\t}\n"
    "\n"
    + LINEAGE_BLOCK
)

if old not in text:
    raise SystemExit("no 7nm PHY calc-fail needle")
p.write_text(text.replace(old, new, 1))
print("patched dsi_phy_7nm.c with Lineage 1.1G PHY timings")
