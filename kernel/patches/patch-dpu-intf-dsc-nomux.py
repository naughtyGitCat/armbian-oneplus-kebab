#!/usr/bin/env python3
"""Keep INTF_MUX bound to pingpong even with DSC (do not disconnect).

#24 bound INTF_MUX to PINGPONG_NONE when dsc!=0. Live: mux pp=-1 dsc=0x3,
wait_for_idle -110 storm, dsi_isr idle, status4=0 — DSI starved. Command
mode GRAM kept the previous snow. INTF must stay on PP0; TE is not this
mux. Revert if the force is present. Idempotent.
"""
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "/opt/kebab-kernel/linux")
p = root / "drivers/gpu/drm/msm/disp/dpu1/dpu_encoder_phys_cmd.c"
text = p.read_text()

forced = (
    "\t/* DSC merge feeds INTF via CTL_DSC_ACTIVE. Binding INTF_MUX to\n"
    "\t * PP0 as well can mix uncompressed PP into compressed STREAM0.\n"
    "\t * TE lives on the INTF block (has_intf_te), not this mux.\n"
    "\t */\n"
    "\tif (phys_enc->dpu_kms->catalog->mdss_ver->core_major_ver >= 5 &&\n"
    "\t    phys_enc->hw_intf->ops.bind_pingpong_blk) {\n"
    "\t\tenum dpu_pingpong pp = phys_enc->hw_pp->idx;\n"
    "\n"
    "\t\tif (intf_cfg.dsc)\n"
    "\t\t\tpp = PINGPONG_NONE;\n"
    "\t\tphys_enc->hw_intf->ops.bind_pingpong_blk(phys_enc->hw_intf, pp);\n"
    "\t\tpr_info_once(\"dpu intf mux pp=%d dsc=%#x\\n\",\n"
    "\t\t\t     pp ? (int)(pp - PINGPONG_0) : -1, intf_cfg.dsc);\n"
    "\t}\n"
)
orig = (
    "\t/* setup which pp blk will connect to this intf */\n"
    "\tif (phys_enc->dpu_kms->catalog->mdss_ver->core_major_ver >= 5 &&\n"
    "\t    phys_enc->hw_intf->ops.bind_pingpong_blk)\n"
    "\t\tphys_enc->hw_intf->ops.bind_pingpong_blk(\n"
    "\t\t\t\tphys_enc->hw_intf,\n"
    "\t\t\t\tphys_enc->hw_pp->idx);\n"
)

if "dpu intf mux pp=" in text:
    if forced not in text:
        raise SystemExit("nomux marker without exact body")
    p.write_text(text.replace(forced, orig, 1))
    print("reverted INTF_MUX to always bind pingpong")
elif orig in text:
    print("INTF_MUX already bound to pingpong")
else:
    raise SystemExit("no INTF bind_pingpong needle")
