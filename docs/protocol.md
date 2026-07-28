# Firmware protocol

The controller uses a line-oriented ASCII protocol over CH340 USB serial:
9600 baud, 8 data bits, no parity, one stop bit, and no flow control. Commands
end in LF (the firmware also accepts CR/CRLF).

| Command | Meaning | Expected response |
| --- | --- | --- |
| `STATE` | Calibrated setpoints, live values and UI state | `STATE ...` |
| `READ` | Raw ADC codes and ADC pin voltages | `ADC ...` |
| `VSET <mV>` | Set calibrated voltage target | `OK VSET` |
| `ISET <mA>` | Set calibrated current limit | `OK ISET` |
| `ON` / `OFF` | Enable/disable output | `OK ON` / `OK OFF` |
| `ZERO` | Disable and clamp the output | `OK ZERO` |
| `VIEW SET` / `VIEW LIVE` | Select front-panel view | `OK VIEW ...` |
| `SET <vcode> <icode>` | Set raw DAC codes (expert use) | `OK SET ...` |
| `CAL?` | Show calibration metadata and coefficients | multiple `CAL ...` lines |

The optically isolated receive path is deliberately slow and can corrupt a
line. `psuctl` therefore retries typed commands until the expected response is
seen and verifies changes through `STATE`. `raw` is intentionally not retried,
because arbitrary commands may not be idempotent.
