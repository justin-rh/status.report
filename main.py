"""SCRY entry point. Phase 5.

Orchestrates the full audit pipeline:
  collect_all(report) -> render_html(report) -> write to logs/ -> open in browser

Output path: Path(sys.executable).parent / "logs" / "{date}_scry_{hostname}.html"
  - sys.executable resolves to USB root when running as frozen exe (CLAUDE.md constraint)
  - NEVER getcwd() -- the cwd points to host PC when double-clicked, not the flash drive
  - NEVER write to host PC (PKG-02, CLAUDE.md)

D-01: pipeline order. D-02: output path. D-03: filename. D-04: console + print().
D-05: os.startfile() + input() pause. D-06: collector failures warn + continue; write failure exits.
"""
from __future__ import annotations

import argparse
import dataclasses
import datetime
import json
import os
import socket
import subprocess
import sys
from pathlib import Path

from collectors import collect_all
from health_checks import evaluate_warnings
from models import AuditReport
from parsers.name_parser import parse_hostname
from renderer import render_html


def _run_cli(args: argparse.Namespace) -> None:
    """Handle targeted CLI flag output. Prints requested fields and exits 0.

    Collection scope (D-08, D-09, D-10, D-11):
      --name only:           no collection needed (socket.gethostname() is sufficient)
      --serial only:         hardware collection only (not full collect_all)
      --warnings only:       full collect_all then evaluate_warnings
      combined flags:        union of required collection
    """
    hostname = socket.gethostname()

    # Determine minimum required collection (D-08, D-09, D-10, D-11)
    needs_full = args.warnings                      # D-10: --warnings needs collect_all
    needs_hardware = args.serial and not needs_full  # D-09: --serial needs hardware only (unless full already)

    report: AuditReport | None = None

    if needs_full:
        # Build minimal report for collect_all
        report = AuditReport(
            hostname=hostname,
            parsed_hostname=parse_hostname(hostname),
            timestamp=datetime.datetime.now().isoformat(),
        )
        collect_all(report)
        report.warnings = evaluate_warnings(report)
    elif needs_hardware:
        # Import hardware collector directly — avoid full collect_all (D-09)
        if sys.platform == "darwin":
            from collectors.mac.hardware import collect_hardware
        else:
            from collectors.windows.hardware import collect_hardware
        report = AuditReport(
            hostname=hostname,
            parsed_hostname=parse_hostname(hostname),
            timestamp=datetime.datetime.now().isoformat(),
        )
        collect_hardware(report)
    # else: args.name only — D-08: no collection needed

    # Output in fixed order: name -> serial -> warnings (D-02)
    if args.name:
        print(hostname)

    if args.serial:
        serial = (report.serial_number if report and report.serial_number else None)
        print(serial if serial is not None else "Unknown")  # D-07

    if args.warnings:
        warn_messages = [
            w.message for w in (report.warnings if report else [])
            if w.severity == "WARN"  # D-04, D-06
        ]
        for msg in warn_messages:
            print(msg)
        # D-05: print nothing when no WARNs -- loop body simply never executes

    sys.exit(0)


def _find_app_spec(query: str, specs: list[dict]) -> dict | None:
    """Return first spec whose name contains query (case-insensitive). D-09, D-10."""
    q = query.lower()
    for spec in specs:
        if q in spec["name"].lower():
            return spec
    return None


def _format_app_status_line(app_status: "AppStatus") -> str:
    """Format single-line --app output. D-12, Claude's discretion per RESEARCH.md Pattern 5."""
    if not app_status.installed:
        return f"{app_status.name}: not installed"
    if app_status.version:
        return f"{app_status.name}: installed (v{app_status.version})"
    if app_status.service_state:
        return f"{app_status.name}: installed ({app_status.service_state})"
    return f"{app_status.name}: installed"


