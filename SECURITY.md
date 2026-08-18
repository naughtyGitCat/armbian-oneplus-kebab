# Security / do not leak host config

This is a public repository. Never commit:

- Wi-Fi SSID or passphrase
- root or user passwords, `/etc/shadow` hashes
- device serial numbers (`androidboot.serialno`, `fastboot getvar serialno`)
- SSH private keys, `authorized_keys` dumps
- home-network addressing that identifies a specific household
- netplan files copied off a live phone

Use the placeholders in `overlay/etc/netplan/20-wifi.example.yaml`.

CI runs `.github/workflows/secret-scan.yml` on every push. `scripts/secret-scan.sh` is the same check, runnable locally before commit.
