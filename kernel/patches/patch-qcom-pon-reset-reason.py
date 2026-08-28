#!/usr/bin/env python3
"""Add read-only PM8998 GEN2 PON reset-reason logging."""

from pathlib import Path
import sys


def replace_once(text: str, old: str, new: str, label: str) -> str:
    """Replace one exact upstream anchor or stop without a partial patch."""
    if old not in text:
        raise SystemExit(f"qcom-pon.c: no {label} anchor")
    return text.replace(old, new, 1)


def main() -> None:
    """Patch qcom-pon.c in an Armbian-patched Linux 6.18 tree."""
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "/opt/kebab-kernel/linux")
    path = root / "drivers/power/reset/qcom-pon.c"
    text = path.read_text()

    if "qcom_pon_log_reset_reasons" in text:
        print("already patched")
        return

    constants = """#define PON_SOFT_RB_SPARE\t\t0x8f

#define PON_GEN2_REASON1\t\t0xc0
#define PON_GEN2_WARM_RESET_REASON1\t0xc2
#define PON_GEN2_POFF_REASON1\t\t0xc5
#define PON_GEN2_OFF_REASON\t\t0xc7
#define PON_GEN2_FAULT_REASON1\t\t0xc8
#define PON_GEN2_FAULT_REASON2\t\t0xc9
#define PON_GEN2_S3_RESET_REASON\t0xca

#define PON_GEN2_POFF_SEQ\t\tBIT(7)
#define PON_GEN2_FAULT_SEQ\t\tBIT(6)
#define PON_GEN2_S3_RESET_SEQ\t\tBIT(5)
"""
    text = replace_once(
        text,
        "#define PON_SOFT_RB_SPARE\t\t0x8f\n",
        constants,
        "PON_SOFT_RB_SPARE",
    )

    helper = r'''enum qcom_pon_reason_reg {
	QCOM_PON_SOFT_RB_SPARE,
	QCOM_PON_REASON1,
	QCOM_PON_WARM_RESET_REASON1,
	QCOM_PON_POFF_REASON1,
	QCOM_PON_OFF_REASON,
	QCOM_PON_FAULT_REASON1,
	QCOM_PON_FAULT_REASON2,
	QCOM_PON_S3_RESET_REASON,
	QCOM_PON_REASON_REG_COUNT,
};

static const unsigned int qcom_pon_reason_offsets[] = {
	[QCOM_PON_SOFT_RB_SPARE] = PON_SOFT_RB_SPARE,
	[QCOM_PON_REASON1] = PON_GEN2_REASON1,
	[QCOM_PON_WARM_RESET_REASON1] = PON_GEN2_WARM_RESET_REASON1,
	[QCOM_PON_POFF_REASON1] = PON_GEN2_POFF_REASON1,
	[QCOM_PON_OFF_REASON] = PON_GEN2_OFF_REASON,
	[QCOM_PON_FAULT_REASON1] = PON_GEN2_FAULT_REASON1,
	[QCOM_PON_FAULT_REASON2] = PON_GEN2_FAULT_REASON2,
	[QCOM_PON_S3_RESET_REASON] = PON_GEN2_S3_RESET_REASON,
};

static const char * const qcom_pon_reason_names[] = {
	[QCOM_PON_SOFT_RB_SPARE] = "soft-rb",
	[QCOM_PON_REASON1] = "pon",
	[QCOM_PON_WARM_RESET_REASON1] = "warm",
	[QCOM_PON_POFF_REASON1] = "poff",
	[QCOM_PON_OFF_REASON] = "off",
	[QCOM_PON_FAULT_REASON1] = "fault1",
	[QCOM_PON_FAULT_REASON2] = "fault2",
	[QCOM_PON_S3_RESET_REASON] = "s3",
};

static const char * const qcom_pon_power_on_reasons[] = {
	"hard reset",
	"SMPL",
	"RTC alarm",
	"DC charger",
	"USB charger",
	"PON1",
	"external supply",
	"power key",
};

static const char * const qcom_pon_power_off_reasons[] = {
	"software",
	"PS_HOLD",
	"PMIC watchdog",
	"GP1/keypad reset 1",
	"GP2/keypad reset 2",
	"power key + RESIN",
	"RESIN",
	"long power key",
};

static const char * const qcom_pon_fault_reasons[] = {
	"GP fault 0",
	"GP fault 1",
	"GP fault 2",
	"GP fault 3",
	"MBG fault",
	"OVLO",
	"UVLO",
	"AVDD rollback",
	NULL,
	NULL,
	NULL,
	"FAULT_N",
	"PBS watchdog",
	"PBS NACK",
	"restart PON",
	"OTST3",
};

static const char * const qcom_pon_s3_reasons[] = {
	NULL,
	NULL,
	NULL,
	NULL,
	"fault",
	"PBS watchdog",
	"PBS NACK",
	"power key / RESIN",
};

static void qcom_pon_log_reason_bits(struct qcom_pon *pon, const char *group,
				     unsigned int value,
				     const char * const *reasons,
				     unsigned int reason_count)
{
	unsigned int bit;

	if (!value) {
		dev_info(pon->dev, "PMIC reset reason: %s=none\n", group);
		return;
	}

	for (bit = 0; bit < reason_count; bit++) {
		if (!(value & BIT(bit)))
			continue;

		if (reasons[bit])
			dev_info(pon->dev,
				 "PMIC reset reason: %s=%s (bit %u)\n",
				 group, reasons[bit], bit);
		else
			dev_info(pon->dev,
				 "PMIC reset reason: %s=reserved (bit %u)\n",
				 group, bit);
	}
}

static void qcom_pon_log_reset_reasons(struct qcom_pon *pon)
{
	unsigned int value[QCOM_PON_REASON_REG_COUNT] = {};
	unsigned int fault;
	unsigned long valid = 0;
	unsigned int i;
	int error;

	for (i = 0; i < ARRAY_SIZE(qcom_pon_reason_offsets); i++) {
		error = regmap_read(pon->regmap,
				    pon->baseaddr + qcom_pon_reason_offsets[i],
				    &value[i]);
		if (error) {
			dev_warn(pon->dev,
				 "PMIC reset reason: failed to read %s at %#x: %d\n",
				 qcom_pon_reason_names[i],
				 pon->baseaddr + qcom_pon_reason_offsets[i],
				 error);
			continue;
		}

		valid |= BIT(i);
	}

	dev_info(pon->dev,
		 "PMIC reset reason: raw valid=%#lx soft-rb=%02x pon=%02x warm=%02x poff=%02x\n",
		 valid, value[QCOM_PON_SOFT_RB_SPARE], value[QCOM_PON_REASON1],
		 value[QCOM_PON_WARM_RESET_REASON1],
		 value[QCOM_PON_POFF_REASON1]);
	dev_info(pon->dev,
		 "PMIC reset reason: raw off=%02x fault1=%02x fault2=%02x s3=%02x\n",
		 value[QCOM_PON_OFF_REASON], value[QCOM_PON_FAULT_REASON1],
		 value[QCOM_PON_FAULT_REASON2],
		 value[QCOM_PON_S3_RESET_REASON]);

	if (valid & BIT(QCOM_PON_REASON1))
		qcom_pon_log_reason_bits(pon, "power-on",
					 value[QCOM_PON_REASON1],
					 qcom_pon_power_on_reasons,
					 ARRAY_SIZE(qcom_pon_power_on_reasons));

	/* GEN2 only defines WARM_RESET_REASON1 as an opaque warm-boot latch. */
	if (valid & BIT(QCOM_PON_WARM_RESET_REASON1))
		dev_info(pon->dev, "PMIC reset reason: boot=%s (warm=%02x)\n",
			 value[QCOM_PON_WARM_RESET_REASON1] ? "warm" : "cold",
			 value[QCOM_PON_WARM_RESET_REASON1]);

	if (!(valid & BIT(QCOM_PON_OFF_REASON)))
		return;

	if ((value[QCOM_PON_OFF_REASON] & PON_GEN2_POFF_SEQ) &&
	    (valid & BIT(QCOM_PON_POFF_REASON1)))
		qcom_pon_log_reason_bits(pon, "power-off",
					 value[QCOM_PON_POFF_REASON1],
					 qcom_pon_power_off_reasons,
					 ARRAY_SIZE(qcom_pon_power_off_reasons));

	if (value[QCOM_PON_OFF_REASON] & PON_GEN2_FAULT_SEQ) {
		fault = 0;
		if (valid & BIT(QCOM_PON_FAULT_REASON1))
			fault |= value[QCOM_PON_FAULT_REASON1];
		if (valid & BIT(QCOM_PON_FAULT_REASON2))
			fault |= value[QCOM_PON_FAULT_REASON2] << 8;
		if (valid & (BIT(QCOM_PON_FAULT_REASON1) |
			     BIT(QCOM_PON_FAULT_REASON2)))
			qcom_pon_log_reason_bits(pon, "fault", fault,
						 qcom_pon_fault_reasons,
						 ARRAY_SIZE(qcom_pon_fault_reasons));
	}

	if ((value[QCOM_PON_OFF_REASON] & PON_GEN2_S3_RESET_SEQ) &&
	    (valid & BIT(QCOM_PON_S3_RESET_REASON)))
		qcom_pon_log_reason_bits(pon, "s3-reset",
					 value[QCOM_PON_S3_RESET_REASON],
					 qcom_pon_s3_reasons,
					 ARRAY_SIZE(qcom_pon_s3_reasons));
}

'''
    probe_anchor = "static int qcom_pon_reboot_mode_write(struct reboot_mode_driver *reboot,\n"
    text = replace_once(
        text,
        probe_anchor,
        helper + probe_anchor,
        "qcom_pon_reboot_mode_write",
    )

    reason_shift = "\treason_shift = (long)of_device_get_match_data(&pdev->dev);\n\n"
    reason_shift_new = reason_shift + (
        "\tif (of_device_is_compatible(pdev->dev.of_node, "
        '"qcom,pm8998-pon"))\n'
        "\t\tqcom_pon_log_reset_reasons(pon);\n\n"
    )
    text = replace_once(
        text,
        reason_shift,
        reason_shift_new,
        "reason_shift assignment",
    )

    path.write_text(text)
    print("patched qcom-pon.c with read-only PM8998 GEN2 reset reasons")


if __name__ == "__main__":
    main()
