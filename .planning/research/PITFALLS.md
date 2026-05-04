# Pitfalls Research

**Domain:** Windows IT audit/inventory executable (USB-portable, PyInstaller, multi-locale deployment)
**Researched:** 2026-05-04
**Confidence:** HIGH (all critical pitfalls verified against official docs, PyInstaller docs, or known community post-mortems)

---

## Critical Pitfalls

### Pitfall 1: CrowdStrike Falcon Quarantines the Executable Before IT Staff Can Run It

**What goes wrong:**
The tool is copied to the USB drive and handed to IT staff. On the first machine they try it on, CrowdStrike Falcon silently quarantines or blocks the .exe before it ever launches. The IT staff member sees nothing, or sees a generic Windows "this app has been prevented" error. The audit cannot run. This is not a theoretical risk — CrowdStrike has behavioral detection rules specifically targeting the PyInstaller one-file pattern: write files to %TEMP%\\_MEIxxxxxx, then execute them. That is textbook "dropper" behavior to an EDR.

**Why it happens:**
PyInstaller `--onefile` mode works by embedding all Python files and the interpreter into a single executable. At launch, the bootloader extracts everything into a randomly-named temp directory (`_MEIxxxxxx`) and then executes from there. This extract-then-execute pattern is identical to how malware "packers" work. CrowdStrike's behavioral engine does not distinguish intent — it sees the pattern and blocks it. Since CrowdStrike is the project's own EDR (per PROJECT.md), every target machine will have it.

**How to avoid:**
1. **Primary: Use `--onedir` mode instead of `--onefile`.** A folder layout with a single launcher `.exe` plus a `_internal/` subfolder does not trigger the extract-then-execute heuristic because nothing is written to `%TEMP%` at startup. The USB drive holds the folder; IT staff runs the `.exe` from within it. This is the correct choice for this project.
2. **If `--onefile` is kept:** Submit the signed binary hash to CrowdStrike's allowlisting process before deployment. This requires a code-signing certificate. Without a certificate, each rebuilt binary has a new hash and must be re-submitted.
3. **Code-sign the binary** regardless of which mode is used — signed binaries face substantially fewer behavioral blocks from both Defender and Falcon.
4. **Test on a CrowdStrike-enrolled machine before first deployment.** Do not discover this on a customer site.

**Warning signs:**
- Binary runs fine on the developer machine (not CrowdStrike-enrolled) but fails on any production machine.
- Windows shows "Windows protected your PC" (SmartScreen) rather than a CrowdStrike message — this is a different but related problem (see Pitfall 2).
- IT staff reports the file "disappears" after copying — this is quarantine.

**Phase to address:**
Packaging phase (PyInstaller configuration). Decide `--onedir` vs `--onefile` before writing any packaging code. Test on an enrolled machine as part of the packaging acceptance criteria.

---

### Pitfall 2: Windows SmartScreen Blocks Every New Build Until Reputation Accumulates

**What goes wrong:**
Even if CrowdStrike allows the binary, Windows SmartScreen (built into Windows 10/11) shows a blue "Windows protected your PC" dialog the first time an unsigned or newly-signed binary is run from a USB drive. SmartScreen reputation is file-hash-based and accumulated from download telemetry — a binary that has never been seen by Microsoft's cloud has zero reputation and is blocked by default. Every time the binary is rebuilt (new features, bug fixes), the hash changes and reputation resets to zero.

**Why it happens:**
SmartScreen uses a cloud-based reputation system. New binaries with unknown hashes are treated as suspicious. Binaries run from removable drives are subject to stricter evaluation than those installed via trusted channels.

**How to avoid:**
1. **Code-sign with an Extended Validation (EV) certificate.** EV certificates bypass SmartScreen's reputation requirement entirely — the binary runs without the warning dialog on first execution. Standard OV certificates reduce friction but do not eliminate it for zero-reputation binaries.
2. **If no certificate is available for v1:** Document the manual bypass (click "More info" → "Run anyway") in the IT staff runbook. This is an acceptable short-term position since the audience is internal IT staff, not end users.
3. **Do not rebuild the binary more often than necessary.** Each rebuild resets reputation. Pin dependency versions.

**Warning signs:**
- Blue SmartScreen dialog appears on any machine the tool is run on for the first time.
- Unsigned or OV-signed binary fails to run at all on machines with SmartScreen set to "Block" (configurable via Intune/Group Policy).

