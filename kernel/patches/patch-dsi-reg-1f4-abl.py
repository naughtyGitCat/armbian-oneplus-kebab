#!/usr/bin/env python3
"""#61: DSI xml 0x1f4 = 1 (ABL). STALLED — do not re-invoke.

Wrote undocumented VERSION+4. Live 0x1f4=1. Webcam starved back to
#59-like dark + sparse colored streaks vs #60 full-frame snow. Reverted
from the 07c tree and apply-dsi-to-tree.sh. ABL 1 is likely status, not
a pixel control. Keep TPG=0 + HS_TIMER=0x4ea60.
"""
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "/opt/kebab-kernel/linux")
p = root / "drivers/gpu/drm/msm/dsi/dsi_host.c"
text = p.read_text()

if "kebab #61: ABL xml 0x1f4=1" in text:
    print("xml 0x1f4 already 1 (ABL)")
    raise SystemExit(0)

old = (
    "\tdsi_write(msm_host, REG_DSI_HS_TIMER_CTRL, 0x4ea60);\n"
    "\tpr_info_once(\"dsi hs_timer=0x4ea60 (ABL)\\n\");\n"
)
new = (
    "\tdsi_write(msm_host, REG_DSI_HS_TIMER_CTRL, 0x4ea60);\n"
    "\tpr_info_once(\"dsi hs_timer=0x4ea60 (ABL)\\n\");\n"
    "\t/* kebab #61: ABL xml 0x1f4=1. Undocumented, next to VERSION. */\n"
    "\tdsi_write(msm_host, 0x1f4, 1);\n"
    "\tpr_info_once(\"dsi xml 0x1f4=1 (ABL)\\n\");\n"
)
if old not in text:
    raise SystemExit("no HS_TIMER needle for 0x1f4 insert")
p.write_text(text.replace(old, new, 1))
print("patched dsi_host.c xml 0x1f4=1 (ABL)")
