"""Read genuine FIT, GPX and TCX records and select unmodified preview points."""
from pathlib import Path
import base64
import json
import subprocess
import xml.etree.ElementTree as ET
from activity_model import number
from settings import as_json, NATIVE_READER

HERE = Path(__file__).parent

def xml_points(raw, kind):
    root = ET.fromstring(raw.lstrip())
    points = []
    containers = [node for node in root.iter() if node.tag.rsplit('}', 1)[-1] == ('trkseg' if kind == 'gpx' else 'Track')]
    segment = 0
    for container in containers:
        segment += 1
        for item in container.iter():
            tag = item.tag.rsplit('}', 1)[-1]
            if kind == 'gpx' and tag == 'trkpt':
                fields = {child.tag.rsplit('}', 1)[-1]: child.text for child in item}
                lat, lon = number(item.get('lat')), number(item.get('lon'))
                stamp, altitude = fields.get('time'), number(fields.get('ele'))
            elif kind == 'tcx' and tag == 'Trackpoint':
                fields = {child.tag.rsplit('}', 1)[-1]: child.text for child in item.iter()}
                lat, lon = number(fields.get('LatitudeDegrees')), number(fields.get('LongitudeDegrees'))
                stamp, altitude = fields.get('Time'), number(fields.get('AltitudeMeters'))
            else:
                continue
            if lat is not None and lon is not None and abs(lat) <= 90 and abs(lon) <= 180:
                points.append([lat, lon, stamp, altitude, segment])
            else:
                segment += 1
    return points

def fit_points(raw, file_path=None):
    process = subprocess.run(['node', str(HERE / 'read_fit.cjs')], input=as_json({'bytes': base64.b64encode(raw).decode()}),
                             text=True, capture_output=True, timeout=35, check=True)
    if not process.stdout.strip():
        native = NATIVE_READER
        if file_path is None or not native.is_file():
            raise ValueError('The older FIT parser returned no result. Run npm run build:fit to enable the FIT Preview fallback.')
        process = subprocess.run([str(native), str(file_path)], text=True, capture_output=True, timeout=35, check=True)
    result = json.loads(process.stdout)
    if result.get('error'):
        raise ValueError(result['error'])
    return result['points'], result.get('source', 'fit-file-parser')

def sample_points(points):
    indices = {round(i * (len(points)-1) / min(799, len(points)-1)) for i in range(min(800, len(points)))}
    indices.update([0, len(points)-1])
    for axis in [0, 1]:
        indices.add(min(range(len(points)), key=lambda i: points[i][axis]))
        indices.add(max(range(len(points)), key=lambda i: points[i][axis]))
    for position in range(1, len(points)):
        if points[position][4] != points[position-1][4]:
            indices.update([position-1, position])
    selected = sorted(indices)
    return selected, [points[i] for i in selected]