**Phase to address:**
Packaging phase. The code-signing decision must be made before distribution begins. If EV certificate is not available, document the bypass in the user-facing runbook during the same phase.

---

### Pitfall 3: Win32_Product WMI Query Triggers MSI Reconfiguration on Every Target Machine

**What goes wrong:**
Using `wmi.WMI().Win32_Product()` to enumerate installed software triggers a Windows Installer consistency check ("reconfiguration") on every installed MSI package during the query. This: (a) takes 30-120 seconds depending on how many MSI packages are installed, (b) can trigger MSI repairs that re-enable services IT deliberately disabled, (c) writes to the Windows event log, leaving an audit footprint on a tool that is supposed to be read-only, and (d) can break partially-installed or intentionally-modified applications. This is documented by Microsoft and is a well-known hazard.

**Why it happens:**
Win32_Product is implemented via the Windows Installer provider, which validates every package as part of enumeration. It is not a passive registry read — it is an active installer operation. Many IT tools use it because it is the most obvious WMI class for "list installed software," and the side effects are not visible until they cause problems.

**How to avoid:**
**Never use Win32_Product.** Use the registry Uninstall keys instead:
- `HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*` (64-bit apps)
- `HKLM\SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*` (32-bit apps on 64-bit Windows)
- `HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\*` (user-scoped installs)

These are passive reads — no side effects. They are what Add/Remove Programs reads. For apps not installed via MSI (XCOPY deploys, ClickOnce, Intune Win32 apps managed outside Windows Installer), supplement with file-path existence checks against known install directories.

**Warning signs:**
- Software enumeration step takes longer than 5 seconds.
- Event log shows MSI 1035 (reconfiguration) events timestamped to when the audit ran.
- IT staff report that a service that was disabled is re-enabled after running the audit tool.

**Phase to address:**
Software detection implementation phase. Lock in the registry-based approach in the data collection module before writing any WMI-based detection code. Add Win32_Product to the explicit "do not use" list in code comments.

---

### Pitfall 4: 32-bit/64-bit Registry Redirection Causes Apps to Appear Undetected

**What goes wrong:**
A 64-bit Python process opens `HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall` and does not find a known 32-bit app (e.g., an older version of Zoom or a 32-bit Office component). The tool reports the app as absent when it is actually installed. The inverse also happens: reading `Wow6432Node` exclusively misses 64-bit native installs.

**Why it happens:**
On 64-bit Windows, registry access from a 64-bit process is automatically redirected so that `HKLM\SOFTWARE\SomeApp` goes to the 64-bit view. 32-bit app installers write to the 32-bit view, which is stored at `HKLM\SOFTWARE\Wow6432Node\SomeApp` and visible from a 64-bit process only if you explicitly use the `KEY_WOW64_32KEY` flag or enumerate `Wow6432Node` directly. PyInstaller produces 64-bit executables by default.

**How to avoid:**
Always enumerate all four Uninstall key locations:
1. `HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall` (64-bit, no flag needed)
2. `HKLM\SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall` (32-bit apps, explicit path)
3. `HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall` (user installs, 64-bit)
4. `HKCU\Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall` (user installs, 32-bit)

Deduplicate by `DisplayName` + `DisplayVersion` after merging all four.

**Warning signs:**
- Zoom, Teams, or older Office add-ins are reported absent on machines where IT staff can clearly see them in Add/Remove Programs.
- Testing on a developer machine (likely a clean 64-bit install) passes, but production machines (with legacy 32-bit software) fail.

**Phase to address:**
Software detection implementation phase. Write the registry enumeration helper to cover all four paths from the start. Add a test fixture that simulates 32-bit-only registry entries.

---

### Pitfall 5: International Machine Names Corrupt or Crash the Hostname Parser

**What goes wrong:**
The tool is deployed to Jordan (Amman office), Netherlands, Malaysia, and Hong Kong. While Master Electronics' naming convention uses ASCII city codes (AMM, AMS, KUL, HKG), the Windows hostname itself may contain non-ASCII characters on some machines (especially in offices where local IT provisioned machines before the naming standard was enforced). Additionally, the logged-in username, profile paths, and display names retrieved from registry or WMI can contain Arabic, Dutch diacritics (ë, ü), Malay characters, or Chinese characters. Python's `socket.gethostname()` on Windows returns bytes decoded with the system locale (e.g., cp1256 for Arabic Windows, cp1252 for Dutch, cp950 for Traditional Chinese Hong Kong). When these bytes are mixed with UTF-8 strings elsewhere in the code, you get `UnicodeDecodeError` crashes or silent data corruption in the JSON log and HTML output.

