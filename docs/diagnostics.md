# Persistent reset diagnostics

The kebab kernel source in this repo has two complementary reset-forensics
paths:

- **ramoops/pstore** preserves panic/oops records, the kernel console, and
  userspace pmsg markers in a reserved 4 MiB RAM region.
- **PM8150 PON logs** read the PMIC's latched GEN2 power-on, power-off, fault,
  and S3-reset registers during `qcom-pon` probe.

They answer different questions. Ramoops can retain the kernel's last words;
the PMIC can distinguish events such as software/PS_HOLD shutdown, watchdog,
long key press, UVLO, and over-temperature even when no useful kernel record
survives.

## Build requirements

The DTS reserves `0xb0000000–0xb03fffff` in both generated safe and display
DTBs:

| area | size | purpose |
|------|------|---------|
| dmesg record | 256 KiB each | panic/oops (`max-reason = 2`) |
| console | 1 MiB | circular kernel console |
| pmsg | 256 KiB | explicit userspace markers |
| ECC | 16 bytes per block | recover limited corruption after a hard reset |

The remainder provides about eleven dmesg slots. ECC and metadata make each
slot's usable payload slightly smaller than its nominal size. Persistent
ftrace is deliberately disabled.

The required Kconfig commands and full build sequence are in
[build.md](build.md). In particular,
`CONFIG_PSTORE_DEFAULT_KMSG_BYTES=262144` avoids limiting each 256 KiB record
to the old 10 KiB default.

The same ramoops reservation in safe and display DTBs is intentional: after a
display-DTB crash, a safe-DTB boot must map the identical region to recover the
record. The checked-in `dtb/` binary remains the pre-existing safe default and
is not silently replaced by this source change.

## PMIC reason log

`qcom-pon` remains a module and retains its existing reboot-mode, power-key,
and RESIN behavior. On the exact `qcom,pm8998-pon` compatible used by PM8150,
it performs diagnostic-only reads and logs lines with a stable prefix:

```text
PMIC reset reason: raw ...
PMIC reset reason: power-on=...
PMIC reset reason: boot=warm ...
PMIC reset reason: power-off=...
PMIC reset reason: fault=...
PMIC reset reason: s3-reset=...
```

Search the current boot with:

```sh
journalctl -k -b | grep -F 'PMIC reset reason:'
```

Interpretation details:

- `pon` is a bitmap, so every set power-on bit is printed rather than only the
  least-significant one.
- `warm` is an opaque GEN2 warm-boot latch. A nonzero value identifies a warm
  boot, but this driver does not invent undocumented per-bit names for it.
- `off` selects whether `poff`, `fault1/2`, or `s3` contains the relevant
  previous shutdown reason. Decoding is gated by those selector bits so stale
  reason registers are not presented as current causes.
- `soft-rb` is the stored reboot-mode byte. It is logged raw and is not treated
  as a hardware fault reason.
- A failed register read produces a warning and a missing bit in `valid`; it
  never aborts PON probe and never clears or writes a diagnostic latch.

## Live result on kebab (kernel #67)

Both the safe and display DTBs booted successfully with kernel #67. The live
checks confirmed the exact 4 MiB reservation, the ramoops platform device,
the pstore backend, and the PM8150 GEN2 decoder. Ordinary `reboot` consistently
reported:

- power-on: hard reset plus external supply;
- previous power-off: `PS_HOLD`;
- warm latch: zero, therefore classified as cold by the read-only decoder.

A harmless pmsg/console marker test did **not** survive that ordinary reboot.
The next boot found no pstore records and reported stale, uncorrectable ramoops
headers. This indicates that the PMIC `PS_HOLD` / ABL path does not preserve
this DRAM range across a normal reboot on the tested phone.

The backend itself was checked independently: after writing new pmsg and
console markers, unbinding and rebinding `b0000000.ramoops` within the same
boot recovered both records exactly. That proves the reservation, pmsg writer,
console writer, ECC layout, and pstore reader work before firmware resets the
machine. The test-only records were then removed without exporting their
contents.

Consequently, ramoops may still preserve a panic or watchdog reset if that
reset path retains DRAM, but that has not been tested. An intentional panic is
not justified merely to make the normal-reboot test pass. The PMIC reason log
remains useful even when ABL destroys the ramoops evidence.

## Finding pstore records

Armbian already mounts pstore. `systemd-pstore.service` normally uses
`Storage=external` and `Unlink=yes`, so it moves records out of
`/sys/fs/pstore` during boot. Always inspect both locations:

```sh
find /sys/fs/pstore /var/lib/systemd/pstore \
  -maxdepth 1 -type f -print 2>/dev/null
```

Typical names include:

- `dmesg-ramoops-*` — panic/oops kmsg records
- `console-ramoops-*` — persistent kernel console
- `pmsg-ramoops-*` — explicit userspace markers

Use `less` or a narrow `grep` locally. An empty `/sys/fs/pstore` alone does not
mean that no record existed; systemd may already have archived and unlinked it.

## Harmless retention probe

This is safe to use when evaluating a different firmware/reset path, but the
normal `PS_HOLD` / ABL reboot tested with kernel #67 did not retain the markers.
Run it only after a newly built kernel and both matching DTBs have been
installed and a reboot has been explicitly approved. It does not trigger a
panic:

```sh
printf '%s\n' 'kebab-pstore-normal-reboot-test' > /dev/pmsg0
printf '<6>%s\n' 'kebab-console-normal-reboot-test' > /dev/kmsg
sync
reboot
```

After the next boot, search both pstore locations for the two markers. Finding
them would prove that the tested reset path retained DRAM. On the current
kebab ABL path they were absent after a normal reboot, while a same-boot driver
rebind recovered them. Any SysRq or intentional panic test is a separate
destructive action and is not part of the normal procedure.

## Limits and privacy

- Ramoops depends on DRAM contents surviving. A true cold power loss, battery
  disconnect, bootloader memory scrub, or overwrite of the reserved range can
  leave it empty. PMIC latch logs are the fallback for those cases.
- A normal reboot does not create a panic/oops dmesg record; use the console and
  pmsg marker test instead.
- `systemd-pstore` may archive a record only once and then unlink the firmware
  copy.
- Console and dmesg records can contain kernel command-line values, device
  serials, network addresses, host identity, filesystem UUIDs, or other local
  configuration. Before publishing any excerpt, remove those values as well
  as SSIDs, passwords, BSSIDs, account hashes, and SSH material. Do not add
  live pstore dumps to this repository.
