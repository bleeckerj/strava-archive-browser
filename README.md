# Strava archive browser

A local browser for the supplied Strava export. Search and filter activities, compare yearly and gear totals, examine recorded routes and elevation, and download individual activity files.

The current archive contains 1,014 activities from January 5, 2010 through August 16, 2021: 390 GPX, 399 FIT, and 223 TCX recordings. Two activity rows have no source file. There are 1,009 recorded route previews; three files contain no usable GPS track.

## Browse

Run these commands from this project folder:

```sh
npm start
```

Open <http://127.0.0.1:8765/>. The server listens on this computer only. Stop it with Control-C. You can also open `index.html` directly in a browser that supports local script loading. No Strava credentials are required.

The table supports search, date, year, activity type, gear and file filters, sorting, pagination, and metric or imperial units. Select an activity name for its recorded route, elevation profile, measurements, description, private notes and original CSV fields. The full index and filtered selections can be saved as CSV.

## Files

- `index.html` and `src/` contain the browser code and styles.
- `scripts/` contains archive import, track decoding, local serving and verification logic.
- `archive.config.json` selects the source ZIP, generated catalog, display timezone and FIT Preview repository.
- `data/Strava-Activity-Archive-2026-10-12.zip` is the complete original export.
- `data/catalog/activities/` contains exact archived recordings and lossless decompressed copies of `.gz` files.
- `data/catalog/tracks/` contains sampled original GPS records with timestamps, source indices and segment boundaries.
- `data/catalog/source-activities.csv` preserves the source CSV bytes and repeated headers.
- `data/catalog/activities-index.csv` supplies unique column names and explicit units.
- `data/catalog/manifest.json` records archive and per-file SHA-256 checksums.

Personal data, generated catalog files, dependencies and compiled readers are excluded from Git. Keep the entire project folder together for its relative download links to work. The original Downloads copies are preserved.

## Rebuild and verify

The supplied catalog is already generated. Rebuilding requires Python 3.9 or newer and Node.js 18 or newer:

```sh
npm ci
npm run build:fit
npm run build
npm run verify
npm test
```

The JavaScript FIT parser handles the standard recordings. Four older FIT files use the native decoder from the existing sibling `nfl-fit-file-preview` repository. `build:fit` compiles the adapter against that repository's existing Debug build products; build FIT Preview first if those products are absent. Its repository and source files are left intact. This fallback requires macOS.

Rebuilding writes a fresh catalog before replacing the previous one. Update `archive.config.json` when selecting another export; place its ZIP directly under `data/`. Route decoding errors are reported in the catalog and manifest, while the complete source files remain available.

Verification compares every activity's source fields and all 1,012 recording files with the ZIP, checks decompressed bytes and hashes, and compares GPX/TCX preview coordinates, timestamps and elevations with their original XML records. Browser tests check download paths, units, escaping and route rendering with an actual archived recording.

## Measurements and coverage

Source activity dates were verified as UTC against the exported track timestamps. Local display uses America/Los_Angeles with PST or PDT. Distance uses the second source Distance column in metres; the first column contains kilometres. Missing average speed is calculated from distance divided by moving time and marked in activity details. Other absent measurements stay empty.

Previews retain original GPS points, source indices, timestamps, segment boundaries and coordinate extrema. They sample the recording for display; full-resolution activity files remain available. Routes are drawn north-up without downloading map imagery. Select a readable `.fit` file in Finder and press Space to use the installed FIT Preview viewer.

This project covers the supplied export and does not synchronize the current Strava account.