**Why it happens:**
Windows still defaults to legacy ANSI code pages for system APIs on many configurations. `socket.gethostname()` uses the ANSI API internally. Python 3 on Windows does not set UTF-8 as the default encoding unless `PYTHONUTF8=1` is set or `-X utf8` is passed. A developer on an English Windows machine never encounters this because cp1252 is a subset of latin-1 and most hostnames are ASCII — the bug is invisible in development and appears only in international deployments.

**How to avoid:**
1. **Set `PYTHONUTF8=1` in the PyInstaller runtime environment** or pass `-X utf8` to the Python interpreter at build time. This forces all string I/O to UTF-8 mode.
2. **Use `os.environ.get('COMPUTERNAME', '')` or `socket.gethostname()` wrapped in explicit encoding handling:**
   ```python
   import ctypes
   buf = ctypes.create_unicode_buffer(256)
   ctypes.windll.kernel32.GetComputerNameW(buf, ctypes.byref(ctypes.c_ulong(256)))
   hostname = buf.value  # Always a proper Unicode string
   ```
   `GetComputerNameW` is the Unicode Windows API and always returns a proper `str`, bypassing locale encoding entirely.
3. **Write the HTML output with `encoding='utf-8'` and include `<meta charset="UTF-8">` as the first tag in `<head>`.** Do not rely on the system default encoding for file writes.
4. **Write the JSON log with `ensure_ascii=False` and `encoding='utf-8'`.** This preserves non-ASCII characters rather than escaping them as `\uXXXX`.
5. **Normalize all string values to NFC Unicode** before storing (`unicodedata.normalize('NFC', value)`) to handle composed vs. decomposed forms from different OS locales.
6. **Wrap all registry reads and WMI queries in `try/except (UnicodeDecodeError, OSError)`** — treat encoding failures as "unknown" values rather than crashes.

**Warning signs:**
- Tool works perfectly in Phoenix/Chicago offices but crashes or produces garbled output in HKG or AMM offices.
- JSON log contains ` ` or replacement characters (`�`) in name fields.
- HTML opens blank in the browser on international machines.

**Phase to address:**
Data collection and HTML generation phases. Encoding must be a first-class concern from the first line of code that reads a hostname or username — retrofitting encoding handling is error-prone.

---

### Pitfall 6: Output Written to Wrong Directory (Working Directory vs. Executable Directory)

**What goes wrong:**
The tool writes the HTML and JSON log to `os.getcwd()`, which is the current working directory at launch time — not the directory the executable lives in. When IT staff launches the .exe by double-clicking it from Windows Explorer, the working directory is typically the user's `%USERPROFILE%` or `C:\Windows\System32` (if launched via Run dialog), not the USB drive. The output files land on the target PC's local drive, violating the constraint that the tool must leave no artifacts on the host machine.

**Why it happens:**
`os.getcwd()` is a standard Python idiom for "where am I running." In interactive terminal use, it works because the terminal is usually opened in the relevant directory. When double-clicking an `.exe`, Windows sets the working directory to the executable's own directory — but this behavior is not guaranteed by all launchers, and it breaks entirely when the tool is launched via a scheduled task, mapped drive shortcut, or command line from a different directory.

