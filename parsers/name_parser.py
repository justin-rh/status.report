"""Hostname parser — decodes Master Electronics naming convention to ParsedHostname.

Decision rules D-01 through D-09 from 01-CONTEXT.md govern all disambiguation.
Anti-pattern: never check seg3.isdigit() before checking seg2 in P3_CODES (Pitfall 1).
"""
from models import ParsedHostname

# 21 confirmed city codes as of 2026-05-04.
# KUL (Kuala Lumpur) and HKG (Hong Kong) are flagged in STATE.md as unconfirmed
# for this convention — confirm with IT/Edgar before adding.
CITY_CODES: dict[str, str] = {
    'AMM': 'Amman',
    'AMS': 'Amsterdam',
    'CHI': 'Chicago',
    'EDE': 'Eden Prairie',
    'GEO': 'Georgetown',
    'GER': 'Germany',
    'GUA': 'Guadalajara',
    'MIA': 'Miami',
    'MON': 'Montreal',
    'NYC': 'New York',
    'PEO': 'Peoria',
    'PEN': 'Pensacola',
    'PHX': 'Phoenix',
    'ROC': 'Rockford',
    'SCL': 'Santiago',
    'SEA': 'Seattle',
    'SMO': 'Santa Monica',
    'TAM': 'Tampa',
    'TOR': 'Toronto',
    'TSU': 'Tsuchiura',
    'VAN': 'Vancouver',
}

P3_CODES: frozenset[str] = frozenset({'P3A', 'P3B', 'P3C'})


def parse_hostname(hostname: str) -> ParsedHostname:
    """Pure function: hostname string -> ParsedHostname. Never raises.

    Decision rules D-01 through D-09 from CONTEXT.md apply.
    Anti-pattern: do NOT check seg3.isdigit() before seg2 in P3_CODES.
    """
    parts = hostname.upper().split('-')

    # D-04: unrecognized city prefix -> Unknown, silent, no further parsing
    if parts[0] not in CITY_CODES:
        return ParsedHostname(raw_hostname=hostname, device_type='Unknown')

    city = CITY_CODES[parts[0]]

    # D-09: recognized city but not enough segments for type determination
    if len(parts) < 3:
        return ParsedHostname(raw_hostname=hostname, city=city, device_type='Unknown')

    seg2, seg3 = parts[1], parts[2]

    # P3 Warehouse Device — MUST be checked BEFORE seg3.isdigit() (Pitfall 1)
    if seg2 in P3_CODES:
        return ParsedHostname(
            raw_hostname=hostname, city=city,
            device_type='P3 Warehouse Device',
            station=_parse_station(seg3),
        )

    # Department Laptop — LAP suffix in seg2 (D-01); suffix-only per CITY-DEPTLAP-### convention
    if seg2.endswith('LAP'):
        return ParsedHostname(
            raw_hostname=hostname, city=city,
            device_type='Department Laptop',
            department=seg2,
            station=_parse_station(seg3),
        )

    # Warehouse Workstation — seg3 is all digits (D-01, D-02, D-06)
    # D-06: no whitelist on dept code — any seg2 qualifies
    if seg3.isdigit():
        return ParsedHostname(
            raw_hostname=hostname, city=city,
            device_type='Warehouse Workstation',
            department=seg2,
            station=int(seg3),
        )

    # User-Assigned Laptop — seg3 is alphabetic uppercase (D-01, D-03)
    # D-03: unrecognized company code still yields User-Assigned Laptop
    if seg3.isalpha() and seg3.isupper():
        return ParsedHostname(
            raw_hostname=hostname, city=city,
            device_type='User-Assigned Laptop',
            company_code=seg3,
        )

    # Ambiguous structure with recognized city (D-09 extension)
    return ParsedHostname(raw_hostname=hostname, city=city, device_type='Unknown')


def _parse_station(seg: str) -> int | None:
    """Convert segment to int station number; return None if not numeric."""
    try:
        return int(seg)
    except (ValueError, TypeError):
        return None
