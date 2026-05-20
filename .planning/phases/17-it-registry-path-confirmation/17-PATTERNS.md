# Phase 17: IT Registry Path Confirmation - Pattern Map

**Mapped:** 2026-05-20
**Files analyzed:** 5 (3 code/test, 2 documentation/planning)
**Analogs found:** 4 / 5 (1 planning artifact has no code analog by design)

## File Classification

| New/Modified File | New/Modify | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------------|------|-----------|----------------|---------------|
| `collectors/windows/vendor.py` | Modify | collector + new diagnostic function | registry read + filesystem read | self (lines 29–60 `_detect_dcu` + 13 import of `_search_uninstall_keys`) | exact (extends existing module) |
| `main.py` | Modify | CLI argparse short-circuit branch | request-response (CLI in / stdout out / exit) | `main.py` lines 113–153 `_run_cli_app` and lines 167–176 `--app` dispatch | exact |
| `tests/test_vendor_collector.py` | Modify | unit tests | mock-based assertion | self (lines 78–96 keyword-variant DCU test) + `tests/test_cli_phase15.py` lines 69–123 (CLI short-circuit tests) | exact (extend existing file) |
| `.planning/phases/17-it-registry-path-confirmation/17-IT-CONFIRMATION.md` | New | planning artifact (Edgar-authored execution evidence) | n/a — human-authored doc | none — no code analog by design (see "No Analog Found") | n/a |
| `.planning/STATE.md` | Modify | GSD state document | n/a — YAML+markdown | git commit `066d5f9` (Phase 16 close — removed phase ref + advanced phase pointer) | exact (same shape edit) |

---

## Pattern Assignments

### `collectors/windows/vendor.py` (collector, registry+file passive read; +new diagnostic)

**Analog:** Self — the file already follows the patterns the new diagnostic must mirror. Reuse the existing helper import and the DCU XML probe verbatim.

**Existing import — reuse the production registry helper (lines 7–13):**
```python
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from models import AuditReport, VendorUpdateStatus
from collectors.windows.apps import _search_uninstall_keys
```
The diagnostic MUST call `_search_uninstall_keys` (or enumerate `UNINSTALL_PATHS` directly when an unfiltered dump is needed — see below) so what Edgar sees is what production sees. No new helper; no duplicated hive list. Per CONTEXT.md §D-01 and §code_context "Reusable Assets".

**Existing DCU XML probe — reuse for the `--diag-vendor` XML section (lines 38–49):**
```python
if installed:
    p = Path(DCU_XML_PATH)
    if p.exists():
        try:
            root = ET.parse(p).getroot()
            # Root element: <updates>, direct children: <update> per D-12 / RESEARCH.md
            pending_count = len(root.findall("update"))
            scan_data_present = True
        except ET.ParseError:
            # File present but malformed (e.g. partial write during DCU scan)
            scan_data_present = True
            pending_count = None
```
The diagnostic XML section should print `DCU_XML_PATH`, `p.exists()`, `p.stat().st_size` if present, and the same `len(root.findall("update"))` count — matching the production read exactly (CONTEXT.md §D-03).

**Unfiltered hive enumeration — pattern from `apps.py` lines 134–174 (read for the new diagnostic function):**
```python
for hive, path in UNINSTALL_PATHS:
    try:
        with winreg.OpenKey(hive, path) as root:
            i = 0
            while True:
                try:
                    subkey_name = winreg.EnumKey(root, i)
                    i += 1
                except OSError:
                    break  # EnumKey raises OSError when index exhausted — normal end
                try:
                    with winreg.OpenKey(root, subkey_name) as subkey:
                        display_name, _ = winreg.QueryValueEx(subkey, "DisplayName")
                        # ... read DisplayVersion / InstallLocation here
                except (FileNotFoundError, OSError):
                    continue  # Skip unreadable subkey silently
    except (FileNotFoundError, OSError):
        continue  # Path not present on this machine
```
The diagnostic needs an unfiltered walk (D-02: "every Uninstall subkey across all 4 hives whose `DisplayName` contains 'Dell' or 'Lenovo'") so it can surface DisplayNames NOT in the keyword list. Use this enumeration shape with a coarse `if "dell" in dn_lower or "lenovo" in dn_lower:` filter at the inner read. Per-hive label printing requires iterating with hive index so each row can be tagged `HKLM` / `HKLM\Wow6432Node` / `HKCU` / `HKCU\Wow6432Node` — derive the label from the `(hive, path)` tuple at the top of the loop.

