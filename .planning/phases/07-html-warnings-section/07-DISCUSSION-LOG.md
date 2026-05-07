# Phase 7: HTML Warnings Section - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-07
**Phase:** 07-html-warnings-section
**Areas discussed:** Rename warning fate, Per-check row layout, Collapsible mechanism, Box position in the sheet

---

## Rename Warning Fate

| Option | Description | Selected |
|--------|-------------|----------|
| Keep as standalone banner | rename_warning stays as amber banner; template checks device_type directly | |
| Absorb into warnings box | Add RENAME_REQUIRED check to health_checks.py; rename warning becomes a third Warning object | ✓ |
| Remove it entirely | Drop the banner — hostname is visible at the top of the sheet | |

**User's choice:** Absorb into warnings box  
**Notes:** evaluate_warnings() will now return 3 Warning objects. RENAME_REQUIRED check fires when parsed_hostname.device_type == 'Unknown'. No AuditReport changes needed — parsed_hostname already in scope.

---

## Per-Check Row Layout

| Option | Description | Selected |
|--------|-------------|----------|
| Badge + message | [OK/WARN badge] + message text only; detail hidden | |
| Badge + message + detail | Message on line 1; detail on line 2 (muted, indented) | ✓ |
| Badge only (minimal) | Just badge + check code (e.g., ✓ OS_VERSION) | |

**User's choice:** Badge + message + detail  
**Notes:** Show full Warning content per row. Detail line appears only when detail is not None.

---

## Collapsible Mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| `<details>/<summary>` native HTML | Browser-native collapse; Jinja2 sets `open` attribute; zero JS | ✓ |
| CSS + JS toggle | Custom animation/chevron; introduces JavaScript to currently JS-free file | |

**User's choice:** `<details>/<summary>` native HTML  
**Notes:** `open` attribute set by Jinja2 when any warning.severity == 'WARN'. Keeps project JS-free.

---

## Box Position in the Sheet

| Option | Description | Selected |
|--------|-------------|----------|
| After Quest Status, before Dept Reference | Replaces existing os_warning/rename_warning banner slot | ✓ |
| After Dept Reference, before Chronicle | Literally the last content before the timestamp | |

**User's choice:** After Quest Status, before Dept Reference  
**Notes:** Natural replacement for the existing banner area. New order: header → stat block → software → quest status → WARNINGS BOX → dept reference → chronicle.

---

## Claude's Discretion

- CSS class names for warnings box elements
- `<summary>` chevron styling
- Detail line indentation
- "1 warning" vs "1 warning(s)" singular/plural form

## Deferred Ideas

None.
