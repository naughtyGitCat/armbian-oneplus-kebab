#!/usr/bin/env python3
"""MDP_CTRL2 DST_FORMAT2=6, matching live ABL 0x10006.

#25 programmed RGB888 (8). ABL scanout of a 32bpp stolen fb uses dst2=6
(RGB565 enum) and shows a picture. Fetch topology now matches ABL; this
is the last DSI register mismatch. Idempotent.
"""
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "/opt/kebab-kernel/linux")
p = root / "drivers/gpu/drm/msm/dsi/dsi_host.c"
text = p.read_text()

if "ABL scanout of a 32bpp stolen fb uses dst2=6" in text:
    print("MDP_CTRL2 DST_FORMAT2 already ABL 6")
    raise SystemExit(0)

old = (
    "			/* Reset leftover DST_FORMAT2=RGB565 (6). STREAM0 is RGB888. */\n"
    "			data &= ~DSI_CMD_MODE_MDP_CTRL2_DST_FORMAT2__MASK;\n"
    "			data |= DSI_CMD_MODE_MDP_CTRL2_DST_FORMAT2(\n"
    "					CMD_DST_FORMAT_RGB888);\n"
)
new = (
    "			/* ABL scanout of a 32bpp stolen fb uses dst2=6. */\n"
    "			data &= ~DSI_CMD_MODE_MDP_CTRL2_DST_FORMAT2__MASK;\n"
    "			data |= DSI_CMD_MODE_MDP_CTRL2_DST_FORMAT2(\n"
    "					CMD_DST_FORMAT_RGB565);\n"
)

if old not in text:
    raise SystemExit("no DST_FORMAT2 RGB888 needle")
p.write_text(text.replace(old, new, 1))
print("patched MDP_CTRL2 DST_FORMAT2=ABL 6")
