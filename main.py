"""StatusReport entry point. Phase 5.

Orchestrates the full audit pipeline:
  collect_all(report) -> render_html(report) -> write to logs/ -> open in browser

Output path: Path(sys.executable).parent / "logs" / "status_{hostname}_{date}.html"
  - sys.executable resolves to USB root when running as frozen exe (CLAUDE.md constraint)
  - NEVER getcwd() -- the cwd points to host PC when double-clicked, not the flash drive
  - NEVER write to host PC (PKG-02, CLAUDE.md)

D-01: pipeline order. D-02: output path. D-03: filename. D-04: console + print().
D-05: webbrowser.open(). D-06: collector failures warn + continue; write failure exits.
"""
from __future__ import annotations

import datetime
import os
import socket
import sys
from pathlib import Path

from collectors import collect_all
from models import AuditReport
from parsers.name_parser import parse_hostname
from renderer import render_html


def main() -> None:
    hostname = socket.gethostname()
    date_str = datetime.date.today().isoformat()

    print("StatusReport -- Master Electronics IT Audit Tool")

    report = AuditReport(
        hostname=hostname,
        parsed_hostname=parse_hostname(hostname),
        timestamp=datetime.datetime.now().isoformat(),
    )

    print("Collecting hardware info...")
    collect_all(report)  # mutates report in place -- D-06: never raises

    # Surface collector warnings -- never exit on collection failure (D-06)
    for err in report.collection_errors:
        print(f"[WARN] {err}")

    print("Detecting installed apps...")  # collect_all already called collect_apps
    # (progress label shown after collect_all so it aligns with D-04 console spec)

    print("Rendering character sheet...")

    # Output path -- USB only (D-02, CLAUDE.md constraint)
    # Path(sys.executable).parent = USB root (e.g., D:\status_report\) when frozen
    usb_root = Path(sys.executable).parent
    logs_dir = usb_root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    base_name = f"status_{hostname}_{date_str}"
    output_path = logs_dir / f"{base_name}.html"
    counter = 2
    while output_path.exists():
        output_path = logs_dir / f"{base_name} ({counter}).html"
        counter += 1

    html = render_html(report)  # returns str; main.py controls filename (D-03)

    try:
        output_path.write_text(html, encoding="utf-8")
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
    print("Opening in browser...")
    try:
        os.startfile(str(output_path))  # Windows ShellExecute — opens with default browser
    except OSError:
        pass  # best-effort; file is already saved on the USB
    print("Done.")


if __name__ == "__main__":
    main()
