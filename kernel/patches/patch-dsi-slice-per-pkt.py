from pathlib import Path

import sys
root = Path(sys.argv[1] if len(sys.argv) > 1 else "/opt/kebab-kernel/linux")
p = root / "drivers/gpu/drm/msm/dsi/dsi_host.c"
text = p.read_text()
if "dsi_get_slice_per_pkt" in text:
    print("already patched")
    raise SystemExit(0)

helper = """
/* Mainline has no slice_per_pkt on mipi_dsi_device yet. Dual-slice
 * command-mode DSC panels (AMB655X: 2 x 540) need two slices in one
 * DCS long write; spp=1 produces full-screen snow.
 */
static unsigned int dsi_get_slice_per_pkt(const struct drm_dsc_config *dsc,
					  bool is_cmd_mode)
{
	if (is_cmd_mode && dsc && dsc->slice_count == 2)
		return 2;
	return 1;
}

"""

needle = "static void dsi_update_dsc_timing(struct msm_dsi_host *msm_host, bool is_cmd_mode)\n"
if needle not in text:
    raise SystemExit("no dsi_update_dsc_timing needle")
text = text.replace(needle, helper + needle, 1)

old_body = """	u32 pkt_per_line;
	u32 eol_byte_num;
	u32 bytes_per_pkt;

	/* first calculate dsc parameters and then program
	 * compress mode registers
	 */
	slice_per_intf = dsc->slice_count;

	total_bytes_per_intf = dsc->slice_chunk_size * slice_per_intf;
	bytes_per_pkt = dsc->slice_chunk_size; /* * slice_per_pkt; */

	eol_byte_num = total_bytes_per_intf % 3;

	/*
	 * Typically, pkt_per_line = slice_per_intf * slice_per_pkt.
	 *
	 * Since the current driver only supports slice_per_pkt = 1,
	 * pkt_per_line will be equal to slice per intf for now.
	 */
	pkt_per_line = slice_per_intf;
"""
new_body = """	u32 pkt_per_line;
	u32 eol_byte_num;
	u32 bytes_per_pkt;
	unsigned int slice_per_pkt = dsi_get_slice_per_pkt(dsc, is_cmd_mode);

	/* first calculate dsc parameters and then program
	 * compress mode registers
	 */
	slice_per_intf = dsc->slice_count;

	total_bytes_per_intf = dsc->slice_chunk_size * slice_per_intf;
	bytes_per_pkt = dsc->slice_chunk_size * slice_per_pkt;

	eol_byte_num = total_bytes_per_intf % 3;

	/* pkt_per_line = slice_per_intf / slice_per_pkt (1, 2 or 4). */
	pkt_per_line = slice_per_intf / slice_per_pkt;
	if (!pkt_per_line)
		pkt_per_line = 1;
"""
if old_body not in text:
    raise SystemExit("no timing body needle")
text = text.replace(old_body, new_body, 1)

old_wc = """			/*
			 * When DSC is enabled, WC = slice_chunk_size * slice_per_pkt + 1.
			 * Currently, the driver only supports default value of slice_per_pkt = 1
			 *
			 * TODO: Expand mipi_dsi_device struct to hold slice_per_pkt info
			 *       and adjust DSC math to account for slice_per_pkt.
			 */
			wc = msm_host->dsc->slice_chunk_size + 1;
"""
new_wc = """			wc = msm_host->dsc->slice_chunk_size *
			     dsi_get_slice_per_pkt(msm_host->dsc, true) + 1;
"""
if old_wc not in text:
    raise SystemExit("no wc needle")
text = text.replace(old_wc, new_wc, 1)
p.write_text(text)
print("patched dsi_host.c")
print("slice_per_pkt refs:", text.count("dsi_get_slice_per_pkt"))
