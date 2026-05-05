---
phase: 03
slug: html-character-sheet-renderer
status: verified
threats_open: 0
asvs_level: 1
created: 2026-05-05
---

# Phase 03 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| renderer → writers | HTML string produced by Jinja2 (already escaped) crosses into file I/O | HTML string (autoescape applied) |
| writers → filesystem | `output_path` is caller-supplied; could point outside flash drive if caller misbehaves | HTML file write |
| AuditReport fields → Jinja2 template | Untrusted strings (hostname, cpu_model, os_version, app names) cross from Python into HTML rendering | Device data strings |
| Template file → renderer | Template loaded from package resources via importlib.resources | Static Jinja2 template source |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-03-01-01 | Tampering | `write_html` — output_path parameter | accept | Path is caller-controlled by design (D-16/D-17). Flash drive path validation is Phase 5 / main.py concern. | closed |
| T-03-01-02 | Information Disclosure | `requirements.txt` — dependency version exposure | accept | No secrets in requirements.txt. Jinja2 3.1.6 has no known CVEs at audit date. Internal IT tool. | closed |
| T-03-01-03 | Denial of Service | `write_html` — disk full on flash drive | accept | `OSError` propagates to main.py. IT staff see traceback. No data loss (read-only audit). | closed |
| T-03-02-01 | Injection (XSS) | `render_report` — AuditReport string fields rendered into HTML | mitigate | `Environment(autoescape=True)` at `renderer/__init__.py:47` — escapes `<`, `>`, `&`, `"`, `'` in all template variables automatically. Verified in code. | closed |
| T-03-02-02 | Injection (Template) | `env.from_string(template_source)` — template loaded from package resource | accept | Template is a static file shipped with the tool. Attacker needs write access to the bundle directory — equivalent to compromising the executable. | closed |
| T-03-02-03 | Spoofing | `disk_pct` — inline style `width: {{ disk_pct }}%` | accept | `disk_pct` is a Python float computed from `float / float` in `_build_context`. Not user-supplied. Autoescape also prevents injection in style values. | closed |
| T-03-02-04 | Information Disclosure | `tests/test_renderer.py` — MOCK_REPORT data | accept | MOCK_REPORT uses fictional hostname `PHX-INV-003` and synthetic versions. No real machine data. Test file is dev-only, not bundled into the .exe. | closed |
| T-03-02-05 | Denial of Service | `_load_template_source()` — template file missing at runtime | accept | Missing template raises `FileNotFoundError`, propagates to caller. No data loss, no security impact. Phase 5 packaging must include the templates/ directory. | closed |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-03-01 | T-03-01-01 | output_path caller-controlled by design; validation deferred to Phase 5 main.py per D-16/D-17 | gsd-security-auditor | 2026-05-05 |
| AR-03-02 | T-03-01-02 | requirements.txt version exposure is acceptable for an internal IT tool with no secrets in deps | gsd-security-auditor | 2026-05-05 |
| AR-03-03 | T-03-01-03 | disk-full OSError is acceptable failure mode; IT staff will see traceback; no data loss | gsd-security-auditor | 2026-05-05 |
| AR-03-04 | T-03-02-02 | template tampering requires bundle write access ≡ executable compromise; accepted for internal tool | gsd-security-auditor | 2026-05-05 |
| AR-03-05 | T-03-02-03 | disk_pct is Python-computed float; not user-supplied; no injection vector | gsd-security-auditor | 2026-05-05 |
| AR-03-06 | T-03-02-04 | MOCK_REPORT contains only fictional data; dev-only file excluded from .exe bundle | gsd-security-auditor | 2026-05-05 |
| AR-03-07 | T-03-02-05 | template missing raises FileNotFoundError; packaging concern, not security concern; tracked in Phase 5 | gsd-security-auditor | 2026-05-05 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-05-05 | 8 | 8 | 0 | gsd-secure-phase (inline) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-05-05
