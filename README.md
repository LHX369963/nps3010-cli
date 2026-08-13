# custom-psu-cli

Linux CLI for up to two STM32F103 + MCP4728 bench supplies in `dev-board/power`.
It uses CH340 serial adapters, retries the slow isolated UART, verifies typed
writes, and emits JSON/JSONL. Firmware and PCB source stay in their own project.

## Install

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[test]'
```

If `/dev/ttyUSB*` is inaccessible, install `udev/99-custom-psu.rules`, reload
udev rules, and reconnect the adapter.

## Start

```bash
psuctl --device 1 set --voltage 12 --current 1.5
psuctl --device 1 output on
psuctl --device 1 output off
```

`set` does not change output enable. Limits are 0–30 V and 0–10 A; firmware
clamps them to each unit's calibrated DAC range, and the CLI reports mismatches.

Without `--port`, slots 1/2 follow physical USB location. Use `list` only when
ports are unknown. Explicit paths are direct and do not enumerate serial ports:

```bash
psuctl --port /dev/ttyUSB0 --port /dev/ttyUSB1 --device all state
```

Normal control needs no prior `list`/`state`, saved configuration, restoration,
or post-operation health check. `--device` precedes its subcommand.

Firmware with automatic telemetry can be captured at 20 Hz without polling:

```bash
psuctl --device 1 telemetry --duration 20 --format csv \
  --output captures/startup.csv
```

## Guides

- [Control, simultaneous units, and display](docs/usage/control.md)
- [Monitoring and files](docs/usage/recording.md)
- [Diagnostics and raw protocol](docs/usage/diagnostics.md)
- [Firmware protocol](docs/protocol.md)
- [Validation limits](docs/validation.md)

## Development

```bash
.venv/bin/pytest
python -m build
```

Keep README short; put feature examples in `docs/usage/`.
