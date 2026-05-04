import pytest
from parsers.name_parser import parse_hostname


@pytest.mark.parametrize('hostname,expected', [
    # ROADMAP SC1
    ('PHX-INV-003',     {'city': 'Phoenix', 'device_type': 'Warehouse Workstation', 'department': 'INV', 'station': 3}),
    # ROADMAP SC2
    ('PHX-ABC123-ME',   {'device_type': 'User-Assigned Laptop', 'company_code': 'ME'}),
    # ROADMAP SC3 / OUT-03
    ('DESKTOP-XYZ123',  {'device_type': 'Unknown', 'raw_hostname': 'DESKTOP-XYZ123', 'city': None}),
    # P3 Warehouse Device
    ('CHI-P3B-002',     {'device_type': 'P3 Warehouse Device', 'city': 'Chicago', 'station': 2}),
    ('PHX-P3A-001',     {'device_type': 'P3 Warehouse Device'}),  # Pitfall 1 guard
    ('VAN-P3C-010',     {'device_type': 'P3 Warehouse Device', 'city': 'Vancouver'}),
    # Department Laptop
    ('NYC-INVLAP-004',  {'device_type': 'Department Laptop', 'department': 'INVLAP', 'city': 'New York'}),
    ('MIA-SHPLAP-002',  {'device_type': 'Department Laptop', 'department': 'SHPLAP'}),
    # D-02: unrecognized dept code -> Warehouse Workstation
    ('PHX-NEWDEPT-005', {'device_type': 'Warehouse Workstation', 'department': 'NEWDEPT'}),
    # D-03: unrecognized company code -> User-Assigned Laptop
    ('PHX-ABC123-XX',   {'device_type': 'User-Assigned Laptop', 'company_code': 'XX'}),
    # D-04: unrecognized city prefix
    ('ZZZ-INV-003',     {'device_type': 'Unknown', 'city': None}),
    # D-08: fully unrecognized
    ('DESKTOP-XYZ123',  {'device_type': 'Unknown', 'city': None}),
    # D-09: recognized city but too few segments
    ('PHX-BADSTRUCT',   {'city': 'Phoenix', 'device_type': 'Unknown'}),
    # City code representative sample (D-07)
    ('AMM-SHP-001',     {'city': 'Amman',        'device_type': 'Warehouse Workstation'}),
    ('AMS-REC-003',     {'city': 'Amsterdam',    'device_type': 'Warehouse Workstation'}),
    ('VAN-REC-007',     {'city': 'Vancouver',    'device_type': 'Warehouse Workstation'}),
    ('TSU-P3A-003',     {'city': 'Tsuchiura',    'device_type': 'P3 Warehouse Device'}),
    ('SEA-INV-012',     {'city': 'Seattle',      'device_type': 'Warehouse Workstation'}),
    ('GUA-ABC-ME',      {'city': 'Guadalajara',  'device_type': 'User-Assigned Laptop'}),
    ('TOR-ABC-ES',      {'city': 'Toronto',      'device_type': 'User-Assigned Laptop'}),
    ('SCL-RECLAP-001',  {'city': 'Santiago',     'device_type': 'Department Laptop'}),
])
def test_parse_hostname(hostname, expected):
    result = parse_hostname(hostname)
    for field_name, value in expected.items():
        assert getattr(result, field_name) == value, (
            f'{hostname}: expected {field_name}={value!r}, got {getattr(result, field_name)!r}'
        )


def test_raw_hostname_always_preserved():
    """D-05: raw_hostname field preserved regardless of parse outcome."""
    for hostname in ['PHX-INV-003', 'DESKTOP-XYZ123', 'PHX-BADSTRUCT', 'ZZZ-X-X', 'phx-inv-003']:
        result = parse_hostname(hostname)
        assert result.raw_hostname == hostname, f'raw_hostname not preserved for {hostname!r}'


def test_no_exception_on_any_input():
    """OUT-03: parser never raises on any string input."""
    bad_inputs = ['', '-', '--', 'PHX', 'phx-inv-003', '123-INV-003', 'PHX-INV',
                  'A' * 300, ';;;', '\x00\x01\x02']
    for bad in bad_inputs:
        result = parse_hostname(bad)
        assert result.device_type is not None, f'device_type is None for {bad!r}'


def test_station_is_int_not_string():
    """ROADMAP SC1, Pitfall 2: station must be int, not '003'."""
    result = parse_hostname('PHX-INV-003')
    assert result.station == 3
    assert isinstance(result.station, int), f'station type={type(result.station)}'


def test_lowercase_hostname_handled():
    """Pitfall 3: lowercase input produces same device_type as uppercase."""
    lower = parse_hostname('phx-inv-003')
    upper = parse_hostname('PHX-INV-003')
    assert lower.device_type == upper.device_type
    assert lower.city == upper.city
    assert lower.department == upper.department
    assert lower.station == upper.station
    assert lower.raw_hostname == 'phx-inv-003'


def test_p3_not_misclassified_as_workstation():
    """Pitfall 1: PHX-P3A-001 must be P3 Warehouse Device, not Warehouse Workstation."""
    result = parse_hostname('PHX-P3A-001')
    assert result.device_type == 'P3 Warehouse Device', (
        f'Disambiguation order bug: P3A classified as {result.device_type!r}'
    )
