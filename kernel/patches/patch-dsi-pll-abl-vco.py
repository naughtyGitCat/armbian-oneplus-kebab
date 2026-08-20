#!/usr/bin/env python3
"""#49: revert ABL analog VCO hacks.

#44–#48 tried to stick analog DEC=0x15 / 825.338672 MHz while CCF kept
the working 1.1G byte/pclk pair. Every path that left analog at 825 M
*while clk_pixel 1/1 ran* returned -22 (Power on failed / black).
#46 prepare-only worked only because a later vanilla set_rate wrote
1.1G analog back. #47 analog stuck + same snow with broken dividers.
#48 freeze+recalc-lie: pixel -22, wait_for_idle -110, black.

825 M analog is incompatible with Linux clk_pixel 1/1 of 78.5 MHz.
Restore vanilla set_rate / prepare / recalc so analog follows CCF 1.1G.
Keep ABL PHY timings (not the picture at 1.1G). Idempotent.
"""
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "/opt/kebab-kernel/linux")
p = root / "drivers/gpu/drm/msm/dsi/phy/dsi_phy_7nm.c"
text = p.read_text()

changed = False

# --- prepare: drop analog rewrite ---
old_prep = (
    "\tstruct dsi_pll_7nm *pll_7nm = to_pll_7nm(hw);\n"
    "\tstruct dsi_pll_config config;\n"
    "\tu64 saved;\n"
    "\tint rc;\n"
    "\n"
    "\tdsi_pll_enable_pll_bias(pll_7nm);\n"
    "\tif (pll_7nm->slave)\n"
    "\t\tdsi_pll_enable_pll_bias(pll_7nm->slave);\n"
    "\n"
    "\t/* kebab #46: CCF already accepted 1.1G byte/pclk. Rewrite analog\n"
    "\t * DEC/FRAC to ABL 825.338672 MHz immediately before the PLL starts\n"
    "\t * so clk_pixel 1/1 is not involved. V4.1 inverters follow 825 M.\n"
    "\t */\n"
    "\tsaved = pll_7nm->vco_current_rate;\n"
    "\tpll_7nm->vco_current_rate = 825338672ULL;\n"
    "\tdsi_pll_setup_config(&config);\n"
    "\tdsi_pll_calc_dec_frac(pll_7nm, &config);\n"
    "\tdsi_pll_commit(pll_7nm, &config);\n"
    "\tpll_7nm->vco_current_rate = saved;\n"
    "\tpr_info(\"dsi pll prepare analog ABL VCO 825.338672 MHz (ccf %llu) dec=0x%x frac=0x%x\\n\",\n"
    "\t\tsaved, config.decimal_div_start, config.frac_div_start);\n"
    "\n"
    "\t/* Start PLL */\n"
)
new_prep = (
    "\tstruct dsi_pll_7nm *pll_7nm = to_pll_7nm(hw);\n"
    "\tint rc;\n"
    "\n"
    "\tdsi_pll_enable_pll_bias(pll_7nm);\n"
    "\tif (pll_7nm->slave)\n"
    "\t\tdsi_pll_enable_pll_bias(pll_7nm->slave);\n"
    "\n"
    "\t/* Start PLL */\n"
)
if old_prep in text:
    text = text.replace(old_prep, new_prep, 1)
    changed = True

