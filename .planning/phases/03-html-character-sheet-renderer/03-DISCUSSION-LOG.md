# Phase 3: HTML Character Sheet Renderer - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-04
**Phase:** 03-html-character-sheet-renderer
**Areas discussed:** RPG field mappings, Visual style, Equipment slot detail, None field display

---

## RPG Field Mappings

### Character Class
| Option | Description | Selected |
|--------|-------------|----------|
| Device type → class (with fantasy names) | Warehouse Workstation → 'Sentinel', etc. | |
| Device type verbatim (no renaming) | Class = device_type as-is | ✓ |
| You decide the class names | Claude picks thematic names | |

**User's choice:** "Just keep it as Device Type, no fantasy flavoring here."
**Notes:** All header fields (class, realm, guild, station) use real IT terminology — no D&D renaming.

### Realm and Guild
| Option | Description | Selected |
|--------|-------------|----------|
| Realm = city, Guild = department | For laptops: guild = company code; None → — | ✓ |
| Realm = city, Guild = omit if no dept | Hidden for laptops and unknowns | |
| You decide | Claude picks mappings | |

**User's choice:** "Map as City and Department, again no fantasy re-theming"
**Notes:** Consistent with no-renaming preference across all header fields.

### Level
| Option | Description | Selected |
|--------|-------------|----------|
| Station number | Level = station int | ✓ |
| Omit level entirely | Not all devices have station | |
| You decide | Claude picks mapping | |

**User's choice:** "List as Station Number"

### Stat Labels
| Option | Description | Selected |
|--------|-------------|----------|
| Keep D&D stat names (STR/CON) | Stat name with real value as subtext | |
| Plain hardware labels only | CPU, RAM, Disk — no RPG terminology | ✓ |
| Both — stat name + hardware label | STR (CPU), CON (RAM) | |

**User's choice:** "Plain hardware labels only"
**Notes:** Solidifies the overall direction: IT-functional layout, not thematic renaming.

### Stat Values
| Option | Description | Selected |
|--------|-------------|----------|
| Raw hardware values | CPU model string, RAM in GB | ✓ |
| Scaled D&D score (1–20) | Converts hardware to D&D numbers | |
| You decide the formula | Claude picks scaling | |

**User's choice:** "Raw hardware values (Recommended)"

### HP Bar (Disk)
| Option | Description | Selected |
|--------|-------------|----------|
| Free space as % of total | Full bar = empty disk | ✓ |
| Used space as % of total | Full bar = full disk | |
| You decide the formula | Claude picks | |

**User's choice:** "Free space as % of total (Recommended)"

---

## Visual Style

| Option | Description | Selected |
|--------|-------------|----------|
| Dark panel, colored accents | Deep navy/charcoal, CRPG game UI | ✓ |
| Parchment / paper texture | Cream/tan, printed D&D sheet look | |
| Clean white, minimal | White background, modern web report | |

**User's choice:** "Dark panel, colored accents"
**Notes:** Selected via visual preview of ASCII mockup.

---

## Equipment Slot Detail

### Per-slot information
| Option | Description | Selected |
|--------|-------------|----------|
| Name + badge + version | Name, ✓/✗ badge, version when installed | ✓ |
| Name + badge only | No version numbers | |
| Name + badge + version + service state | Most complete | |

**User's choice:** "Name + badge + version (Recommended)"
**Notes:** Service state (Running/Stopped) was added via Claude's Discretion for apps that have it (CrowdStrike Falcon).

### Mock data app list
| Option | Description | Selected |
|--------|-------------|----------|
| All 7 required apps, mixed state | Some installed, some missing | ✓ |
| All 7 installed | Only Quest Complete path | |
| Minimal 3-4 apps for layout | Faster setup, less representative | |

**User's choice:** "All 7 required apps, mixed state (Recommended)"

---

## None Field Display

| Option | Description | Selected |
|--------|-------------|----------|
| '—' dash, greyed out | Em-dash in muted grey | ✓ |
| 'Unavailable' text | Explicit text, muted grey | |
| Omit the row entirely | Clean but hides attempted fields | |

**User's choice:** "'—' dash, greyed out (Recommended)"

---

## Claude's Discretion

- CSS approach (inline vs `<style>` block vs external) — Claude picks safest option for PyInstaller
- Exact color palette values within the dark/colored-accents direction
- Jinja2 filter/macro design for HP bar, badges, None substitution
- Whether OS version and build render as separate rows or combined
- Whether `local_profiles` appears in Phase 3 character sheet

## Deferred Ideas

None.
