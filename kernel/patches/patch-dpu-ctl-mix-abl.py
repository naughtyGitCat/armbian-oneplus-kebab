#!/usr/bin/env python3
"""#50: put the plane on DPU_STAGE_3 so CTL_LAYER mix=5 (ABL).

ABL (picture):  LM0 CTL_LAYER=0x1000005  LM1=0x1000028  (mix=5)
Linux #49:      LM0 CTL_LAYER=0x1000002  LM1=0x1000010  (mix=2)

mix = (stage + 1) & 7, so mix=2 is DPU_STAGE_0 and mix=5 is DPU_STAGE_3.
Blend config follows pstate->stage, so this also moves LM_BLEND to the
ABL stage slot (sdm845_lm_sblk +0x68) instead of STAGE_0 (+0x20).
"""
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "/opt/kebab-kernel/linux")
p = root / "drivers/gpu/drm/msm/disp/dpu1/dpu_plane.c"
text = p.read_text()

if "kebab #50: ABL CTL mix=5" in text:
    print("plane stage already DPU_STAGE_3 (ABL mix=5)")
    raise SystemExit(0)

old = (
    "\tpstate->stage = DPU_STAGE_0 + pstate->base.normalized_zpos;\n"
)
new = (
    "\t/* kebab #50: ABL CTL mix=5 → DPU_STAGE_3. Linux zpos mapped to\n"
    "\t * STAGE_0 (mix=2). Blend registers follow this stage index.\n"
    "\t */\n"
    "\tpstate->stage = DPU_STAGE_3;\n"
    "\tpr_info_once(\"dpu plane stage=3 (ABL mix=5)\\n\");\n"
)
if old not in text:
    raise SystemExit("no pstate->stage needle")
text = text.replace(old, new, 1)
p.write_text(text)
print("patched dpu_plane.c stage=DPU_STAGE_3 (ABL mix=5)")
