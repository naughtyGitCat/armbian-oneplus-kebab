# armbian-oneplus-kebab

Notes, a QCA6390 device-tree delta, and a small userspace overlay for
[Armbian](https://github.com/armbian/build) on the **OnePlus 8T** (`kebab`,
SM8250). Official board support is [`oneplus-kebab.conf`](https://github.com/armbian/build/blob/main/config/boards/oneplus-kebab.conf)
(amazingfate). This repository is the leftover bring-up that is not upstream yet.

[![secret-scan](https://github.com/naughtyGitCat/armbian-oneplus-kebab/actions/workflows/secret-scan.yml/badge.svg)](https://github.com/naughtyGitCat/armbian-oneplus-kebab/actions/workflows/secret-scan.yml)
[![watch-armbian](https://github.com/naughtyGitCat/armbian-oneplus-kebab/actions/workflows/watch-armbian.yml/badge.svg)](https://github.com/naughtyGitCat/armbian-oneplus-kebab/actions/workflows/watch-armbian.yml)

## Status

| piece | state |
|-------|--------|
| Armbian trixie / kernel 6.18 `current` | boots from `boot_a` |
| USB Type-C gadget (NCM, `172.16.42.1`) | works (`usb_1` / `a600000`, HS only). May not re-enumerate after a display-DTB reboot; Wi-Fi SSH still works. |
| QCA6390 Wi-Fi (`ath11k_pci`) | works **with the DTB in this repo** |
| Power key / 5 min idle blank | `kebab-powerd`: DCS backlight 0 on kebab-dsi; `simpledrm` fb blank on the shipped DTB |
| Time / RTC | NTP + `fake-hwclock`. PMIC RTC is read-only (`SET_TIME` → `ENODEV`). |
| SSH | keys only (overlay drop-in). Hostname `oneplus-kebab-256g` — use `oneplus-kebab-256g.lan` (bare name is fake-ip). USB gadget is the recovery path. |
| Display | **Linux fbcon** on kebab-dsi (AMB655X 1080×2400, `msm` 1.13). Shipped `dtb/` still has `&dispcc` disabled. |
| GPU | Adreno 650.2 on kebab-dsi (OnePlus zap, `devfreq-3d00000.gpu` cooling). Mesa not tested. Safe DTB still has `&gpu` disabled. |
| Type-C host / OTG | not done (`usb_2` is the internal host) |
| Charge limit (80%) | kebab-dsi: `kebab-charge start` / `stop` / `status`. No `charge_control_end_threshold`; reboot re-enables until `stop`. |
| Android restore | GPT kept; you need your own stock images |

## Docs

- [Build / patch / pack / flash](docs/build.md)
- [Flashing (keep the stock GPT)](docs/flashing.md)
- [QCA6390 DTB](docs/dtb-wifi.md)
- [Changing Wi-Fi](docs/wifi.md)
- [Display (Linux fbcon on kebab-dsi)](docs/display.md)
- [Battery / SMB5 charge switch](docs/battery.md)
- [Headless (timezone, RTC, SSH)](docs/headless.md)
- [Do not leak host config](SECURITY.md)

## Releases

Prebuilt images live on [GitHub Releases](https://github.com/naughtyGitCat/armbian-oneplus-kebab/releases), not in git. Current bring-up tag: [`6.18.43-kebab-dsi-66`](https://github.com/naughtyGitCat/armbian-oneplus-kebab/releases/tag/6.18.43-kebab-dsi-66).

Pick **one** path.

### A. Zero-install (no Armbian on the phone yet)

Official-style split: Orange Fox `dd`, keep the stock GPT. UUID is already baked into the ext4 image **and** the boot cmdline. Do **not** mix with Armbian’s `boot_recovery.img`.

| file | write to |
|------|----------|
| `Armbian_26.8.1_Oneplus-kebab_trixie_current_6.18.43-kebab-dsi_minimal.rootfs.img.xz` | `linux` |
| `…minimal.boot_display.img.xz` | `boot_a` (Linux fbcon + SMB5 + GPU) |
| `…minimal.boot_safe.img.xz` | rollback only (`dispcc` off) |

```sh
xz -dk Armbian_*_kebab-dsi_minimal.rootfs.img.xz
xz -dk Armbian_*_kebab-dsi_minimal.boot_display.img.xz
# Orange Fox adb — macOS fastboot dies on the rootfs
adb push Armbian_*_kebab-dsi_minimal.rootfs.img /tmp/rootfs.img
adb push Armbian_*_kebab-dsi_minimal.boot_display.img /tmp/boot.img
adb shell 'dd if=/tmp/rootfs.img of=/dev/block/by-name/linux bs=4M; sync'
adb shell 'dd if=/tmp/boot.img of=/dev/block/by-name/boot_a bs=4M; sync'
adb reboot
```

First boot: `ssh root@172.16.42.1` (USB gadget). Change the password immediately. Copy `/root/20-wifi.example.yaml` → `/etc/netplan/20-wifi.yaml`, fill **your** SSID, `chmod 600`, `netplan apply`. Then `kebab-charge stop` (reboot re-enables charging).

GPT backup, partition layout, and why not macOS `fastboot`: [docs/flashing.md](docs/flashing.md). Checksums: `SHA256SUMS` on the same release.

### B. Already running Armbian (kernel hop only)

Use the tarball, not the rootfs.

| file | what |
|------|------|
| `kebab-dsi-6.18.43-66-full.tar.gz` | kernel, ramdisk, both DTBs, modules, overlay, `pack-abl-boot.sh`, ABL templates |
| `kebab-dsi-6.18.43-66.tar.gz` | kernel + DTBs + modules only |

The ABL templates in the full tarball have a **placeholder** root UUID (`00000000-…`). They will not mount root until you pack on the phone:

```sh
ver=6.18.43-kebab-dsi
install -D -m 644 vmlinuz-${ver} /boot/vmlinuz-${ver}
install -D -m 644 initrd.img-${ver} /boot/initrd.img-${ver}   # full tarball
install -D -m 644 sm8250-oneplus-kebab.dtb sm8250-oneplus-kebab-dsi.dtb \
  /usr/lib/linux-image-${ver}/qcom/
tar -C / -xzf modules-${ver}.tar.gz
depmod -a "${ver}"
# /boot/armbianEnv.txt must keep extraargs=clk_ignore_unused
pack-abl-boot.sh display --flash
reboot
```

Keep a copy of the last known-good `boot_a` **on the host**. After boot: `kebab-charge stop`.

Do **not** enable `&dispcc` or `&gpu` alone. Do not use kebab-dsi as the default `dtb/` in git.

## Build

This tree does **not** replace `armbian/build`. For a first install prefer the
zero-install split above. To rebuild from official kebab `current` instead:
download or `compile.sh BOARD=oneplus-kebab`, then apply this repo (Wi-Fi DTS +
overlay, and `scripts/apply-dsi-to-tree.sh --enable-display` packed with
`scripts/pack-abl-boot.sh` on the device). Step-by-step:
[docs/build.md](docs/build.md).

## Tree

```
dts/upstream/     Armbian 0011 kebab DTS, verbatim
dts/sm8250-…dts   same file with the Wi-Fi PMU delta
dts/patches/      git-style patch, `patch -p1` on a kernel tree
dts/wip/          display-enable DTS + panel sketch (not the shipped DTB)
dtb/              prebuilt DTB (dispcc still disabled)
kernel/           out-of-tree Samsung AMB655X panel driver
overlay/          systemd / modules / netplan *example*
scripts/          gadget, display, powerd, charge, apply-dsi, pack-abl
reference/        stock 256 GB GPT text dumps (no serial)
```

Images (`.img`, `.img.xz`) are gitignored on purpose. Get them from
[Releases](https://github.com/naughtyGitCat/armbian-oneplus-kebab/releases)
(kebab-dsi) or from Armbian (stock `current`).

## Userspace overlay

On a booted phone (USB gadget SSH):

```sh
scripts/install-overlay.sh root@172.16.42.1
```

Then copy `overlay/etc/netplan/20-wifi.example.yaml` to
`/etc/netplan/20-wifi.yaml` **on the device** and fill in your own SSID.
That live file must never land in git. To switch networks later, see
[docs/wifi.md](docs/wifi.md).

## CI

- `secret-scan` — every push. Blocks private keys, shadow hashes, dumped
  `androidboot.serialno=`, live netplan, non-placeholder Wi-Fi passwords.
- `watch-armbian` — weekly, and on DTS changes. Pulls the current kebab DTS
  from `armbian/build` and checks that
  `dts/patches/0001-sm8250-oneplus-kebab-qca6390-pmu-wifi.patch` still applies.

A full `compile.sh` for sm8250 does not fit on a GitHub-hosted runner. Build
the *base* image locally with [armbian/build](https://github.com/armbian/build);
this repo's kernel/DTB overlay is [docs/build.md](docs/build.md).

## License

GPL-2.0-only. The DTS comes from the Armbian / Linux kebab port (d4n1 / Jiali Chen).
