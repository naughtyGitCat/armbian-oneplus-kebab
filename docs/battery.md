# Battery / charge limit

The 8T pack is 2S Li-ion (`simple-battery` in the kebab DTS, 4.35 V/cell
design). Sitting at 100% on USB for days is worse for calendar aging than
parking around 80%.

On **kebab-dsi**, the PM8150B SMB5 charger is bound. Clearing
`charging_enabled` stops the battery-side charge switch. VBUS can still
feed VSYS (USB-C as PSU, pack as UPS). The shipped `dtb/` (dispcc off)
still leaves SMB5 disabled.

There is no `charge_control_end_threshold`. Manage the switch with
[`scripts/kebab-charge`](../scripts/kebab-charge) (`/usr/local/sbin/kebab-charge`
on the phone). Probe's init seq turns charging **on**, so a reboot starts
charging again until `kebab-charge stop`.

```sh
kebab-charge status
kebab-charge stop     # park the pack
kebab-charge start    # allow charge
```

`start`/`stop` are aliases for `on`/`off`. `install-overlay.sh` installs
the script.

## What is bound (kebab-dsi)

```
bq27541-0          type=Battery   i2c16 @ 0x55   bq27xxx-battery
pm8150b-charger    type=USB       spmi charger@1000   qcom-pm8150b-charger
```

Under the hood that is `pm8150b-charger/charging_enabled`. Live check:
`kebab-charge status` (SMB5 `Not charging` / `Charging`).
`bq27541-0/status` is a bad observer at 1–2 mA trickle (gauge still says
Charging). `pm8150b-charger/current_now` is the **USB-in IIO** channel,
not IBAT — it reads 0 when the switcher is off even though VBUS is up.

## What stayed off

Under `spmi@c440000/pmic@2`:

| node | compatible | status |
|------|------------|--------|
| `charger@1000` | `qcom,pm8150b-charger` | **okay** on kebab-dsi |
| `typec@1500` | `qcom,pm8150b-typec` | disabled |
| `usb-vbus-regulator@1100` | `qcom,pm8150b-vbus-reg` | disabled |
| `fuel-gauge@4000` | `qcom,pm8150b-fg` | disabled |

USB gadget stays `dr_mode = peripheral`. 8 Pro enables charger+typec+vbus
and flips USB to `otg` + role-switch; kebab did not. Charger probe still
writes `TYPE_C_MODE_CFG` TRY_SNK (gadget risk). First boot with this DTB
kept `usb0`.

Do not bind BQ25980 with the BQ25970 driver. `CONFIG_CHARGER_BQ25980` is
unset. That IC is the flash charge pump, not the everyday CC-CV path.

## Rollback

`/boot/boot_a.pre-smb5.img` and
`sm8250-oneplus-kebab-dsi.dtb.pre-smb5` were saved on the phone before
the first SMB5 flash. `pack-abl-boot.sh safe --flash` is the dispcc-off
DTB (SMB5 off too).
