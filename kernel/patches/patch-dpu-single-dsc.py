#!/usr/bin/env python3
"""2:2:1 DSC merge with full pic_width per engine (CAF).

#5/#13-#17 forced enc_dsc.pic_width = enc_ip_w (540). CAF's
_sde_encoder_dsc_2_lm_2_enc_1_intf programs each engine with the full
ROI pic_width (1080) and only halves width for initial_lines.
#18-#22 1:1:1 unstalls but snows; #22 1-slice PPS proved the panel
honors PPS. Restore vendor 2 DSC + vanilla dsc pointer. Idempotent.
"""
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "/opt/kebab-kernel/linux")
p = root / "drivers/gpu/drm/msm/disp/dpu1/dpu_encoder.c"
text = p.read_text()
changed = False

orig_topo = (
    "\t\tif (topology->num_intf >= 2 || dpu_kms->catalog->dsc_count >= 2)\n"
    "\t\t\ttopology->num_dsc = 2;\n"
    "\t\telse\n"
    "\t\t\ttopology->num_dsc = 1;\n"
)
force1 = (
    "\t\t/* AMB655X: force 1 DSC (1 LM + 1 INTF). 2:2:1 merge still\n"
    "\t\t * FIFO-overflows after INTF compress / widebus / PHY timings.\n"
    "\t\t * Uncompressed 1 LM completes; vendor lists <1 1 1>.\n"
    "\t\t */\n"
    "\t\ttopology->num_dsc = 1;\n"
)
old_force1 = (
    "\t\t/* AMB655X: force 1 DSC (1 LM + 1 INTF). 2 DSC + merge snows\n"
    "\t\t * because each DSC 1.1 engine is programmed with full\n"
    "\t\t * pic_width while each LM only feeds slice_width.\n"
    "\t\t */\n"
    "\t\ttopology->num_dsc = 1;\n"
)

if orig_topo in text:
    print("2-DSC topology already vanilla")
elif force1 in text:
    text = text.replace(force1, orig_topo, 1)
    changed = True
    print("restored vanilla 2-DSC topology")
elif old_force1 in text:
    text = text.replace(old_force1, orig_topo, 1)
    changed = True
    print("restored vanilla 2-DSC topology (old comment)")
else:
    raise SystemExit("no topology num_dsc needle")

logged_full = (
    "\tenc_ip_w = intf_ip_w / num_dsc;\n"
    "\tinitial_lines = dpu_encoder_dsc_initial_line_calc(dsc, enc_ip_w);\n"
    "\n"
    "\tpr_info_once(\"dpu dsc num_dsc=%d mode=%#x enc_ip_w=%d pic=%dx%d hw_pic_w=%d slice=%dx%d count=%d init_lines=%u\\n\",\n"
    "\t\tnum_dsc, dsc_common_mode, enc_ip_w, pic_width, dsc->pic_height,\n"
    "\t\tdsc->pic_width, dsc->slice_width, dsc->slice_height, this_frame_slices,\n"
    "\t\tinitial_lines);\n"
    "\n"
    "\t/* CAF 2:2:1 programs each engine with the full ROI pic_width.\n"
    "\t * enc_ip_w is only for initial_lines. Do not shrink DSC_PICTURE.\n"
    "\t */\n"
    "\tfor (i = 0; i < num_dsc; i++)\n"
    "\t\tdpu_encoder_dsc_pipe_cfg(ctl, hw_dsc[i], hw_pp[i],\n"
    "\t\t\t\t\t dsc, dsc_common_mode, initial_lines);\n"
)

enc_ip_w_loop = (
    "\tenc_ip_w = intf_ip_w / num_dsc;\n"
    "\tinitial_lines = dpu_encoder_dsc_initial_line_calc(dsc, enc_ip_w);\n"
    "\n"
    "\tpr_info_once(\"dpu dsc num_dsc=%d mode=%#x enc_ip_w=%d pic=%dx%d hw_pic_w=%d slice=%dx%d count=%d init_lines=%u\\n\",\n"
    "\t\tnum_dsc, dsc_common_mode, enc_ip_w, pic_width, dsc->pic_height,\n"
    "\t\tenc_ip_w, dsc->slice_width, dsc->slice_height, this_frame_slices,\n"
    "\t\tinitial_lines);\n"
    "\n"
    "\t/* Each DSC 1.1 engine encodes enc_ip_w, not the full panel\n"
    "\t * pic_width. 2:2:1 merge with 1080 programmed into both\n"
    "\t * engines (or 1:1:1 with two soft slices) snows on AMB655X.\n"
    "\t * PPS sent to the panel still uses the full 1080 config.\n"
    "\t */\n"
    "\t{\n"
    "\t\tstruct drm_dsc_config enc_dsc = *dsc;\n"
    "\n"
    "\t\tenc_dsc.pic_width = enc_ip_w;\n"
    "\t\tfor (i = 0; i < num_dsc; i++)\n"
    "\t\t\tdpu_encoder_dsc_pipe_cfg(ctl, hw_dsc[i], hw_pp[i],\n"
    "\t\t\t\t\t\t &enc_dsc, dsc_common_mode,\n"
    "\t\t\t\t\t\t initial_lines);\n"
    "\t}\n"
)

old_loop_logged = (
    "\tenc_ip_w = intf_ip_w / num_dsc;\n"
    "\tinitial_lines = dpu_encoder_dsc_initial_line_calc(dsc, enc_ip_w);\n"
    "\n"
    "\tpr_info(\"dpu dsc num_dsc=%d mode=%#x enc_ip_w=%d pic=%dx%d slice=%dx%d count=%d init_lines=%u\\n\",\n"
    "\t\tnum_dsc, dsc_common_mode, enc_ip_w, pic_width, dsc->pic_height,\n"
    "\t\tdsc->slice_width, dsc->slice_height, this_frame_slices,\n"
    "\t\tinitial_lines);\n"
    "\n"
    "\tfor (i = 0; i < num_dsc; i++)\n"
    "\t\tdpu_encoder_dsc_pipe_cfg(ctl, hw_dsc[i], hw_pp[i],\n"
    "\t\t\t\t\t dsc, dsc_common_mode, initial_lines);\n"
)
old_loop = (
    "\tenc_ip_w = intf_ip_w / num_dsc;\n"
    "\tinitial_lines = dpu_encoder_dsc_initial_line_calc(dsc, enc_ip_w);\n"
    "\n"
    "\tfor (i = 0; i < num_dsc; i++)\n"
    "\t\tdpu_encoder_dsc_pipe_cfg(ctl, hw_dsc[i], hw_pp[i],\n"
    "\t\t\t\t\t dsc, dsc_common_mode, initial_lines);\n"
)

if "enc_ip_w is only for initial_lines" in text:
    print("full pic_width CAF loop already patched")
elif enc_ip_w_loop in text:
    text = text.replace(enc_ip_w_loop, logged_full, 1)
    changed = True
    print("reverted enc_ip_w pic_width; CAF full pic_width")
elif old_loop_logged in text:
    text = text.replace(old_loop_logged, logged_full, 1)
    changed = True
    print("patched prep_dsc (from logged loop)")
elif old_loop in text:
    text = text.replace(old_loop, logged_full, 1)
    changed = True
    print("patched prep_dsc (from vanilla loop)")
else:
    raise SystemExit("no prep_dsc loop needle")

if changed:
    p.write_text(text)
    print("patched dpu_encoder.c (2 DSC + full pic_width)")
else:
    print("dpu_encoder.c unchanged")
