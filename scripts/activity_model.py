"""Preserve source fields and normalize activity values with explicit units."""
from collections import Counter
from datetime import datetime, timezone
import math
from settings import LOCAL_TIMEZONE

def number(value):
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None

def source_columns(headers, row):
    seen = Counter()
    output = {}
    for header, value in zip(headers, row):
        seen[header] += 1
        key = header if seen[header] == 1 else f'{header} [{seen[header]}]'
        output[key] = value
    return output

def create_activity(headers, row):
    source = source_columns(headers, row)
    utc = datetime.strptime(row[1], '%b %d, %Y, %I:%M:%S %p').replace(tzinfo=timezone.utc)
    local = utc.astimezone(LOCAL_TIMEZONE)
    distance = number(row[17])
    distance_basis = 'recorded metres'
    if distance is None:
        first_distance = number(row[6])
        distance = first_distance * 1000 if first_distance is not None else None
        distance_basis = 'first Distance column (kilometres)'
    moving = number(row[16])
    elapsed = number(row[15]) if number(row[15]) is not None else number(row[5])
    speed = number(row[19])
    speed_derived = speed is None and distance is not None and moving is not None and moving > 0
    if speed_derived:
        speed = distance / moving
    filename = row[12].strip()
    item = {
        'id': row[0], 'name': row[2], 'type': row[3], 'description': row[4], 'note': row[10],
        'utc': utc.isoformat(), 'localDate': local.strftime('%Y-%m-%d'),
        'localTime': local.strftime('%H:%M'), 'localZone': local.tzname(), 'year': local.year,
        'gear': row[11], 'distance': distance, 'distanceBasis': distance_basis,
        'elapsed': elapsed, 'moving': moving, 'speed': speed, 'speedDerived': speed_derived,
        'maxSpeed': number(row[18]), 'elevation': number(row[20]),
        'heartRate': number(row[31]), 'maxHeartRate': number(row[30]) if number(row[30]) is not None else number(row[7]),
        'cadence': number(row[29]), 'power': number(row[33]), 'calories': number(row[34]),
        'temperature': number(row[36]), 'commute': row[9].lower() == 'true',
        'format': None, 'originalFile': filename or None, 'file': None,
        'preview': None, 'pointCount': 0, 'previewPointCount': 0, 'previewError': None,
        'source': source,
    }
    return item
