# Monitor supplies

For high-rate acquisition, use automatic 20 Hz binary telemetry:

```bash
psuctl --device 1 telemetry --duration 20 --format csv \
  --output captures/startup.csv
```

The CRC-protected frame includes a device timestamp and sequence number, making
timing and dropped frames auditable. Prefer this to repeated `STATE` polling for
startup curves.

Write compact JSONL or CSV while keeping a finite capture bound:

```bash
psuctl --device all monitor --interval 0.5 --count 100 \
  --output captures/two-supplies.jsonl
psuctl --device 1 monitor --format csv --duration 60 \
  --output captures/supply-1.csv
```

Each record contains UTC time, physical slot, port, setpoints, calibrated live
voltage/current/power, output state, and front-panel view. Use the output path
appropriate for generated local capture data; do not add capture files to source
control unless they are explicitly curated evidence.
