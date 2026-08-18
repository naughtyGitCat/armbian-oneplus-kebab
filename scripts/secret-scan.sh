#!/usr/bin/env bash
# Fail if the tree looks like it grew a live phone dump.
# Do not encode any real SSID, passphrase, serial, or password here —
# listing them would publish them.
set -euo pipefail

root=$(cd "$(dirname "$0")/.." && pwd)
cd "$root"

fail=0
hit() {
	printf 'SECRET-SCAN: %s\n' "$*" >&2
	fail=1
}

# Live netplan (example files are allowed).
while IFS= read -r f; do
	case "$f" in
	*.example.yaml) ;;
	*) hit "live netplan, not the example: $f" ;;
	esac
done < <(find overlay/etc/netplan -name '*.yaml' -o -name '*.yml' 2>/dev/null)

# Private keys / host identity.
while IFS= read -r f; do
	hit "private key / host identity: $f"
done < <(find . -type f \( \
	-name 'id_rsa*' -o -name 'id_ed25519*' -o -name 'id_ecdsa*' \
	-o -name 'authorized_keys' -o -name '*.pem' \
	\) ! -path './.git/*')

# Content patterns. Keep them generic.
#   - OpenSSH / PEM private keys
#   - /etc/shadow-style hashes
#   - androidboot.serialno= (a dumped cmdline)
#   - household RFC1918 used by this author's lab notes (do not commit)
#   - netplan password that is not the placeholder
# Require a value after serialno= so docs that name the key do not trip.
scan_re='BEGIN (OPENSSH|RSA|EC|DSA) PRIVATE KEY|\$6\$[./A-Za-z0-9]+|\$y\$[./A-Za-z0-9]+|\$5\$[./A-Za-z0-9]+|androidboot\.serialno=[0-9A-Za-z]+|10\.100\.100\.|10\.100\.101\.'

while IFS= read -r f; do
	[ -f "$f" ] || continue
	case "$f" in
	*.dtb|*.mbn|*.bin|*.gz|*.xz|*.png|*.jpg) continue ;;
	./scripts/secret-scan.sh|scripts/secret-scan.sh) continue ;;
	esac
	if grep -nE "$scan_re" "$f" >/dev/null 2>&1; then
		grep -nE "$scan_re" "$f" | while IFS= read -r line; do
			hit "$f: $line"
		done
	fi
	if grep -nE 'password:[[:space:]]*"' "$f" >/dev/null 2>&1; then
		if ! grep -nE 'password:[[:space:]]*"YOUR_PASSPHRASE"' "$f" >/dev/null 2>&1; then
			grep -nE 'password:[[:space:]]*"' "$f" | while IFS= read -r line; do
				hit "non-placeholder wifi password in $f: $line"
			done
		fi
	fi
done < <(git ls-files 2>/dev/null || find . -type f ! -path './.git/*' ! -name '*.dtb')

if [ "$fail" -ne 0 ]; then
	echo "secret-scan failed" >&2
	exit 1
fi
echo "secret-scan: clean"
