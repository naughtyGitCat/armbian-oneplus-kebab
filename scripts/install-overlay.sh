#!/usr/bin/env bash
# Copy the userspace overlay onto a live kebab over SSH.
# Usage: scripts/install-overlay.sh [user@host]
# Default host is the USB gadget. This script never copies a live netplan.
set -euo pipefail

root=$(cd "$(dirname "$0")/.." && pwd)
target=${1:-root@172.16.42.1}

ssh "$target" 'mkdir -p /usr/local/sbin /etc/modules-load.d /etc/systemd/network \
  /etc/systemd/logind.conf.d /etc/systemd/system/usbgadget-rndis.service.d'

scp "$root/scripts/setup-usbgadget-network-kebab.sh" "$target:/usr/local/sbin/setup-usbgadget-network-kebab.sh"
scp "$root/scripts/kebab-display" "$target:/usr/local/sbin/kebab-display"
scp "$root/scripts/kebab-powerd" "$target:/usr/local/sbin/kebab-powerd"
scp "$root/overlay/etc/modules-load.d/qca6390.conf" "$target:/etc/modules-load.d/qca6390.conf"
scp "$root/overlay/etc/systemd/network/10-wlan.link" "$target:/etc/systemd/network/10-wlan.link"
scp "$root/overlay/etc/systemd/logind.conf.d/kebab-power.conf" "$target:/etc/systemd/logind.conf.d/kebab-power.conf"
scp "$root/overlay/etc/systemd/system/kebab-powerd.service" "$target:/etc/systemd/system/kebab-powerd.service"
scp "$root/overlay/etc/systemd/system/usbgadget-rndis.service.d/override.conf" \
	"$target:/etc/systemd/system/usbgadget-rndis.service.d/override.conf"

ssh "$target" 'chmod 755 /usr/local/sbin/setup-usbgadget-network-kebab.sh \
  /usr/local/sbin/kebab-display /usr/local/sbin/kebab-powerd
systemctl daemon-reload
systemctl enable --now kebab-powerd.service
echo overlay installed. copy overlay/etc/netplan/20-wifi.example.yaml by hand.'
