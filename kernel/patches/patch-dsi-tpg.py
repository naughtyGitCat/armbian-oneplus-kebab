#!/usr/bin/env python3
"""Retrigger command-mode DSI TPG so the panel GRAM holds a checkerboard.

TPG bypasses DPU/INTF and feeds the DSI packer. Command mode only emits one
frame per SW_TRIGGER; DPU kickoff would overwrite it, so retrigger while the
host is enabled. Pair with AMB655X_UNCOMPRESSED_DIAG=1 — compression-on TPG
sends RGB through the DSC packer and snows. Idempotent.
"""
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "/opt/kebab-kernel/linux")
p = root / "drivers/gpu/drm/msm/dsi/dsi_host.c"
text = p.read_text()

if "kebab cmd tpg retrigger" in text:
    print("dsi TPG retrigger already patched")
    raise SystemExit(0)

helpers = (
    "/* kebab cmd tpg retrigger: DPU would overwrite a single SW_TRIGGER. */\n"
    "static struct msm_dsi_host *kebab_tpg_host;\n"
    "static void kebab_tpg_fn(struct work_struct *work);\n"
    "static DECLARE_DELAYED_WORK(kebab_tpg_work, kebab_tpg_fn);\n"
    "\n"
    "static void kebab_tpg_fn(struct work_struct *work)\n"
    "{\n"
    "\tstruct msm_dsi_host *h = READ_ONCE(kebab_tpg_host);\n"
    "\n"
    "\tif (!h || !h->enabled)\n"
    "\t\treturn;\n"
    "\tmsm_dsi_host_test_pattern_en(&h->base);\n"
    "\tschedule_delayed_work(&kebab_tpg_work, msecs_to_jiffies(100));\n"
    "}\n"
    "\n"
    "static void kebab_tpg_start(struct msm_dsi_host *msm_host)\n"
    "{\n"
    "\tWRITE_ONCE(kebab_tpg_host, msm_host);\n"
    "\tmsm_dsi_host_test_pattern_en(&msm_host->base);\n"
    "\tpr_info_once(\"dsi tpg enabled (cmd checkered)\\n\");\n"
    "\tschedule_delayed_work(&kebab_tpg_work, msecs_to_jiffies(100));\n"
    "}\n"
    "\n"
    "static void kebab_tpg_stop(void)\n"
    "{\n"
    "\tWRITE_ONCE(kebab_tpg_host, NULL);\n"
    "\tcancel_delayed_work_sync(&kebab_tpg_work);\n"
    "}\n"
    "\n"
)

anchor = "int msm_dsi_host_enable(struct mipi_dsi_host *host)\n"
old_en = (
    "\tmsm_host->enabled = true;\n"
    "\treturn 0;\n"
    "}\n"
    "\n"
    "int msm_dsi_host_disable(struct mipi_dsi_host *host)\n"
)
new_en = (
    "\tmsm_host->enabled = true;\n"
    "\tkebab_tpg_start(msm_host);\n"
    "\treturn 0;\n"
    "}\n"
    "\n"
    "int msm_dsi_host_disable(struct mipi_dsi_host *host)\n"
)
old_dis = (
    "\tmsm_host->enabled = false;\n"
    "\tdsi_op_mode_config(msm_host,\n"
)
new_dis = (
    "\tmsm_host->enabled = false;\n"
    "\tkebab_tpg_stop();\n"
    "\tdsi_op_mode_config(msm_host,\n"
)

if anchor not in text:
    raise SystemExit("no msm_dsi_host_enable needle")
if old_en not in text:
    raise SystemExit("no host_enable return needle")
if old_dis not in text:
    raise SystemExit("no host_disable needle")

text = text.replace(anchor, helpers + anchor, 1)
text = text.replace(old_en, new_en, 1)
text = text.replace(old_dis, new_dis, 1)
p.write_text(text)
print("patched dsi_host.c with kebab cmd TPG retrigger")
