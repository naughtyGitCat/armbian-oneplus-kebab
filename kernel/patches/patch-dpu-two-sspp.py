#!/usr/bin/env python3
"""ABL topology: two VIG SSPPs, each mixer gets one pipe.

#35 split 1080 into SmartDMA RECT0+RECT1 on VIG0 (still snow). ABL uses
VIG0+VIG1 as separate SSPPs and CTL_LAYER LM0=VIG0 / LM1=VIG1. Dedicated
primary is VIG0; steal VIG1 as r_pipe (fbdev does not use the overlay).
Idempotent.
"""
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "/opt/kebab-kernel/linux")

plane = root / "drivers/gpu/drm/msm/disp/dpu1/dpu_plane.c"
text = plane.read_text()
if "ABL uses VIG0+VIG1 as separate SSPPs" in text:
    print("two-sspp plane already patched")
else:
    old = (
        "	if (!dpu_plane_try_multirect_parallel(pipe, pipe_cfg, r_pipe, r_pipe_cfg,\n"
        "					      pipe->sspp,\n"
        "					      msm_framebuffer_format(new_plane_state->fb),\n"
        "					      max_linewidth)) {\n"
        "		DPU_DEBUG_PLANE(pdpu, \"invalid \" DRM_RECT_FMT \" /\" DRM_RECT_FMT\n"
        "				\" max_line:%u, can't use split source\\n\",\n"
        "				DRM_RECT_ARG(&pipe_cfg->src_rect),\n"
        "				DRM_RECT_ARG(&r_pipe_cfg->src_rect),\n"
        "				max_linewidth);\n"
        "		return -E2BIG;\n"
        "	}\n"
    )
    new = (
        "	if (drm_rect_width(&r_pipe_cfg->src_rect) != 0 &&\n"
        "	    pdpu->pipe == SSPP_VIG0) {\n"
        "		/* ABL uses VIG0+VIG1 as separate SSPPs, not SmartDMA. */\n"
        "		r_pipe->sspp = dpu_rm_get_sspp(&dpu_kms->rm, SSPP_VIG1);\n"
        "		if (!r_pipe->sspp)\n"
        "			return -ENODEV;\n"
        "		pipe->multirect_index = DPU_SSPP_RECT_SOLO;\n"
        "		pipe->multirect_mode = DPU_SSPP_MULTIRECT_NONE;\n"
        "		r_pipe->multirect_index = DPU_SSPP_RECT_SOLO;\n"
        "		r_pipe->multirect_mode = DPU_SSPP_MULTIRECT_NONE;\n"
        "		pr_info_once(\"dpu dual sspp %d+%d src %d+%d\\n\",\n"
        "			     pipe->sspp->idx, r_pipe->sspp->idx,\n"
        "			     drm_rect_width(&pipe_cfg->src_rect),\n"
        "			     drm_rect_width(&r_pipe_cfg->src_rect));\n"
        "	} else if (!dpu_plane_try_multirect_parallel(pipe, pipe_cfg, r_pipe, r_pipe_cfg,\n"
        "					      pipe->sspp,\n"
        "					      msm_framebuffer_format(new_plane_state->fb),\n"
        "					      max_linewidth)) {\n"
        "		DPU_DEBUG_PLANE(pdpu, \"invalid \" DRM_RECT_FMT \" /\" DRM_RECT_FMT\n"
        "				\" max_line:%u, can't use split source\\n\",\n"
        "				DRM_RECT_ARG(&pipe_cfg->src_rect),\n"
        "				DRM_RECT_ARG(&r_pipe_cfg->src_rect),\n"
        "				max_linewidth);\n"
        "		return -E2BIG;\n"
        "	}\n"
    )
    if old not in text:
        raise SystemExit("no try_multirect_parallel needle")
    plane.write_text(text.replace(old, new, 1))
    print("patched plane two-sspp VIG0+VIG1")

crtc = root / "drivers/gpu/drm/msm/disp/dpu1/dpu_crtc.c"
text = crtc.read_text()
if "ABL: LM0=left SSPP only" in text:
    print("per-mixer CTL_LAYER already patched")
else:
    old = (
        "		if (ctl->ops.setup_blendstage)\n"
        "			ctl->ops.setup_blendstage(ctl, mixer[i].hw_lm->idx,\n"
        "						  &stage_cfg);\n"
        "\n"
        "		if (lm->ops.setup_blendstage)\n"
        "			lm->ops.setup_blendstage(lm, mixer[i].hw_lm->idx,\n"
        "						 &stage_cfg);\n"
    )
    new = (
        "		/* ABL: LM0=left SSPP only, LM1=right SSPP only. */\n"
        "		{\n"
        "			struct dpu_hw_stage_cfg lm_cfg = stage_cfg;\n"
        "			int s;\n"
        "\n"
        "			if (cstate->num_mixers == 2) {\n"
        "				if (i == 0) {\n"
        "					for (s = 0; s < DPU_STAGE_MAX; s++) {\n"
        "						lm_cfg.stage[s][1] = SSPP_NONE;\n"
        "						lm_cfg.multirect_index[s][1] =\n"
        "							DPU_SSPP_RECT_SOLO;\n"
        "					}\n"
        "				} else {\n"
        "					for (s = 0; s < DPU_STAGE_MAX; s++) {\n"
        "						lm_cfg.stage[s][0] = lm_cfg.stage[s][1];\n"
        "						lm_cfg.multirect_index[s][0] =\n"
        "							lm_cfg.multirect_index[s][1];\n"
        "						lm_cfg.stage[s][1] = SSPP_NONE;\n"
        "						lm_cfg.multirect_index[s][1] =\n"
        "							DPU_SSPP_RECT_SOLO;\n"
        "					}\n"
        "				}\n"
        "			}\n"
        "			if (ctl->ops.setup_blendstage)\n"
        "				ctl->ops.setup_blendstage(ctl, mixer[i].hw_lm->idx,\n"
        "							  &lm_cfg);\n"
        "			if (lm->ops.setup_blendstage)\n"
        "				lm->ops.setup_blendstage(lm, mixer[i].hw_lm->idx,\n"
        "							 &lm_cfg);\n"
        "		}\n"
    )
    if old not in text:
        raise SystemExit("no setup_blendstage needle")
    crtc.write_text(text.replace(old, new, 1))
    print("patched crtc per-mixer CTL_LAYER")
