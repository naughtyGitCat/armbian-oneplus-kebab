#!/usr/bin/env bash
# Pack an ABL boot.img on a live kebab. Never touches boot_a unless --flash.
#
# Usage (on the phone):
#   scripts/pack-abl-boot.sh safe                  # dispcc still off
#   scripts/pack-abl-boot.sh display               # dispcc+DSI+panel
#   scripts/pack-abl-boot.sh safe --flash          # dd to boot_a
#
# zz-update-abl-kernel hardcodes sm8250-oneplus-kebab.dtb and always dds.
# Use this for the display DTB, and for a dry-run pack of the safe DTB.
set -euo pipefail

which=${1:?safe or display}
flash=0
shift || true
for arg in "$@"; do
	case "$arg" in
	--flash) flash=1 ;;
	*) echo "unknown arg: $arg" >&2; exit 2 ;;
	esac
done

ver=$(ls -1 /boot/vmlinuz-*-kebab-dsi 2>/dev/null | sed 's|^/boot/vmlinuz-||' | sort -V | tail -n1)
[ -n "$ver" ] || { echo "no /boot/vmlinuz-*-kebab-dsi" >&2; exit 1; }

case "$which" in
safe) dtb="sm8250-oneplus-kebab.dtb" ;;
display) dtb="sm8250-oneplus-kebab-dsi.dtb" ;;
*) echo "first arg must be safe or display" >&2; exit 2 ;;
esac

kernel="/boot/vmlinuz-${ver}"
ramdisk="/boot/initrd.img-${ver}"
dtb_path="/usr/lib/linux-image-${ver}/qcom/${dtb}"
out="/boot/armbian-kernel-kebab-dsi-${which}.img"

for f in "$kernel" "$ramdisk" "$dtb_path"; do
	[ -f "$f" ] || { echo "missing $f" >&2; exit 1; }
done

uuid=$(sed -e 's/^.*root=UUID=//' -e 's/ .*$//' < /proc/cmdline)
source /boot/armbianEnv.txt
slot_suffix=${abl_boot_partition_label#boot}

gzip -c "$kernel" > /tmp/Image.gz
cat /tmp/Image.gz "$dtb_path" > /tmp/Image.gz-dtb
mkbootimg \
	--kernel /tmp/Image.gz-dtb \
	--ramdisk "$ramdisk" \
	--base 0x0 \
	--second_offset 0x00f00000 \
	--cmdline "root=UUID=${uuid} slot_suffix=${slot_suffix} ${extraargs:-}" \
	--kernel_offset 0x8000 \
	--ramdisk_offset 0x1000000 \
	--tags_offset 0x100 \
	--pagesize 4096 \
	-o "$out"
rm -f /tmp/Image.gz /tmp/Image.gz-dtb
ls -lh "$out"

if [ "$flash" -eq 1 ]; then
	[ -n "${abl_boot_partition_label:-}" ] || {
		echo "abl_boot_partition_label empty, not flashing" >&2
		exit 1
	}
	echo "dd $out -> /dev/disk/by-partlabel/${abl_boot_partition_label}"
	dd if="$out" of="/dev/disk/by-partlabel/${abl_boot_partition_label}"
else
	echo "packed only. pass --flash to write boot_a"
fi
