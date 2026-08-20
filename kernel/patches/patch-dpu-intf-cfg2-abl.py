#!/usr/bin/env python3
"""Command-mode INTF_CONFIG2: match live ABL (BIT8), not DCE BIT12.

ABL scanout (working console) has INTF1 CONFIG2=0x100. Linux #13+#23
wrote INTF_CFG2_DCE_DATA_COMPRESS (BIT12 → 0x1000). That bit is only
programmed for video-mode DPU >= 7; DPU 6 ABL does not set it and still
runs DSC + STREAM0 hdisp=360. Idempotent.
"""
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "/opt/kebab-kernel/linux")
p = root / "drivers/gpu/drm/msm/disp/dpu1/dpu_hw_intf.c"
text = p.read_text()

if "ABL live CONFIG2=0x100" in text:
    print("INTF_CONFIG2 already ABL BIT8")
    raise SystemExit(0)

old = (
    "\tif (cmd_mode_cfg->data_compress)\n"
    "\t\tintf_cfg2 |= INTF_CFG2_DCE_DATA_COMPRESS;\n"
)
new = (
    "\t/* ABL live CONFIG2=0x100 (BIT8). DPU 6 command DSC does not\n"
    "\t * set DCE_DATA_COMPRESS BIT(12); that bit is video-mode >=7.\n"
    "\t */\n"
    "\tif (cmd_mode_cfg->data_compress)\n"
    "\t\tintf_cfg2 |= BIT(8);\n"
)

if old not in text:
    raise SystemExit("no data_compress BIT12 needle")
p.write_text(text.replace(old, new, 1))
print("patched INTF_CONFIG2 cmd DSC to ABL BIT8")
