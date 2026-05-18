# Phase 13: System Health Collectors - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-18
**Phase:** 13-system-health-collectors
**Areas discussed:** Severity model, Uptime collection method, Uptime warning shape, Stat block placement

---

## Severity Model

| Option | Description | Selected |
|--------|-------------|----------|
| New level field | Keep severity as 'OK'/'WARN'. Add `level: str \| None = None` with values 'yellow' \| 'red'. Phase 11 --warnings CLI works unchanged. Renderer checks level to pick color. | ✓ |
| Replace WARN with yellow/red | Change severity values to 'OK' \| 'yellow' \| 'red'. No new field. Breaking change: Phase 11 CLI filter and renderer has_warnings check both need updating. | |

**User's choice:** New level field
**Notes:** Backward compatibility with Phase 11 `--warnings` CLI filter was the deciding factor. Level field added after `detail` as `level: str | None = None`.

---

## Uptime Collection Method

| Option | Description | Selected |
|--------|-------------|----------|
| psutil.boot_time() | Already in the stack. Returns epoch timestamp — subtract from now for elapsed seconds. Works on Windows and Mac. No new dependency, no elevation needed. | ✓ |
| ctypes GetTickCount64 | Windows-only, no new deps. GetTickCount64 doesn't roll over. Adds Windows-specific branch, breaks Mac path. | |

**User's choice:** psutil.boot_time()
**Notes:** psutil is already imported in collectors/windows/hardware.py — no new dependency required.

---

## Uptime Warning Shape

| Option | Description | Selected |
|--------|-------------|----------|
| One Warning, escalating | evaluate_warnings() returns one UPTIME Warning. severity='OK' if ≤ 7 days, level='yellow' if 7–30 days, level='red' if > 30 days. | ✓ |
| Two Warnings, one per threshold | Returns two separate uptime Warning objects — one for WARN-04 (yellow) and one for WARN-05 (red). A 45-day machine fires both. A 10-day machine fires only yellow. | |

**User's choice:** One Warning, escalating
**Notes:** Code escalates — `code='UPTIME'` (OK), `code='UPTIME_WARN'` (yellow), `code='UPTIME_STALE'` (red). evaluate_warnings() grows from 3 to 4 objects total.

---

## Stat Block Placement

| Option | Description | Selected |
|--------|-------------|----------|
| New System Health rows | New rows in stat block grouped under "System Health" label. N/A for standard user (WUA inaccessible). | ✓ |
| Alongside OS version row | Uptime and pending updates inline with OS version stat block row. Compact but crowded. | |

**User's choice:** New System Health rows
**Notes:** Intentionally extensible — Phase 14 (vendor update detection) will add Dell/Lenovo rows to the same section.

---

## Claude's Discretion

- Exact display label text for System Health rows
- Sub-hour/sub-day edge case uptime formatting
- Whether WUA COM collection is a new collector file or added to hardware.py
- Exact WUA COM searcher criteria string
- Test fixture approach for `_WIN32COM_AVAILABLE = False` path

## Deferred Ideas

None — discussion stayed within phase scope.
