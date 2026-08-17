"""Command-line upper computer for up to two NPS3010 units."""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .errors import NPS3010Error, ProtocolError, TransportError
from .instrument import NPS3010
from .transport import SerialTransport, discover, select_ports


def emit(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")), flush=True)


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="nps3010", description="Control up to two NPS3010 bench power supplies")
    ap.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    ap.add_argument("--port", action="append", help="serial port, repeat for two NPS3010 units")
    ap.add_argument("--device", choices=("1", "2", "all"), default="1", help="physical USB slot (default: 1)")
    ap.add_argument("--timeout", type=float, default=1.0, help="seconds per command attempt")
    ap.add_argument("--retries", type=int, default=10, help="retries for the slow isolated UART")
    sub = ap.add_subparsers(dest="command", required=True)
    sub.add_parser("list", help="list and probe attached CH340 adapters")
    sub.add_parser("state", help="read setpoints, measurements and output state")
    sub.add_parser("read-adc", help="read raw ADC codes and ADC pin voltages")

    setting = sub.add_parser("set", help="set calibrated voltage/current targets")
    setting.add_argument("--voltage", type=float, help="target voltage in V (0..30)")
    setting.add_argument("--current", type=float, help="current limit in A (0..10)")

    output = sub.add_parser("output", help="enable or disable output")
    output.add_argument("state", choices=("on", "off"))
    sub.add_parser("zero", help="force output off (setpoints are retained)")

    view = sub.add_parser("view", help="select front-panel display values")
    view.add_argument("mode", choices=("set", "live"))

    monitor = sub.add_parser("monitor", help="record calibrated measurements")
    monitor.add_argument("--interval", type=float, default=0.5)
    monitor.add_argument("--count", type=int, default=0, help="0 means unlimited")
    monitor.add_argument("--duration", type=float, default=0, help="seconds; 0 means unlimited")
    monitor.add_argument("--format", choices=("jsonl", "csv"), default="jsonl")
    monitor.add_argument("--output", type=Path)

    telemetry = sub.add_parser("telemetry", help="capture automatic 20 Hz binary telemetry")
    telemetry.add_argument("--count", type=int, default=0, help="0 means unlimited")
    telemetry.add_argument("--duration", type=float, default=0, help="seconds; 0 means unlimited")
    telemetry.add_argument("--format", choices=("jsonl", "csv"), default="jsonl")
    telemetry.add_argument("--output", type=Path)

    raw = sub.add_parser("raw", help="send one firmware command")
    raw.add_argument("line")
    return ap


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def state_record(slot: int, port: str, state, sequence: int | None = None) -> dict:
    record = {"timestamp": timestamp(), "slot": slot, "port": port}
    if sequence is not None:
        record["sequence"] = sequence
    return record | state.to_dict()


def connect_all(args: argparse.Namespace, stack: ExitStack) -> list[tuple[int, str, NPS3010]]:
    selected = select_ports(args.port, args.device)
    result = []
    for slot, port in selected:
        transport = stack.enter_context(SerialTransport(port, args.timeout, args.retries))
        result.append((slot, port, NPS3010(transport)))
    return result


def monitor(args: argparse.Namespace, devices: list[tuple[int, str, NPS3010]]) -> None:
    if args.interval < 0.1 or args.count < 0 or args.duration < 0:
        raise ProtocolError("interval must be >= 0.1; count/duration cannot be negative")
    output = args.output.open("w", newline="", encoding="utf-8") if args.output else sys.stdout
    fields = [
        "timestamp", "slot", "port", "sequence", "output", "set_voltage_v",
        "set_current_a", "voltage_v", "current_a", "power_w", "view", "selected_digit",
        "selected_voltage_digit", "selected_current_digit", "constant_current",
        "settling", "fault",
    ]
    writer = csv.DictWriter(output, fieldnames=fields) if args.format == "csv" else None
    if writer:
        writer.writeheader()
    started = time.monotonic()
    sequence = 0
    try:
        while (not args.count or sequence < args.count) and (
            not args.duration or time.monotonic() - started < args.duration
        ):
            tick = time.monotonic()
            sequence += 1
            for slot, port, supply in devices:
                record = state_record(slot, port, supply.state(), sequence)
                if writer:
                    writer.writerow(record)
                    output.flush()
                else:
                    print(json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")), file=output, flush=True)
            delay = args.interval - (time.monotonic() - tick)
            if delay > 0:
                time.sleep(delay)
    except KeyboardInterrupt:
        pass
    finally:
        if args.output:
            output.close()


def capture_telemetry(args: argparse.Namespace, devices: list[tuple[int, str, NPS3010]]) -> None:
    if len(devices) != 1:
        raise ProtocolError("telemetry capture supports one selected NPS3010")
    if args.count < 0 or args.duration < 0 or (not args.count and not args.duration):
        raise ProtocolError("telemetry requires positive --count or --duration")
    slot, port, supply = devices[0]
    output = args.output.open("w", newline="", encoding="utf-8") if args.output else sys.stdout
    fields = ["timestamp", "slot", "port", "version", "sequence", "device_time_ms",
              "voltage_v", "current_a", "power_w", "output", "constant_current",
              "settling", "fault"]
    writer = csv.DictWriter(output, fieldnames=fields) if args.format == "csv" else None
    if writer:
        writer.writeheader()
    try:
        for item in supply.transport.telemetry(args.duration, args.count):
            record = {"timestamp": timestamp(), "slot": slot, "port": port} | item.to_dict()
            if writer:
                writer.writerow(record)
                output.flush()
            else:
                print(json.dumps(record, ensure_ascii=False, sort_keys=True,
                                 separators=(",", ":")), file=output, flush=True)
    finally:
        if args.output:
            output.close()


def run(args: argparse.Namespace) -> int:
    if args.timeout <= 0 or args.retries < 0:
        raise ProtocolError("timeout must be positive and retries cannot be negative")
    if args.command == "list":
        items = discover(args.timeout, args.retries)
        emit({"count": len(items), "max_devices": 2, "devices": items})
        return 0
    with ExitStack() as stack:
        devices = connect_all(args, stack)
        if args.command == "monitor":
            monitor(args, devices)
            return 0
        if args.command == "telemetry":
            capture_telemetry(args, devices)
            return 0
        for slot, port, supply in devices:
            if args.command == "state":
                result = supply.state().to_dict()
            elif args.command == "read-adc":
                result = supply.read_adc().to_dict()
            elif args.command == "set":
                supply.set_targets(args.voltage, args.current)
                continue
            elif args.command == "output":
                supply.output(args.state == "on")
                continue
            elif args.command == "zero":
                supply.zero()
                continue
            elif args.command == "view":
                supply.view(args.mode)
                continue
            elif args.command == "raw":
                result = {"response": supply.transport.command(args.line)}
            else:
                raise AssertionError("unreachable")
            emit({"slot": slot, "port": port} | result)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        return run(args)
    except TransportError as exc:
        print(f"nps3010: {exc}", file=sys.stderr)
        return 4
    except (ProtocolError, NPS3010Error) as exc:
        print(f"nps3010: {exc}", file=sys.stderr)
        return 5
