# Display (simpledrm only)

What you see after boot is the **bootloader framebuffer** via `simpledrm` (`9c000000`, 1080×2376, 32 bpp). There is no `/sys/class/backlight`. Blanking is a userspace write to `/sys/class/graphics/fb0/blank` plus a black fill of `/dev/fb0` (AMOLED) — that is what `scripts/kebab-display` does.

`msm-mdss ae00000.display-subsystem` probes with **-110 ETIMEDOUT**. MDSS wants:

```
power-domains = <&dispcc MDSS_GDSC>;
```

and the DSI clocks from `dispcc` (`clock-controller@af00000`). Upstream kebab DTS enables `&mdss` but leaves **`&dispcc` disabled**. DSI0/1, the 7 nm PHYs, and the panel node are also off. This 6.18 Armbian kernel has **no** `panel-samsung-amb655x` / oplus20828 driver.

## Do not enable only dispcc

Setting `dispcc` to `okay` and rebooting **hangs** the phone (no USB gadget, no Wi-Fi, no SSH). Likely causes, not fully isolated:

- DPU child re-init tears down the bootloader scanout and nothing puts a picture back
- deferred-probe deadlock: MDSS now waits on DSI PHY clocks that are still disabled
- `dispcc` also lists DP PHY clocks; Type-C QMP PHY (`phy@88e8000`) is disabled (HS-only gadget)

Leave `dispcc` disabled until **all** of these land together: `dispcc` + DSI0 + PHY + supplies + a real panel driver. A candidate driver lives out of tree in Xo666/mainline-instantnoodle (`panel-samsung-amb655x.c`). Do not treat that as packaged in Armbian current.

`&gpu` is also `disabled` in the kebab DTS. That is separate.

## Power key

`pm8941_pwrkey` is `/dev/input/event1`. systemd-logind defaults to `HandlePowerKey=poweroff`. The overlay sets that to `ignore` and runs `kebab-powerd`:

| input | action |
|-------|--------|
| short KEY_POWER | `kebab-display toggle` |
| hold 3 s | `systemctl poweroff --force`, then sysrq `o` |
| 5 min idle (screen on) | blank |
| Power + Vol-Up 15–20 s | PMIC hard reset (hardware, always) |