# --- set_rate: drop skip-analog / re-ABL ---
old_set_48 = (
    "\tstruct dsi_pll_7nm *pll_7nm = to_pll_7nm(hw);\n"
    "\tstruct dsi_pll_config config;\n"
    "\n"
    "\tDBG(\"DSI PLL%d rate=%lu, parent's=%lu\", pll_7nm->phy->id, rate,\n"
    "\t    parent_rate);\n"
    "\n"
    "\tpll_7nm->vco_current_rate = rate;\n"
    "\n"
    "\t/* kebab #48: #47 re-ABL while pll_on made recalc return 825 M and\n"
    "\t * clk_pixel 1/1 miss 78.5 MHz (CLK_CFG0=0x41). Keep analog frozen\n"
    "\t * at prepare's ABL 825 M; CCF still sees 1.1 G via vco_current_rate.\n"
    "\t */\n"
    "\tif (pll_7nm->phy->pll_on) {\n"
    "\t\tpr_info(\"dsi pll set_rate skip analog (pll_on ccf %lu)\\n\", rate);\n"
    "\t\treturn 0;\n"
    "\t}\n"
    "\n"
    "\tdsi_pll_enable_pll_bias(pll_7nm);\n"
    "\n"
    "\tdsi_pll_setup_config(&config);\n"
)
old_set_47 = (
    "\tstruct dsi_pll_7nm *pll_7nm = to_pll_7nm(hw);\n"
    "\tstruct dsi_pll_config config;\n"
    "\tu64 saved;\n"
    "\n"
    "\tdsi_pll_enable_pll_bias(pll_7nm);\n"
    "\tDBG(\"DSI PLL%d rate=%lu, parent's=%lu\", pll_7nm->phy->id, rate,\n"
    "\t    parent_rate);\n"
    "\n"
    "\tpll_7nm->vco_current_rate = rate;\n"
    "\n"
    "\tdsi_pll_setup_config(&config);\n"
)
new_set = (
    "\tstruct dsi_pll_7nm *pll_7nm = to_pll_7nm(hw);\n"
    "\tstruct dsi_pll_config config;\n"
    "\n"
    "\tdsi_pll_enable_pll_bias(pll_7nm);\n"
    "\tDBG(\"DSI PLL%d rate=%lu, parent's=%lu\", pll_7nm->phy->id, rate,\n"
    "\t    parent_rate);\n"
    "\n"
    "\tpll_7nm->vco_current_rate = rate;\n"
    "\n"
    "\tdsi_pll_setup_config(&config);\n"
)
if old_set_48 in text:
    text = text.replace(old_set_48, new_set, 1)
    changed = True
elif old_set_47 in text:
    text = text.replace(old_set_47, new_set, 1)
    changed = True

old_reabl_live = (
    "\tdsi_pll_commit(pll_7nm, &config);\n"
    "\n"
    "\t/* kebab #46 prepare writes ABL analog, then a later set_rate(1.1G)\n"
    "\t * while pll_on overwrote live DEC back to 0x1c. Re-commit ABL after\n"
    "\t * that so 825 M actually sticks. First set_rate (!pll_on) stays\n"
    "\t * vanilla so clk_pixel 1/1 still accepts 78.5 MHz.\n"
    "\t */\n"
    "\tif (pll_7nm->phy->pll_on && rate >= 800000000UL) {\n"
    "\t\tsaved = pll_7nm->vco_current_rate;\n"
    "\t\tpll_7nm->vco_current_rate = 825338672ULL;\n"
    "\t\tdsi_pll_calc_dec_frac(pll_7nm, &config);\n"
    "\t\tdsi_pll_commit(pll_7nm, &config);\n"
    "\t\tpll_7nm->vco_current_rate = saved;\n"
    "\t\tpr_info(\"dsi pll set_rate re-ABL (pll_on ccf %lu) dec=0x%x frac=0x%x\\n\",\n"
    "\t\t\trate, config.decimal_div_start, config.frac_div_start);\n"
    "\t}\n"
    "\n"
    "\tdsi_pll_config_hzindep_reg(pll_7nm);\n"
)
if old_reabl_live in text:
    text = text.replace(
        old_reabl_live,
        "\tdsi_pll_commit(pll_7nm, &config);\n"
        "\n"
        "\tdsi_pll_config_hzindep_reg(pll_7nm);\n",
        1,
    )
    changed = True

# --- recalc: drop CCF lie ---
old_re = (
    "\tu64 pll_freq, tmp64;\n"
    "\n"
    "\t/* kebab #48: analog is ABL 825 M after prepare. Do not overwrite\n"
    "\t * CCF's 1.1 G view or clk_pixel 1/1 misses 78.5 MHz.\n"
    "\t */\n"
    "\tif (pll_7nm->vco_current_rate)\n"
    "\t\treturn (unsigned long)pll_7nm->vco_current_rate;\n"
    "\n"
    "\tdsi_pll_enable_pll_bias(pll_7nm);\n"
    "\tdec = readl(base + REG_DSI_7nm_PHY_PLL_DECIMAL_DIV_START_1);\n"
)
new_re = (
    "\tu64 pll_freq, tmp64;\n"
    "\n"
    "\tdsi_pll_enable_pll_bias(pll_7nm);\n"
    "\tdec = readl(base + REG_DSI_7nm_PHY_PLL_DECIMAL_DIV_START_1);\n"
)
if old_re in text:
    text = text.replace(old_re, new_re, 1)
    changed = True

if "prepare analog ABL" in text or "set_rate skip analog" in text or "set_rate re-ABL" in text:
    raise SystemExit("analog VCO hack still present after revert")

if changed:
    p.write_text(text)
    print("reverted 7nm PLL analog VCO hacks; CCF 1.1G analog restored")
else:
    print("7nm PLL analog VCO already vanilla")