**LSU keyword list — add comment block here (current lines 63–72):**
```python
def _detect_lsu(report: AuditReport) -> None:
    """Detect Lenovo System Update via registry. No passive count source in v3.0 (D-14)."""
    try:
        installed, _version = _search_uninstall_keys([
            "Lenovo System Update",
            "Lenovo Vantage Service",
            "Lenovo Vantage",
            "Lenovo Commercial Vantage",
        ])
```
Per D-11: add a comment block above the keyword list. The two Edgar-confirmed entries (per D-09) are `"Lenovo Vantage"` and `"Lenovo Commercial Vantage"`. The other two (`"Lenovo System Update"`, `"Lenovo Vantage Service"`) are defensive — explicitly label them and cite `.planning/phases/17-it-registry-path-confirmation/17-IT-CONFIRMATION.md`.

**Never-raise envelope (existing pattern, lines 29–60) — diagnostic must match:**
```python
def _detect_dcu(report: AuditReport) -> None:
    try:
        # ... real work
    except Exception as exc:
        report.collection_errors.append(f"DCU detection failed: {exc}")
        report.dell_dcu = VendorUpdateStatus(
            installed=None, pending_count=None, scan_data_present=False
        )
```
The new `--diag-vendor` function follows the same envelope but writes to **stdout instead of a report field** (it's a CLI mode, not a collector). Wrap registry enumeration per-hive in `try/except (OSError, FileNotFoundError)` and print a one-line note on failure rather than raising — per CONTEXT.md "Established Patterns" #2.

**Constraint reminder (PROJECT.md / CLAUDE.md):** NO subprocess invocation of `dcu-cli.exe` or `tvsu.exe`. Diagnostic stays registry + file passive.

---

### `main.py` (CLI argparse short-circuit dispatch)

**Analog:** `main.py` lines 113–153 (`_run_cli_app`) and 167–176 (`--app` dispatcher block). The `--diag-vendor` flag is structurally identical.

**Argparse declaration — add alongside existing flags (current lines 161–167):**
```python
parser.add_argument("--name", action="store_true", help="Print PC hostname to stdout and exit")
parser.add_argument("--serial", action="store_true", help="Print device serial number to stdout and exit")
parser.add_argument("--warnings", action="store_true", help="Print active warnings to stdout and exit")
parser.add_argument("--updates", action="store_true", help="Query Windows Update Agent for pending update count (slow; omitted by default)")
parser.add_argument("--json",   action="store_true", help="Write AuditReport as JSON alongside HTML report; full pipeline always runs")
parser.add_argument("--output", metavar="PATH",      help="Override default logs/ destination for all file output (HTML and JSON)")
parser.add_argument("--app",    metavar="NAME",      help="Run app-detection for one named app; print result to stdout and exit")
```
Add: `parser.add_argument("--diag-vendor", action="store_true", help="<one-line per D-Discretion §1>")`. Boolean action (no metavar), short-circuit. Note argparse converts `--diag-vendor` to `args.diag_vendor`.

**Short-circuit dispatcher — pattern from `--app` block (lines 170–176):**
```python
# --app: single-app detection path — exits before cli_mode check
# MUST be checked before cli_mode (RESEARCH.md Anti-Patterns, Pitfall note)
if args.app:
    if args.output:
        print("WARNING: --output is ignored in --app mode", file=sys.stderr)
    _run_cli_app(args)
    return
```
Add a parallel block (above or below this one — planner picks ordering):
```python
if args.diag_vendor:
    if args.output:
        print("WARNING: --output is ignored in --diag-vendor mode", file=sys.stderr)
    _run_cli_diag_vendor(args)
    return
```
The DEBT-03 stderr warning shape (`"WARNING: --output is ignored in --<mode> mode"`) is reused verbatim per CONTEXT.md §code_context "Established Patterns" #3.

**Short-circuit function body — pattern from `_run_cli_app` (lines 113–153, abridged):**
```python
def _run_cli_app(args: argparse.Namespace) -> None:
    """Handle --app <name> mode: detect one app, print result to stdout, exit.

    Runs only the app-detection pipeline for a single named app.
    Never writes files (D-08, D-13). Exits 0 on match, 1 on no match (D-11).
    Platform dispatch selects correct spec list (D-14, RESEARCH.md Pitfall 1).
    """
    if sys.platform == "darwin":
        from collectors.mac.apps import _detect_one_app, MAC_APP_SPECS as specs
    else:
        from collectors.windows.apps import _detect_one_app, APP_SPECS as specs
    # ... do work ...
    if args.json:
        print(json.dumps(dataclasses.asdict(app_status), indent=2))
    else:
        print(_format_app_status_line(app_status))
    sys.exit(0)
```
The new `_run_cli_diag_vendor` function:
- Lives in `main.py` (parallel to `_run_cli_app`).
- Imports the new diagnostic from `collectors.windows.vendor` (Windows-only — `--diag-vendor` is meaningless on Mac; gate with `sys.platform != "darwin"` and exit gracefully if invoked on Mac per planner discretion).
- Calls the diagnostic, which prints to stdout directly (or returns a string the function prints — planner picks).
- Calls `sys.exit(0)` at end — same as `_run_cli_app` line 153.
- Writes nothing to disk (the `--output` warning above is precisely because output is ignored).

**Constraint reminder:** Per CLAUDE.md and CONTEXT.md `<canonical_refs>` Standing constraints — output goes to stdout only. Do NOT write to host PC.

---

### `tests/test_vendor_collector.py` (extension — keyword-variant + new diagnostic tests)

**Analog A — existing keyword-variant test (current lines 78–96):**
```python
def test_dcu_installed_xml_present_two_updates(self, tmp_path):
    xml_content = """<updates>
  <update><name>Driver A</name><urgency>Recommended</urgency></update>
  <update><name>BIOS 1.5</name><urgency>Urgent</urgency></update>
</updates>"""
    xml_file = tmp_path / "DCUApplicableUpdates.xml"
    xml_file.write_text(xml_content)
    fake_ctx = _make_fake_ctx()
    with patch.object(apps_mod.winreg, "OpenKey", return_value=fake_ctx), \
         patch.object(apps_mod.winreg, "EnumKey",
                      side_effect=_make_enum_fn(["DCU key"])), \
         patch.object(apps_mod.winreg, "QueryValueEx",
                      side_effect=_make_query_fn("Dell Command | Update", "5.5.0")), \
         patch.object(vendor_mod, "DCU_XML_PATH", str(xml_file)):
        report = make_report()
        vendor_mod.collect_vendor_updates(report)
    assert report.dell_dcu.installed is True
```
**Apply for D-13 keyword variants:** if Edgar reports a new Dell or Lenovo DisplayName variant, add a parameterized test that mocks `QueryValueEx` with `_make_query_fn("<new variant>", "<version>")` and asserts `report.dell_dcu.installed is True` (or `report.lenovo_lsu.installed is True`).

**Apply for D-14 new XML path:** if Edgar reports the XML lives elsewhere, the test still uses `patch.object(vendor_mod, "DCU_XML_PATH", str(xml_file))` for behavior verification — but additionally add a constant-value test:
```python
def test_dcu_xml_path_constant():
    assert vendor_mod.DCU_XML_PATH == r"<new confirmed path>"
```

**Mock helpers (already in file, reuse — lines 25–45):**
```python
def _make_fake_ctx() -> MagicMock:
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=ctx)
    ctx.__exit__ = MagicMock(return_value=False)
    return ctx

def _make_enum_fn(subkeys: list[str]):
    def enum_fn(key, index):
        if index < len(subkeys):
            return subkeys[index]
        raise OSError("exhausted")
    return enum_fn

def _make_query_fn(display_name: str, display_version: str | None = None):
    def query_fn(key, value_name):
        if value_name == "DisplayName":
            return (display_name, 1)
        if value_name == "DisplayVersion" and display_version is not None:
            return (display_version, 1)
        raise FileNotFoundError(f"no value {value_name!r}")
    return query_fn
```
Reuse verbatim for any new vendor-collector tests. For diagnostic tests that need to surface multiple DisplayNames (Dell + Lenovo + unrelated), extend `_make_query_fn` to accept a list of `(displayName, displayVersion)` pairs indexed by subkey, or write a per-test custom side_effect.

**Analog B — CLI short-circuit test pattern (from `tests/test_cli_phase15.py` lines 69–104, the `--app` flag tests):**
```python
def test_app_flag_not_installed(capsys):
    """--app ninjaone prints '<name>: not installed' when app is absent (D-12)."""
    import main
    def fake_detect(spec, report):
        report.apps.append(AppStatus(name="NinjaOne", installed=False))
    with (
        patch("sys.argv", ["scry", "--app", "ninjaone"]),
        patch("main.sys.platform", "win32"),
        patch("collectors.windows.apps._detect_one_app", side_effect=fake_detect),
    ):
        with pytest.raises(SystemExit) as exc_info:
            main.main()
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert captured.out.strip() == "NinjaOne: not installed"
```
**Apply for `--diag-vendor` CLI tests:**
- `patch("sys.argv", ["scry", "--diag-vendor"])`.
- `patch("main.sys.platform", "win32")`.
- Mock the diagnostic function (or mock `winreg.OpenKey` / `winreg.EnumKey` / `winreg.QueryValueEx` from `apps_mod` since that's where `_search_uninstall_keys` lives — see analog A pattern).
- Wrap `main.main()` in `pytest.raises(SystemExit)` and assert `exit_info.value.code == 0`.
- `capsys.readouterr()` to assert the printed dump contains expected DisplayName / hive label / XML path lines.

**`--diag-vendor --output PATH` stderr warning test — pattern from existing DEBT-03 test (search `tests/test_cli_phase16*.py` or wherever the `--app --output` warning lives — planner verifies):**
```python
# Expected shape:
def test_diag_vendor_with_output_warns_to_stderr(capsys):
    with patch("sys.argv", ["scry", "--diag-vendor", "--output", "/tmp/x"]):
        with pytest.raises(SystemExit):
            main.main()
    captured = capsys.readouterr()
    assert "WARNING: --output is ignored in --diag-vendor mode" in captured.err
```

**Standard never-raise assertion (current lines 150–156):**
```python
def test_never_raises_on_exception(self):
    with patch.object(apps_mod.winreg, "OpenKey", side_effect=RuntimeError("total failure")):
        report = make_report()
        try:
            vendor_mod.collect_vendor_updates(report)
        except Exception as exc:
            pytest.fail(f"collect_vendor_updates raised: {exc}")
```
Mirror this for the new diagnostic function: if `winreg.OpenKey` raises `RuntimeError`, `--diag-vendor` should print a one-line note (not crash) and still `sys.exit(0)`.

---

### `.planning/phases/17-it-registry-path-confirmation/17-IT-CONFIRMATION.md` (new planning artifact)

**Analog:** None in codebase by design. Created during phase execution by the executor running `--diag-vendor` and pasting Edgar's findings.

Per CONTEXT.md §D-06, minimum per-machine content:
- hostname (proves real enrolled machine)
- date of the run
- raw matched DisplayName + DisplayVersion
- hive where the matching Uninstall subkey was found

Per CONTEXT.md §D-Discretion §6, keep template simple: one section per machine + top-line summary of which CONF-IDs are closed. Per §D-08, BOTH CONF-01 (Dell) and CONF-02 (Lenovo) must have an entry — positive OR negative result (per §D-15 / §D-16) — before phase 17 closes.

The planner should add a "create artifact" action to the plan with skeleton headings only; the executor populates per-machine sections from `--diag-vendor` output.

---

### `.planning/STATE.md` (modify — clear blocker lines, advance pointer)

**Analog:** Phase 16 closure — git commit `066d5f9` (`docs(phase-16): complete phase execution — mark complete, advance to phase 17`).

**Pattern excerpt from commit `066d5f9`:**
```diff
-status: ready-to-execute
-stopped_at: Phase 16 planned — 2 plans, 1 wave
+status: phase-complete
+stopped_at: Phase 16 complete — 2/2 plans, verification passed
-last_activity: 2026-05-19 — Phase 16 planned; ...
+last_activity: 2026-05-19 — Phase 16 executed; ...
-  completed_phases: 0
+  completed_phases: 1
-  completed_plans: 0
-  percent: 0
+  completed_plans: 2
+  percent: 20
...
-**Current focus:** v3.1 Cleanup — Phase 16 ready to plan (tech debt cleanup)
+**Current focus:** v3.1 Cleanup — Phase 17 next (Requirements Automation Hook)
-Phase: 16 of 20 (Tech Debt Cleanup)
+Phase: 17 of 20 (Requirements Automation Hook)
```
The Phase 17 closure edit follows the same shape, plus removing the blocker lines:

**Current `STATE.md` lines 56–60 (the blockers to remove on phase 17 close):**
```markdown
### Blockers/Concerns

- **Phase 18 gate:** Dell Command Update and Lenovo System Update registry paths unconfirmed — requires scheduling meeting with Edgar/IT before Phase 18 can complete
- **Phase 20 gate:** Depends on Phase 18 completing first (confirmed paths may require code updates before live Dell/Lenovo validation)
- **Phase 19/20 gate:** Requires access to real enrolled Windows machines (SYSTEM/Admin account, Dell hardware, Intune-enrolled machine) and a real Mac
```
**Action:** Remove the "Phase 18 gate" line (DCU/LSU registry paths now confirmed via `17-IT-CONFIRMATION.md`). Remove or rewrite the "Phase 20 gate" line (its dependency was on the now-removed registry-path blocker; the cascade reference is stale). Keep the "Phase 19/20 gate" line (real-hardware dependency is unchanged by Phase 17). Per CONTEXT.md §code_context "Drift to fix": also update line 24's parenthetical from `Phase 17 next (IT Registry Path Confirmation)` to whichever phase comes next (Phase 18 once 17 closes).

**Also fix in this edit (planner discretion — can be one-line side-fix at plan-phase start or part of phase close):** STATE.md still says "Phase 18 gate" for what was actually a Phase 18+19 gate before the phase renumbering. CONTEXT.md §code_context "Integration Points" notes: "currently mis-tagged to 'Phase 18' — they actually gate phases 18 AND 19".

---

## Shared Patterns

### Pattern: Reuse the production registry helper (DRY guarantee)
**Source:** `collectors/windows/apps.py` lines 134–174 (`_search_uninstall_keys`) and lines 25–30 (`UNINSTALL_PATHS`).
**Apply to:** `collectors/windows/vendor.py` new diagnostic function.
**Excerpt (the import — already in vendor.py line 13):**
```python
from collectors.windows.apps import _search_uninstall_keys
```
For the unfiltered dump variant, also import `UNINSTALL_PATHS` and iterate it directly:
```python
from collectors.windows.apps import UNINSTALL_PATHS, _search_uninstall_keys
```
Per CONTEXT.md §D-01: "Reuses the production `_search_uninstall_keys` helper so what Edgar sees IS what the production collector sees. No standalone script and no PowerShell runbook."

### Pattern: Never raise across the layer boundary
**Source:** `collectors/windows/vendor.py` lines 56–60 (existing `_detect_dcu` exception envelope) and `collectors/windows/apps.py` lines 170–174 (per-hive try/except in `_search_uninstall_keys`).
**Apply to:** New `--diag-vendor` diagnostic. Wrap per-hive enumeration in `try/except (FileNotFoundError, OSError)` and print a one-line note rather than raising. CLI mode still `sys.exit(0)` even on partial failure (the diagnostic is observational — incomplete output is more useful than a crash).
**Excerpt:**
```python
try:
    with winreg.OpenKey(hive, path) as root:
        # ... enumerate ...
except (FileNotFoundError, OSError):
    print(f"  [note] hive {label} unreadable — skipped")
    continue
```

### Pattern: Short-circuit CLI flag (parse → run → print → exit before full pipeline)
**Source:** `main.py` lines 113–153 (`_run_cli_app`) and lines 170–176 (dispatcher block).
**Apply to:** New `--diag-vendor` flag (D-04: "short-circuit mode like `--name` / `--app`").
**Excerpt (dispatcher shape):**
```python
if args.diag_vendor:
    if args.output:
        print("WARNING: --output is ignored in --diag-vendor mode", file=sys.stderr)
    _run_cli_diag_vendor(args)
    return
```
Must be checked BEFORE the `cli_mode = args.name or args.serial or args.warnings` gate (mirrors how `args.app` is checked before `cli_mode` on lines 172–176).

### Pattern: Stderr warning when output is ignored (DEBT-03 from Phase 16)
**Source:** `main.py` lines 172–174 (`--app NAME --output PATH` warning).
**Apply to:** `--diag-vendor --output PATH` combination.
**Excerpt:**
```python
if args.output:
    print("WARNING: --output is ignored in --<mode> mode", file=sys.stderr)
```
Exact wording: `"WARNING: --output is ignored in --diag-vendor mode"`. Goes to `sys.stderr`, then the short-circuit handler proceeds normally.

### Pattern: Standard-user account compatibility
**Source:** `_search_uninstall_keys` enumerates both HKLM AND HKCU hives — works under any account.
**Apply to:** `--diag-vendor` (D-04: "Runs under any account — no SYSTEM elevation required. Mirrors production"). No additional code change needed; reusing `_search_uninstall_keys` / `UNINSTALL_PATHS` inherits this property for free.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `.planning/phases/17-it-registry-path-confirmation/17-IT-CONFIRMATION.md` | planning artifact (human-authored evidence log) | n/a — markdown documentation | No code analog by design. Created during phase execution by pasting `--diag-vendor` output and Edgar's annotations. Planner should add a skeleton-template step to the plan; executor populates from real-machine runs. See CONTEXT.md §D-05 and §D-06 for required content; §D-Discretion §6 for template freedom. |

---

## Metadata

**Analog search scope:** `collectors/windows/`, `main.py`, `tests/test_vendor_collector.py`, `tests/test_cli_phase15.py`, `.planning/STATE.md` git history (commit `066d5f9`).
**Files scanned:** 7 (vendor.py, apps.py, main.py, test_vendor_collector.py, test_cli_phase15.py, STATE.md, CONTEXT.md).
**Pattern extraction date:** 2026-05-20.
**Key insight:** All four code/test analogs already exist in-repo. Phase 17 is structurally an extension of existing patterns — no new architectural primitives are introduced. The diagnostic is a re-presentation of the same registry data the collector already reads, making "production reads X, diagnostic shows X" trivially true.
