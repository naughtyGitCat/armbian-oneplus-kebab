#!/usr/bin/env bash
# Drop the AMB655X panel driver + kebab Wi-Fi DTS + optional display
# enablement onto an already-patched linux tree (6.18 + Armbian sm8250-6.18).
#
# Usage:
#   scripts/apply-dsi-to-tree.sh /path/to/linux [--enable-display]
set -euo pipefail

root=$(cd "$(dirname "$0")/.." && pwd)
tree=${1:?linux tree}
shift || true
enable_display=0
for arg in "$@"; do
	case "$arg" in
	--enable-display) enable_display=1 ;;
	*) echo "unknown arg: $arg" >&2; exit 2 ;;
	esac
done

[ -f "$tree/Makefile" ] || { echo "not a kernel tree: $tree" >&2; exit 1; }

cp "$root/kernel/panel-samsung-amb655x.c" \
	"$tree/drivers/gpu/drm/panel/panel-samsung-amb655x.c"

python3 "$root/kernel/patches/patch-dsi-slice-per-pkt.py" "$tree"
python3 "$root/kernel/patches/patch-dpu-single-dsc.py" "$tree"
python3 "$root/kernel/patches/patch-dsi-dsc-log.py" "$tree"
python3 "$root/kernel/patches/patch-dsi-cmd-hs-clock.py" "$tree"
python3 "$root/kernel/patches/patch-dsi-mdp-dstfmt.py" "$tree"
python3 "$root/kernel/patches/patch-dpu-intf-wd-timer.py" "$tree"
python3 "$root/kernel/patches/patch-dpu-intf-cmd-dsc.py" "$tree"
python3 "$root/kernel/patches/patch-dpu-intf-dsc-nomux.py" "$tree"
python3 "$root/kernel/patches/patch-dsi-widebus.py" "$tree"
python3 "$root/kernel/patches/patch-dsi-phy-timing.py" "$tree"
	python3 "$root/kernel/patches/patch-dsi-clkout-abl.py" "$tree"
	python3 "$root/kernel/patches/patch-dsi-trig-abl.py" "$tree"
	python3 "$root/kernel/patches/patch-dsi-phy-lane-ctrl1.py" "$tree"
	python3 "$root/kernel/patches/patch-dsi-lane-force-abl.py" "$tree"
	python3 "$root/kernel/patches/patch-dsi-tpg-off-abl.py" "$tree"
	python3 "$root/kernel/patches/patch-dsi-hs-timer-abl.py" "$tree"
		python3 "$root/kernel/patches/patch-dsi-err-mask-abl.py" "$tree"
		python3 "$root/kernel/patches/patch-dsi-pclk-div6.py" "$tree"
		python3 "$root/kernel/patches/patch-dpu-mdp-460.py" "$tree"
		python3 "$root/kernel/patches/patch-dsi-phy-hstx.py" "$tree"
	python3 "$root/kernel/patches/patch-dpu-intf-cfg2-abl.py" "$tree"
	python3 "$root/kernel/patches/patch-dpu-intf-mux-clean.py" "$tree"
	python3 "$root/kernel/patches/patch-dsi-cmd-comp-clean.py" "$tree"
	python3 "$root/kernel/patches/patch-dsi-cmd-interleave.py" "$tree"
	python3 "$root/kernel/patches/patch-msm-packed-pitch.py" "$tree"
	python3 "$root/kernel/patches/patch-dpu-dual-vig.py" "$tree"
	python3 "$root/kernel/patches/patch-dpu-two-sspp.py" "$tree"
	python3 "$root/kernel/patches/patch-dsi-mdp-dstfmt-abl.py" "$tree"
	python3 "$root/kernel/patches/patch-dpu-revert-solid-fill.py" "$tree"
	python3 "$root/kernel/patches/patch-dpu-pp-dsc-endian.py" "$tree"
	python3 "$root/kernel/patches/patch-dsi-abl-byteclk.py" "$tree"
	python3 "$root/kernel/patches/patch-dsi-pll-abl-vco.py" "$tree"
	python3 "$root/kernel/patches/patch-dpu-lm-blend-abl.py" "$tree"
	python3 "$root/kernel/patches/patch-dpu-ctl-mix-abl.py" "$tree"

	python3 - "$tree" <<'PY'
