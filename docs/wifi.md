# Changing Wi-Fi

The kebab overlay uses **netplan + systemd-networkd**, not NetworkManager.
There is no `nmtui` / `nmcli`. The live file on the phone is
`/etc/netplan/20-wifi.yaml`. The copy in this repo is only
[`overlay/etc/netplan/20-wifi.example.yaml`](../overlay/etc/netplan/20-wifi.example.yaml)
— placeholders, never a real SSID.

Keep a USB gadget SSH session open (`ssh root@172.16.42.1`) while you
switch networks. If the new AP is isolated or the passphrase is wrong,
Wi-Fi SSH dies; the Type-C gadget does not.

## Switch

On the phone:

```sh
iw dev wlan0 scan | awk '/SSID:/{print}'
```

Edit `/etc/netplan/20-wifi.yaml` so it lists **only** the AP you want:

```yaml
network:
  version: 2
  renderer: networkd
  wifis:
    wlan0:
      dhcp4: true
      dhcp6: true
      ipv6-privacy: true
      regulatory-domain: CN
      access-points:
        "YOUR_SSID":
          password: "YOUR_PASSPHRASE"
```

Then:

```sh
chmod 600 /etc/netplan/20-wifi.yaml
netplan apply
iw dev wlan0 link
ip -4 -br addr show wlan0
```

`wlan0` is pinned by [`overlay/etc/systemd/network/10-wlan.link`](../overlay/etc/systemd/network/10-wlan.link)
(`Driver=ath11k_pci`). Do not put a MAC in the `[Match]` block — ath11k can
change it. To *stop* it changing (DHCP reservation), add `MACAddress=`
under `[Link]` on the phone only; keep that line out of git. Re-running
`scripts/install-overlay.sh` overwrites the file and drops the pin.

Hidden SSIDs need `hidden: true` under that `access-points` entry.

## After it associates

- DHCP address is whatever that AP's LAN gives you.
- A guest / IoT AP that NATs behind another router is reachable **from**
  the internet side of that router, but not from the rest of your LAN
  unless you add a route and punch a hole. That is a router problem, not
  a kebab problem.
- USB gadget stays `172.16.42.1` regardless of Wi-Fi.

## Do not commit the live file

`20-wifi.yaml` belongs only on the phone. CI `secret-scan` rejects a
non-example netplan and any `password:` that is not `YOUR_PASSPHRASE`.
See [SECURITY.md](../SECURITY.md).
