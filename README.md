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
| USB Type-C gadget (NCM, `172.16.42.1`) | works (`usb_1` / `a600000`, HS only) |
| QCA6390 Wi-Fi (`ath11k_pci`) | works **with the DTB in this repo** |
| Power key / 5 min idle blank | `kebab-powerd` on `simpledrm` |
| Time / RTC | NTP + `fake-hwclock`. PMIC RTC is read-only (`SET_TIME` → `ENODEV`). |
| SSH | keys only (overlay drop-in). USB gadget is the recovery path. |
| `msm-mdss` / panel / GPU | **not** up. `6.18.43-kebab-dsi` + AMB655X driver built, not flashed. Do not enable `dispcc` alone. |
| Type-C host / OTG | not done (`usb_2` is the internal host) |
| Charge limit (80%) | **not** possible. Only the bq27541 gauge is bound; SMB5 is disabled. |
| Android restore | GPT kept; you need your own stock images |

## Docs

- [Flashing (keep the stock GPT)](docs/flashing.md)
- [QCA6390 DTB](docs/dtb-wifi.md)
- [Changing Wi-Fi](docs/wifi.md)
- [Display / why dispcc is off](docs/display.md)
- [Battery / why there is no 80% cap](docs/battery.md)
- [Headless (timezone, RTC, SSH)](docs/headless.md)
- [Do not leak host config](SECURITY.md)

## Tree

```
dts/upstream/     Armbian 0011 kebab DTS, verbatim
dts/sm8250-…dts   same file with the Wi-Fi PMU delta
dts/patches/      git-style patch, `patch -p1` on a kernel tree
dts/wip/          display-enable DTS + panel sketch (not the shipped DTB)
dtb/              prebuilt DTB (dispcc still disabled)
kernel/           out-of-tree Samsung AMB655X panel driver
overlay/          systemd / modules / netplan *example*
scripts/          gadget, display, powerd, apply-dsi, pack-abl
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
images locally (or on a self-hosted runner) with [armbian/build](https://github.com/armbian/build).

## License

GPL-2.0-only. The DTS comes from the Armbian / Linux kebab port (d4n1 / Jiali Chen).
