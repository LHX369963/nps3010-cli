# custom-psu-cli

Linux command-line upper computer for the custom STM32F103 + MCP4728 numerical
bench power supply in `dev-board/power`. It discovers CH340 adapters, controls
**up to two supplies**, retries the slow optically isolated UART, verifies
writes, emits machine-readable JSON, and records measurements.

## Install

```bash
cd /home/harry/Desktop/instrument-cli/psu
python3 -m venv .venv
.venv/bin/pip install -e '.[test]'
```

If the current desktop user cannot open `/dev/ttyUSB*`:

```bash
sudo install -m 0644 udev/99-custom-psu.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger
```

## Device selection

Without `--port`, compatible CH340 ports are ordered by physical USB location
and assigned slots 1 and 2. Keep each supply connected to the same hub socket
for stable slot numbering. Explicit paths override discovery:

```bash
psuctl list
psuctl --device 1 state
psuctl --device 2 state
psuctl --device all state
psuctl --port /dev/ttyUSB0 --port /dev/ttyUSB1 --device all state
```

Use `list` only when the ports are unknown. Explicit `--port` paths are opened
directly without serial-port enumeration. Normal control does not require a
separate `list`/`state` preflight, configuration snapshot, restoration, or
post-operation health check; typed writes perform their own targeted readback.

`--device` is a global option and must precede the subcommand. More than two
candidate/explicit ports are rejected rather than controlling an unintended
adapter.

## Control

```bash
# Set targets; this does not change the existing output enable state.
psuctl --device 1 set --voltage 12 --current 1.5
psuctl --device 1 output on
psuctl --device 1 output off

# Apply the same operation to both supplies.
psuctl --device all set --voltage 5 --current 0.5
psuctl --device all output on
psuctl --device all zero

# Calibrated state/live measurements and low-level ADC data.
psuctl --device all state
psuctl --device 1 read-adc
psuctl --device 1 view live
```

The CLI accepts 0–30 V and 0–10 A; the firmware clamps a target to each unit's
calibrated DAC range. A mismatch is reported instead of silently claiming that
the requested value was applied.

## Recording

```bash
psuctl --device all monitor --interval 0.5 --count 100 \
  --output captures/two-supplies.jsonl
psuctl --device 1 monitor --format csv --duration 60 \
  --output captures/supply-1.csv
```

Each record includes UTC time, physical slot, port, setpoints, calibrated live
voltage/current/power, output state and front-panel view.

## Diagnostics

```bash
psuctl --device 1 raw 'CAL?'
psuctl --device 1 raw 'STATE'
```

Prefer typed commands for normal control: they retry acknowledgements and
verify state. See [`docs/protocol.md`](docs/protocol.md).

## Development

```bash
.venv/bin/pytest
python -m build
```

The software is MIT licensed. Firmware and PCB source remain in their original
project and are not duplicated here.
