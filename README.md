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

## Build

This tree does **not** replace `armbian/build`. First image = official kebab
`current` (download or `compile.sh BOARD=oneplus-kebab`). Then apply this
repo: Wi-Fi DTS + overlay on the phone, and — for Linux fbcon / SMB5 / GPU — a
6.18 kernel with `scripts/apply-dsi-to-tree.sh --enable-display` packed
via `scripts/pack-abl-boot.sh` on the device. Step-by-step:
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

Images (`.img`, `.img.xz`) are gitignored on purpose. Get them from Armbian.

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
