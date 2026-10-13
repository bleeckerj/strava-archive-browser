const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const project = path.resolve(__dirname, '..');
const context = vm.createContext({window: {}});
for (const file of ['archive-utils.js', 'route-view.js', 'route-map.js']) {
  vm.runInContext(fs.readFileSync(path.join(project, 'src', file), 'utf8'), context);
}
const utils = context.window.ArchiveUtils;

test('activity downloads resolve to the project data folder and escape path segments', () => {
  assert.equal(utils.fileUrl('activities/A & B.fit'), 'data/catalog/activities/A%20%26%20B.fit');
  assert.equal(utils.fileUrl('tracks/123.js'), 'data/catalog/tracks/123.js');
});

test('unit conversions preserve missing measurements and escape archived text', () => {
  assert.equal(utils.distance(1609.344, true), '1.0');
  assert.equal(utils.speed(10, false), '36.0');
  assert.equal(utils.duration(3661), '1h 01m');
  assert.equal(utils.distance(null, true), '—');
  assert.equal(utils.esc('<script>"&'), '&lt;script&gt;&quot;&amp;');
});

const dataFile = path.join(project, 'data/catalog/archive-data.js');
test('every original recording and route preview resolves under data/', {skip: !fs.existsSync(dataFile)}, () => {
  vm.runInContext(fs.readFileSync(dataFile, 'utf8'), context);
  for (const item of context.window.STRAVA_ARCHIVE.activities) {
    for (const key of ['file', 'originalFile', 'preview']) {
      if (item[key]) {
        assert.ok(fs.existsSync(path.join(project, decodeURI(utils.fileUrl(item[key])))), item[key]);
      }
    }
  }
});

test('the recorded preview renders finite coordinates and preserves segment breaks', {skip: !fs.existsSync(dataFile)}, () => {
  const item = context.window.STRAVA_ARCHIVE.activities.find(a => a.preview);
  vm.runInContext(fs.readFileSync(path.join(project, 'data/catalog', item.preview), 'utf8'), context);
  const track = context.window.STRAVA_TRACKS[item.id];
  for (const imperial of [false, true]) {
    const svg = context.window.ArchiveRoute.draw(track, imperial);
    assert.ok(svg.includes('Recorded route'));
    assert.doesNotMatch(svg, /NaN|Infinity/);
    const routePath = svg.match(/<path d="([^"]+)"/)[1];
    const segments = track.points.reduce((n, p, i, all) => n + (i === 0 || p[4] !== all[i - 1][4]), 0);
    assert.equal((routePath.match(/M/g) || []).length, segments);
  }
});


test('map segments preserve every archived preview coordinate and recording boundary', {skip: !fs.existsSync(dataFile)}, () => {
  for (const item of context.window.STRAVA_ARCHIVE.activities.filter(a => a.preview)) {
    vm.runInContext(fs.readFileSync(path.join(project, 'data/catalog', item.preview), 'utf8'), context);
    const track = context.window.STRAVA_TRACKS[item.id];
    const groups = context.window.ArchiveMap.segments(track);
    const recorded = track.points.map(point => [point[0], point[1]]);
    assert.equal(JSON.stringify(groups.flat()), JSON.stringify(recorded), item.id);
    const expected = track.points.reduce((n, p, i, all) => n + (i === 0 || p[4] !== all[i - 1][4]), 0);
    assert.equal(groups.length, expected, item.id);
  }
});

test('map fits the genuine recording, keeps endpoints, and disposes its resources', {skip: !fs.existsSync(dataFile)}, () => {
  const item = context.window.STRAVA_ARCHIVE.activities.find(a => a.preview);
  const track = context.window.STRAVA_TRACKS[item.id];
  const captured = {lines: [], markers: [], fits: [], removed: 0};
  const layer = () => ({addTo() {return this;}, bindTooltip() {return this;}, on() {return this;}});
  const map = {
    invalidateSize() {},
    fitBounds(bounds) {captured.fits.push(bounds);},
    remove() {captured.removed++;},
  };
  context.window.ArchiveMapConfig = {tileUrl: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png', maxZoom: 19, fitMaxZoom: 16};
  context.window.L = {
    map: () => map,
    latLngBounds: points => points,
    tileLayer: layer,
    polyline(points) {captured.lines.push(points);return layer();},
    circleMarker(point) {captured.markers.push(point);return layer();},
    control: {scale: layer},
  };
  const view = context.window.ArchiveMap.mount({}, track, false, {});
  assert.equal(JSON.stringify(captured.fits[0]), JSON.stringify(track.points.map(point => point.slice(0, 2))));
  assert.equal(JSON.stringify(captured.markers), JSON.stringify([track.points[0].slice(0, 2), track.points.at(-1).slice(0, 2)]));
  view.fit();
  assert.equal(captured.fits.length, 2);
  view.destroy();view.destroy();view.fit();
  assert.equal(captured.removed, 1);
  assert.equal(captured.fits.length, 2);
  delete context.window.L;
});
