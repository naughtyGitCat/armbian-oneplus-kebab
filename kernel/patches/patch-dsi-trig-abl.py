#!/usr/bin/env python3
"""#55: DSI TRIG_CTRL = 0x4 (ABL picture).

ABL (readable console): REG_DSI_TRIG_CTRL = 0x4  (DMA_TRIGGER SW only)
Linux #54 (snow):        0x80001004 = TE | BLOCK_DMA_WITHIN_FRAME | DMA SW

Mainline always assumes a dedicated TE pin and blocks DMA inside the
MDP frame. ABL command-mode scanout does neither. Isolated from #20
(clock-stop) and #54 (clkout=0, kept). Idempotent.
"""
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "/opt/kebab-kernel/linux")
p = root / "drivers/gpu/drm/msm/dsi/dsi_host.c"
text = p.read_text()

if "kebab #55: ABL TRIG_CTRL=0x4" in text:
    print("TRIG_CTRL already 0x4 (ABL)")
    raise SystemExit(0)

old = (
    "\tdata = 0;\n"
    "\t/* Always assume dedicated TE pin */\n"
    "\tdata |= DSI_TRIG_CTRL_TE;\n"
    "\tdata |= DSI_TRIG_CTRL_MDP_TRIGGER(TRIGGER_NONE);\n"
    "\tdata |= DSI_TRIG_CTRL_DMA_TRIGGER(TRIGGER_SW);\n"
    "\tdata |= DSI_TRIG_CTRL_STREAM(msm_host->channel);\n"
    "\tif ((cfg_hnd->major == MSM_DSI_VER_MAJOR_6G) &&\n"
    "\t\t(cfg_hnd->minor >= MSM_DSI_6G_VER_MINOR_V1_2))\n"
    "\t\tdata |= DSI_TRIG_CTRL_BLOCK_DMA_WITHIN_FRAME;\n"
    "\tdsi_write(msm_host, REG_DSI_TRIG_CTRL, data);\n"
)
new = (
    "\t/* kebab #55: ABL TRIG_CTRL=0x4 (DMA SW only). Linux was\n"
    "\t * 0x80001004 = TE | BLOCK_DMA | DMA SW.\n"
    "\t */\n"
    "\tdata = DSI_TRIG_CTRL_DMA_TRIGGER(TRIGGER_SW);\n"
    "\tdsi_write(msm_host, REG_DSI_TRIG_CTRL, data);\n"
    "\tpr_info_once(\"dsi trig_ctrl=%#x (ABL)\\n\", data);\n"
)
if old not in text:
    raise SystemExit("no TRIG_CTRL write needle")
p.write_text(text.replace(old, new, 1))
print("patched dsi_host.c TRIG_CTRL=0x4 (ABL)")
