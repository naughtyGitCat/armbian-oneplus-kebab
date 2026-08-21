# Build, patch, pack, flash

This repository is **not** a fork of [armbian/build](https://github.com/armbian/build).
Official kebab images come from Armbian (`BOARD=oneplus-kebab`, family
`sm8250`, `BRANCH=current`, Qualcomm ABL). Everything here is leftover
bring-up that is not upstream yet: QCA6390 DTB, the AMB655X panel path,
SMB5 on kebab-dsi, and a small userspace overlay.

Do not expect `./compile.sh` in this tree. There is no `userpatches/`
series that turns the display MSM edits into an Armbian kernel package.

## What to use when

| goal | path |
|------|------|
| First install | Official Armbian kebab `current` image (download **or** `compile.sh`) + [flashing.md](flashing.md) (keep the stock GPT) |
| Wi-Fi + SSH overlay | This repo's DTB + `scripts/install-overlay.sh` on a booted phone |
| Linux fbcon + SMB5 | Kernel tree + `scripts/apply-dsi-to-tree.sh --enable-display`, then `pack-abl-boot.sh` **on the phone** |

`zz-update-abl-kernel` (Armbian postinst) always appends
`sm8250-oneplus-kebab.dtb` and `dd`s `boot_a`. That is the **safe** DTB
(`dispcc` still disabled). Display/SMB5 images must be packed with
[`scripts/pack-abl-boot.sh`](../scripts/pack-abl-boot.sh).

## 1. Base image from armbian/build

Download a split Qcom ABL image (`boot_recovery` + `rootfs`) from Armbian,
or build one:

```sh
git clone --depth=1 https://github.com/armbian/build
cd build
./compile.sh build \
  BOARD=oneplus-kebab \
  BRANCH=current \
  RELEASE=trixie \
  BUILD_MINIMAL=yes \
  KERNEL_CONFIGURE=no
```

Artifacts land under `output/images/` as
`Armbian_*_Oneplus-kebab_*_current_*_minimal.{boot_recovery,rootfs}.img.xz`.

Optional — fold **only** the Wi-Fi DTS into that build, so the image's
`sm8250-oneplus-kebab.dtb` already has QCA6390 PMU:

```sh
# archive name must match Armbian's sm8250 series (6.18, 6.19, …).
# scripts/check-armbian-dts.sh prints the one that currently carries kebab.
mkdir -p userpatches/kernel/archive/sm8250-6.18
cp /path/to/armbian-oneplus-kebab/dts/patches/0001-sm8250-oneplus-kebab-qca6390-pmu-wifi.patch \
   userpatches/kernel/archive/sm8250-6.18/
```

Then re-run `compile.sh`. If the patch does not apply, Armbian moved the
kebab DTS — see `watch-armbian` / `dts/upstream/`.

The display DSI/DPU python patches and `kebab-dsi.dts` do **not** go here.
Putting `&dispcc` in the default DTB hangs the first boot
([display.md](display.md)).

## 2. Flash (keep GPT)

Follow [flashing.md](flashing.md). Short version:

1. Unlock, Orange Fox (or any recovery with `adb`).
2. Shrink `userdata`, add `linux` (ext4). Do not wipe `sde`.
3. `adb push` + `dd` the **rootfs** onto `linux`. macOS `fastboot flash`
   of 40+ MiB images is unreliable.
4. Pack `boot.img` (stock `boot_recovery.img` has an empty cmdline) with
   this repo's [`dtb/sm8250-oneplus-kebab.dtb`](../dtb/sm8250-oneplus-kebab.dtb)
   if the image DTB still has the old QCA6390 genpd.
5. `dd` that onto `boot_a`. Set `/boot/armbianEnv.txt` to `boot_a` and the
   real root UUID **before** the next `apt upgrade`.
6. `adb reboot`. USB gadget SSH: `root@172.16.42.1`.

## 3. Overlay (userspace)

From a machine that can SSH to the gadget:

```sh
scripts/install-overlay.sh root@172.16.42.1
```

That installs gadget helpers, `kebab-display`, `kebab-powerd`,
`kebab-charge`, modules-load for ath11k, and the keys-only sshd drop-in
(only if `authorized_keys` is already there). Then copy
`overlay/etc/netplan/20-wifi.example.yaml` to `/etc/netplan/20-wifi.yaml`
**on the phone** and put in your SSID. Never commit that file.

Wi-Fi hostname is `oneplus-kebab-256g`. SSH to `oneplus-kebab-256g.lan`
([headless.md](headless.md)). Charge switch:

```sh
kebab-charge status
kebab-charge stop
kebab-charge start
```

## 4. Display + SMB5 kernel (this repo)

Need a **6.18.x** kernel tree that already includes Armbian's
`sm8250-6.18` patches (the tree `compile.sh` left in cache, or linux-stable
6.18 plus those patches). Cross-compile on x86_64 with
`aarch64-linux-gnu-`; on arm64 omit `CROSS_COMPILE`.

```sh
git clone https://github.com/naughtyGitCat/armbian-oneplus-kebab
# TREE = Armbian-patched 6.18 linux sources
./armbian-oneplus-kebab/scripts/apply-dsi-to-tree.sh "$TREE" --enable-display
```

That copies the Wi-Fi kebab DTS, the AMB655X panel driver, the DSI/DPU
python patches, and writes `sm8250-oneplus-kebab-dsi.dts` (dispcc + DSI0 +
panel + **SMB5**; gpu / typec / vbus / fg stay off).

```sh
cd "$TREE"
export ARCH=arm64
export CROSS_COMPILE=aarch64-linux-gnu-   # empty on native arm64
# Start from the running phone's /proc/config.gz or Armbian's kebab config.
./scripts/config --set-str LOCALVERSION "-kebab-dsi"
./scripts/config --enable DRM_PANEL_SAMSUNG_AMB655X
./scripts/config --enable CHARGER_QCOM_SMB5
./scripts/config --disable DEBUG_INFO_BTF
./scripts/config --enable DEBUG_INFO_NONE
make olddefconfig
make -j"$(nproc)" Image modules
make qcom/sm8250-oneplus-kebab.dtb qcom/sm8250-oneplus-kebab-dsi.dtb
```

(`make arch/arm64/boot/dts/qcom/….dtb` double-prefixes on 6.18; use the
`qcom/….dtb` target.)

Install **onto the phone** (SSH). `pack-abl-boot.sh` is not part of the
userspace overlay; copy it too. It wants `/boot/vmlinuz-*-kebab-dsi`,
`/boot/initrd.img-<ver>`, and
`/usr/lib/linux-image-<ver>/qcom/sm8250-oneplus-kebab{,-dsi}.dtb`.

```sh
ver=$(make -s kernelrelease)          # e.g. 6.18.43-kebab-dsi
host=root@172.16.42.1                 # or root@oneplus-kebab-256g.lan
ssh "$host" "mkdir -p /usr/lib/linux-image-${ver}/qcom"
scp arch/arm64/boot/Image "$host:/boot/vmlinuz-${ver}"
scp arch/arm64/boot/dts/qcom/sm8250-oneplus-kebab.dtb \
    arch/arm64/boot/dts/qcom/sm8250-oneplus-kebab-dsi.dtb \
    "$host:/usr/lib/linux-image-${ver}/qcom/"
scp /path/to/armbian-oneplus-kebab/scripts/pack-abl-boot.sh \
    "$host:/usr/local/sbin/pack-abl-boot.sh"
make INSTALL_MOD_STRIP=1 INSTALL_MOD_PATH=/tmp/kmods modules_install
rsync -a /tmp/kmods/lib/modules/${ver}/ "$host:/lib/modules/${ver}/"
```

On the phone (`extraargs` in `/boot/armbianEnv.txt` must keep
`clk_ignore_unused`; pack-abl reads that file):

```sh
chmod 755 /usr/local/sbin/pack-abl-boot.sh
depmod -a "${ver}"
update-initramfs -c -k "${ver}"
# Stage A: same kernel, dispcc still off
pack-abl-boot.sh safe --flash
reboot
# Stage B: once SSH is back, Linux fbcon + SMB5
pack-abl-boot.sh display --flash
reboot
```

`pack-abl-boot.sh` gzip's `vmlinuz`, concatenates the DTB, and `mkbootimg`s
an ABL v0 image. Pass `--flash` only when you mean to `dd` `boot_a`.
Keep a copy of the last known-good `boot_a` **on the host**.

Rollback: `pack-abl-boot.sh safe --flash`, or `dd` a saved boot image from
recovery ([flashing.md](flashing.md) rescue table).

Do not enable `&gpu` or `&dispcc` alone. Do not make kebab-dsi the shipped
`dtb/` default.

## 5. After a display-DTB boot

- Picture: Linux fbcon on AMB655X — [display.md](display.md)
- Charge: `kebab-charge stop` / `start` / `status` — [battery.md](battery.md)
- Type-C gadget may not re-enumerate; Wi-Fi SSH still works
