#!/usr/bin/env python3
"""#64: fix DPU core clk at 460 MHz (SM8250 OPP nom).

dpu_kms_hw_init stores clk_get_rate("core") — 200 MHz at probe — as
max_core_clk_rate, so later opp_set_rate can never climb. ABL-ratio
pclk=bit/6=183 MHz (#8) then MDP-FIFO under-ran. Force FIXED 460 MHz
so DSC/MDP can feed DSI at that pclk. Idempotent.
"""
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "/opt/kebab-kernel/linux")
p = root / "drivers/gpu/drm/msm/disp/dpu1/dpu_core_perf.c"
text = p.read_text()

if "kebab #64: core clk fixed 460 MHz" in text:
    print("DPU core clk already fixed 460 MHz")
    raise SystemExit(0)

old = (
    "\tperf->perf_cfg = perf_cfg;\n"
    "\tperf->max_core_clk_rate = max_core_clk_rate;\n"
    "\n"
    "\treturn 0;\n"
)
new = (
    "\tperf->perf_cfg = perf_cfg;\n"
    "\t/* kebab #64: core clk fixed 460 MHz. Probe rate 200 MHz was the cap. */\n"
    "\tif (max_core_clk_rate < 460000000)\n"
    "\t\tmax_core_clk_rate = 460000000;\n"
    "\tperf->max_core_clk_rate = max_core_clk_rate;\n"
    "\tperf->fix_core_clk_rate = 460000000;\n"
    "\tperf->perf_tune.mode = DPU_PERF_MODE_FIXED;\n"
    "\tpr_info_once(\"dpu core clk fixed 460 MHz (kebab #64)\\n\");\n"
    "\n"
    "\treturn 0;\n"
)
if old not in text:
    raise SystemExit("no dpu_core_perf_init needle")
p.write_text(text.replace(old, new, 1))
print("patched dpu_core_perf.c core clk 460 MHz")
