#!/usr/bin/env python3
"""PP_DCE_DATA_OUT_SWAP BIT18 follows ABL.

#39 cleared BIT18 (Linux setup_dsc always ORed it). Safe-boot ABL has
OUT=0x6c688 (BIT18 set) and pictures. Restore the OR. Idempotent.
"""
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "/opt/kebab-kernel/linux")
p = root / "drivers/gpu/drm/msm/disp/dpu1/dpu_hw_pingpong.c"
text = p.read_text()

if "ABL OUT=0x6c688 has BIT18" in text:
    print("PP DSC endian already ABL BIT18")
    raise SystemExit(0)

no_endian = (
    "	/* ABL scanout pictures without that RMW. */\n"
    "	data = DPU_REG_READ(pp_c, PP_DCE_DATA_OUT_SWAP);\n"
    "	data &= ~BIT(18);\n"
    "	DPU_REG_WRITE(pp_c, PP_DCE_DATA_OUT_SWAP, data);\n"
    "	pr_info_once(\"dpu pp dsc out_swap=0x%x (no endian)\\n\", data);\n"
)
abl = (
    "	/* ABL OUT=0x6c688 has BIT18. */\n"
    "	data = DPU_REG_READ(pp_c, PP_DCE_DATA_OUT_SWAP);\n"
    "	data |= BIT(18); /* endian flip */\n"
    "	DPU_REG_WRITE(pp_c, PP_DCE_DATA_OUT_SWAP, data);\n"
    "	pr_info_once(\"dpu pp dsc out_swap=0x%x (ABL endian)\\n\", data);\n"
)
vanilla = (
    "	data = DPU_REG_READ(pp_c, PP_DCE_DATA_OUT_SWAP);\n"
    "	data |= BIT(18); /* endian flip */\n"
    "	DPU_REG_WRITE(pp_c, PP_DCE_DATA_OUT_SWAP, data);\n"
)

if no_endian in text:
    p.write_text(text.replace(no_endian, abl, 1))
    print("restored PP DSC ABL BIT18 from no-endian")
elif vanilla in text:
    p.write_text(text.replace(vanilla, abl, 1))
    print("annotated PP DSC ABL BIT18")
else:
    raise SystemExit("no PP_DCE_DATA_OUT_SWAP needle")
