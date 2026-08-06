# Monitor supplies

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
