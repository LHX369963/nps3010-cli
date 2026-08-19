---
name: nps3010-cli
description: Control NPS3010 supplies and read back their outputs.
---

# NPS3010 CLI

Use `nps3010/.venv/bin/nps3010` from the instrument-cli workspace. Omit device
selection when unambiguous; if the CLI reports ambiguity, use the selector named
in that error. Execute the request directly.
Do not scan processes or query preliminary state.

Common forms:

```bash
nps3010/.venv/bin/nps3010 --device 1 state
nps3010/.venv/bin/nps3010 --device 1 readback
nps3010/.venv/bin/nps3010 --device all readback
nps3010/.venv/bin/nps3010 --device 1 set --voltage 12 --current 1.5
nps3010/.venv/bin/nps3010 --device 1 output on
```

Control success is silent. `readback` returns output voltage/current and spread;
absence of a warning means the internal readback sample was stable.
