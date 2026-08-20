#!/usr/bin/env python3
"""Keep SM8250 on mainline's v2.5 widebus gate (do not force 6G).

#16 forced widebus for any 6G+dsc. Live: STREAM0 hdisp=180, cfg2=0x1101,
still status=4 + wait_for_idle, same fine snow as 1ppc. Lineage kebab
has no qcom,mdss-dsi-widebus-mode. Revert if the force is present.
Idempotent.
"""
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "/opt/kebab-kernel/linux")
p = root / "drivers/gpu/drm/msm/dsi/dsi_host.c"
text = p.read_text()

forced = (
    "\t/* SM8250 is 6G v2.4.0; mainline gates widebus at v2.5.\n"
    "\t * 1ppc command-mode DSC stalls the packer (FIFO status=4).\n"
    "\t */\n"
    "\treturn msm_host->dsc &&\n"
    "\t\t(msm_host->cfg_hnd->major == MSM_DSI_VER_MAJOR_6G);\n"
)
orig = (
    "\treturn msm_host->dsc &&\n"
    "\t\t(msm_host->cfg_hnd->major == MSM_DSI_VER_MAJOR_6G &&\n"
    "\t\t msm_host->cfg_hnd->minor >= MSM_DSI_6G_VER_MINOR_V2_5_0);\n"
)

if "1ppc command-mode DSC stalls the packer" in text:
    if forced not in text:
        raise SystemExit("widebus force marker without exact body")
    p.write_text(text.replace(forced, orig, 1))
    print("reverted msm_dsi_host_is_wide_bus_enabled to v2.5 gate")
elif orig in text:
    print("widebus already v2.5-gated")
else:
    raise SystemExit("no widebus version-gate needle")
