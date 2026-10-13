"""Verify source preservation, generated metadata and original XML preview points."""
from pathlib import Path
from settings import PROJECT, SOURCE, DESTINATION as ROOT
from collections import Counter
import csv, gzip, hashlib, io, json, math, re, time, zipfile
import xml.etree.ElementTree as ET

manifest=json.loads((ROOT/'manifest.json').read_text())
text=(ROOT/'archive-data.js').read_text()
catalog=json.loads(text.removeprefix('window.STRAVA_ARCHIVE=').strip().removesuffix(';'))
activities=catalog['activities'];by_id={a['id']:a for a in activities}
assert len(activities)==len(by_id)==catalog['meta']['records']
assert len(manifest['files'])==catalog['meta']['files']
assert dict(Counter(a['format'] for a in activities if a['format']))==catalog['meta']['formats']
assert sum(bool(a['preview']) for a in activities)==catalog['meta']['previews']
last_report=time.monotonic();xml_previews=0;preview_points=0
with zipfile.ZipFile(SOURCE) as archive:
    assert archive.read('activities.csv')==(ROOT/'source-activities.csv').read_bytes()
    reader=csv.reader(io.StringIO(archive.read('activities.csv').decode('utf-8-sig')))
    headers=next(reader);rows=list(reader)
    assert len(rows)==len(activities) and {row[0] for row in rows}==set(by_id)
    for row in rows:
        a=by_id[row[0]];assert a['name']==row[2] and a['originalFile']==(row[12] or None)
        counts=Counter()
        for header,value in zip(headers,row):
            counts[header]+=1;key=header if counts[header]==1 else f'{header} [{counts[header]}]'
            assert a['source'][key]==value
        if row[17]:assert a['distance']==float(row[17])
    for index,entry in enumerate(manifest['files'],1):
        source=archive.read(entry['archivePath']);readable=(ROOT/entry['readablePath']).read_bytes()
        assert source==(ROOT/entry['archivePath']).read_bytes()
        assert readable==(gzip.decompress(source) if entry['archivePath'].endswith('.gz') else source)
        assert hashlib.sha256(source).hexdigest()==entry['sourceSha256']
        assert hashlib.sha256(readable).hexdigest()==entry['readableSha256']
        if time.monotonic()-last_report>=2:
            print(f'Verified source bytes and checksums for {index:,}/{len(manifest["files"]):,} files',flush=True)
            last_report=time.monotonic()
        a=by_id[entry['activityId']]
        if not a['preview']:continue
        track_text=(ROOT/a['preview']).read_text()
        track=json.loads(track_text.split('=',1)[1].strip().removesuffix(';'))
        assert track['id']==a['id'] and track['sourcePoints']==a['pointCount']
        assert len(track['points'])==len(track['sourceIndices'])==a['previewPointCount']
        assert track['sourceIndices']==sorted(set(track['sourceIndices']))
        assert track['sourceIndices'][0]==0 and track['sourceIndices'][-1]==a['pointCount']-1
        assert all(len(p)==5 and -90<=p[0]<=90 and -180<=p[1]<=180 for p in track['points'])
        preview_points+=len(track['points'])
        if a['format'] in {'GPX','TCX'}:
            root=ET.fromstring(readable.lstrip());points=[]
            for node in root.iter():
                tag=node.tag.rsplit('}',1)[-1]
                if (a['format']=='GPX' and tag!='trkpt') or (a['format']=='TCX' and tag!='Trackpoint'):continue
                fields={child.tag.rsplit('}',1)[-1]:child.text for child in node.iter()}
                try:
                    lat=float(node.attrib['lat']) if a['format']=='GPX' else float(fields['LatitudeDegrees'])
                    lon=float(node.attrib['lon']) if a['format']=='GPX' else float(fields['LongitudeDegrees'])
                    if not(math.isfinite(lat) and math.isfinite(lon) and abs(lat)<=90 and abs(lon)<=180):continue
                except (KeyError,TypeError,ValueError):continue
                altitude=fields.get('ele' if a['format']=='GPX' else 'AltitudeMeters')
                try:altitude=float(altitude)
                except(TypeError,ValueError):altitude=None
                if altitude is not None and not math.isfinite(altitude):altitude=None
                stamp=fields.get('time' if a['format']=='GPX' else 'Time')
                points.append([lat,lon,stamp,altitude])
            assert len(points)==a['pointCount']
            for position,point in zip(track['sourceIndices'],track['points']):assert points[position]==point[:4]
            xml_previews+=1
scripts=re.findall(r'<script[^>]+src="([^"]+)"',(PROJECT/'index.html').read_text())
assert all((PROJECT/path).is_file() for path in scripts)
assert (PROJECT/'src/catalog.css').is_file()
links=re.findall(r'href="([^"]+)"',(PROJECT/'index.html').read_text())
assert all((PROJECT/path).is_file() for path in links if not path.startswith(('#','https:','http:')))
for a in activities:
    for key in ['file','originalFile','preview']:
        if a[key]: assert (PROJECT/'data/catalog'/a[key]).is_file()
with (ROOT/'activities-index.csv').open(encoding='utf-8-sig',newline='') as source:
    reader=csv.reader(source);header=next(reader);normalized=list(reader)
assert len(header)==len(set(header)) and len(normalized)==len(activities)
assert {row[0] for row in normalized}==set(by_id)
assert catalog['meta']['sourceSha256']==hashlib.sha256(SOURCE.read_bytes()).hexdigest()
results={'sourceRecordsPreserved':len(activities),'sourceFilesByteVerified':len(manifest['files']),
         'xmlPreviewsComparedWithRecordedPoints':xml_previews,'previewPointsValidated':preview_points,
         'assetPathsVerified':len(scripts)+1,'normalizedCsvRowsVerified':len(normalized)}
print('Validation passed:',json.dumps(results),flush=True)