**How to avoid:**
Always derive the output path from the executable's own location using PyInstaller's runtime information:
```python
import sys, os
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
```
Write all output relative to `BASE_DIR`. Test by launching the `.exe` from a `cmd.exe` in `C:\` — if output appears in `C:\`, the implementation is wrong.

**Warning signs:**
- HTML and JSON files appear in `C:\Users\<name>\` instead of on the USB drive.
- Tool appears to "work" (no errors) but IT staff cannot find the output.
- Output path varies depending on how the tool was launched.

**Phase to address:**
Core architecture / first working prototype phase. Establish `BASE_DIR` as the canonical output root before any file I/O code is written.

---

### Pitfall 7: USB Drive Write Fails Silently or Crashes Without User-Facing Error

**What goes wrong:**
Some USB drives have a physical write-protect switch (or are configured read-only via Windows Group Policy or BitLocker). If the write to the USB drive fails with `PermissionError` or `OSError` and the code does not handle it, the tool crashes with a Python traceback that means nothing to an IT staff member, or silently produces no output. The IT staff member concludes "the tool doesn't work" without knowing the HTML was generated successfully in memory.

**Why it happens:**
Write failures are uncommon in development (writing to a local SSD) and easy to forget to test. USB drives can be locked by Endpoint Protection policies, by the physical switch, or by corruption. The error is not surfaced unless explicitly caught.

**How to avoid:**
1. Wrap all file write operations in `try/except (PermissionError, OSError)` with explicit user-facing error messages.
2. Consider writing the HTML to a temp location first, then moving to the USB — if the move fails, display the HTML from temp and warn the user.
3. Display a clear console/stdout message: "WARNING: Could not write to USB drive at E:\. Check write protection switch. Output saved to: C:\Temp\status_report_HOSTNAME.html"
4. Never silently suppress write errors.

**Warning signs:**
- Tool exits without producing any files.
- Unhandled exception traceback referencing `PermissionError` at the file write step.

**Phase to address:**
File I/O implementation phase. Write a test that attempts to write to a read-only directory and verify the error message is user-readable.

---

### Pitfall 8: Software Detected as "Present" After Uninstall Due to Stale Registry Keys

**What goes wrong:**
An application is uninstalled but its Uninstall registry key is not cleaned up (common with sloppy uninstallers, partial uninstalls via Intune, or forced removal). The tool reads the registry and reports the app as installed with a version number. This is a false positive — IT staff may trust the audit and skip reinstalling a broken agent.

**Why it happens:**
Windows has no mechanism to guarantee registry cleanup on uninstall. Uninstall keys are written by the installer and deleted by the uninstaller — if the uninstaller is broken, skipped, or the files were manually deleted, the keys remain. This is a documented limitation of registry-based software detection.

**How to avoid:**
1. For the apps that matter most (NinjaOne, CrowdStrike, M365, Intune), add a secondary confirmation check: verify that the expected executable or service actually exists at the path listed in the `InstallLocation` registry value.
2. Use a tiered confidence model: "Detected (registry + file confirmed)" vs. "Detected (registry only — verify manually)".
3. For NinjaOne specifically, check for the service `ninjarmmagent` running via `win32serviceutil` or `subprocess sc query`, not just the registry key.
4. For CrowdStrike, check for the `CsFalconService` Windows service state.

**Warning signs:**
- Known-uninstalled apps continue to appear in the report on the same test machine across multiple runs.
- `InstallLocation` path in the registry points to a directory that no longer exists.

**Phase to address:**
Software detection implementation phase. Define the detection strategy for each app (registry + file/service confirmation) before coding. Document which apps use tiered vs. registry-only detection.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| `--onefile` PyInstaller mode | Single file is easier to hand off on USB | EDR quarantine in production; slower startup; antivirus friction on every rebuild | Never for this project — use `--onedir` |
| `Win32_Product` for software enumeration | Single WMI query returns everything | MSI reconfiguration side effects; 30-120s runtime; event log artifacts; may break managed apps | Never |
| `os.getcwd()` for output path | Works in development | Output lands on host PC not USB in production | Never — use `sys.executable` path |
| Hardcoded app install paths (e.g., `C:\Program Files\...`) | Fast to implement | Breaks for non-default installs, per-user installs, 32-bit vs. 64-bit | Only as a fallback after registry check fails |
| Ignoring registry 32-bit view | Simpler code | 32-bit apps invisible to the tool | Never — enumerate all four Uninstall key paths |
| `open(file, 'w')` without explicit encoding | Works on English Windows | Crashes or corrupts data on Arabic/Chinese/Dutch locales | Never — always specify `encoding='utf-8'` |
| Single-source software detection (registry only) | Faster to build | False positives from stale keys | Acceptable for v1 if tier is labeled "registry only — unconfirmed" |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Windows Registry | Opening only `HKLM\SOFTWARE\...\Uninstall` on a 64-bit Python process | Enumerate all four paths (HKLM 64-bit, HKLM WOW6432Node, HKCU 64-bit, HKCU WOW6432Node) |
| WMI (system info) | Using `Win32_Product` for software | Use WMI only for hardware info (`Win32_ComputerSystem`, `Win32_Processor`, `Win32_DiskDrive`) where it is passive |
| PyInstaller runtime | Using `__file__` to find the exe directory | Use `sys.executable` in frozen mode; `__file__` points to the extracted temp dir |
| HTML output | Writing with system default encoding | Always `open(path, 'w', encoding='utf-8')` + `<meta charset="UTF-8">` as first head element |
| JSON log | `json.dump()` with default settings | Use `ensure_ascii=False, indent=2` and `encoding='utf-8'` on the file open |
| `socket.gethostname()` | Trusting the return value as clean Unicode | Use `GetComputerNameW` via ctypes for guaranteed Unicode; wrap in encoding error handler |
| Windows services check | No fallback when `win32serviceutil` not available | Use `subprocess.run(['sc', 'query', service_name], ...)` as the standard-user-safe fallback |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| `Win32_Product` WMI query | 30-120s hang during software scan | Never use it; use registry reads instead | Every run, every machine |
| `--onefile` PyInstaller with Windows Defender active | 3-8s cold start due to AV scanning %TEMP% extraction | Use `--onedir`; or set `--runtime-tmpdir` to a non-scanned path | Every launch on Defender-managed machine |
| Enumerating all WMI classes at startup | Tool hangs for 10+ seconds before showing anything | Query only specific known-fast classes (`Win32_ComputerSystem`, `Win32_OperatingSystem`) | Machines with many WMI providers |
| Synchronous HTML open via `webbrowser.open()` | Opens wrong application (e.g., text editor) on machines where .html default is not a browser | Use `os.startfile(path)` on Windows; it uses the registered file association | Machines with non-standard .html associations |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Hardcoding internal app names or registry paths in plaintext | Enumerable attack surface in a dropped binary | Acceptable for this internal tool — the risk is theoretical given the audience |
| Writing audit data to host machine %TEMP% as a fallback | Leaves PII (usernames, software inventory) on the target PC | If USB write fails, warn user; offer to open HTML from memory without writing; never silently write to local disk |
| Running with elevated privileges unnecessarily | Elevating to admin when standard user suffices increases blast radius | Design for standard user first; document which checks need elevation; never auto-elevate without explicit user confirmation |
| Trusting hostname-derived data without sanitization in HTML output | XSS in the generated HTML if hostname contains `<script>` characters | Escape all data inserted into HTML using `html.escape()` from Python stdlib — this is a real edge case for machines with non-standard names |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Tool crashes with Python traceback | IT staff sees cryptic error, cannot diagnose | Wrap all top-level logic in `try/except Exception as e`; show a plain-English error with actionable instructions |
| No visual feedback during data collection | IT staff double-clicks .exe, sees nothing for 3-5 seconds, assumes it failed and clicks again | Print a status line to stdout for each collection step; even a console window with progress is better than silence |
| HTML output not automatically opened | IT staff has to find the output file on the USB drive | After successful write, call `os.startfile(html_path)` to open in default browser automatically |
| Report silently omits apps it couldn't check | IT staff trusts a "not installed" result that actually means "could not check" | Use three states: Installed / Not Found / Unknown (check failed — reason) |
| Drive letter in output path changes between offices | IT staff documentation says "open E:\report.html" but their USB is F: | Output file is always in the same directory as the .exe; use a relative path in any user-facing instructions |

---

## "Looks Done But Isn't" Checklist

- [ ] **Software detection:** Only `HKLM` 64-bit registry checked — verify `Wow6432Node` and `HKCU` paths are also enumerated
- [ ] **Output path:** `os.getcwd()` used instead of `sys.executable` directory — verify by launching from `cmd.exe` in `C:\`
- [ ] **International hostnames:** Tested only on English-locale developer machine — verify on a machine with a non-ASCII username or machine name
- [ ] **Write failure handling:** No `try/except` around file writes — verify behavior when target directory is read-only
- [ ] **Win32_Product absent:** Verify no WMI software queries remain; search codebase for `Win32_Product` before shipping
- [ ] **HTML encoding:** Missing `<meta charset="UTF-8">` — verify HTML displays correctly in Chrome when hostname contains non-ASCII
- [ ] **CrowdStrike test:** Binary tested on developer machine only — verify on a CrowdStrike-enrolled machine before handing to IT staff
- [ ] **Hostname parser with Unknown devices:** `None` or empty string from hostname passed to name parser without guard — verify "Unknown Adventurer" fallback triggers correctly for all invalid inputs
- [ ] **JSON log completeness:** JSON written before HTML generation, or only on success — verify JSON is written even if HTML generation fails

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| CrowdStrike blocks the binary | HIGH | Switch to `--onedir`, rebuild, retest on enrolled machine; if `--onefile` must be kept, submit hash to CrowdStrike console and wait for allowlist propagation (hours to days) |
| SmartScreen blocks unsigned binary | LOW | Document "More info → Run anyway" bypass in IT staff runbook; long-term: acquire EV code-signing certificate |
| Win32_Product used (discovered in code review) | LOW | Delete the WMI software query; replace with registry enumeration; retest — no architectural rework needed |
| Output written to host PC (not USB) | LOW | Replace `os.getcwd()` with `sys.executable`-derived path; rebuild; one-line fix |
| Encoding crash on international machine | MEDIUM | Add `PYTHONUTF8=1` to PyInstaller build, replace `socket.gethostname()` with `GetComputerNameW` ctypes call, add `encoding='utf-8'` to all file opens, rebuild and test |
| 32-bit apps invisible to tool | LOW | Add `Wow6432Node` and `HKCU` paths to registry enumeration; retest with a known 32-bit app; rebuild |
| Stale registry keys causing false positives | MEDIUM | Add file/service existence check as secondary confirmation for the 5 highest-priority apps; label all others as "registry only — unconfirmed" |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| CrowdStrike quarantine | Packaging configuration (first packaging build) | Run on a CrowdStrike-enrolled machine before any distribution |
| SmartScreen blocking | Packaging configuration + runbook writing | Test cold launch on a machine that has never seen the binary |
| Win32_Product side effects | Software detection implementation | Code review: grep for `Win32_Product` must return zero results |
| 32-bit registry redirection | Software detection implementation | Test with a known 32-bit app (e.g., older 32-bit Zoom) on a 64-bit Windows machine |
| International encoding crashes | Data collection implementation (day one) | Run tool on a VM with locale set to Arabic (Jordan) or Traditional Chinese (Hong Kong) |
| Wrong output directory | Core architecture / prototype | Launch .exe from `C:\` via cmd.exe; output must appear on the USB, not in `C:\` |
| USB write failure | File I/O implementation | Write to a read-only directory; verify user-facing error message appears |
| Stale registry false positives | Software detection implementation | Uninstall a test app without registry cleanup; verify tool flags it as "unconfirmed" |
| HTML encoding/display | HTML generation phase | Open generated HTML in Chrome on a machine with Arabic locale; verify no garbled characters |
| XSS in HTML from unescaped data | HTML generation phase | Set hostname to `<script>alert(1)</script>` in test; verify it appears escaped in HTML output |

---

## Sources

- PyInstaller antivirus false positive documentation: https://www.pythonguis.com/faq/problems-with-antivirus-software-and-pyinstaller/
- PyInstaller runtime information (sys.executable, sys._MEIPASS): https://pyinstaller.org/en/stable/runtime-information.html
- Win32_Product is evil — detailed post-mortem: https://gregramsey.net/2012/02/20/win32_product-is-evil/
- Microsoft TechCommunity — do not use Win32_Product in GPO: https://techcommunity.microsoft.com/blog/askds/how-to-not-use-win32-product-in-group-policy-filtering/399983
- Windows registry Uninstall key documentation: https://learn.microsoft.com/en-us/windows/win32/msi/uninstall-registry-key
- Registry WOW6432Node and 32-bit/64-bit redirection: https://www.advancedinstaller.com/user-guide/registry-wow6432node.html
- Python winreg KEY_WOW64_32KEY usage: https://runebook.dev/en/docs/python/library/winreg/winreg.KEY_WOW64_32KEY
- Python UTF-8 mode on Windows (PYTHONUTF8): https://dev.to/methane/python-use-utf-8-mode-on-windows-212i
- socket.gethostname() non-ASCII encoding issue: https://github.com/mitogen-hq/mitogen/issues/687
- CrowdStrike blocking PyInstaller executables: https://uah.teamdynamix.com/TDClient/2075/Portal/KB/ArticleDet?ID=137260
- Python PermissionError handling: https://realpython.com/ref/builtin-exceptions/permissionerror/
- Windows HTML file open via os.startfile: https://bobbyhadz.com/blog/open-html-file-in-the-browser-using-python

---
*Pitfalls research for: Windows IT audit USB-portable executable (StatusReport)*
*Researched: 2026-05-04*
