#!/usr/bin/env python3
"""#63: skip AMB655X GPIO reset pulse (MR11). STALLED — do not re-invoke.

Retry of #27-#29 on the #62 DSI baseline (TPG=0, HS_TIMER ABL). Still
black (`desk-skip63.jpg` ~109 KiB). PHY re-init without a panel reset
kills the HS link. Restored `.pre-skip63.img` (#62). Keep the pulse.
"""
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "/opt/kebab-kernel/linux")
p = root / "drivers/gpu/drm/panel/panel-samsung-amb655x.c"
text = p.read_text()

if "kebab #63: skip reset pulse" in text:
    print("panel reset already skipped")
    raise SystemExit(0)

old = (
    "\tgpiod_set_value_cansleep(amb655x->reset_gpio, 0);\n"
    "\tusleep_range(10000, 11000);\n"
    "\tgpiod_set_value_cansleep(amb655x->reset_gpio, 1);\n"
    "\tusleep_range(1000, 2000);\n"
    "\tgpiod_set_value_cansleep(amb655x->reset_gpio, 0);\n"
    "\tusleep_range(10000, 11000);\n"
)
new = (
    "\t/* kebab #63: skip reset pulse (MR11). Delay only. */\n"
    "\tpr_info_once(\"AMB655X skip reset pulse\\n\");\n"
    "\tusleep_range(10000, 11000);\n"
    "\tusleep_range(1000, 2000);\n"
    "\tusleep_range(10000, 11000);\n"
)
if old not in text:
    raise SystemExit("no reset gpio pulse needle")
p.write_text(text.replace(old, new, 1))
print("patched panel skip reset pulse")