import pathlib, sys
tree = pathlib.Path(sys.argv[1])

mk = tree / "drivers/gpu/drm/panel/Makefile"
text = mk.read_text()
line = "obj-$(CONFIG_DRM_PANEL_SAMSUNG_AMB655X) += panel-samsung-amb655x.o\n"
if "DRM_PANEL_SAMSUNG_AMB655X" not in text:
    needle = "obj-$(CONFIG_DRM_PANEL_SAMSUNG_AMS581VF01)"
    if needle not in text:
        raise SystemExit("Makefile: no AMS581VF01 anchor")
    text = text.replace(needle, line + needle, 1)
    mk.write_text(text)
    print("Makefile: inserted AMB655X")
else:
    print("Makefile: already has AMB655X")

kc = tree / "drivers/gpu/drm/panel/Kconfig"
text = kc.read_text()
block = """
config DRM_PANEL_SAMSUNG_AMB655X
	tristate "Samsung AMB655X DSI command-mode panel"
	depends on OF
	depends on DRM_MIPI_DSI
	depends on BACKLIGHT_CLASS_DEVICE
	select DRM_DISPLAY_DSC_HELPER
	help
	  Samsung AMB655X 1080x2400 DSC AMOLED used on the OnePlus 8T
	  (kebab / oplus20828). Compatible: samsung,amb655x.

"""
if "DRM_PANEL_SAMSUNG_AMB655X" not in text:
    needle = "config DRM_PANEL_SAMSUNG_AMS581VF01"
    if needle not in text:
        raise SystemExit("Kconfig: no AMS581VF01 anchor")
    text = text.replace(needle, block + needle, 1)
    kc.write_text(text)
    print("Kconfig: inserted AMB655X")
else:
    print("Kconfig: already has AMB655X")
PY

dst="$tree/arch/arm64/boot/dts/qcom/sm8250-oneplus-kebab.dts"
cp "$root/dts/sm8250-oneplus-kebab.dts" "$dst"
echo "installed wifi kebab DTS (dispcc still disabled)"

if grep -q 'sm8250-oneplus-kebab.dtb' \
	"$tree/arch/arm64/boot/dts/qcom/Makefile"; then
	echo "dtb already in Makefile"
else
	echo "WARNING: sm8250-oneplus-kebab.dtb missing from qcom/Makefile" >&2
fi

if [ "$enable_display" -eq 1 ]; then
	dsi_dts="$tree/arch/arm64/boot/dts/qcom/sm8250-oneplus-kebab-dsi.dts"
	cp "$dst" "$dsi_dts"
	python3 - "$dsi_dts" <<'PY'
from pathlib import Path
import sys
p = Path(sys.argv[1])
text = p.read_text()

avdd = '''
	panel_avdd_5p5: regulator-panel-avdd {
		compatible = "regulator-fixed";
		regulator-name = "panel_avdd_5p5";
		regulator-min-microvolt = <5500000>;
		regulator-max-microvolt = <5500000>;
		regulator-enable-ramp-delay = <233>;
		gpio = <&tlmm 61 GPIO_ACTIVE_HIGH>;
		enable-active-high;
		regulator-boot-on;
		pinctrl-names = "default";
		pinctrl-0 = <&panel_avdd_pins>;
	};

'''
if "panel_avdd_5p5" not in text:
    needle = "\t/* QCA6390 PMU:"
    if needle not in text:
        raise SystemExit("no QCA6390 PMU anchor for avdd")
    text = text.replace(needle, avdd + needle, 1)

text = text.replace(
    "&dispcc {\n       status = \"disabled\";\n};",
    "&dispcc {\n       status = \"okay\";\n};",
    1,
)

