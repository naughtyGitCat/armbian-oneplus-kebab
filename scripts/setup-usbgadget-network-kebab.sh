#!/bin/bash
# kebab: force Type-C DWC3 (a600000) into device mode, wait for UDC, then
# bind an NCM gadget. Tear down any stale g1 left by initramfs.
set -x
exec > /var/log/gadget-kebab.log 2>&1
echo "=== gadget kebab $(date -Is) ==="

CONFIGFS=/sys/kernel/config/usb_gadget
GADGET=$CONFIGFS/g1

mount -t debugfs debugfs /sys/kernel/debug 2>/dev/null || true
mount -t configfs configfs /sys/kernel/config 2>/dev/null || true
modprobe libcomposite 2>/dev/null || true
modprobe usb_f_ncm 2>/dev/null || true

teardown_g1() {
	[ -d "$GADGET" ] || return 0
	echo "tearing down stale g1"
	echo "" > "$GADGET/UDC" 2>/dev/null || true
	for f in "$GADGET"/configs/*.*/*.*; do
		[ -e "$f" ] && rm -f "$f"
	done
	for d in "$GADGET"/configs/*/strings/*; do
		[ -d "$d" ] && rmdir "$d"
	done
	for d in "$GADGET"/configs/*; do
		[ -d "$d" ] && rmdir "$d"
	done
	for d in "$GADGET"/functions/*; do
		[ -d "$d" ] && rmdir "$d"
	done
	for d in "$GADGET"/strings/*; do
		[ -d "$d" ] && rmdir "$d"
	done
	rmdir "$GADGET" 2>/dev/null || true
}

# Only the Type-C controller. Never touch a800000 (internal host).
force_peripheral() {
	local modef=/sys/kernel/debug/usb/a600000.usb/mode
	if [ -e "$modef" ]; then
		echo device > "$modef" 2>/dev/null || echo peripheral > "$modef" 2>/dev/null || true
		echo "mode now: $(cat "$modef" 2>/dev/null)"
	else
		echo "no $modef yet"
	fi
}

rebind_dwc3() {
	local name
	for name in a600000.usb a6f8800.usb a6f8800.usb3; do
		if [ -d /sys/bus/platform/drivers/dwc3/"$name" ]; then
			echo "rebind dwc3 $name"
			echo "$name" > /sys/bus/platform/drivers/dwc3/unbind
			sleep 1
			echo "$name" > /sys/bus/platform/drivers/dwc3/bind
		fi
		if [ -d /sys/bus/platform/drivers/qcom-dwc3/"$name" ]; then
			echo "rebind qcom-dwc3 $name"
			echo "$name" > /sys/bus/platform/drivers/qcom-dwc3/unbind
			sleep 1
			echo "$name" > /sys/bus/platform/drivers/qcom-dwc3/bind
		fi
	done
}

wait_udc() {
	local i
	for i in $(seq 1 25); do
		if [ -n "$(ls /sys/class/udc 2>/dev/null)" ]; then
			echo "UDC ready: $(ls /sys/class/udc)"
			return 0
		fi
		force_peripheral
		if [ "$i" -eq 8 ]; then
			rebind_dwc3
		fi
		sleep 1
	done
	echo "NO UDC after wait"
	echo "debugfs usb:"; ls -la /sys/kernel/debug/usb/ 2>/dev/null || true
	echo "platform dwc:"; ls /sys/bus/platform/drivers/dwc3/ 2>/dev/null || true
	echo "class udc:"; ls -la /sys/class/udc 2>/dev/null || true
	return 1
}

teardown_g1
force_peripheral
wait_udc || true

# Recreate gadget even if UDC is late — bind loop below retries.
teardown_g1
mkdir -p "$GADGET"/strings/0x409 "$GADGET"/configs/c.1/strings/0x409
echo 0x1D6B > "$GADGET"/idVendor
echo 0x0103 > "$GADGET"/idProduct
echo 0x0100 > "$GADGET"/bcdDevice
echo 0x0200 > "$GADGET"/bcdUSB
echo Armbian > "$GADGET"/strings/0x409/manufacturer
echo kebab > "$GADGET"/strings/0x409/serialnumber
echo "USB Gadget Network" > "$GADGET"/strings/0x409/product
mkdir -p "$GADGET"/functions/ncm.usb0
echo 250 > "$GADGET"/configs/c.1/MaxPower
echo "NCM Configuration" > "$GADGET"/configs/c.1/strings/0x409/configuration
ln -s "$GADGET"/functions/ncm.usb0 "$GADGET"/configs/c.1/ncm.usb0 2>/dev/null || \
	ln -s "$GADGET"/functions/ncm.usb0 "$GADGET"/configs/c.1/

for i in $(seq 1 20); do
	udc=$(ls /sys/class/udc 2>/dev/null | head -n1)
	if [ -n "$udc" ]; then
		echo "$udc" > "$GADGET"/UDC && echo "bound to $udc" && break
		echo "bind $udc failed, retry $i"
	else
		force_peripheral
		echo "still no UDC, retry $i"
	fi
	sleep 1
done

echo "UDC file: $(cat "$GADGET"/UDC 2>/dev/null)"
echo "ifaces:"; ip link

# usb0 / usb1 depending on ncm
for iface in usb0 usb1 eth0; do
	if ip link show "$iface" >/dev/null 2>&1; then
		ip addr add 172.16.42.1/16 dev "$iface" 2>/dev/null || true
		ip link set "$iface" up
		echo "addr on $iface"
		if ! pgrep -x unudhcpd >/dev/null 2>&1; then
			nohup /usr/bin/unudhcpd -i "$iface" -s 172.16.42.1 -c 172.16.42.2 \
				>> /var/log/unudhcpd.log 2>&1 &
		fi
		break
	fi
done

echo "=== done $(date -Is) ==="
exit 0
