#!/usr/bin/env python3
"""DPU 5+ command-mode INTF: DSC compress bit + RGB888 PANEL_FORMAT.

Mainline only assigns program_intf_cmd_cfg for core_major_ver >= 7.
SM8250 is DPU 6. Command mode never calls setup_timing_engine, so
INTF_PANEL_FORMAT stays at reset while video programs RGB888 8bpc
(0x213f). Idempotent.
"""
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "/opt/kebab-kernel/linux")
p = root / "drivers/gpu/drm/msm/disp/dpu1/dpu_hw_intf.c"
text = p.read_text()
changed = False

old = (
    "\t/* Technically, INTF_CONFIG2 is present for DPU 5.0+, but\n"
    "\t * we can configure it for DPU 7.0+ since the wide bus and DSC flags\n"
    "\t * would not be set for DPU < 7.0 anyways\n"
    "\t */\n"
    "\tif (mdss_rev->core_major_ver >= 7)\n"
    "\t\tc->ops.program_intf_cmd_cfg = dpu_hw_intf_program_intf_cmd_cfg;\n"
)
new = (
    "\t/* INTF_CONFIG2 is on DPU 5+ (0x060). Command-mode DSC needs\n"
    "\t * INTF_CFG2_DCE_DATA_COMPRESS; the >=7-only path left SM8250\n"
    "\t * (DPU 6) pushing 24bpp into compressed STREAM0.\n"
    "\t */\n"
    "\tif (mdss_rev->core_major_ver >= 5)\n"
    "\t\tc->ops.program_intf_cmd_cfg = dpu_hw_intf_program_intf_cmd_cfg;\n"
)
if "pushing 24bpp into compressed STREAM0" in text:
    print("program_intf_cmd_cfg already DPU 5+")
elif old not in text:
    raise SystemExit("no program_intf_cmd_cfg needle")
else:
    text = text.replace(old, new, 1)
    changed = True
    print("patched program_intf_cmd_cfg for DPU 5+")

if "cmd_cfg compress=%d widebus=%d cfg2=%#x fmt=" in text:
    print("cmd PANEL_FORMAT already programmed")
elif "dpu intf cmd_cfg compress=" in text:
    old_log = (
        "\tDPU_REG_WRITE(&intf->hw, INTF_CONFIG2, intf_cfg2);\n"
        "\tpr_info_once(\"dpu intf cmd_cfg compress=%d widebus=%d cfg2=%#x\\n\",\n"
        "\t\tcmd_mode_cfg->data_compress, cmd_mode_cfg->wide_bus_en,\n"
        "\t\tintf_cfg2);\n"
        "}\n"
    )
    new_fmt = (
        "\tDPU_REG_WRITE(&intf->hw, INTF_CONFIG2, intf_cfg2);\n"
        "\t{\n"
        "\t\tu32 panel_format = BPC8 | (BPC8 << 2) | (BPC8 << 4) |"
        " (0x21 << 8);\n"
        "\n"
        "\t\tDPU_REG_WRITE(&intf->hw, INTF_PANEL_FORMAT, panel_format);\n"
        "\t\tpr_info_once(\"dpu intf cmd_cfg compress=%d widebus=%d "
        "cfg2=%#x fmt=%#x\\n\",\n"
        "\t\t\tcmd_mode_cfg->data_compress, cmd_mode_cfg->wide_bus_en,\n"
        "\t\t\tintf_cfg2, panel_format);\n"
        "\t}\n"
        "}\n"
    )
    if old_log not in text:
        raise SystemExit("no cmd_cfg log body needle")
    text = text.replace(old_log, new_fmt, 1)
    changed = True
    print("patched cmd INTF_PANEL_FORMAT RGB888")
else:
    old_fn = (
        "\tif (cmd_mode_cfg->wide_bus_en)\n"
        "\t\tintf_cfg2 |= INTF_CFG2_DATABUS_WIDEN;\n"
        "\n"
        "\tDPU_REG_WRITE(&intf->hw, INTF_CONFIG2, intf_cfg2);\n"
        "}\n"
    )
    new_fn = (
        "\tif (cmd_mode_cfg->wide_bus_en)\n"
        "\t\tintf_cfg2 |= INTF_CFG2_DATABUS_WIDEN;\n"
        "\n"
        "\tDPU_REG_WRITE(&intf->hw, INTF_CONFIG2, intf_cfg2);\n"
        "\t{\n"
        "\t\tu32 panel_format = BPC8 | (BPC8 << 2) | (BPC8 << 4) |"
        " (0x21 << 8);\n"
        "\n"
        "\t\tDPU_REG_WRITE(&intf->hw, INTF_PANEL_FORMAT, panel_format);\n"
        "\t\tpr_info_once(\"dpu intf cmd_cfg compress=%d widebus=%d "
        "cfg2=%#x fmt=%#x\\n\",\n"
        "\t\t\tcmd_mode_cfg->data_compress, cmd_mode_cfg->wide_bus_en,\n"
        "\t\t\tintf_cfg2, panel_format);\n"
        "\t}\n"
        "}\n"
    )
    if old_fn not in text:
        raise SystemExit("no program_intf_cmd_cfg body needle")
    text = text.replace(old_fn, new_fn, 1)
    changed = True
    print("patched cmd_cfg log+PANEL_FORMAT")

# Leftover INTF_CONFIG2 BIT(8)=0x100 survived RMW (live cfg2=0x1100 /
# 0x100). Command timing never programs this register on DPU 6, so
# write a clean value instead of OR-ing into reset leftovers.
rmw = "\tu32 intf_cfg2 = DPU_REG_READ(&intf->hw, INTF_CONFIG2);\n"
clean = "\tu32 intf_cfg2 = 0;\n"
if rmw in text:
    text = text.replace(rmw, clean, 1)
    changed = True
    print("INTF_CONFIG2 cmd_cfg starts from 0")
elif clean in text:
    print("INTF_CONFIG2 cmd_cfg already starts from 0")
else:
    raise SystemExit("no INTF_CONFIG2 init needle")

if changed:
    p.write_text(text)
    print("patched dpu_hw_intf.c (cmd DSC compress)")
else:
    print("dpu_hw_intf.c unchanged")
