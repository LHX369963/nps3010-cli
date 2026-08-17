---
name: nps3010-cli
description: Control and measure up to two connected NPS3010 bench power supplies.
---

# NPS3010 CLI

Use `nps3010/.venv/bin/nps3010` from the instrument-cli workspace. Device
selection is automatic when one unit is attached; with multiple units use
`--device 1`, `--device 2`, or `--device all`. Execute the request directly.

Common forms:

```bash
nps3010/.venv/bin/nps3010 --device 1 state
nps3010/.venv/bin/nps3010 --device 1 measure
nps3010/.venv/bin/nps3010 --device 1 set --voltage 12 --current 1.5
nps3010/.venv/bin/nps3010 --device 1 output on
nps3010/.venv/bin/nps3010 --device all monitor --count 20
```

Control success is silent. `measure` returns voltage/current and observed spread.
