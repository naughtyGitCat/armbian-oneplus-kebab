#!/usr/bin/env python3
"""#62: DSI ERR_INT_MASK0 = 0x7ffffbff (ABL).

Last named programmed DSI delta vs ABL after TPG=0 + HS_TIMER + FORCE=0.
Linux writes 0x13ff3fe0 (live 0x13ff3be0). Irq mask, weak for pixels.
Isolated; 0x1f4 write starved and was reverted. Idempotent.
"""
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "/opt/kebab-kernel/linux")
p = root / "drivers/gpu/drm/msm/dsi/dsi_host.c"
text = p.read_text()

if "kebab #62: ABL ERR_INT_MASK0=0x7ffffbff" in text:
    print("ERR_INT_MASK0 already 0x7ffffbff (ABL)")
    raise SystemExit(0)

old = (
    "\t/* allow only ack-err-status to generate interrupt */\n"
    "\tdsi_write(msm_host, REG_DSI_ERR_INT_MASK0, 0x13ff3fe0);\n"
)
new = (
    "\t/* kebab #62: ABL ERR_INT_MASK0=0x7ffffbff. Linux 0x13ff3fe0. */\n"
    "\tdsi_write(msm_host, REG_DSI_ERR_INT_MASK0, 0x7ffffbff);\n"
    "\tpr_info_once(\"dsi err_int_mask0=0x7ffffbff (ABL)\\n\");\n"
)
if old not in text:
    raise SystemExit("no ERR_INT_MASK0 needle")
p.write_text(text.replace(old, new, 1))
print("patched dsi_host.c ERR_INT_MASK0=0x7ffffbff (ABL)")
