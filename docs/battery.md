# Battery / charge limit

The 8T pack is 2S Li-ion (`simple-battery` in the kebab DTS, 4.35 V/cell design).
Sitting at 100% on USB for days is worse for calendar aging than parking around
80%. **This tree cannot set that cap.** Charging continues in hardware with no
Linux stop switch.

## What is bound

`/sys/class/power_supply/` has only the fuel gauge:

```
bq27541-0   type=Battery   i2c16 @ 0x55   driver bq27xxx-battery
```

Typical always-plugged reading: `status=Charging`, `capacity=100`,
`voltage_now` ≈ 8.67 V, `current_now` a 1–3 mA trickle. There is no
`charge_control_end_threshold` / `charge_control_start_threshold` /
`input_current_limit`. The gauge nodes look writable as root; writes only
change reported values (or are rejected). They do **not** open the charge
path.

`/sys/devices/platform/battery` is the DT `simple-battery` node. No driver.

## Two chargers, neither usable

### PM8150B SMB5 (main USB charge)

Under `spmi@c440000/pmic@2`:

| node | compatible | live status |
|------|------------|-------------|
| `charger@1000` | `qcom,pm8150b-charger` | **disabled** |
| `typec@1500` | `qcom,pm8150b-typec` | **disabled** |
| `usb-vbus-regulator@1100` | `qcom,pm8150b-vbus-reg` | **disabled** |
| `fuel-gauge@4000` | `qcom,pm8150b-fg` | **disabled** |

The platform driver `qcom-pm8150b-charger` is built in
(`CONFIG_CHARGER_QCOM_SMB5=y`) and never binds, because the node is off.
Those children come from the PM8150B include, not from the kebab DTS; kebab
does not turn them on.

### BQ25980 (flash / switched-cap)

`&i2c5` / `charger@66` is `ti,bq25980`, `status = "ok"`, **unbound**.
Armbian current has `CONFIG_CHARGER_BQ25970=y` (`bq2597x-charger`) and
**`CONFIG_CHARGER_BQ25980 is not set`**. Do not bind the 25970 driver onto
this chip. Even with the right driver this IC is a charge pump for fast
charge, not the everyday USB CC-CV path, and it has no SOC stop.

## Do not enable only the SMB5 node

Same class of footgun as [dispcc](display.md). The Type-C gadget
(`usb_1` / `a600000`, NCM) shares that port with VBUS / Type-C. Flipping
`charger@1000` (or Type-C / VBUS) to `okay` and rebooting can drop gadget
SSH. Leave all four PM8150B power nodes disabled until they come up
**together**, and only after the sysfs contract is known — ideally a real
`charge_control_end_threshold` on the SMB5 psy.

A userspace loop that watches `bq27541-0/capacity` cannot stop charge. Do
not add one.

## Until the charger binds

Unplug Type-C when you do not need the gadget or adb. Wi-Fi SSH stays up
independently (see [wifi.md](wifi.md)). That is the only safe way to get
the pack off 8.7 V today.
