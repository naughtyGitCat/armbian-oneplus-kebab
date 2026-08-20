# QCA6390 Wi-Fi DTB

Stock Armbian kebab DTS (patch `0011` on the sm8250-6.18 / 6.19 branch, d4n1 / Jiali Chen) describes the Wi-Fi PMU as the old `qcom,qca6390` genpd and points several rails at **PM8009 `vreg_s2f_0p95`**.

On this 8T the RPMH cmd-db has `smpa*` / `smpc*` / `ldoa*` / `ldoc*` and **no `smpf*`**. `vreg_s2f_0p95` never comes up, `pwrseq-qcom-wcn` never releases the chip, `ath11k_pci` never binds.

## Local delta

[`dts/patches/0001-sm8250-oneplus-kebab-qca6390-pmu-wifi.patch`](../dts/patches/0001-sm8250-oneplus-kebab-qca6390-pmu-wifi.patch) is the whole change. Apply it with `patch -p1` on a kernel tree (paths are `arch/arm64/boot/dts/qcom/sm8250-oneplus-kebab.dts`).

What it does:

- `qcom,qca6390` → `qcom,qca6390-pmu` so `pwrseq-qcom-wcn` can own the chip
- `vddpmu` / `vddrfa0p95` use `vreg_s6a_0p95` (not PM8009)
- PMU `ldo0`–`ldo9` regulators
- `wlan-enable-gpios` / `bt-enable-gpios` (TLMM 20 / 21)
- drop the PHY `power-domains` consumer of the old genpd
- `&pcieport0 { wifi@0 { compatible = "pci17cb,1101"; … } }`
- Bluetooth takes the PMU LDO supplies; `regulators-0` (PM8009) is `disabled`

Prebuilt DTB: [`dtb/sm8250-oneplus-kebab.dtb`](../dtb/sm8250-oneplus-kebab.dtb).

Userspace that has to load with it is in [`overlay/`](../overlay/):

- `pwrseq-qcom-wcn`, `pci-pwrctrl-pwrseq`, `ath11k_pci` via `modules-load.d`
- `10-wlan.link` so the iface is named `wlan0`

`slpi.mbn` from this board still fails with `-22`. That is unrelated to station Wi-Fi.

## Rebuild

You cannot compile the DTS in this repo by itself — it `#include`s `sm8250.dtsi` and the PMIC dtsi files from the kernel. Either:

- drop `dts/sm8250-oneplus-kebab.dts` into an sm8250 tree and `make dtbs`, or
- take the Armbian DTB and `fdtput` the same nodes (how the first working image was made).

`dispcc` (`clock-controller@af00000`) stays **disabled** in this DTB on
purpose. Linux fbcon is the separate display DTB (`kebab-dsi`). See
[display.md](display.md).
