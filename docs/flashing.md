# Flashing Armbian on OnePlus 8T (kebab)

Official images are split Qcom ABL artifacts from Armbian:

- `Armbian_*_Oneplus-kebab_*_current_*_minimal.boot_recovery.img.xz`
- `Armbian_*_Oneplus-kebab_*_current_*_minimal.rootfs.img.xz`

Board config lives in [armbian/build `oneplus-kebab.conf`](https://github.com/armbian/build/blob/main/config/boards/oneplus-kebab.conf). The stock first-boot path is the same family as amazingfate's elish notes: write `boot_recovery.img` to a boot slot, write the rootfs to a GPT partition, then let the USB gadget come up.

This repo documents a **keep-the-GPT** variant so Android can be restored later. It does **not** replace the whole UFS with a single Linux disk.

## What you must keep

Back up the stock GPT **before** you touch userdata:

```sh
adb shell sgdisk --backup=/tmp/sda.gpt /dev/block/sda
adb shell sgdisk --backup=/tmp/sde.gpt /dev/block/sde
adb pull /tmp/sda.gpt
adb pull /tmp/sde.gpt
```

Human-readable dumps of a stock 256 GB kebab are in [`reference/`](../reference/). Those dumps have no serial number.

Stock `sda` userdata (256 GB UFS) starts at sector **2913312** (4096-byte sectors) and runs to the end of the LUN. If you ever rebuild the Linux split, do not move the start of partitions 1–27.

`recovery_a` / `recovery_b` can stay Orange Fox (or stock recovery). That is the rescue path once `boot_a` is Armbian — volume-up no longer boots recovery.

## Layout used here

After the shrink, `sda` looks like:

| part | name     | role                                      |
|------|----------|-------------------------------------------|
| 1–27 | (stock)  | untouched Android partitions              |
| 28   | userdata | shrunk Android userdata (~2 GiB leftover) |
| 29   | esp      | 512 MiB ESP, unused today                 |
| 30   | linux    | ext4 rootfs (rest of the LUN)             |

`sde` stays stock A/B (`boot_a` = `sde11`, `boot_b` = `sde39` on this SKU). Armbian runs from **slot A**.

## Why not `fastboot flash` from macOS

Large `fastboot` writes on macOS frequently die with IOKit `e00002ed` / `e00002d8` / `e00002c0`. `fastboot devices` can still list the phone. Treat that as a dead link.

The reliable 40+ MiB path is **Orange Fox `adb push` + `dd`**, same as the original rootfs flash.

## Flash (keep GPT)

You need:

- unlocked bootloader
- a custom recovery with working `adb` (Orange Fox is fine)
- the two Armbian xz images, decompressed
- `mkbootimg`, `abootimg` or a packed boot from this repo's notes

1. Boot recovery, confirm `adb shell` and that `/dev/block/by-name/linux` exists (create it with `parted`/`sgdisk` on `sda` if you are doing this for the first time). Do not wipe `sde`.
2. Push and write the rootfs:

   ```sh
   adb push Armbian_…_rootfs.img /tmp/rootfs.img
   adb shell 'dd if=/tmp/rootfs.img of=/dev/block/by-name/linux bs=4M; sync'
   ```

3. Read the new root UUID (`blkid` on `linux`). The stock `boot_recovery.img` has an **empty** cmdline — it will not find the rootfs. Pack a boot image (see below) or reuse `dtb/sm8250-oneplus-kebab.dtb` from this repo on top of the Armbian kernel/ramdisk.
4. Write that image to `boot_a` **via adb**, not macOS fastboot:

   ```sh
   adb push packed-boot.img /tmp/boot_a.img
   adb shell 'dd if=/tmp/boot_a.img of=/dev/block/by-name/boot_a bs=4M; sync'
   ```

5. `adb reboot`. The Type-C USB gadget should appear as `172.16.42.1` (host `172.16.42.2`). SSH as `root`.

### Packing `boot.img`

Armbian's `zz-update-abl-kernel` does:

```sh
gzip -c /boot/vmlinuz-<ver> > /tmp/Image.gz
cat /tmp/Image.gz /usr/lib/linux-image-<ver>/qcom/sm8250-oneplus-kebab.dtb > /tmp/Image.gz-dtb
mkbootimg \
  --kernel /tmp/Image.gz-dtb \
  --ramdisk /boot/initrd.img-<ver> \
  --base 0x0 \
  --second_offset 0x00f00000 \
  --cmdline "root=UUID=<uuid> slot_suffix=_a clk_ignore_unused pd_ignore_unused" \
  --kernel_offset 0x8000 \
  --ramdisk_offset 0x1000000 \
  --tags_offset 0x100 \
  --pagesize 4096 \
  -o boot.img
```

Replace the DTB with [`dtb/sm8250-oneplus-kebab.dtb`](../dtb/sm8250-oneplus-kebab.dtb) if you want working QCA6390 Wi-Fi (see [dtb-wifi.md](dtb-wifi.md)).

### `armbianEnv.txt` landmine

On first boot, `/boot/armbianEnv.txt` may say `abl_boot_partition_label=boot_b` and a **wrong** `rootdev` UUID. `zz-update-abl-kernel` will then flash the next kernel to the other slot with a cmdline that cannot mount root.

Set it **before** the next `apt upgrade`:

```
abl_boot_partition_label=boot_a
rootdev=UUID=<the linux partition UUID>
rootfstype=ext4
```

## First boot

- USB gadget: `ssh root@172.16.42.1`. Change the root password immediately; do not commit it anywhere.
- Copy [`overlay/`](../overlay/) and [`scripts/`](../scripts/) onto the phone (see the README). Wi-Fi: copy `20-wifi.example.yaml` to `/etc/netplan/20-wifi.yaml` and put **your** SSID there. Never add that file to git.
- Display is the bootloader framebuffer via `simpledrm`. Power key and idle blank come from `kebab-powerd`.
- Do **not** flip `dispcc` to `okay` by itself. That hang is documented in [display.md](display.md).

## Rescue

| state | what to do |
|-------|------------|
| Armbian up | SSH over USB or Wi-Fi |
| Armbian hung, USB dead | Power + Vol-Up 15–20 s (PMIC hard reset) |
| FASTBOOT | Vol-Down + Power. Then `fastboot reboot recovery` (if the Mac USB link dies, use the key combo / another cable) |
| Orange Fox | `adb` is up. Rewrite `boot_a` from a known-good image, `sync`, `adb reboot` |
| Need stock Android | restore the GPT backups, flash back the original `boot_*` / `super` / `userdata` images you saved. This repo does not host those images. |

Keep a copy of the last known-good `boot_a` **on the host**. A file that lives only on the phone is gone when the phone does not boot.

## Restore Android later

1. Fastboot / recovery.
2. `sgdisk --load-backup=sda.gpt /dev/block/sda` (and `sde` if you ever touched it).
3. Flash the original `super`, `userdata`, `boot_a`/`boot_b`, `dtbo_*`, `vbmeta_*` dumps.
4. `fastboot --set-active=a` (or whichever slot was stock).

If you skipped the GPT backup, the sector map in [`reference/stock-partition-tables-sectors.txt`](../reference/stock-partition-tables-sectors.txt) is the fallback for a 256 GB kebab.
