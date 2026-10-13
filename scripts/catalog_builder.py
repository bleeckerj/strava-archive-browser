"""Rebuild the private catalog while preserving the original archive."""
from pathlib import Path, PurePosixPath
from datetime import datetime, timezone
from collections import Counter
import csv
import gzip
import hashlib
import io
import json
import shutil
import tempfile
import time
import uuid
import zipfile
from activity_model import create_activity
from track_readers import xml_points, fit_points, sample_points
from settings import PROJECT, SOURCE, DESTINATION, LOCAL_TIMEZONE, as_json

def build(output):
    (output / 'activities').mkdir()
    (output / 'tracks').mkdir()
    digest = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    print(f'Building catalog in {output}', flush=True)
    activities, files, preview_errors = [], [], []
    last_report = time.monotonic()
    with zipfile.ZipFile(SOURCE) as archive:
        csv_bytes = archive.read('activities.csv')
        (output / 'source-activities.csv').write_bytes(csv_bytes)
        reader = csv.reader(io.StringIO(csv_bytes.decode('utf-8-sig')))
        headers, rows = next(reader), list(reader)
        assert len(rows) == len({row[0] for row in rows}), 'Duplicate activity IDs in the source.'
        archive_names = set(archive.namelist())
        for index, row in enumerate(rows, 1):
            assert len(row) == len(headers), 'A CSV record has an unexpected number of fields.'
            item = create_activity(headers, row)
            filename = item['originalFile']
            if filename:
                path = PurePosixPath(filename)
                assert not path.is_absolute() and '..' not in path.parts and path.parts[0] == 'activities'
                assert filename in archive_names, 'An activity file referenced by the CSV is missing.'
                raw_original = archive.read(filename)
                original_path = output.joinpath(*path.parts)
                original_path.parent.mkdir(parents=True, exist_ok=True)
                original_path.write_bytes(raw_original)
                raw = gzip.decompress(raw_original) if filename.endswith('.gz') else raw_original
                readable_filename = filename.removesuffix('.gz')
                readable_path = output / readable_filename
                if filename.endswith('.gz'):
                    readable_path.write_bytes(raw)
                kind = PurePosixPath(readable_filename).suffix[1:].lower()
                item['file'], item['format'] = readable_filename, kind.upper()
                item['sourceSha256'] = hashlib.sha256(raw_original).hexdigest()
                item['fileSha256'] = hashlib.sha256(raw).hexdigest()
                files.append({'activityId': row[0], 'archivePath': filename, 'sourceSha256': item['sourceSha256'],
                              'readablePath': readable_filename, 'readableSha256': item['fileSha256'], 'bytes': len(raw)})
                try:
                    if kind == 'fit':
                        points, item['previewDecoder'] = fit_points(raw, readable_path)
                    else:
                        points, item['previewDecoder'] = xml_points(raw, kind), 'recorded XML trackpoints'
                    item['pointCount'] = len(points)
                    if len(points) >= 2:
                        indices, sampled = sample_points(points)
                        item['previewPointCount'] = len(sampled)
                        item['preview'] = f'tracks/{row[0]}.js'
                        payload = {'id': row[0], 'sourcePoints': len(points), 'sourceIndices': indices, 'points': sampled}
                        (output / item['preview']).write_text('window.STRAVA_TRACKS[' + as_json(row[0]) + ']=' + as_json(payload) + ';\n', encoding='utf-8')
                except Exception as error:
                    item['previewError'] = type(error).__name__ + ': ' + str(error)[:220]
                    preview_errors.append({'activityId': row[0], 'file': filename, 'error': item['previewError']})
            activities.append(item)
            if time.monotonic() - last_report >= 2 or index == len(rows):
                print(f'Indexed {index:,}/{len(rows):,} activities; route previews: {sum(bool(a["preview"]) for a in activities):,}', flush=True)
                last_report = time.monotonic()
    activities.sort(key=lambda a: a['utc'], reverse=True)
    meta = {'sourceArchive': SOURCE.name, 'sourceSha256': digest, 'builtAt': datetime.now(timezone.utc).isoformat(),
            'timezone': str(LOCAL_TIMEZONE), 'records': len(activities), 'files': len(files),
            'formats': dict(Counter(a['format'] for a in activities if a['format'])),
            'previews': sum(bool(a['preview']) for a in activities), 'previewErrors': preview_errors,
            'noFileIds': [a['id'] for a in activities if not a['file']],
            'units': {'distance': 'metres', 'elevation': 'metres', 'speed': 'metres per second', 'duration': 'seconds'},
            'notes': ['CSV Activity Date was verified as UTC against GPX and TCX timestamps.',
                      'Distance uses the second Distance column in metres; the first column is kilometres.',
                      'Missing average speed is derived from distance divided by moving time and marked in detail views.',
                      'Route previews sample original GPS records and retain segment endpoints, source indices, and timestamps.',
                      'Missing GPS, recorded track boundaries, FIT timer stops, and FIT sessions keep route segments separate.',
                      'Preview sampling changes only the display; the complete archived activity file is preserved.',
                      'Source columns with repeated names are retained with numbered suffixes.',
                      'This catalog covers the supplied archive; it does not query the current Strava account.']}
    (output / 'archive-data.js').write_text('window.STRAVA_ARCHIVE=' + as_json({'meta': meta, 'activities': activities}) + ';\n', encoding='utf-8')
    (output / 'manifest.json').write_text(json.dumps({'schemaVersion': 1, 'meta': meta, 'files': files}, indent=2), encoding='utf-8')
    fields = ['Activity ID','Name','Activity type','Date UTC',f'Date {LOCAL_TIMEZONE}','Gear','Distance km','Distance miles',
              'Moving time seconds','Elapsed time seconds','Elevation gain m','Average speed km/h','Average speed derived',
              'Average heart rate bpm','Average power W','File format','Original archive path','Readable file','Route GPS records']
    with (output / 'activities-index.csv').open('w', encoding='utf-8-sig', newline='') as target:
        writer = csv.writer(target); writer.writerow(fields)
        for a in activities:
            values = [a['id'], a['name'], a['type'], a['utc'], a['localDate']+' '+a['localTime']+' '+a['localZone'], a['gear'],
                a['distance']/1000 if a['distance'] is not None else '', a['distance']/1609.344 if a['distance'] is not None else '',
                a['moving'], a['elapsed'], a['elevation'], a['speed']*3.6 if a['speed'] is not None else '', a['speedDerived'],
                a['heartRate'], a['power'], a['format'], a['originalFile'], a['file'], a['pointCount']]
            writer.writerow(["'" + value if isinstance(value, str) and value.startswith(('=', '+', '@', '-')) else value for value in values])
    print('Catalog complete:', json.dumps({key: meta[key] for key in ['records','files','formats','previews','noFileIds']}), flush=True)
    print(f'Preview parsing issues: {len(preview_errors)}', flush=True)


def main():
    if not SOURCE.is_file():
        raise SystemExit(f'Archive not found: {SOURCE}. Update archive.config.json to select a ZIP under data/.')
    data = (PROJECT / 'data').resolve()
    if not DESTINATION.is_relative_to(data) or DESTINATION == data:
        raise SystemExit('The generated catalog must be a subfolder of data/.')
    if SOURCE.parent != data:
        raise SystemExit('Place the original ZIP directly under data/ so the browser download link can find it.')
    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='.catalog-build-', dir=DESTINATION.parent))
    backup = DESTINATION.parent / ('.catalog-previous-' + uuid.uuid4().hex)
    try:
        build(staging)
        if DESTINATION.exists():
            DESTINATION.rename(backup)
        try:
            staging.rename(DESTINATION)
        except OSError:
            if backup.exists():
                backup.rename(DESTINATION)
            raise
        if backup.exists():
            shutil.rmtree(backup)
        print(f'Catalog installed: {DESTINATION}', flush=True)
    finally:
        if staging.exists():
            shutil.rmtree(staging)


if __name__ == '__main__':
    main()
