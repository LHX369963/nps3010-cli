# Validation

Validation date: 2026-07-28 (Asia/Shanghai).

## Automated

- Python 3.13
- 12 unit tests passed.
- Source distribution and universal wheel built successfully.
- A two-PTY firmware simulation exercised `set`, `output on`, `state`, and
  `zero` against two simultaneously open serial sessions. Both slot 1 and slot
  2 returned independently tagged JSON records and finished output-off.

## Connected hardware

One of the two supplies was enumerated by Linux during acceptance as
`/dev/ttyUSB1`, CH340 `1a86:7523`, physical USB location `1-2.1.1.2`. The
second supply was not present in the kernel's serial-device list at that time,
so its connected run remains pending.

The enumerated unit passed:

1. Discovery and protocol probe through `STATE`.
2. Calibrated setpoint write and verification at 3.300 V / 0.250 A.
3. Output enable and state verification.
4. Calibrated live state read (approximately 3.3 V at no load).
5. Raw ADC read.
6. Three-sample JSONL monitor capture.
7. `ZERO` with verified `output=false` as the final state.

No load was attached, as stated by the operator. The connected test did not
exercise regulation under load, constant-current transition, protection
behavior, or measurement accuracy.
