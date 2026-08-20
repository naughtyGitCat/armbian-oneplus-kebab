#!/usr/bin/env python3
"""Command-mode 6G MDP_CTRL2: set DST_FORMAT2 to RGB888.

dsi_ctrl_cfg() RMW-ORs BURST_MODE onto the reset value and never programs
DST_FORMAT2. Live #23 MDP_CTRL2=0x10006: burst on, DST_FORMAT2=6 (RGB565).
CMD_CFG0 is already RGB888 (8). The MDP stream packer then groups compressed
bytes as 16-bit pixels while STREAM0 hdisp=360 assumes 24 bpp.
Idempotent.
"""
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "/opt/kebab-kernel/linux")
p = root / "drivers/gpu/drm/msm/dsi/dsi_host.c"
text = p.read_text()

old = (
	"\t\tif (cfg_hnd->major == MSM_DSI_VER_MAJOR_6G) {\n"
	"\t\t\tdata = dsi_read(msm_host, REG_DSI_CMD_MODE_MDP_CTRL2);\n"
	"\n"
	"\t\t\tif (cfg_hnd->minor >= MSM_DSI_6G_VER_MINOR_V1_3)\n"
	"\t\t\t\tdata |= DSI_CMD_MODE_MDP_CTRL2_BURST_MODE;\n"
	"\n"
	"\t\t\tif (msm_dsi_host_is_wide_bus_enabled(&msm_host->base))\n"
	"\t\t\t\tdata |= DSI_CMD_MODE_MDP_CTRL2_DATABUS_WIDEN;\n"
	"\n"
	"\t\t\tdsi_write(msm_host, REG_DSI_CMD_MODE_MDP_CTRL2, data);\n"
	"\t\t}\n"
)

new = (
	"\t\tif (cfg_hnd->major == MSM_DSI_VER_MAJOR_6G) {\n"
	"\t\t\tdata = dsi_read(msm_host, REG_DSI_CMD_MODE_MDP_CTRL2);\n"
	"\n"
	"\t\t\t/* Reset leftover DST_FORMAT2=RGB565 (6). STREAM0 is RGB888. */\n"
	"\t\t\tdata &= ~DSI_CMD_MODE_MDP_CTRL2_DST_FORMAT2__MASK;\n"
	"\t\t\tdata |= DSI_CMD_MODE_MDP_CTRL2_DST_FORMAT2(\n"
	"\t\t\t\t\tCMD_DST_FORMAT_RGB888);\n"
	"\n"
	"\t\t\tif (cfg_hnd->minor >= MSM_DSI_6G_VER_MINOR_V1_3)\n"
	"\t\t\t\tdata |= DSI_CMD_MODE_MDP_CTRL2_BURST_MODE;\n"
	"\n"
	"\t\t\tif (msm_dsi_host_is_wide_bus_enabled(&msm_host->base))\n"
	"\t\t\t\tdata |= DSI_CMD_MODE_MDP_CTRL2_DATABUS_WIDEN;\n"
	"\n"
	"\t\t\tdsi_write(msm_host, REG_DSI_CMD_MODE_MDP_CTRL2, data);\n"
	"\t\t\tpr_info_once(\"dsi mdp_ctrl2=%#x burst=%d wide=%d dst2=%u\\n\",\n"
	"\t\t\t\tdata,\n"
	"\t\t\t\t!!(data & DSI_CMD_MODE_MDP_CTRL2_BURST_MODE),\n"
	"\t\t\t\t!!(data & DSI_CMD_MODE_MDP_CTRL2_DATABUS_WIDEN),\n"
	"\t\t\t\tdata & 0xf);\n"
	"\t\t}\n"
)

if "dsi mdp_ctrl2=" in text:
	print("MDP_CTRL2 DST_FORMAT2 already RGB888")
elif old not in text:
	raise SystemExit("no MDP_CTRL2 burst needle")
else:
	p.write_text(text.replace(old, new, 1))
	print("patched MDP_CTRL2 DST_FORMAT2=RGB888")
