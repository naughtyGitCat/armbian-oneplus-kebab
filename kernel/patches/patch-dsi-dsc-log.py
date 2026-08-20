#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "/opt/kebab-kernel/linux")
p = root / "drivers/gpu/drm/msm/dsi/dsi_host.c"
text = p.read_text()
changed = False

if "dsi dsc spp=" not in text:
    old = (
        "\tpkt_per_line = slice_per_intf / slice_per_pkt;\n"
        "\tif (!pkt_per_line)\n"
        "\t\tpkt_per_line = 1;\n"
    )
    new = (
        "\tpkt_per_line = slice_per_intf / slice_per_pkt;\n"
        "\tif (!pkt_per_line)\n"
        "\t\tpkt_per_line = 1;\n"
        "\n"
        "\tpr_info(\"dsi dsc spp=%u pkt_per_line=%u bytes_per_pkt=%u eol=%u chunk=%u slices=%u cmd=%d\\n\",\n"
        "\t\tslice_per_pkt, pkt_per_line, bytes_per_pkt, eol_byte_num,\n"
        "\t\tdsc->slice_chunk_size, slice_per_intf, is_cmd_mode);\n"
    )
    if old not in text:
        raise SystemExit("no pkt_per_line needle")
    text = text.replace(old, new, 1)
    changed = True
    print("patched dsi_host.c dsc log")
else:
    print("dsc spp log already present")

if "dsi stream hdisp=" in text:
    print("stream log already present")
else:
    old = (
        "\t\tdsi_write(msm_host, REG_DSI_CMD_MDP_STREAM0_TOTAL,\n"
        "\t\t\tDSI_CMD_MDP_STREAM0_TOTAL_H_TOTAL(hdisplay) |\n"
        "\t\t\tDSI_CMD_MDP_STREAM0_TOTAL_V_TOTAL(mode->vdisplay));\n"
    )
    new = (
        "\t\tdsi_write(msm_host, REG_DSI_CMD_MDP_STREAM0_TOTAL,\n"
        "\t\t\tDSI_CMD_MDP_STREAM0_TOTAL_H_TOTAL(hdisplay) |\n"
        "\t\t\tDSI_CMD_MDP_STREAM0_TOTAL_V_TOTAL(mode->vdisplay));\n"
        "\t\tpr_info_once(\"dsi stream hdisp=%u wc=%u widebus=%d ver=%u.%08x dsc=%d\\n\",\n"
        "\t\t\thdisplay, wc, wide_bus_enabled,\n"
        "\t\t\tmsm_host->cfg_hnd->major, msm_host->cfg_hnd->minor,\n"
        "\t\t\t!!msm_host->dsc);\n"
    )
    if old not in text:
        raise SystemExit("no STREAM0_TOTAL needle")
    text = text.replace(old, new, 1)
    changed = True
    print("patched dsi_host.c stream log")

if changed:
    p.write_text(text)
else:
    print("dsi_host.c unchanged")
