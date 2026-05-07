---
phase: 08-ninjaone-compatibility
reviewed: 2026-05-07T00:00:00Z
depth: standard
files_reviewed: 2
files_reviewed_list:
  - main.py
  - tests/test_main.py
findings:
  critical: 0
  warning: 1
  info: 2
  total: 3
status: issues_found
---

# Phase 8: Code Review Report

**Reviewed:** 2026-05-07
**Depth:** standard
**Files Reviewed:** 2
**Status:** issues_found

## Summary

Reviewed `main.py` (NINJA-01 isatty guard + NINJA-02 [SUMMARY] line) and `tests/test_main.py` (4 new tests). The core logic is correct: the `[SUMMARY]` print fires unconditionally before the `isatty()` block, ensuring NinjaOne always captures it. The headless guard on lines 93-98 correctly wraps both `os.startfile()` and `input()`. Field names (`ram_gb`, `disk_total_gb`, `disk_free_gb`) match `models.AuditReport`. The test helper `_patched_main` is well-structured and covers the required scenarios.

One warning-level issue: the inline `import errno` inside the `except` handler is a Python anti-pattern that can mask `ImportError` at runtime. One info item covers the unbounded filename-collision loop; another covers Windows-only test portability.

---

## Warnings

### WR-01: Inline `import errno` inside exception handler can mask import failures

**File:** `main.py:76`
**Issue:** `import errno as _errno` is placed inside an `except OSError` block. If the stdlib `errno` module somehow fails to import (edge case, but possible in a corrupted PyInstaller bundle), the `ImportError` will be raised inside an already-active exception handler, replacing the original `OSError` with a confusing `ImportError` and hiding the real failure. Even in normal operation, re-importing on every write failure adds unnecessary overhead, and the unusual placement will confuse future readers.
**Fix:** Move the import to the top of the file with the other stdlib imports:

```python
# At top of file, with other imports
import errno
import os
import socket
import sys
```

Then remove the inline import from inside the handler:

```python
except OSError as exc:
    if exc.errno == errno.ENOSPC:
        print("[ERROR] USB drive is full. Free up space and try again.")
    else:
        print(f"[ERROR] Write failed: {exc}")
    sys.exit(1)
```

---

## Info

### IN-01: Filename collision loop has no upper bound

**File:** `main.py:62-65`
**Issue:** The loop that generates unique filenames (`status_HOST_DATE (2).html`, `(3).html`, etc.) has no maximum iteration cap. If a very large number of files already exist, it will run indefinitely. In practice this cannot happen (a USB drive would be full long before thousands of same-day reports), but the unbounded loop is a code smell.
**Fix:** Add a reasonable cap and exit cleanly if exceeded:

```python
MAX_DEDUP = 999
counter = 2
while output_path.exists() and counter <= MAX_DEDUP:
    output_path = logs_dir / f"{base_name} ({counter}).html"
    counter += 1
if output_path.exists():
    print("[ERROR] Too many reports for today. Clear old files from the logs/ folder.")
    sys.exit(1)
```

---

### IN-02: `patch("main.os.startfile")` will raise `AttributeError` on non-Windows

**File:** `tests/test_main.py:72`
**Issue:** `os.startfile` does not exist on Linux or macOS. `unittest.mock.patch` looks up the attribute before replacing it, so `patch("main.os.startfile", mock_startfile)` raises `AttributeError` on non-Windows platforms. This means all four tests fail on any non-Windows CI environment. The tool is Windows-only, so this may be intentional, but it is not documented and will cause confusing CI failures if the repo is ever tested cross-platform.
**Fix:** Guard the patch with a platform check, or mark the tests explicitly:

```python
import sys as _sys
import pytest

pytestmark = pytest.mark.skipif(
    _sys.platform != "win32",
    reason="os.startfile is Windows-only; tests require Windows"
)
```

Alternatively, document the Windows-only requirement in the module docstring so future contributors are not surprised.

---

_Reviewed: 2026-05-07_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
