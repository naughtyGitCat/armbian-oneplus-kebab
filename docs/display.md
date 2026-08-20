# Display

Linux scanout works on `6.18.43-kebab-dsi` plus the display DTB
(`sm8250-oneplus-kebab-dsi.dtb`). The panel shows a **stable framebuffer
console** (`getty@tty1`, `fgconsole=1`). That is the picture criterion.

The shipped `dtb/sm8250-oneplus-kebab.dtb` still has `&dispcc` disabled.
Official Armbian `current` therefore still boots ABL `simpledrm` only
(`msm-mdss` `-110 ETIMEDOUT`). Blanking there is `fb0/blank` plus a black
fill — `scripts/kebab-display` still does that, and it also works on
`msmdrmfb`.

| | |
|---|---|
| driver | `panel-samsung-amb655x` bound at `ae94000.dsi.0` |
| KMS | `msm` 1.13 on `ae01000.display-controller` (`card1-DSI-1`) |
| FB | `msmdrmfb` 1080×2400 32 bpp, packed `stride=4320` (ABL YSTRIDE; ABL simpledrm was 1080×2376) |
| console | `getty@tty1` on `tty1`; `fb0` `virtual_size=1080,2400` |
| backlight | `/sys/class/backlight/ae94000.dsi.0` DCS raw 0–2047 |
| GPU | still **disabled** (`no GPU device was found`) |

## What actually made a picture

Snow through `#62` was HS FIFO underflow, not GEM / DSC / panel.

Linux 7nm PHY programmed `CLK_CFG0=0xE1` (`pclk=bit/14` = 78.5 MHz) while
ABL uses `CLK_CFG0=0x31` / `CFG1=0x31` (`pclk=bit/6` = 183.229 MHz).
`FIFO_STATUS` was `0x99991310` (EMPTY|UNDERFLOW on all four lanes) vs ABL
`0x11111310` (EMPTY only). `#8` unscaled pclk to bit/6 without raising MDP
and the MDP FIFO under-ran (`dsi_err_worker status=0xc`). Probe stored the
200 MHz core clock as `max_core_clk_rate`, so OPP could never climb.

| hop | change | webcam |
|---|---|---|
| `#64` | force command-mode `pclk=bit/6` + pin DPU core at **460 MHz** (`DPU_PERF_MODE_FIXED`) | **stable solid red** (CONST fill from `#38`) |
| `#65` | revert `#38` CONST fill; restore GEM + CSC in `dpu_plane_flush` | **readable Linux fbcon** (systemd journal / getty), no snow, no flash |

Live `#65`:

| clock / status | value |
|---|---|
| pclk | 183229000 |
| byte | 137421750 |
| mdp core | 460000000 |
| FIFO_STATUS | `0x11111310` (ABL match) |
| panel | AMB655X 1100 Mbps FFC, `0x60=0x10` (120 Hz) |
| fb0 | `1080,2400` stride `4320` |

Black tape on the glass is physical, not a scanout bar. Desk-cam bursts
often only see the earpiece strip.

`#38` solid-fill is stalled (`patch-dpu-solid-fill.py` exits). Do not
re-apply it. `patch-dpu-revert-solid-fill.py` is the `#65` path.

## Keep / do not

Keep (required for the picture, or ABL-matched and snow-neutral):

- `pclk=bit/6` (`patch-dsi-pclk-div6.py`)
- MDP 460 MHz fixed (`patch-dpu-mdp-460.py`)
- TPG=0, `HS_TIMER=0x4ea60`, `ERR_INT_MASK0=0x7ffffbff`
- `FORCE=0`, `LANE_CTRL1=0`, `CLKOUT=0`, `TRIG=0x4`
- GPIO 75 reset pulse
- Lineage 1.1G PHY timings, FFC 1100 Mbps, `0x60=0x10`
- `clk_ignore_unused`
- DSC 2:2:1 with `pic_width=1080` per engine
- packed pitch 4320, dual VIG
- `MIPI_DSI_MODE_LPM` for panel `on()`

Do not:

- skip the reset pulse (`#27`–`#29`, `#63` black)
- HS DCS `on()` / `MIPI_DSI_CLOCK_NON_CONTINUOUS` (black)
- double `mode.clock` for 120 Hz
- 825 M analog VCO (never actually ran HS; pixel `-22`)
- live-poke DPU (`INTF_PANEL_FORMAT` write rebooted the SoC)
- INTF `AUTOREFRESH` (`#56` stalls kickoff)
- xml `0x1f4=1` (`#61` starved the picture)
- re-apply `#38` solid-fill
- enable `&dispcc` **alone** (hang)
- ship `kebab-dsi.dtb` as the official `dtb/` default unless asked

Safe DTB + `clk_ignore_unused` still leaves ABL scanout running
(`msm-mdss` `-110`). That path is a readable bootloader console, not Linux
KMS.

Boot-time `DSI PLL(0) lock failed` is a warning during PHY probe; DSI still
binds afterwards. Do not treat that as a hang.

After a display-DTB reboot the Type-C gadget may not re-enumerate. Wi-Fi
SSH still works; USB gadget SSH (`root@172.16.42.1`) is the recovery path
on the safe DTB.

## Bring-up hops

Hops below are the snow / black path. `#64` / `#65` at the end of this
section are the working picture. Pitch was later packed to 4320 (`#35`).

KMS coming up was not a picture. First scanout was black with a few
vertical red lines:

- `msmdrmfb` pitch is **4352**, not `1080×4=4320`. Userspace must pad each
  line (8 pixels / 32 bytes). A packed 1080 write shears the test pattern.
- The panel is command-mode DSC, 2×540 slices. Downstream sends PPS as DCS
  `0x9E` + 128 bytes, then `0x9D=1`. The generated driver packed PPS before
  RC parameters existed and wrote the raw 128 bytes (first byte `0x11` =
  `EXIT_SLEEP`). The decoder never got a PPS. Fixed in
  `kernel/panel-samsung-amb655x.c`.
