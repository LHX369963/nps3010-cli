# Diagnostics

Prefer typed control commands: they retry expected acknowledgements and perform
targeted state readback. Use `raw` only for a known protocol command whose
semantics require inspection:

```bash
psuctl --device 1 read-adc
psuctl --device 1 raw 'CAL?'
psuctl --device 1 raw 'STATE'
```

The isolated receive path is slow. `raw` is intentionally not retried because
an arbitrary command may not be idempotent. See the [firmware protocol](../protocol.md)
before using an untyped command.