if "&pm8150b_charger" not in text:
    text = text.replace(
        "&gpu {\n\tstatus = \"disabled\";\n};",
        "&gpu {\n\tstatus = \"disabled\";\n};\n\n"
        "/*\n"
        " * Main USB CC-CV charger. typec / vbus / fg stay disabled — charger\n"
        " * probe still writes TYPE_C_MODE_CFG TRY_SNK (gadget risk). 8 Pro\n"
        " * enables charger+typec+vbus together; this is the smaller hop.\n"
        " */\n"
        "&pm8150b_charger {\n"
        "\tstatus = \"okay\";\n"
        "\tmonitored-battery = <&battery>;\n"
        "};",
        1,
    )

dsi = '''
&mdss_dsi0 {
	vdda-supply = <&vreg_l9a_1p2>;
	status = "okay";

	display_panel: panel@0 {
		compatible = "samsung,amb655x";
		reg = <0>;

		vddio-supply = <&vreg_l14a_1p8>;
		vdd-supply = <&vreg_l11c_3p3>;
		avdd-supply = <&panel_avdd_5p5>;

		reset-gpios = <&tlmm 75 GPIO_ACTIVE_LOW>;

		pinctrl-names = "default";
		pinctrl-0 = <&panel_reset_pins &panel_vsync_pins &panel_vout_pins>;

		status = "okay";

		port {
			panel_in_0: endpoint {
				remote-endpoint = <&mdss_dsi0_out>;
			};
		};
	};
};

&mdss_dsi0_out {
	data-lanes = <0 1 2 3>;
	remote-endpoint = <&panel_in_0>;
	/* #10 vsync_p and #11 vsync_s both left wait_for_idle -110.
	 * Watchdog TE isolates gpio66 from scanout/DSC/PHY. */
	qcom,te-source = "timer0";
};

&mdss_dsi0_phy {
	vdds-supply = <&vreg_l5a_0p88>;
	status = "okay";
};

'''
if "&mdss_dsi0 {" not in text:
    needle = "&mdss {\n\tstatus = \"okay\";\n};"
    if needle not in text:
        raise SystemExit("no &mdss okay anchor")
    text = text.replace(needle, needle + "\n" + dsi, 1)

# &tlmm children are one-tab (see bt_en_active / ts_rst_suspend).
pins = '''
	panel_reset_pins: panel-reset-state {
		pins = "gpio75";
		function = "gpio";
		drive-strength = <8>;
		bias-disable;
	};

	panel_vsync_pins: panel-vsync-state {
		pins = "gpio66";
		function = "mdp_vsync";
		drive-strength = <16>;
		bias-pull-down;
	};

	/* kebab vout load-switch; OP8 uses gpio8 for the same job */
	panel_vout_pins: panel-vout-state {
		pins = "gpio24";
		function = "gpio";
		drive-strength = <8>;
		output-high;
	};

	panel_avdd_pins: panel-avdd-state {
		pins = "gpio61";
		function = "gpio";
		drive-strength = <8>;
		output-high;
	};

'''
if "panel_reset_pins:" not in text:
    needle = "\tts_rst_suspend: ts-rst-suspend {"
    if needle not in text:
        raise SystemExit("no ts_rst_suspend definition")
    text = text.replace(needle, pins + needle, 1)

p.write_text(text)
print("display chain enabled in kebab-dsi DTS (gpu/dsi1/dp still off, SMB5 on)")
PY
	python3 - "$tree/arch/arm64/boot/dts/qcom/Makefile" <<'PY'
from pathlib import Path
import sys
p = Path(sys.argv[1])
t = p.read_text()
if "sm8250-oneplus-kebab-dsi.dtb" not in t:
    t = t.replace(
        "sm8250-oneplus-kebab.dtb",
        "sm8250-oneplus-kebab.dtb sm8250-oneplus-kebab-dsi.dtb",
        1,
    )
    p.write_text(t)
    print("Makefile: added kebab-dsi.dtb")
else:
    print("Makefile: kebab-dsi.dtb already listed")
PY
fi

echo "apply-dsi-to-tree: done"
