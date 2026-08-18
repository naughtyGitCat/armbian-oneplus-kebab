#!/usr/bin/env bash
# Track armbian/build kebab DTS and verify the local QCA6390 patch still applies.
set -euo pipefail

root=$(cd "$(dirname "$0")/.." && pwd)
cd "$root"

API=${ARMBIAN_API:-https://api.github.com/repos/armbian/build/contents}
RAW=${ARMBIAN_RAW:-https://raw.githubusercontent.com/armbian/build/main}
WORKDIR=$(mktemp -d)
trap 'rm -rf "$WORKDIR"' EXIT

echo "listing sm8250 kernel patch archives"
curl -fsSL "$API/patch/kernel/archive" \
	| python3 -c '
import json,sys
names=[e["name"] for e in json.load(sys.stdin) if e["name"].startswith("sm8250-")]
# newest version last in the file, we want newest first
def key(n):
    parts=n.split("-",1)[1].split(".")
    return tuple(int(x) if x.isdigit() else 0 for x in parts)
for n in sorted(names, key=key, reverse=True):
    print(n)
' > "$WORKDIR/archives.txt"
cat "$WORKDIR/archives.txt"

found=""
while IFS= read -r archive; do
	echo "scanning $archive"
	if ! curl -fsSL "$API/patch/kernel/archive/$archive" -o "$WORKDIR/list.json"; then
		echo "skip $archive (list failed)"
		continue
	fi
	path=$(python3 -c '
import json,sys
want=None
for e in json.load(open(sys.argv[1])):
    n=e["name"]
    if "sm8250-oneplus-kebab-Add-device-tree" in n or "add-OnePlus-8T-kebab" in n:
        want=e["path"]
        break
if want:
    print(want)
' "$WORKDIR/list.json")
	if [ -n "$path" ]; then
		found=$path
		echo "using $found"
		break
	fi
done < "$WORKDIR/archives.txt"

if [ -z "$found" ]; then
	echo "could not find kebab DTS patch on armbian/build" >&2
	exit 1
fi

curl -fsSL "$RAW/$found" -o "$WORKDIR/0011.patch"
mkdir -p "$WORKDIR/upstream"
# 0011 also touches qcom/Makefile. Pull only the new DTS out of the mail.
python3 - "$WORKDIR/0011.patch" "$WORKDIR/upstream/sm8250-oneplus-kebab.dts" <<'PY'
import sys
src, dst = sys.argv[1], sys.argv[2]
want = "sm8250-oneplus-kebab.dts"
lines = open(src, "rb").read().splitlines(True)
out = []
take = False
for line in lines:
    if line.startswith(b"diff --git "):
        take = want.encode() in line
        continue
    if not take:
        continue
    if line.startswith(b"@@"):
        continue
    if line.startswith(b"--- ") or line.startswith(b"+++ ") or line.startswith(b"index ") or line.startswith(b"new file"):
        continue
    if line.startswith(b"+"):
        out.append(line[1:])
    elif line.startswith(b"\\"):
        continue
if not out:
    sys.exit("no dts content in patch")
open(dst, "wb").write(b"".join(out))
print(f"extracted {len(out)} lines -> {dst}")
PY
up="$WORKDIR/upstream/sm8250-oneplus-kebab.dts"
if [ ! -s "$up" ]; then
	echo "extracted patch did not contain sm8250-oneplus-kebab.dts" >&2
	exit 1
fi

echo "=== diff vs dts/upstream/sm8250-oneplus-kebab.dts ==="
if diff -u dts/upstream/sm8250-oneplus-kebab.dts "$up"; then
	echo "upstream snapshot is current"
	upstream_changed=0
else
	echo "WARNING: armbian/build kebab DTS changed vs dts/upstream/"
	upstream_changed=1
fi

echo "=== apply local QCA6390 patch onto extracted upstream ==="
mkdir -p "$WORKDIR/apply/arch/arm64/boot/dts/qcom"
cp "$up" "$WORKDIR/apply/arch/arm64/boot/dts/qcom/sm8250-oneplus-kebab.dts"
if patch -d "$WORKDIR/apply" -p1 --forward < dts/patches/0001-sm8250-oneplus-kebab-qca6390-pmu-wifi.patch; then
	echo "wifi patch applies"
else
	echo "wifi patch does NOT apply to current armbian kebab DTS — rebase dts/patches/" >&2
	exit 1
fi

if [ "$upstream_changed" -ne 0 ]; then
	echo "rebase needed: copy the extracted DTS to dts/upstream/ and refresh the patch" >&2
	exit 1
fi
echo "armbian kebab DTS watch: ok ($found)"
