#!/usr/bin/env python3
"""#38 CONST red. REVERTED after #64 solid red — do not re-invoke.

#64 pclk=bit/6 + MDP 460 produced stable webcam red. DSC/DSI/panel carry
correct pixels; fetch was the remaining question. #65 restores GEM RGBW
(`patch-dpu-revert-solid-fill.py`). Keep this file as history.
"""
raise SystemExit("STALLED: solid-fill reverted after #64 red")

# Original docstring follows (dead):
"""Force SSPP solid-fill red so scanout does not touch SMMU/GEM.

RGBW never appears after ABL-matching dual-VIG packed fetch. Either the
DPU is not reading the painted fb (IOVA 0x2000 / SMMU) or DSC/panel
destroys even correct pixels. Solid fill programs CONSTANT_COLOR and
SRC_FORMAT BIT(22); no memory fetch. Red on screen => fetch was the
bug. Remaining snow => DSC/DSI/panel. Idempotent.
"""
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "/opt/kebab-kernel/linux")
p = root / "drivers/gpu/drm/msm/disp/dpu1/dpu_plane.c"
text = p.read_text()

if "kebab #38: solid fill, skip SMMU fetch" in text:
    print("solid-fill already patched")
    raise SystemExit(0)

old = (
    "	if (pdpu->is_error)\n"
    "		/* force white frame with 100% alpha pipe output on error */\n"
    "		_dpu_plane_color_fill(pdpu, 0xFFFFFF, 0xFF);\n"
    "	else if (pdpu->color_fill & DPU_PLANE_COLOR_FILL_FLAG)\n"
    "		/* force 100% alpha */\n"
    "		_dpu_plane_color_fill(pdpu, pdpu->color_fill, 0xFF);\n"
    "	else {\n"
    "		dpu_plane_flush_csc(pdpu, &pstate->pipe);\n"
    "		dpu_plane_flush_csc(pdpu, &pstate->r_pipe);\n"
    "	}\n"
)
new = (
    "	/* kebab #38: solid fill, skip SMMU fetch. RGB=red. */\n"
    "	_dpu_plane_color_fill(pdpu, 0x0000FF, 0xFF);\n"
)

if old not in text:
    raise SystemExit("no dpu_plane_flush color_fill needle")
p.write_text(text.replace(old, new, 1))
print("patched solid-fill red")
