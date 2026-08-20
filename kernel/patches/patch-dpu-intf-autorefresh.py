#!/usr/bin/env python3
"""#56: ABL INTF tearcheck (AUTOREFRESH + HEIGHT + thresh + WR_PTR_IRQ).

ABL (readable console):
  INTF_TEAR_AUTOREFRESH 0x2B4 = 0x80000001
  INTF_TEAR_HEIGHT      0x28C = 0xffff
  INTF_TEAR_THRESH      0x29C = 0x00050004  (start=5, continue=4)
  INTF_TEAR_WR_PTR_IRQ  0x2A8 = 1

Linux #55 (snow):
  AUTOREFRESH = 0  (enable_te always calls disable_autorefresh)
  HEIGHT      = 0x12e0  (vtotal*2)
  THRESH      = 0x00040004  (start=4)
  WR_PTR_IRQ  = 0  (never written)

Keep TEAR_VSEL=timer0 (0xf). ABL VSEL=0 is gpio66 TE and historically
stalled wait_for_idle.

#56 live: AUTOREFRESH/HEIGHT/WR_PTR matched ABL; webcam still snow;
wait_for_idle -110 came back. Reverted. Do not invoke from
apply-dsi-to-tree.sh. Idempotent if re-run by hand.
"""
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "/opt/kebab-kernel/linux")

intf = root / "drivers/gpu/drm/msm/disp/dpu1/dpu_hw_intf.c"
text = intf.read_text()
changed = False

if "kebab #56: ABL AUTOREFRESH" in text:
    print("dpu_hw_intf already ABL autorefresh")
else:
    old_ar = (
        "static void dpu_hw_intf_disable_autorefresh(struct dpu_hw_intf *intf,\n"
        "\t\t\t\t\t    uint32_t encoder_id, u16 vdisplay)\n"
        "{\n"
        "\tstruct dpu_hw_pp_vsync_info info;\n"
        "\tint trial = 0;\n"
        "\n"
        "\t/* If autorefresh is already disabled, we have nothing to do */\n"
        "\tif (!dpu_hw_intf_get_autorefresh_config(intf, NULL))\n"
        "\t\treturn;\n"
        "\n"
        "\t/*\n"
        "\t * If autorefresh is enabled, disable it and make sure it is safe to\n"
        "\t * proceed with current frame commit/push. Sequence followed is,\n"
        "\t * 1. Disable TE\n"
        "\t * 2. Disable autorefresh config\n"
        "\t * 4. Poll for frame transfer ongoing to be false\n"
        "\t * 5. Enable TE back\n"
        "\t */\n"
        "\n"
        "\tdpu_hw_intf_connect_external_te(intf, false);\n"
        "\tdpu_hw_intf_setup_autorefresh_config(intf, 0, false);\n"
        "\n"
        "\tdo {\n"
        "\t\tudelay(DPU_ENC_MAX_POLL_TIMEOUT_US);\n"
        "\t\tif ((trial * DPU_ENC_MAX_POLL_TIMEOUT_US)\n"
        "\t\t\t\t> (KICKOFF_TIMEOUT_MS * USEC_PER_MSEC)) {\n"
        "\t\t\tDPU_ERROR(\"enc%d intf%d disable autorefresh failed\\n\",\n"
        "\t\t\t\t  encoder_id, intf->idx - INTF_0);\n"
        "\t\t\tbreak;\n"
        "\t\t}\n"
        "\n"
        "\t\ttrial++;\n"
        "\n"
        "\t\tdpu_hw_intf_get_vsync_info(intf, &info);\n"
        "\t} while (info.wr_ptr_line_count > 0 &&\n"
        "\t\t info.wr_ptr_line_count < vdisplay);\n"
        "\n"
        "\tdpu_hw_intf_connect_external_te(intf, true);\n"
        "\n"
        "\tDPU_DEBUG(\"enc%d intf%d disabled autorefresh\\n\",\n"
        "\t\t  encoder_id, intf->idx - INTF_0);\n"
        "\n"
        "}\n"
    )
    new_ar = (
        "static void dpu_hw_intf_disable_autorefresh(struct dpu_hw_intf *intf,\n"
        "\t\t\t\t\t    uint32_t encoder_id, u16 vdisplay)\n"
        "{\n"
        "\t/* kebab #56: ABL AUTOREFRESH=0x80000001. Linux enable_te always\n"
        "\t * disabled it. Keep frame_count=1 so INTF retriggers scanout.\n"
        "\t */\n"
        "\t(void)encoder_id;\n"
        "\t(void)vdisplay;\n"
        "\tdpu_hw_intf_setup_autorefresh_config(intf, 1, true);\n"
        "\tpr_info_once(\"dpu intf autorefresh=0x80000001 (ABL)\\n\");\n"
        "}\n"
    )
    if old_ar not in text:
        raise SystemExit("no disable_autorefresh needle")
    text = text.replace(old_ar, new_ar, 1)
    changed = True
    print("patched disable_autorefresh -> enable 0x80000001")

if "kebab #56: ABL WR_PTR_IRQ" in text:
    print("WR_PTR_IRQ already written")
else:
    old_wr = (
        "\tDPU_REG_WRITE(c, INTF_TEAR_RD_PTR_IRQ, te->rd_ptr_irq);\n"
        "\tDPU_REG_WRITE(c, INTF_TEAR_START_POS, te->start_pos);\n"
    )
    new_wr = (
        "\tDPU_REG_WRITE(c, INTF_TEAR_RD_PTR_IRQ, te->rd_ptr_irq);\n"
        "\t/* kebab #56: ABL WR_PTR_IRQ=1. Linux never programmed it. */\n"
        "\tDPU_REG_WRITE(c, INTF_TEAR_WR_PTR_IRQ, 1);\n"
        "\tDPU_REG_WRITE(c, INTF_TEAR_START_POS, te->start_pos);\n"
    )
    if old_wr not in text:
        raise SystemExit("no RD_PTR_IRQ needle")
    text = text.replace(old_wr, new_wr, 1)
    changed = True
    print("patched WR_PTR_IRQ=1")

if changed:
    intf.write_text(text)

cmd = root / "drivers/gpu/drm/msm/disp/dpu1/dpu_encoder_phys_cmd.c"
ct = cmd.read_text()
if "kebab #56: ABL tear height" in ct:
    print("tearcheck_config already ABL height/thresh")
else:
    old_tc = (
        "\ttc_cfg.hw_vsync_mode = 1;\n"
        "\ttc_cfg.sync_cfg_height = mode->vtotal * 2;\n"
        "\ttc_cfg.vsync_init_val = mode->vdisplay;\n"
        "\ttc_cfg.sync_threshold_start = DEFAULT_TEARCHECK_SYNC_THRESH_START;\n"
    )
    new_tc = (
        "\ttc_cfg.hw_vsync_mode = 1;\n"
        "\t/* kebab #56: ABL HEIGHT=0xffff THRESH start=5. Linux used\n"
        "\t * vtotal*2 (0x12e0) and start=4.\n"
        "\t */\n"
        "\ttc_cfg.sync_cfg_height = 0xffff;\n"
        "\ttc_cfg.vsync_init_val = mode->vdisplay;\n"
        "\ttc_cfg.sync_threshold_start = 5;\n"
        "\tpr_info_once(\"dpu tearcheck height=0xffff start=5 (ABL)\\n\");\n"
    )
    if old_tc not in ct:
        raise SystemExit("no tearcheck_config needle")
    cmd.write_text(ct.replace(old_tc, new_tc, 1))
    print("patched tearcheck height=0xffff start=5")