- After the PPS fix the panel showed full-screen colorful snow: MSM
  hardcoded `slice_per_pkt=1` while the panel (and Lineage DT) wants 2.
  `apply-dsi-to-tree.sh` patches `dsi_host.c` so command-mode
  `slice_count==2` uses spp=2 (`wc = 1080+1`, one packet per line).
  spp=2 still snowed. Live topology was 2 LM + 2 DSC (`dsc=89 89`);
  DPU 6.0 programs each DSC 1.1 engine with full `pic_width=1080`
  while each mixer only feeds 540. Forcing 1 DSC / 1 LM (downstream
  also lists `<1 1 1>`) still snowed — DSC 1.1 on DPU 6 does not do
  two soft slices on one engine. Vendor default is `<2 2 1>` with
  `lm-split 540+540`. `patch-dpu-single-dsc.py` now keeps 2 DSC and
  programs each engine with `enc_ip_w` (540), not the panel
  `pic_width` (1080). PPS to the panel is still the full 1080 config.
- Forcing uncompressed RGB888 (`AMB655X_UNCOMPRESSED_DIAG`, no PPS,
  `dsi->dsc = NULL`) still snowed, with more black blocks (command-mode
  ~91% of 4×1.026 Gbps). DSI TPG checkered-rectangle (bypasses DPU,
  same STREAM0 packer + PHY) also snowed. So this is not DSC-merge or
  SSPP stride (live YSTRIDE is 4352). Next lever: panel FFC is written
  for downstream 1100 Mbps; live PLL was 1.026 Gbps. Mode porches now
  scale HS to ~1.099 Gbps. Uncompressed at 1.099 Gbps still snowed
  (the earlier black screen was `fb0/blank=1`). Mainline *drops* HS
  to ~400 Mbps when DSC is attached; `patch-dsi-cmd-hs-clock.py`
  keeps command-mode HS at the mode clock so DSC + FFC can both be
  1.1 G. `#8` unscaled *both* byte and pixel (`pclk=183229000
  byte=137421750 dsc=1`). STREAM0 was still `hdisp=360 wc=1081`, so
  DSI drained the MDP FIFO at 24bpp-line rate: continuous
  `dsi_err_worker: status=c` (FIFO|MDP_FIFO_UNDERFLOW) and still snow.
  7nm `dsiN_phy_pll_out_dsiclk` pix_div has no `CLK_SET_RATE_PARENT`,
  so `#9` kept byte/PHY at 1.1 G and left `pixel_clk` at raw DSC-scaled
  78858050. `clk_pixel` 1/1 only accepts `|pclk-parent|<100 kHz`;
  `bit/14` is 331 kHz off, `clk_set_rate` returned `-22`, panel init
  failed. `#10` snaps pclk to `bit/N` (N=1..15). Clocks then split
  (`pclk=78526714 byte=137421750`, HS 1.1 G) and the underrun storm
  stopped, but kickoff hit `wait_for_idle -110` on pp:0: default TE
  is `mdp_vsync_p` while downstream `te-pin-select=<1>` is
  `mdp_vsync_s`. First unprepare also dropped `vddio`/`avdd` because
  prepare skipped the enable. `#11` sets `qcom,te-source =
  "mdp_vsync_s"` and always enables the panel rails in prepare.
  Rails stayed up (`avdd`/`vddio` users≥1) but `wait_for_idle -110`
  on pingpong 0 continued (~88 ms, thousands of retries);
  `gpio66` is muxed `mdp_vsync` and sampled low. Kickoff is waiting
  on `INTR_IDX_PINGPONG`, which in command mode only fires after TE
  releases the INTF. Image `#12` arms INTF watchdog TE (`dpu te-source=timer0 vsync_source=15`; DPU 6 needed the v8 vsync_sel helper). gpio66 *is* pulsing. pingpong still never completes (`wait_for_idle -110`, MDP IRQ idle vs millions of `dsi_isr`, boot `status=4`). TE is not the missing PP-done. `#13` programs `INTF_CFG2_DCE_DATA_COMPRESS` on DPU 6 (`cmd_cfg compress=1 widebus=0 cfg2=0x1100`). First kickoff still `status=4` and `wait_for_idle -110`. Webcam after unblank: full-screen vertical magenta/cyan snow, RGBW not visible. `#14` uncompressed (`dsc=0`, `pclk=183229000`, `hdisp=1080 wc=3241`, `compress=0`). `wait_for_idle` gone, `dsi_isr` idle, msm_mdss IRQs advancing — DPU is completing frames — but the panel still snows, now with more black vertical bars. Uncompressed `0x9D=0` was written without the `0xF0` unlock the DSC path uses. `#15` writes `0x9D=0` inside the same `0xF0 5a5a` unlock as PPS; still snow with black bars, no RGBW. DPU still completes frames (`wait_for_idle` quiet). Unlock was not sufficient — panel is not showing RGB888 (still decoding as DSC, or PHY/lane/format).
