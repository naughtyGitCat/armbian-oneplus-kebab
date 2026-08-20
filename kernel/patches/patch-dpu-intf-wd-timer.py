#!/usr/bin/env python3
"""DPU 5+ DSI INTF: start WD_TIMER_0 when te-source is timer0.

SM8250 is DPU 6. Mainline only assigns dpu_hw_intf_vsync_sel_v8 (the
helper that loads/enables INTF_WD_TIMER_0) for core_major_ver >= 8.
DPU 6 then writes INTF_TEAR_MDP_VSYNC_SEL=15 and never ticks the
timer, so qcom,te-source = "timer0" is a no-op and wait_for_idle
still -110. GPIO TE on gpio66 is pulsing; this is the watchdog
diagnostic. Idempotent.
"""
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "/opt/kebab-kernel/linux")
p = root / "drivers/gpu/drm/msm/disp/dpu1/dpu_hw_intf.c"
text = p.read_text()
changed = False

old = (
    "\t\tif (mdss_rev->core_major_ver >= 8)\n"
    "\t\t\tc->ops.vsync_sel = dpu_hw_intf_vsync_sel_v8;\n"
    "\t\telse\n"
    "\t\t\tc->ops.vsync_sel = dpu_hw_intf_vsync_sel;\n"
)
new = (
    "\t\t/* DPU 5+ DSI INTF has WD_TIMER_0 + TEAR (len 0x2c0).\n"
    "\t\t * v8 helper starts the watchdog; the >=8-only path left\n"
    "\t\t * SM8250 (DPU 6) with VSYNC_SEL=timer0 and no ticks.\n"
    "\t\t */\n"
    "\t\tc->ops.vsync_sel = dpu_hw_intf_vsync_sel_v8;\n"
)
if "SM8250 (DPU 6) with VSYNC_SEL=timer0" in text:
    print("vsync_sel_v8 already used on DPU 5+")
elif old not in text:
    raise SystemExit("no vsync_sel major>=8 needle")
else:
    text = text.replace(old, new, 1)
    changed = True
    print("patched vsync_sel_v8 for DPU 5+")

if changed:
    p.write_text(text)

kms = root / "drivers/gpu/drm/msm/disp/dpu1/dpu_kms.c"
kt = kms.read_text()
if "dpu te-source=" in kt:
    print("te-source log already present")
else:
    needle = (
        "\t\tif (dpu_vsync_sources[i] &&\n"
        "\t\t    !strcmp(dpu_vsync_sources[i], te_source)) {\n"
        "\t\t\tinfo->vsync_source = i;\n"
    )
    # read the actual function to patch after assignment
    oldk = (
        "\tif (!te_source) {\n"
        "\t\tinfo->vsync_source = DPU_VSYNC_SOURCE_GPIO_0;\n"
        "\t\treturn 0;\n"
        "\t}\n"
    )
    if oldk not in kt:
        raise SystemExit("no te_source default needle")
    # log just before return 0 at end of function — find unique trailer
    # Fall back: log after the match loop by replacing the default block
    # and adding a log at both return points via a single pr_info before
    # every return is messy. Patch the function end instead.
    end = (
        "\treturn -EINVAL;\n"
        "}\n"
    )
    # too generic. Insert after vsync_source assigned in the loop — look
    # at following lines.
    idx = kt.find("info->vsync_source = i;")
    if idx < 0:
        raise SystemExit("no vsync_source = i")
    # insert log before the function's success return
    old_ret = (
        "\t\t\tinfo->vsync_source = i;\n"
        "\t\t\treturn 0;\n"
    )
    new_ret = (
        "\t\t\tinfo->vsync_source = i;\n"
        "\t\t\tpr_info(\"dpu te-source=%s vsync_source=%d\\n\",\n"
        "\t\t\t\tte_source, info->vsync_source);\n"
        "\t\t\treturn 0;\n"
    )
    if old_ret not in kt:
        raise SystemExit("no vsync_source return needle")
    kt = kt.replace(old_ret, new_ret, 1)
    kms.write_text(kt)
    print("patched dpu te-source log")
