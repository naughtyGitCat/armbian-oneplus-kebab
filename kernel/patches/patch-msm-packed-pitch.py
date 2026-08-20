#!/usr/bin/env python3
"""Stolen/dumb fb pitch: pack 1080×4=4320, drop 32-pixel Adreno pad.

ABL scanout YSTRIDE=0x10e0 (4320). Mainline align_pitch ALIGN(width,32)
makes 1088×4=4352. Source-split of that padded line into two 540 DSC
slices is the remaining ABL vs Linux fetch delta. GPU is off, so the
Adreno 32-pixel rule is unused. Idempotent.
"""
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "/opt/kebab-kernel/linux")
p = root / "drivers/gpu/drm/msm/msm_drv.h"
text = p.read_text()

if "ABL stolen fb is packed" in text:
    print("align_pitch already packed")
    raise SystemExit(0)

old = (
    "static inline int align_pitch(int width, int bpp)\n"
    "{\n"
    "	int bytespp = (bpp + 7) / 8;\n"
    "	/* adreno needs pitch aligned to 32 pixels: */\n"
    "	return bytespp * ALIGN(width, 32);\n"
    "}\n"
)
new = (
    "static inline int align_pitch(int width, int bpp)\n"
    "{\n"
    "	int bytespp = (bpp + 7) / 8;\n"
    "	/* ABL stolen fb is packed (1080*4=4320). 32-pixel pad (4352)\n"
    "	 * source-split into 540 DSC slices snows on AMB655X. GPU off.\n"
    "	 */\n"
    "	return bytespp * width;\n"
    "}\n"
)

if old not in text:
    raise SystemExit("no align_pitch needle")
p.write_text(text.replace(old, new, 1))
print("patched align_pitch packed (no 32-pixel pad)")