def _run_cli_app(args: argparse.Namespace) -> None:
    """Handle --app <name> mode: detect one app, print result to stdout, exit.

    Runs only the app-detection pipeline for a single named app.
    Never writes files (D-08, D-13). Exits 0 on match, 1 on no match (D-11).
    Platform dispatch selects correct spec list (D-14, RESEARCH.md Pitfall 1).
    """
    if sys.platform == "darwin":
        from collectors.mac.apps import _detect_one_app, MAC_APP_SPECS as specs  # type: ignore[attr-defined]  # D-14: intentional internal import
    else:
        from collectors.windows.apps import _detect_one_app, APP_SPECS as specs  # type: ignore[attr-defined]  # D-14: intentional internal import

    spec = _find_app_spec(args.app, specs)
    if spec is None:
        known = ", ".join(s["name"] for s in specs)
        print(f"Unknown app: {args.app}. Known apps: {known}", file=sys.stderr)
        sys.exit(1)

    hostname = socket.gethostname()
    report = AuditReport(
        hostname=hostname,
        parsed_hostname=parse_hostname(hostname),
        timestamp=datetime.datetime.now().isoformat(),
    )
    try:
        _detect_one_app(spec, report)  # mutates report.apps; never raises (D-16)
    except Exception as exc:
        from models import AppStatus
        report.collection_errors.append(str(exc))
        report.apps.append(AppStatus(name=spec["name"], installed=False, error=str(exc)))

    app_status = report.apps[0]

    if args.json:
        # D-13: raw AppStatus dict to stdout, no wrapper, no files written
        print(json.dumps(dataclasses.asdict(app_status), indent=2))
    else:
        # D-12: single-line format
        print(_format_app_status_line(app_status))

    sys.exit(0)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="SCRY -- Master Electronics IT Audit Tool",
        prog="scry",
    )
    parser.add_argument("--name", action="store_true", help="Print PC hostname to stdout and exit")
    parser.add_argument("--serial", action="store_true", help="Print device serial number to stdout and exit")
    parser.add_argument("--warnings", action="store_true", help="Print active warnings to stdout and exit")
    parser.add_argument("--updates", action="store_true", help="Query Windows Update Agent for pending update count (slow; omitted by default)")
    parser.add_argument("--json",   action="store_true", help="Write AuditReport as JSON alongside HTML report; full pipeline always runs")
    parser.add_argument("--output", metavar="PATH",      help="Override default logs/ destination for all file output (HTML and JSON)")
    parser.add_argument("--app",    metavar="NAME",      help="Run app-detection for one named app; print result to stdout and exit")
    args = parser.parse_args()

    # --app: single-app detection path — exits before cli_mode check
    # MUST be checked before cli_mode (RESEARCH.md Anti-Patterns, Pitfall note)
    if args.app:
        if args.output:
            print("WARNING: --output is ignored in --app mode", file=sys.stderr)
        _run_cli_app(args)
        return

    # D-05: --json overrides targeted flags; if --json present, skip _run_cli and run full pipeline
    cli_mode = args.name or args.serial or args.warnings
    if cli_mode and not args.json:
        _run_cli(args)
        return

    hostname = socket.gethostname()
    date_str = datetime.date.today().isoformat()

    print("SCRY -- Master Electronics IT Audit Tool")

    report = AuditReport(
        hostname=hostname,
        parsed_hostname=parse_hostname(hostname),
        timestamp=datetime.datetime.now().isoformat(),
    )

    print("Collecting hardware info...")
    collect_all(report)  # mutates report in place -- D-06: never raises

    if args.updates and sys.platform != "darwin":
        from collectors.windows.hardware import collect_pending_updates
        collect_pending_updates(report)
        from collectors.windows.vendor import collect_vendor_updates
        collect_vendor_updates(report)

    # Surface collector warnings -- never exit on collection failure (D-06)
    for err in report.collection_errors:
        print(f"[WARN] {err}")

    print("Detecting installed apps...")  # collect_all already called collect_apps
    # (progress label shown after collect_all so it aligns with D-04 console spec)

    report.warnings = evaluate_warnings(report)  # D-09: populates warnings before render

    print("Rendering character sheet...")

    # Output path -- USB only (D-02, CLAUDE.md constraint)
    # Platform-aware output root (D-02, Phase 10):
    # - darwin: Path(__file__).parent because tool runs as "python3 main.py" (not frozen)
    # - other:  Path(sys.executable).parent because tool runs as frozen exe (CLAUDE.md)
    if sys.platform == "darwin":
        usb_root = Path(__file__).parent
    else:
        usb_root = Path(sys.executable).parent
    if args.output:
        logs_dir = Path(args.output)
    else:
        logs_dir = usb_root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    base_name = f"{date_str}_scry_{hostname}"
    output_path = logs_dir / f"{base_name}.html"
    counter = 2
    while output_path.exists():
        output_path = logs_dir / f"{base_name} ({counter}).html"
        counter += 1
    json_path = output_path.with_suffix(".json") if args.json else None

    html = render_html(report)  # returns str; main.py controls filename (D-03)

    try:
        output_path.write_text(html, encoding="utf-8")
        if args.json:
            payload = json.dumps(dataclasses.asdict(report), indent=2, default=str)
            json_path.write_text(payload, encoding="utf-8")
    except PermissionError:
        print("[ERROR] Cannot write to USB drive -- it may be write-protected.")
        print("        Check the physical lock switch on the drive.")
        sys.exit(1)
    except OSError as exc:
        import errno as _errno
        if exc.errno == _errno.ENOSPC:
            print("[ERROR] USB drive is full. Free up space and try again.")
        else:
            print(f"[ERROR] Write failed: {exc}")
        sys.exit(1)

    print(f"Saved: {output_path}")

    warning_count = len([w for w in report.warnings if w.severity == 'WARN'])
    disk_used_pct = 0
    if report.disk_total_gb:
        disk_used_pct = round((report.disk_total_gb - (report.disk_free_gb or 0)) / report.disk_total_gb * 100)
    cpu = report.cpu_model or "Unknown CPU"
    ram = f"{round(report.ram_gb)} GB RAM" if report.ram_gb else "Unknown RAM"
    print(f"[SUMMARY] {hostname} | {report.os_version or 'Unknown OS'} | {cpu} | {ram} | {disk_used_pct}% disk used | {warning_count} warnings")

    if sys.stdin.isatty():
        if sys.platform == "darwin":
            try:
                subprocess.run(["open", str(output_path)])  # macOS open command (D-03)
            except OSError:
                pass
        else:
            try:
                os.startfile(str(output_path))
            except OSError:
                pass
        input("\nPress Enter to close this window, then eject the USB drive.")


if __name__ == "__main__":
    main()