`#16` forced 6G widebus (`hdisp=180`, `cfg2=0x1101`); same fine snow, still `status=4`. Lineage kebab has no `widebus-mode`. Reverted to the v2.5 gate. `#17` forced Lineage 7nm PHY timings; clocks already close, still snow. `#18` 1:1:1 unstalls (`wait_for_idle` 0) with vendor 2×540 PPS; still fine snow. `#19` programs command-mode `INTF_PANEL_FORMAT` RGB888 `0x213f`; still fine snow. `#20` `MIPI_DSI_CLOCK_NON_CONTINUOUS` blacks the HS scanout (LP DCS still works). Reverted; keep `CLKLN_HS_FORCE_REQUEST`. `#21` DSI TPG + uncompressed: dark, not a checkerboard — panel ignores `0x9D=0` and keeps decoding DSC. TPG unhooked. `#22` 1-slice×1080 PPS: **blocky snow + horizontal black lines** (first PPS-driven structure change). Decoder is on; 1-slice is the wrong geometry. `#23` restores vendor 2×540 + 2:2:1 and programs each DSC 1.1 engine with the **full** `pic_width=1080` (CAF `_sde_encoder_dsc_2_lm_2_enc_1_intf`; `enc_ip_w=540` is only for `initial_lines`). Live: `num_dsc=2 mode=0x3 hw_pic_w=1080 slice=540x30`, `cfg2=0x1000` (leftover BIT(8) cleared), `wait_for_idle=0`, msm IRQs advancing. Webcam: same **fine vertical magenta/cyan snow**, RGBW invisible, `status=4` remains. Shrinking `DSC_PICTURE` to 540 was what stalled 2:2:1. `#24` disconnected `INTF_MUX` from PP0 when DSC was active (`pp=-1 dsc=0x3`): `wait_for_idle -110` storm, `dsi_isr` idle, `status=4` gone — DSI starved; GRAM kept the previous snow. Rolled back to `#23`. INTF must stay bound to PP0.
	Live MMIO on `#23` (DSI 6G `io_offset=+4`, INTF1 `mdp+0x6a800`, DSC0 `mdp+0x80000`): STREAM0 `wc=1081 dt=0x39` `h=360 v=2400`, COMP `EN dt=0x39 slice_w=540`, INSERT_DCS `0x2c/0x3c`, burst on, DSC `COMMON_MODE=0x3` `PICTURE=1080x2400` `SLICE=540x30` `bpp=8.0` `init_lines=3`, INTF `cfg2=0x1000` mux low-nibble PP0. Packer and 2:2:1 engines match CAF. `FIFO_STATUS` live is `0x11111010` (HS/LP EMPTY + undoc bit4), sometimes `FULL|UNF` during a line — `dsi_err_worker status=4` is those EMPTY bits, not MDP overflow. `MDP_CTRL2` was `0x10006`: burst OR'd onto reset `DST_FORMAT2=RGB565(6)` while `CMD_CFG0` is RGB888(8). `#25` programs `DST_FORMAT2=RGB888` (`mdp_ctrl2=0x10008 dst2=8` live). Webcam: same **fine vertical magenta/cyan snow**, RGBW invisible. Format leftover was real and is fixed; it was not the picture. Live scanout on `#25`: VIG0 (DMA0 idle) `SRC_SIZE=1080x2400` `YSTRIDE=4352` `SRC0_ADDR=0x2000` which **is** the `stolenfb` GEM IOVA (`10444800` bytes, pitch 4352), `FORMAT=0x236ff` XR24, mixer `BLEND0=0x100` (const alpha, not pixel X). `CTL_FETCH_PIPE_ACTIVE=0` is unused on DPU 6 (`>=7` only). The DPU is fetching the painted fb0; RGBW-invisible snow is not a wrong buffer. `#26` sent panel `on()` as HS DCS (`mode_flags &= ~LPM`, `panel on HS dcs flags=0x0`). Transfers succeeded, backlight 2047, `dsi_isr` running, `status=4` remains — webcam is a **black** panel (same desk `[1]` frame as `#25` snow). Same class as `#20` non-continuous: HS command mode on this continuous-clock link blacks the scanout. Rolled back to `#25` (`pre-hs-dcs.img`). Keep `MIPI_DSI_MODE_LPM` for `on()`.
	sm8250-mainline [MR11](https://gitlab.com/sm8250-mainline/linux/-/merge_requests/11) says **with reset, backlight works but the panel displays garbage; works if reset is skipped**, and uses `0x60=0x10`. `#27` skipped the reset pulse (`GPIOD_OUT_LOW`, `0x60=0x10`, keep 1.1G porches): webcam **black** (85–101 KiB vs snow ~314 KiB). `#28` isolated skip-reset with `0x60=0x00`: still **black**. `#29` matched MR11 more closely — never claim gpio75, drop `panel_reset_pins` from pinctrl-0, delay-only reset, `0x60=0x10`. gpio75 stayed ABL `out high func0 8mA pull-up`; webcam still **black**. Skip-reset is lethal here: Linux re-inits the 7nm PHY, and without a panel reset the HS link never recovers. Restore the pulse. `#30` restores reset + `0x60=0x00` and drops V4.1 D-PHY HSTX `0x88` → `0x66` (`hstx=0x66 res_top=0x3d res_bot=0x39`). Webcam: same **fine vertical magenta/cyan snow** as `#25`, RGBW invisible. Analog drive is not the picture.

Safe DTB + `clk_ignore_unused` leaves ABL scanout running (`msm-mdss` `-110`). Webcam: **readable systemd console** (streaky, `/tmp/kebab-cam/desk-abl-safe.jpg`). The panel, PHY, DSI packer and DSC engines work; Linux msm reprogramming is what snows. Live ABL MMIO (DSI 6G `xml+4`, PHY CMN `0xae94400`, INTF1 `0xae6b800`, DSC0/1):

| block | ABL (picture) | Linux `#30` (snow) |
|---|---|---|
| STREAM0 | `wc=1081 dt=0x39` `h=360 v=2400` COMP `0x3901` slice 540 | same packer; COMP leftover `0x39003901` (STREAM1) |
| DSC 2:2:1 | `COMMON=0x3` `PICTURE=1080x2400` `SLICE=540x30` `CHUNK=540` | same |
| LANE_CFG / PIN_SWAP | `0x21/0x84`, swap 0 | same |
| HSTX / rescode | `0x88 / 0x3d / 0x39` | `#30` forced `0x66` |
| PHY timings | `00 1C 07 07 23 22 07 07 05 02 04 00 18 17` | Lineage `00 24 0A 0A 26 25 09 0A 06 02 04 00 1E 1A` |
| INTF_CONFIG2 | `0x100` (BIT8) | `0x1000` (`DCE_DATA_COMPRESS` BIT12) |
| INTF_MUX | `0` (low nibble PP0) | `0x000f0000` (low nibble PP0 + leftover) |
| MDP_CTRL2 | `0x10006` dst2=6 | `#25` `0x10008` dst2=8 |

`#31` forces the ABL 14-byte timings and restores HSTX `0x88`. Live MMIO matches ABL analog (`TIMING 00 1C … 18 17`, `hstx=0x88`). Webcam: same **fine vertical magenta/cyan snow**, RGBW invisible. PHY timings and HSTX are not the picture. `#32` writes INTF_CONFIG2 `0x100` (BIT8, no `DCE_DATA_COMPRESS` BIT12; that bit is video-mode DPU ≥7). Live `cfg2=0x100`. Still snow. `#33` stops RMW leftovers: INTF_MUX write 0 (PP0, drop `0xf0000`) and CMD_COMP write `0x3901` / COMP2 `0x21c` (drop STREAM1). Live MUX/COMP now match ABL. Still snow. `#34` sets CMD_CFG0 `INTERLEAVE_MAX=1` (`CFG0=0x100008`). Still snow. DSI/PHY/INTF/DSC now match ABL except MDP_CTRL2 dst2 8 vs 6.

Safe-boot ABL vs Linux `#34` DPU fetch (the remaining picture-path delta):

| block | ABL (picture, simpledrm 4320) | Linux `#34` (snow) |
|---|---|---|
| SSPP | **VIG0+VIG1** each 540×2400, VIG1 XY=0x21c, ADDR=`0x9c000000`, YSTRIDE=`0x10e0`, FMT=`0x237ff` | **VIG0 only** 1080×2400, ADDR IOVA `0x2000`, YSTRIDE=`0x1100` (4352), FMT=`0x236ff` |
| CTL_LAYER | LM0=`0x1000005` LM1=`0x1000028` | both `0x1000002` (same VIG0) |
| LM blend / OP | BLEND0=`0x400`, OP=`0` / `0x80000000` | BLEND0=`0x100`, OP=`0x2` / `0x80000002` |
| DSC / INTF | identical to matched Linux | identical |

`#35` packed pitch 4320 and split 1080→540+540. Live: fb stride 4320, VIG0 RECT0+RECT1 SmartDMA (`SRC=540` `XY=0`/`0x21c` `MULTIRECT=0x3` `STRIDE=0x10e010e0` both ADDR=`0x2000`), VIG1 idle, CTL still `0x1000002`+EXT3 RECT1. Webcam: same **fine vertical magenta/cyan snow**, RGBW invisible (`desk-dualvig.jpg`). Pad+single-pipe source-split was not the picture.

`#36` two physical VIG SSPPs + per-mixer CTL_LAYER. Live: VIG0 `540 XY=0` VIG1 `540 XY=0x21c` both `STRIDE=0x10e0 ADDR=0x2000 MULTIRECT=0`, CTL LM0=`0x1000002` LM1=`0x1000010` (ABL mix=5 vs Linux mix=2). Fetch geometry now matches ABL. Webcam: same **fine vertical magenta/cyan snow**, RGBW invisible (`desk-twosspp.jpg`). Dual-VIG packed fetch is not the picture.

`#37` MDP_CTRL2 `dst2=6` (`0x10006`, ABL). Live `dsi mdp_ctrl2=0x10006 burst=1 wide=0 dst2=6`. Webcam: same **fine vertical magenta/cyan snow**, RGBW invisible (`desk-dst2abl.jpg`). dst2 8 vs 6 is not the picture.

`#38` SSPP solid-fill red (`CONST=0xff0000ff` `FMT=0x4237ff` BIT22 `ADDR=0`). No SMMU fetch. Webcam: same **fine vertical magenta/cyan snow** (`desk-solidfill.jpg`). Fetch/IOVA/GEM is not the picture — snow is after SSPP (LM/DSC/DSI/panel). PP_DSC_MODE=1, DSC0↔PP0 / DSC1↔PP1 bind looks correct. Linux `setup_dsc` ORs `PP_DCE_DATA_OUT_SWAP` BIT18 (endian flip); live poke is overwritten on the next commit. `#39` drops that bit.

`#39` no endian (`OUT=0x2c688`). Webcam: same **fine vertical magenta/cyan snow** (`desk-endian.jpg`). Safe-boot ABL DSC0/1 `0x00–0x140` is **byte-identical** to Linux helper RC (`COMMON=0x3` `ENC=0x3880ca` `CHUNK=0x21c0000` thresh/range match). STREAM0 `wc=1081 dt=0x39 h=360` `COMP=0x3901` slice 540 `CFG0=0x100008` `CFG1=0x13c2c` `CTRL2=0x10006` also match. ABL `OUT=0x6c688` **has** BIT18 — `#39` cleared the bit ABL uses. Remaining analog delta: ABL PLL `DEC=0x15 FRAC=0x1f908` VCO **825.338672 MHz** (byte 103.167 MHz, `CLK_CFG0=0x31` bit_div=1); Linux HS is still 1.1G with ABL's 825 M timings.

`#40` ABL byte=103167334 + BIT18 restored. Live `dsi byte forced ABL 103167334` `pclk=82533867 byte=103167334` `out_swap=0x6c688`. Webcam: **black** (`desk-ablhs.jpg` ~43 KiB). `wait_for_idle -110` on pp:0. ABL HS without matching FFC/pclk/TE stalls kickoff (same class as `#8`/`#10`–`#12`).

`#41` 1.1G byte + Lineage 1.1G PHY timings (`00 24 0A 0A 26 25 09 0A 06 02 04 00 1E 1A` live) + 1100 FFC. Live `pclk=78526714 byte=137421750` `CLK_CFG0=0xE1` `wait_for_idle=0` `CONFIG2=0x100` `DSC_CTL 0/1/7/7`. Webcam: same **fine vertical magenta/cyan snow** (`desk-lineagephy.jpg` ~319 KiB). Consistent 1.1G analog is not the picture.

`#42` ABL 825 M timings+byteclk + pclk `bit/14`. Live `dsi byte forced ABL 103167334` `pclk forced bit/14 58952762`. Webcam: **black** (`desk-ablhs14.jpg` ~43 KiB). `wait_for_idle -110` storm (452+). `#43` skipped the 1100 Mbps FFC (`AMB655X skip 1100 Mbps FFC`) on the same software clocks. Webcam: still **black** (`desk-skipffc.jpg` ~43 KiB). Live: `Failed to set rate pixel clk, -22`, PLL `DEC=0 FRAC=0 VCO=0`, `CLK_CFG0=0xF1`, timings ABL-correct, `wait_for_idle -110`. Software `byte_clk_rate=103167334` never programs the 7nm PLL: `dsi_link_clk_set_rate_6g` does `opp_set_rate(byte)` then `clk_set_rate(pixel)`; pixel 1/1 rejects `|pclk-parent|≥100 kHz` and the function returns before PHY enable, so analog stays off. Linux has **never actually run HS at 825 M**. FFC skip is irrelevant while the PLL is off. `#44` restored the 1.1G CCF snap and forced analog `DEC=0x15 FRAC=0x1f908` on **every** `vco_set_rate`, including the probe restore at `min_pll_rate=600 MHz`. Live: `dsi clk pclk=78526714 byte=137421750`, analog log `ccf 600000000 dec=0x15 frac=0x1f908`, then `Failed to set rate pixel clk, -22`, `Power on failed: -22`, panel DCS `-22`. Webcam: **black** (`desk-pllvco.jpg` ~40 KiB). `vco_sw_rate=600M` made clk_pixel 1/1 miss 78.5 MHz. `#45` only analog-overrides when `rate >= 800 MHz`. Live: native `ccf 600000000`, then `ABL ccf 1099374000 dec=0x15 frac=0x1f908`, **still** `Failed to set rate pixel clk, -22` / `Power on failed: -22`. Webcam: **black** (`desk-pllvco45.jpg` ~40 KiB). `clk_pixel_determine_rate` rounds dsiclk against the analog 825 M parent even when CCF-facing VCO is 1.1G. Analog does not belong in `vco_set_rate`. `#46` restores vanilla `set_rate`/`recalc` and rewrites DEC/FRAC in `vco_prepare`. Live: no pixel `-22`, `wait_for_idle=0`, `CLK_CFG0=0xE1`, prepare log `ABL ccf 1099373876 dec=0x15` — then a later `set_rate(1.1G)` overwrote analog to `DEC=0x1c FRAC=0x284a3` VCO **1.099 GHz**. Webcam: same **fine vertical magenta/cyan snow** (`desk-pllprep46.jpg` ~321 KiB). Kickoff is back; 825 M still did not stick. `#47` re-commits ABL analog from `set_rate` when `pll_on`. Live: analog **stuck** `DEC=0x15 FRAC=0x1f908` VCO **825.338672 MHz**, skip FFC, fb 1080×2400 blank=0 bl=2047 — but 53× `Failed to set rate pixel clk, -22`, `CLK_CFG0=0x41` (pix_div=4, not 0xE1/0x31). Webcam: same **fine vertical magenta/cyan snow** (`desk-pllprep47.jpg` ~358 KiB). Recalc reads analog 825 M so later `clk_pixel` 1/1 misses 78.5 MHz. `#48` skips analog writes once `pll_on` and makes recalc return CCF `vco_current_rate` (1.1 G). Live: prepare `ccf 1099374000` then **immediately** `Failed to set rate pixel clk, -22` / `Power on failed: -22` / `wait_for_idle -110` storm. Webcam: **black** (`desk-pllprep48.jpg` ~107 KiB). Recalc lie is not enough — `clk_pixel` 1/1 still observes analog 825 M (same class as `#44`/`#45`). **825 M analog cannot coexist with Linux `clk_pixel` 1/1 of 78.5 MHz.** `#49` reverts analog VCO hacks (CCF 1.1 G, working `#46` kickoff) and forces ABL LM blend `BLEND0_OP=0x400` / `mixer_op_mode=0` (Linux was `0x100` / `0x2`). Live: `dpu lm blend_op=0x400`, no pixel `-22`, `wait_for_idle=0`, `CLK_CFG0=0xE1`, `DEC=0x1c` VCO **1.099 GHz**. LM0 `OP=0 BLEND0=0x400 CONST=0x00ff0000`; LM1 `OP=0x80000000` same blend — **matches ABL mixer**. Webcam: same **fine vertical magenta/cyan snow** (`desk-lmblend49.jpg` ~352 KiB). Mixer blend is not the picture. Remaining ABL DPU delta: CTL mix=5 vs Linux mix=2. `#50` forces `DPU_STAGE_3` (mix=5) so CTL_LAYER matches ABL `0x1000005` / `0x1000028` and blend lands at stage slot +0x68. Live: `dpu plane stage=3`, `CTL LAYER0=0x1000005 LAYER1=0x1000028`, LM0/1 blend at +0x68 `0x400`/`0xff0000`, `wait_for_idle=0`. Webcam: same **fine vertical magenta/cyan snow** (`desk-ctlmixed50.jpg` ~365 KiB). Mixer/CTL now match ABL; not the picture. `#51` restores 1100 Mbps FFC (`0xE4`/`0xE9`) — analog is 1.1 G and DPU is fully matched; skip FFC was only for 825 M. Live: `AMB655X 1100 Mbps FFC`, `pclk=78526714 byte=137421750`, `CLK_CFG0=0xE1` `DEC=0x1c` VCO **1.099 GHz**, `wait_for_idle=0`. Webcam: same **fine vertical magenta/cyan snow** (`desk-ffc51.jpg` ~358 KiB). FFC + matched DPU is not the picture. Mixer/CTL/FFC/1.1G analog all lined up; remaining is DSC PPS vs encoder or DSI packer. `#52` restores Lineage 1.1G PHY timings (`00 24 0A 0A 26 25 09 0A 06 02 04 00 1E 1A`) — analog is 1.1 G, ABL 825 M UI counts were the wrong pairing. First combo of Lineage timings + matched mixer/CTL + FFC + 1.1 G analog. Live: `dsi 7nm phy force Lineage 1.1G timings`, TIMING **`00 24 0A 0A 26 25 09 0A 06 02 04 00 1E 1A`**, `CLK_CFG0=0xE1` `DEC=0x1c` VCO **1.099 GHz**, `wait_for_idle` quiet, `cfg2=0x100`, DSC `ENC=0x3880ca` `OUT=0x6c688` (ABL), helper PPS **byte-identical** to vendor `0x9E` blob. Webcam: same **fine vertical magenta/cyan snow** (`desk-linphy52.jpg`). Lineage timings on the matched DPU are not the picture; PPS/encoder already match vendor/ABL. `#53` sets panel `0x60=0x10` (vendor default 120 Hz) with reset — 60 Hz `0x00` snowed; skip-reset + `0x10` was black. Live: `AMB655X 120 Hz 0x60=0x10`, `AMB655X 1100 Mbps FFC`, Lineage timings, `pclk=78526714 byte=137421750`, no pixel `-22`. Webcam: same **fine vertical magenta/cyan snow** (`desk-rr120.jpg`). 120 Hz selector is not the picture. `#54` zeros DSI `CLKOUT_TIMING_CTRL` (ABL picture=0; Linux was `0x1a1e` = PHY `clk_post/pre`). Live `dsi clkout_timing=0` `CLKOUT=0`, kickoff good. Webcam: same **fine vertical magenta/cyan snow** (`desk-clkout54.jpg`). Controller clkout is not the picture. `#55` sets DSI `TRIG_CTRL=0x4` (ABL DMA-SW only; Linux was `0x80001004` TE+BLOCK_DMA). Live `dsi trig_ctrl=0x4`, `CLKOUT=0`, STREAM0 good, no `wait_for_idle`. Webcam: same **fine vertical magenta/cyan snow** (`desk-trig55.jpg`). TE/BLOCK_DMA trigger bits are not the picture. `#56` matches ABL INTF tearcheck: `AUTOREFRESH=0x80000001`, `HEIGHT=0xffff`, `WR_PTR_IRQ=1`, `THRESH=0x00040005` (Linux packing is continue<<16|start; ABL `0x00050004` is continue=5 start=4 — the hop inverted that). Live registers matched except THRESH packing. `wait_for_idle -110` returned (~280 ms). Webcam: same **fine vertical magenta/cyan snow** (`desk-tear56.jpg`). Tearcheck/AUTOREFRESH is not the picture and stalls kickoff — reverted. `#57` clears PHY `LANE_CTRL1` BIT(5)|BIT(6) (`0x60`→`0`, ABL) but still returns true so `dsi_host` keeps `CLKLN_HS_FORCE` (`LANE_CTRL=0x10000000`). Live `dsi 7nm LANE_CTRL1=0x0 (ABL, FORCE kept)`, no `wait_for_idle`. Webcam: same **fine vertical magenta/cyan snow** (`desk-lane57.jpg`). Isolated PHY continuous-clock bits are not the picture; keep (ABL-matched, snow-neutral). `#58` drops `CLKLN_HS_FORCE` without `MIPI_DSI_CLOCK_NON_CONTINUOUS`. Live `dsi lane_ctrl=0x0 (no FORCE)`, PHY `LANE_CTRL1=0`, STREAM0 good, no `wait_for_idle`. Webcam: same **fine vertical magenta/cyan snow** (`desk-force58.jpg`). FORCE is not the picture; #20 black was the NON_CONTINUOUS mode flag. Keep FORCE=0 (ABL, snow-neutral). Safe-DTB DSI raw (xml+4) vs Linux #58: named packer/COMP/LANE_CTRL/SWAP/EOT/TRIG/CLKOUT match. Remaining programmed deltas: `HS_TIMER` `0x4ea60` vs `0xffff`, `ERR_INT_MASK0` `0x7ffffbff` vs `0x13ff3be0`, xml `0x1f4` 1 vs 0, `TEST_PATTERN_GEN_CTRL` 0 vs `0x4` (`TPG_DMA_FIFO_MODE`). `#59` writes TPG_CTRL=0. Live `dsi tpg_ctrl=0`, STREAM0 good, no `wait_for_idle`. Webcam (`desk-tpg59.jpg`, 168 KiB): **structure change** — dense magenta/cyan snow collapsed to a dark field with sparse colored vertical streaks. TPG FIFO mode was mixing noise into MDP; keep TPG=0. Not solid red. `#60` writes `HS_TIMER_CTRL=0x4ea60` (ABL; Linux left reset `0xffff`, `TIMER_RESOLUTION=0`). Live `dsi hs_timer=0x4ea60`, TPG=0, STREAM0 good, no `wait_for_idle`. Webcam (`desk-hstimer60.jpg`): **full-frame cyan/blue vertical snow** — #59 dark+streaks was the HS timer starving the link. Keep HS_TIMER (ABL; restores the full-frame MDP/DSC path). Not solid red. Live SSPP VIG0+VIG1 `CONST=0xff0000ff` `FMT=0x4237ff` BIT22 `ADDR=0` `SRC=540×2400`; DSC0/1 `ENC=0x3880ca` `PICTURE=1080×2400` `SLICE=540×30` identical. Remaining programmed DSI: `ERR_INT_MASK0` ABL `0x7ffffbff` vs `0x13ff3be0`, xml `0x1f4` 1 vs 0 (undocumented, next to VERSION `0x1f0`). `#61` writes xml `0x1f4=1`. Live `dsi xml 0x1f4=1`, register stuck 1. Webcam (`desk-1f461.jpg`): **starved** — #60 full-frame snow collapsed back to #59-like dark field with sparse colored streaks. Not the picture; reverted (likely a status latch, not a pixel control). Keep TPG=0 + HS_TIMER. `#62` writes `ERR_INT_MASK0=0x7ffffbff` (ABL) on the #60 baseline. Live mask matches ABL, `0x1f4=0`. Webcam (`desk-err62.jpg`): same **full-frame cyan/magenta vertical snow** as #60. Irq mask is not the picture; keep (ABL, snow-neutral). DSI programmed path is exhausted (packer/COMP/CFG/TPG/HS_TIMER/FORCE/LANE_CTRL1/CLKOUT/TRIG/ERR_MASK). Live SSPP solid-fill still on; PP0/1 `DSC_MODE=1` `OUT=0x6c688`; CTL `DSC_ACTIVE=0x3` `INTF_ACTIVE=0x2` `LAYER=0x1000005/0x1000028`; merge_3d off. `#63` skips the GPIO reset pulse (MR11 delay-only) on that baseline. Live `AMB655X skip reset pulse`, FFC/0x60 still sent, blank=0 bl=2047. Webcam (`desk-skip63.jpg` ~109 KiB): **black**. Same class as `#27`–`#29` — PHY re-init without a panel reset kills HS. Restored `#62`. Keep the pulse. Do not skip-reset. Safe-DTB ABL vs Linux #53 (PHY CMN analog besides PLL/timings **matches**: HSTX/VREG/PEMPH/LANE_CFG). Remaining programmed deltas: INTF `AUTOREFRESH` ABL `0x80000001` vs 0, `TEAR_HEIGHT` `0xffff` vs `0x12e0`, `TEAR_THRESH` `5,4` vs `4,4`, `TEAR_VSEL` 0 vs timer0 `0xf`; PHY `LANE_CTRL1` ABL 0 vs Linux `0x60` (continuous-clock bits; `#20` cleared these *and* `CLKLN_HS_FORCE` and blacked); DSI `TRIG_CTRL` ABL `0x4` vs Linux `0x80001004` (TE+BLOCK_DMA); `HS_TIMER` ABL `0x4ea60` vs Linux reset `0xffff`. `INTF_PANEL_FORMAT` is `0x2100` on **both** (dmesg `0x213f` does not stick; not a delta).

`#64` forces command-mode `pclk=bit/6` (ABL `CLK_CFG0=0x31`/`CFG1=0x31`) and pins DPU core at 460 MHz (`fix_core_clk_rate=460000000`, `DPU_PERF_MODE_FIXED`; probe had stored 200 MHz as `max_core_clk_rate`). Live: `pclk=183229000` `byte=137421750` `mdp=460000000`, `FIFO_STATUS=0x11111310` (ABL match; `#62` was `0x99991310` HS UNDERFLOW). Webcam burst: **stable solid red**. Black tape on the glass is physical, not a scanout bar. CONST fill pixels survive DSC/DSI/panel. Pairing bit/6 without MDP 460 was `#8` (`status=0xc`).

`#65` reverts `#38` solid-fill (`dpu_plane_flush` back on GEM + CSC). Live `getty@tty1` active, `fgconsole=1`, fb0 `virtual_size=1080,2400` `stride=4320`. Webcam burst after boot: **readable Linux fbcon** (systemd journal / getty), no snow, no flash. GEM fetch works. Keep pclk=bit/6 + MDP 460. Official `kebab.dtb` still has `&dispcc` disabled.

## Do not enable only dispcc

Setting `dispcc` to `okay` **by itself** and rebooting **hangs** the phone (no USB gadget, no
Wi-Fi, no SSH). The working path is the display DTB, which enables `dispcc` +
DSI0 + PHY + panel together. Likely causes of the hang, not fully isolated:

- DPU child re-init tears down the bootloader scanout and nothing puts a picture back (no panel driver)
- deferred-probe deadlock: MDSS now waits on DSI PHY clocks that are still disabled
- `dispcc` also lists DP PHY clocks; Type-C QMP PHY (`phy@88e8000`) is disabled (HS-only gadget)

Leave `dispcc` disabled in the **shipped** DTB. Do not treat out-of-tree trees as packaged
in Armbian current.

`&gpu` is also `disabled` in the kebab DTS. That is separate.

## Power key

`pm8941_pwrkey` is `/dev/input/event1`. systemd-logind defaults to
`HandlePowerKey=poweroff`. The overlay sets that to `ignore` and runs
`kebab-powerd`:

| input | action |
|-------|--------|
| short KEY_POWER | `kebab-display toggle` |
| hold 3 s | `systemctl poweroff --force`, then sysrq `o` |
| 5 min idle (screen on) | blank |
| Power + Vol-Up 15–20 s | PMIC hard reset (hardware, always) |

## Downstream panel (what the 8T actually has)

Lineage `android_kernel_oneplus_sm8250` (`lineage-23.2`) describes one panel.
There is no Linux `compatible` in that tree — SDE uses a name string.

| | downstream |
|---|---|
| node | `dsi_oplus20828samsung_amb655x_1080_2400_cmd` |
| name | `samsung amb655x fhd cmd mode dsc dsi panel` |
| vendor | `AMB655X` / `samsung1024` / oplus **20828** |
| mode | command + DSC, 4 lane, 1080×2400, 60/120 Hz (default 120) |
| size | 70 mm × 151 mm |
| backlight | DCS, 1–2047 |

Sources:

- [`dsi-panel-oplus20828-samsung-amb655x-1080-2400-120fps.dtsi`](https://github.com/LineageOS/android_kernel_oneplus_sm8250/blob/lineage-23.2/arch/arm64/boot/dts/vendor/oplus/kebab/dsi-panel-oplus20828-samsung-amb655x-1080-2400-120fps.dtsi)
- [`kona-sde-display.dtsi`](https://github.com/LineageOS/android_kernel_oneplus_sm8250/blob/lineage-23.2/arch/arm64/boot/dts/vendor/oplus/kebab/kona-sde-display.dtsi)

ABL's FB is 1080×2376 (24 px shorter). That is a bootloader crop, not a second panel.

### GPIOs

| function | TLMM | notes |
|---|---|---|
| reset | **75** | sequence `1 / 10 ms / 0 / 1 ms / 1 / 10 ms` |
| TE / vsync | **66** | command-mode tear |
| panel vout enable | **24** | kebab-specific (OP8 uses GPIO 8) |
| AVDD 5.5 V enable | **61** | `regulator-fixed`, boot-on |

### Supplies → Armbian kebab regulator names

| SDE name | downstream label | volts | this DTS |
|---|---|---|---|
| `vddio-supply` | `pm8150_l14` / `L14A` | 1.80 V (max 1.88) | `vreg_l14a_1p8` |
| `vout-supply` | `L2C` / `pm8150a_l2` | 1.20–1.304 V, panel asks 1.28 | `vreg_l2c_1p2` (fixed 1.20 V today) |
| `vdd-supply` | `pm8150a_l11` / `L11C` | 3.104–3.304 V | `vreg_l11c_3p3` (3.296 V, always-on) |
| `avdd-supply` | `display_panel_avdd` | 5.5 V via GPIO 61 | `panel_avdd_5p5` (GPIO 61) in the display DTS |

`lab` / `ibb` tables exist in the same file and are **unused** on this panel.

Downstream `sde_dsi` lists `mdss_dsi0` **and** `mdss_dsi1`. 1080 / 4-lane is a
single DSI; the second set is SDE boilerplate. Mainline only needs `&mdss_dsi0`.

## Existing out-of-tree driver

[Xo666/mainline-instantnoodle `panel-samsung-amb655x.c`](https://github.com/Xo666/mainline-instantnoodle/blob/master/drivers/gpu/drm/panel/panel-samsung-amb655x.c)
is a Caleb Connolly `linux-mdss-dsi-panel-driver-generator` dump of this
panel (1080×2400, DSC 540×30, 70×151 mm, `samsung,amb655x`). That repo's
**board DTS is the OP8** (`samsung,amb655uv01`) — different glass, same GPIO
family. Do not paste the UV01 node onto kebab.

The generated driver only `regulator_bulk_get`s **vddio / vdd / avdd**. It does
not model `vout` / `L2C`. Hold kebab GPIO 24 high with pinctrl (OP8 does that
for GPIO 8) and optionally raise `vreg_l2c_1p2` to 1.28 V.

Reset is `GPIO_ACTIVE_LOW` in that tree. Downstream writes raw 1/0/1 on TLMM 75.

## Kernel + two DTBs

A 6.18.43 tree with every Armbian `sm8250-6.18` patch plus
[`kernel/panel-samsung-amb655x.c`](../kernel/panel-samsung-amb655x.c)
(`CONFIG_DRM_PANEL_SAMSUNG_AMB655X=y`) builds as `6.18.43-kebab-dsi`.
6.18 has no `mipi_dsi_dcs_write_long_multi` — the vendored driver uses
`mipi_dsi_dcs_write_seq_multi`. BTF is off for this bring-up kernel.

`scripts/apply-dsi-to-tree.sh /path/to/linux` drops the driver and the
Wi-Fi DTS. `--enable-display` also writes
[`dts/wip/sm8250-oneplus-kebab-dsi.dts`](../dts/wip/sm8250-oneplus-kebab-dsi.dts):

| node | safe `kebab.dtb` | `kebab-dsi.dtb` |
|---|---|---|
| `&dispcc` | disabled | okay |
| `&mdss` | okay | okay |
| `&mdss_dsi0` + panel `samsung,amb655x` | absent | okay |
| `&mdss_dsi0_phy` | disabled | okay |
| `&mdss_dsi1` / PHY / DP / `&gpu` | disabled | disabled |

`zz-update-abl-kernel` always appends `sm8250-oneplus-kebab.dtb` and `dd`s
`boot_a`. Pack the display image with
[`scripts/pack-abl-boot.sh`](../scripts/pack-abl-boot.sh) instead.

Stage A (new kernel + safe DTB) then Stage B (same kernel + display DTB)
both booted. Stage B `#65` is the working Linux fbcon. Wi-Fi survived
Stage B; the Type-C gadget may not re-enumerate after a display-DTB
reboot. Pack reads `/boot/vmlinuz-*-kebab-dsi`, not `/boot/Image`.
Roll back with `pack-abl-boot.sh safe --flash` or the last known-good
`boot_a` image. Power + Vol-Up 15–20 s is the PMIC hard reset if the
SoC is wedged.

The shipped `dtb/sm8250-oneplus-kebab.dtb` stays `dispcc` disabled so a
stock Armbian image still boots. Do not make `kebab-dsi.dtb` the default
until asked. The panel fragment sketch is
[`dts/wip/sm8250-oneplus-kebab-panel.dtsi`](../dts/wip/sm8250-oneplus-kebab-panel.dtsi).
