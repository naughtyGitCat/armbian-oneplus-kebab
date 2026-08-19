# Display

`6.18.43-kebab-dsi` plus the display DTB lights the Samsung AMB655X:

| | |
|---|---|
| driver | `panel-samsung-amb655x` bound at `ae94000.dsi.0` |
| KMS | `msm` 1.13 on `ae01000.display-controller` (`card1-DSI-1`) |
| FB | `msmdrmfb` 1080×2400 32 bpp (ABL's simpledrm was 1080×2376) |
| backlight | `/sys/class/backlight/ae94000.dsi.0` DCS raw 0–2047 |
| GPU | still **disabled** (`no GPU device was found`) |

Official Armbian `current` (and the DTB in `dtb/`) still has `&dispcc`
disabled. That probe path is `-110 ETIMEDOUT` on `msm-mdss` and you only get
the bootloader FB via `simpledrm`. Blanking there is `fb0/blank` plus a black
fill — `scripts/kebab-display` still does that, and it also works on `msmdrmfb`.

Boot-time `DSI PLL(0) lock failed` is a warning during PHY probe; DSI still
binds afterwards. Do not treat that as a hang.

## Do not enable only dispcc

Setting `dispcc` to `okay` and rebooting **hangs** the phone (no USB gadget, no
Wi-Fi, no SSH). Likely causes, not fully isolated:

- DPU child re-init tears down the bootloader scanout and nothing puts a picture back
- deferred-probe deadlock: MDSS now waits on DSI PHY clocks that are still disabled
- `dispcc` also lists DP PHY clocks; Type-C QMP PHY (`phy@88e8000`) is disabled (HS-only gadget)

Leave `dispcc` disabled until **all** of these land together: `dispcc` + DSI0 +
PHY + supplies + a real panel driver. Do not treat out-of-tree trees as packaged
in Armbian current.

`&gpu` is also `disabled` in the kebab DTS. That is separate.

## Power key

`pm8941_pwrkey` is `/dev/input/event1`. systemd-logind defaults to
`HandlePowerKey=poweroff`. The overlay sets that to `ignore` and runs
`kebab-powerd`:

| input | action |
|-------|--------|
| short KEY_POWER | `kebab-display toggle` |
| hold 3 s | `systemctl poweroff --force`, then sysrq `o` |
| 5 min idle (screen on) | blank |
| Power + Vol-Up 15–20 s | PMIC hard reset (hardware, always) |

## Downstream panel (what the 8T actually has)

Lineage `android_kernel_oneplus_sm8250` (`lineage-23.2`) describes one panel.
There is no Linux `compatible` in that tree — SDE uses a name string.

| | downstream |
|---|---|
| node | `dsi_oplus20828samsung_amb655x_1080_2400_cmd` |
| name | `samsung amb655x fhd cmd mode dsc dsi panel` |
| vendor | `AMB655X` / `samsung1024` / oplus **20828** |
| mode | command + DSC, 4 lane, 1080×2400, 60/120 Hz (default 120) |
| size | 70 mm × 151 mm |
| backlight | DCS, 1–2047 |

Sources:

- [`dsi-panel-oplus20828-samsung-amb655x-1080-2400-120fps.dtsi`](https://github.com/LineageOS/android_kernel_oneplus_sm8250/blob/lineage-23.2/arch/arm64/boot/dts/vendor/oplus/kebab/dsi-panel-oplus20828-samsung-amb655x-1080-2400-120fps.dtsi)
- [`kona-sde-display.dtsi`](https://github.com/LineageOS/android_kernel_oneplus_sm8250/blob/lineage-23.2/arch/arm64/boot/dts/vendor/oplus/kebab/kona-sde-display.dtsi)

ABL's FB is 1080×2376 (24 px shorter). That is a bootloader crop, not a second panel.

### GPIOs

| function | TLMM | notes |
|---|---|---|
| reset | **75** | sequence `1 / 10 ms / 0 / 1 ms / 1 / 10 ms` |
| TE / vsync | **66** | command-mode tear |
| panel vout enable | **24** | kebab-specific (OP8 uses GPIO 8) |
| AVDD 5.5 V enable | **61** | `regulator-fixed`, boot-on |

### Supplies → Armbian kebab regulator names

| SDE name | downstream label | volts | this DTS |
|---|---|---|---|
| `vddio-supply` | `pm8150_l14` / `L14A` | 1.80 V (max 1.88) | `vreg_l14a_1p8` |
| `vout-supply` | `L2C` / `pm8150a_l2` | 1.20–1.304 V, panel asks 1.28 | `vreg_l2c_1p2` (fixed 1.20 V today) |
| `vdd-supply` | `pm8150a_l11` / `L11C` | 3.104–3.304 V | `vreg_l11c_3p3` (3.296 V, always-on) |
| `avdd-supply` | `display_panel_avdd` | 5.5 V via GPIO 61 | `panel_avdd_5p5` (GPIO 61) in the display DTS |

`lab` / `ibb` tables exist in the same file and are **unused** on this panel.

Downstream `sde_dsi` lists `mdss_dsi0` **and** `mdss_dsi1`. 1080 / 4-lane is a
single DSI; the second set is SDE boilerplate. Mainline only needs `&mdss_dsi0`.

## Existing out-of-tree driver

[Xo666/mainline-instantnoodle `panel-samsung-amb655x.c`](https://github.com/Xo666/mainline-instantnoodle/blob/master/drivers/gpu/drm/panel/panel-samsung-amb655x.c)
is a Caleb Connolly `linux-mdss-dsi-panel-driver-generator` dump of this
panel (1080×2400, DSC 540×30, 70×151 mm, `samsung,amb655x`). That repo's
**board DTS is the OP8** (`samsung,amb655uv01`) — different glass, same GPIO
family. Do not paste the UV01 node onto kebab.

The generated driver only `regulator_bulk_get`s **vddio / vdd / avdd**. It does
not model `vout` / `L2C`. Hold kebab GPIO 24 high with pinctrl (OP8 does that
for GPIO 8) and optionally raise `vreg_l2c_1p2` to 1.28 V.

Reset is `GPIO_ACTIVE_LOW` in that tree. Downstream writes raw 1/0/1 on TLMM 75.

## Kernel + two DTBs

A 6.18.43 tree with every Armbian `sm8250-6.18` patch plus
[`kernel/panel-samsung-amb655x.c`](../kernel/panel-samsung-amb655x.c)
(`CONFIG_DRM_PANEL_SAMSUNG_AMB655X=y`) builds as `6.18.43-kebab-dsi`.
6.18 has no `mipi_dsi_dcs_write_long_multi` — the vendored driver uses
`mipi_dsi_dcs_write_seq_multi`. BTF is off for this bring-up kernel.

`scripts/apply-dsi-to-tree.sh /path/to/linux` drops the driver and the
Wi-Fi DTS. `--enable-display` also writes
[`dts/wip/sm8250-oneplus-kebab-dsi.dts`](../dts/wip/sm8250-oneplus-kebab-dsi.dts):

| node | safe `kebab.dtb` | `kebab-dsi.dtb` |
|---|---|---|
| `&dispcc` | disabled | okay |
| `&mdss` | okay | okay |
| `&mdss_dsi0` + panel `samsung,amb655x` | absent | okay |
| `&mdss_dsi0_phy` | disabled | okay |
| `&mdss_dsi1` / PHY / DP / `&gpu` | disabled | disabled |

`zz-update-abl-kernel` always appends `sm8250-oneplus-kebab.dtb` and `dd`s
`boot_a`. Pack the display image with
[`scripts/pack-abl-boot.sh`](../scripts/pack-abl-boot.sh) instead.

Stage A (new kernel + safe DTB) then Stage B (same kernel + display DTB)
both booted. Wi-Fi and the Type-C gadget survived Stage B. Roll back with
`pack-abl-boot.sh safe --flash` or the last known-good `boot_a` image.
Power + Vol-Up 15–20 s is the PMIC hard reset if the SoC is wedged.

The shipped `dtb/sm8250-oneplus-kebab.dtb` stays `dispcc` disabled so a
stock Armbian image still boots. The panel fragment sketch is
[`dts/wip/sm8250-oneplus-kebab-panel.dtsi`](../dts/wip/sm8250-oneplus-kebab-panel.dtsi).
