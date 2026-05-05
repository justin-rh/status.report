---
phase: 05-packaging-and-distribution
reviewed: 2026-05-05T00:00:00Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - .gitignore
  - requirements-dev.txt
  - renderer/__init__.py
  - main.py
  - status_report.spec
  - build.bat
findings:
  critical: 0
  warning: 3
  info: 4
  total: 7
status: issues_found
---

# Phase 05: Code Review Report

**Reviewed:** 2026-05-05
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

Reviewed the Phase 5 packaging and distribution deliverables: the PyInstaller spec, one-command build script, output-path logic in `main.py`, and the renderer additions. The architecture is sound and the critical CLAUDE.md constraints are correctly implemented (`--onedir`, `sys.executable`-relative paths, no host-PC writes, `upx=False`, `console=True`). No security vulnerabilities or data-loss bugs were found.

Three warnings require attention before shipping: a write failure that leaves a zero-byte output file, an untested edge case in the collision-avoidance filename loop, and an `OSError` branch that exits with a fixed code `1` instead of the actual OS error code, masking the real failure reason. Four informational items round out the review.

---

## Warnings

### WR-01: Zero-byte output file left on USB when `write_text` fails mid-write

**File:** `main.py:67`
**Issue:** `output_path.write_text(html, encoding="utf-8")` is called only after `output_path` was determined to be non-existent (lines 60–62). However, `Path.write_text` will create the file before flushing its content. If the write is interrupted (e.g., USB disconnected mid-write, disk full after the `ENOSPC` check races), the file is created but empty or truncated, and `sys.exit(1)` leaves that orphaned file on the drive. On the next run the collision-avoidance loop will see it and bump the counter, and IT will have a confusing `status_HOSTNAME_2026-05-05.html` (0 bytes) alongside `status_HOSTNAME_2026-05-05 (2).html`.

**Fix:** Write to a temp name and rename atomically, or delete the partial file in the `except` handlers:

```python
try:
    output_path.write_text(html, encoding="utf-8")
except (PermissionError, OSError) as exc:
    # Clean up the partial file so the next run doesn't see a stub
    if output_path.exists():
        try:
            output_path.unlink()
        except OSError:
            pass
    # ... existing error message / sys.exit logic ...
```

---

### WR-02: `OSError` general branch exits with code `1` instead of `exc.errno`, hiding the root cause

**File:** `main.py:73-78`
**Issue:** The `ENOSPC` branch correctly identifies disk-full errors, but any other `OSError` (e.g., `EROFS` — read-only filesystem, `EACCES` — permissions denied at directory level, network path gone) falls through to `print(f"[ERROR] Write failed: {exc}")` and `sys.exit(1)`. Exiting with a fixed code `1` means a calling script or IT test harness cannot distinguish write-failure from activation failure (which also exits `1` in `build.bat`). The error text does include `exc` which is good, but:
- `errno` is imported lazily inside the `except` block as `_errno` with an unusual alias — this works but is non-idiomatic and would confuse future maintainers.
- `sys.exit(exc.errno)` would propagate the real OS error code to any wrapper.

**Fix:**

```python
import errno  # move to top-of-file imports

# ...inside the except OSError block:
except OSError as exc:
    if exc.errno == errno.ENOSPC:
        print("[ERROR] USB drive is full. Free up space and try again.")
    else:
        print(f"[ERROR] Write failed: {exc}")
    sys.exit(exc.errno or 1)
```

---

### WR-03: Collision-avoidance loop has no upper bound — hangs indefinitely if filesystem is corrupted

**File:** `main.py:59-62`
**Issue:** The `while output_path.exists()` loop increments a counter with no maximum. On a healthy drive this is fine. On a drive where `Path.exists()` always returns `True` due to filesystem corruption, a permissions anomaly, or a network share reporting stale entries, the loop runs forever. This is particularly relevant because the tool runs on unknown production machines.

**Fix:** Add a reasonable cap (e.g., 99) and fail clearly:

```python
MAX_COLLISIONS = 99
counter = 2
while output_path.exists():
    if counter > MAX_COLLISIONS:
        print(f"[ERROR] Cannot create output file — {MAX_COLLISIONS} copies already exist.")
        sys.exit(1)
    output_path = logs_dir / f"{base_name} ({counter}).html"
    counter += 1
```

---

## Info

### IN-01: `render_report` and `render_html` duplicate the Environment + template-load boilerplate

**File:** `renderer/__init__.py:55-75`
**Issue:** Both `render_report` and `render_html` call `_load_template_source()`, construct a `jinja2.Environment(autoescape=True)`, call `env.from_string()`, call `_build_context()`, and call `template.render()`. The only difference is that `render_report` passes the result to `write_html`. This four-line block is duplicated verbatim. Future edits (e.g., adding `undefined=StrictUndefined`) must be made in two places.

**Fix:** Extract the shared logic into a private helper:

```python
def _render_to_string(report: AuditReport) -> str:
    template_source = _load_template_source()
    env = Environment(autoescape=True)
    template = env.from_string(template_source)
    return template.render(**_build_context(report))

def render_report(report: AuditReport, output_path: Path) -> Path:
    return write_html(_render_to_string(report), output_path)

def render_html(report: AuditReport) -> str:
    return _render_to_string(report)
```

---

### IN-02: `import errno` is deferred inside `except` block rather than at module top

**File:** `main.py:73`
**Issue:** `import errno as _errno` is placed inside the `except OSError` handler. This works in CPython (imports are cached after the first load) but is non-idiomatic and violates PEP 8's convention of placing all imports at the top of the module. It would also slow down repeated `except` paths marginally and confuses static analysis tools (mypy, pylance).

**Fix:** Move `import errno` to the top-level imports block alongside `import sys`.

---

### IN-03: `.gitignore` does not exclude `*.spec` build artifacts or the `logs/` runtime directory

**File:** `.gitignore`
**Issue:** `status_report.spec` is intentionally checked in (per the spec-file comment on line 1), which is correct. However:
- `logs/` (written by `main.py` at `Path(sys.executable).parent / "logs"`) could appear at repo root if a developer runs the unfrozen script directly from the repo directory during testing, writing HTML audit files to `logs/` within the repo. There is no entry in `.gitignore` to prevent accidental commits of those files.
- The `*.spec` note is fine — the file is intentional — but a comment in `.gitignore` would make this explicit to future contributors.

**Fix:**

```gitignore
# Runtime output (from running main.py unfrozen during development)
logs/
```

---

### IN-04: `requirements-dev.txt` pins `pyinstaller==6.20.0` by exact version with no comment on PyInstaller compatibility risks

**File:** `requirements-dev.txt:2`
**Issue:** The exact pin is deliberate and appropriate for reproducible builds. However, `pytest==8.*` uses a range (minor version float) while `pyinstaller==6.20.0` uses an exact pin. The inconsistency is minor but could confuse a developer who wonders why one is pinned loosely and one exactly. A brief comment explaining the PyInstaller pin (e.g., "exact pin — PyInstaller minor versions can change frozen import behaviour") would document the intent.

**Fix:** Add an inline comment:

```
pytest==8.*
pyinstaller==6.20.0  # exact pin: minor version changes can affect frozen bundle behaviour
```

---

_Reviewed: 2026-05-05_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
