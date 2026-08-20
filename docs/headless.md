# Headless daily use

The image is usable as a USB + Wi-Fi box without the panel. This page is the
userspace side. Official `kebab.dtb` stays on `simpledrm`; do not enable
`dispcc` alone. Linux fbcon is the display-DTB path — see
[display.md](display.md).

## Timezone

The image is `Etc/UTC`. Set one and forget it:

```sh
timedatectl set-timezone Asia/Shanghai
```

## Clock

`rtc-pm8xxx` binds as `/dev/rtc0` and **reads**. Writes fail:

```
hwclock: ioctl(RTC_SET_TIME) to /dev/rtc0 to set the time failed: No such device
```

That is the Qualcomm driver refusing a wall-clock set unless the DT node has
`allow-set-time`. Do **not** add that property. ABL and the modem own the
PMIC RTC; Linux is a guest. `hctosys` therefore plants ~1971 at boot.

Two userspace floors cover it:

- `systemd-timesyncd` touches `/var/lib/systemd/timesync/clock` and will not
  let the system clock run backwards past that mtime.
- Debian `fake-hwclock` (already in the image). The meta unit
  `fake-hwclock.service` is a vendor symlink to `/dev/null` — leave it
  masked. The units that actually run are `fake-hwclock-load.service`,
  `fake-hwclock-save.service`, and `fake-hwclock-save.timer`. Enable those
  (package default) and run `fake-hwclock save` once after NTP is up.

NTP itself: put **numeric** servers in a timesyncd drop-in. Domain pool
names often land in a LAN fake-ip blackhole and never sync. The live
drop-in stays on the phone; do not commit it.

## SSH

[`overlay/etc/ssh/sshd_config.d/kebab-headless.conf`](../overlay/etc/ssh/sshd_config.d/kebab-headless.conf)
turns off password logins (`PasswordAuthentication no`,
`PermitRootLogin prohibit-password`). Install it only after
`/root/.ssh/authorized_keys` has your key. USB gadget SSH
(`root@172.16.42.1`) is the recovery path if Wi-Fi or keys go wrong.

Set a root password locally with `passwd` if you want a serial/console
fallback. Never copy `/etc/shadow` or a hash into this tree.

## Hostname / Wi-Fi name

```sh
hostnamectl set-hostname oneplus-kebab
```

[`overlay/etc/systemd/network/10-wlan.link`](../overlay/etc/systemd/network/10-wlan.link)
matches `Driver=ath11k_pci` and names the iface `wlan0`. ath11k can
change the MAC. For a DHCP reservation, add a `MACAddress=` line under
`[Link]` **on the phone only**. Do not put a real MAC in git.
`scripts/install-overlay.sh` will overwrite that file and drop the pin.

## Overlay

```sh
scripts/install-overlay.sh root@172.16.42.1
```

Never copies a live netplan. After keys are in place it also drops the
sshd snippet and reloads `ssh`.
