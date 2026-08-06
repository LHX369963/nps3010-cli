# Control supplies

Set targets without changing the current output-enable state:

```bash
psuctl --device 1 set --voltage 12 --current 1.5
psuctl --device 1 output on
psuctl --device 1 output off
```

Apply the same command to both connected supplies:

```bash
psuctl --device all set --voltage 5 --current 0.5
psuctl --device all output on
psuctl --device all zero
```

Read calibrated live state or select the front-panel view:

```bash
psuctl --device all state
psuctl --device 1 view live
```

Slots 1/2 follow physical USB location when `--port` is omitted; keep adapters
on the same hub sockets for stable numbering. Explicit `--port` paths override
discovery. More than two candidate or explicit ports are rejected.
