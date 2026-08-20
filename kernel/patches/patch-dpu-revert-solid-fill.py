#!/usr/bin/env python3
"""#65: revert #38 CONST red so GEM RGBW can scan out.

#64 pclk=bit/6 + MDP 460 MHz produced stable solid red (webcam burst).
DSC/DSI/PHY/panel are carrying correct pixels. Put dpu_plane_flush back
on the SMMU fetch + CSC path. Idempotent on a tree that never had #38.
"""
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "/opt/kebab-kernel/linux")
p = root / "drivers/gpu/drm/msm/disp/dpu1/dpu_plane.c"
text = p.read_text()

old = (
    "\t/* kebab #38: solid fill, skip SMMU fetch. RGB=red. */\n"
    "\t_dpu_plane_color_fill(pdpu, 0x0000FF, 0xFF);\n"
)
new = (
    "\tif (pdpu->is_error)\n"
    "\t\t/* force white frame with 100% alpha pipe output on error */\n"
    "\t\t_dpu_plane_color_fill(pdpu, 0xFFFFFF, 0xFF);\n"
    "\telse if (pdpu->color_fill & DPU_PLANE_COLOR_FILL_FLAG)\n"
    "\t\t/* force 100% alpha */\n"
    "\t\t_dpu_plane_color_fill(pdpu, pdpu->color_fill, 0xFF);\n"
    "\telse {\n"
    "\t\tdpu_plane_flush_csc(pdpu, &pstate->pipe);\n"
    "\t\tdpu_plane_flush_csc(pdpu, &pstate->r_pipe);\n"
    "\t}\n"
)

if "kebab #38: solid fill, skip SMMU fetch" not in text:
    print("solid-fill already reverted")
    raise SystemExit(0)
if old not in text:
    raise SystemExit("no #38 solid-fill needle")
p.write_text(text.replace(old, new, 1))
print("reverted dpu_plane.c solid-fill (#65 GEM RGBW)")
