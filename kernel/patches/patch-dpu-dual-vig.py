#!/usr/bin/env python3
"""Force 1080 plane into dual 540 pipes, matching ABL VIG0+VIG1.

ABL fetch is two 540×2400 crops (VIG0 XY=0, VIG1 XY=0x21c) of a packed
4320-stride fb. Mainline keeps one 1080 VIG and source-splits it onto
both LMs (max_linewidth=4096). Dedicated VIG0 then uses SmartDMA
multirect RECT0+RECT1 for the two 540 halves. Idempotent.
"""
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "/opt/kebab-kernel/linux")
p = root / "drivers/gpu/drm/msm/disp/dpu1/dpu_plane.c"
text = p.read_text()

if "ABL fetch is two 540" in text:
    print("dual 540 split already patched")
    raise SystemExit(0)

old = (
    "	if ((drm_rect_width(&pipe_cfg->src_rect) > max_linewidth) ||\n"
    "	     _dpu_plane_calc_clk(&crtc_state->adjusted_mode, pipe_cfg) > max_mdp_clk_rate) {\n"
    "		if (drm_rect_width(&pipe_cfg->src_rect) > 2 * max_linewidth) {\n"
    "			DPU_DEBUG_PLANE(pdpu, \"invalid src \" DRM_RECT_FMT \" line:%u\\n\",\n"
    "					DRM_RECT_ARG(&pipe_cfg->src_rect), max_linewidth);\n"
    "			return -E2BIG;\n"
    "		}\n"
    "\n"
    "		*r_pipe_cfg = *pipe_cfg;\n"
    "		pipe_cfg->src_rect.x2 = (pipe_cfg->src_rect.x1 + pipe_cfg->src_rect.x2) >> 1;\n"
    "		pipe_cfg->dst_rect.x2 = (pipe_cfg->dst_rect.x1 + pipe_cfg->dst_rect.x2) >> 1;\n"
    "		r_pipe_cfg->src_rect.x1 = pipe_cfg->src_rect.x2;\n"
    "		r_pipe_cfg->dst_rect.x1 = pipe_cfg->dst_rect.x2;\n"
    "	} else {\n"
    "		memset(r_pipe_cfg, 0, sizeof(*r_pipe_cfg));\n"
    "	}\n"
)
new = (
    "	/* ABL fetch is two 540×2400 VIG crops. max_linewidth=4096 would\n"
    "	 * keep a single 1080 SSPP source-split onto the two LMs.\n"
    "	 */\n"
    "	if ((drm_rect_width(&pipe_cfg->src_rect) > 540) ||\n"
    "	    (drm_rect_width(&pipe_cfg->src_rect) > max_linewidth) ||\n"
    "	     _dpu_plane_calc_clk(&crtc_state->adjusted_mode, pipe_cfg) > max_mdp_clk_rate) {\n"
    "		if (drm_rect_width(&pipe_cfg->src_rect) > 2 * max_linewidth) {\n"
    "			DPU_DEBUG_PLANE(pdpu, \"invalid src \" DRM_RECT_FMT \" line:%u\\n\",\n"
    "					DRM_RECT_ARG(&pipe_cfg->src_rect), max_linewidth);\n"
    "			return -E2BIG;\n"
    "		}\n"
    "\n"
    "		*r_pipe_cfg = *pipe_cfg;\n"
    "		pipe_cfg->src_rect.x2 = (pipe_cfg->src_rect.x1 + pipe_cfg->src_rect.x2) >> 1;\n"
    "		pipe_cfg->dst_rect.x2 = (pipe_cfg->dst_rect.x1 + pipe_cfg->dst_rect.x2) >> 1;\n"
    "		r_pipe_cfg->src_rect.x1 = pipe_cfg->src_rect.x2;\n"
    "		r_pipe_cfg->dst_rect.x1 = pipe_cfg->dst_rect.x2;\n"
    "		pr_info_once(\"dpu plane split %dx%d -> %d+%d\\n\",\n"
    "			     drm_rect_width(&fb_rect), drm_rect_height(&pipe_cfg->src_rect),\n"
    "			     drm_rect_width(&pipe_cfg->src_rect),\n"
    "			     drm_rect_width(&r_pipe_cfg->src_rect));\n"
    "	} else {\n"
    "		memset(r_pipe_cfg, 0, sizeof(*r_pipe_cfg));\n"
    "	}\n"
)

if old not in text:
    raise SystemExit("no r_pipe split needle")
p.write_text(text.replace(old, new, 1))
print("patched dual 540 r_pipe split")
