#!/usr/bin/env python3
"""#49: force ABL LM blend (BLEND0_OP=0x400, mixer_op_mode=0).

Safe-boot ABL (picture) vs Linux snow, after SSPP/INTF/DSC/PHY matched:
  ABL  BLEND0_OP=0x400  mixer_op_mode=0 / 0x80000000
  Linux BLEND0_OP=0x100 mixer_op_mode=0x2 / 0x80000002

Solid-fill red still snows, so the remaining DPU delta is mixer blend,
not GEM/IOVA. 0x400 is DPU_BLEND_BG_INV_ALPHA; Linux 0x100 is
DPU_BLEND_BG_ALPHA_BG_CONST (opaque). mixer_op_mode bit1 is STAGE0 FG
alpha in color_out.
"""
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "/opt/kebab-kernel/linux")
p = root / "drivers/gpu/drm/msm/disp/dpu1/dpu_crtc.c"
text = p.read_text()

if "kebab #49: ABL LM blend" in text:
    print("LM blend already ABL 0x400 / op_mode 0")
    raise SystemExit(0)

old_blend = (
    "\tlm->ops.setup_blend_config(lm, pstate->stage,\n"
    "\t\t\t\tfg_alpha, bg_alpha, blend_op);\n"
)
new_blend = (
    "\t/* kebab #49: ABL LM_BLEND0_OP=0x400 mixer_op_mode=0 */\n"
    "\tblend_op = 0x400;\n"
    "\tpr_info_once(\"dpu lm blend_op=0x400 (ABL BG_INV_ALPHA)\\n\");\n"
    "\tlm->ops.setup_blend_config(lm, pstate->stage,\n"
    "\t\t\t\tfg_alpha, bg_alpha, blend_op);\n"
)
if old_blend not in text:
    raise SystemExit("no setup_blend_config needle")
text = text.replace(old_blend, new_blend, 1)

old_op = (
    "\t\t\tif (bg_alpha_enable && !format->alpha_enable)\n"
    "\t\t\t\tmixer[lm_idx].mixer_op_mode = 0;\n"
    "\t\t\telse\n"
    "\t\t\t\tmixer[lm_idx].mixer_op_mode |=\n"
    "\t\t\t\t\t\t1 << pstate->stage;\n"
)
new_op = (
    "\t\t\t/* kebab #49: ABL mixer_op_mode=0 (no STAGE FG alpha) */\n"
    "\t\t\tmixer[lm_idx].mixer_op_mode = 0;\n"
)
if old_op not in text:
    raise SystemExit("no mixer_op_mode needle")
text = text.replace(old_op, new_op, 1)

p.write_text(text)
print("patched dpu_crtc.c ABL LM blend 0x400 / op_mode 0")
