# Battery / charge limit

The 8T pack is 2S Li-ion (`simple-battery` in the kebab DTS, 4.35 V/cell
design). Sitting at 100% on USB for days is worse for calendar aging than
parking around 80%.

On **kebab-dsi**, the PM8150B SMB5 charger is bound. Clearing
`charging_enabled` stops the battery-side charge switch. VBUS can still
feed VSYS (USB-C as PSU, pack as UPS). The shipped `dtb/` (dispcc off)
still leaves SMB5 disabled.

There is no `charge_control_end_threshold`. 80% is userspace: watch
`bq27541-0/capacity` and write `0`/`1` to SMB5. Probe's init seq turns
charging **on**, so a reboot starts charging again until something writes
`0`.

## What is bound (kebab-dsi)

```
bq27541-0          type=Battery   i2c16 @ 0x55   bq27xxx-battery
pm8150b-charger    type=USB       spmi charger@1000   qcom-pm8150b-charger
```

Stop / resume:

```sh
echo 0 > /sys/class/power_supply/pm8150b-charger/charging_enabled
echo 1 > /sys/class/power_supply/pm8150b-charger/charging_enabled
```

Live check: `pm8150b-charger/status` goes `Not charging` / `Charging`.
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
