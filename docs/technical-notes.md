# Technical notes

The [README](../README.md) covers requesting a Strava archive, importing it, browsing recordings, and making a route video. This file describes the implementation and verification workflow.

## Project files

| Path | Contents |
| --- | --- |
| `index.html`, `src/` | Browser code and styles. |
| `scripts/` | Archive import, track decoding, local serving, and verification. |
| `.runtime/servers/` | Private records for running local servers; excluded from Git and HTTP access. |
| `vendor/leaflet/` | Pinned map library, styles, and license. `src/map-config.js` selects the tile source. |
| `archive.config.json` | Source ZIP, catalog destination, display timezone, and optional FIT Preview repository. |
| `data/*.zip` | Original account archives supplied by the person using the browser. |
| `data/catalog/activities/` | Exact archived recordings and lossless decompressed copies of `.gz` files. |
| `data/catalog/tracks/` | Sampled original GPS records with timestamps, source indices, and segment boundaries. |
| `data/catalog/source-activities.csv` | Original CSV bytes, including repeated headers. |
| `data/catalog/activities-index.csv` | Normalized activity index with unique column names and explicit units. |
| `data/catalog/manifest.json` | Archive and per-file SHA-256 checksums, counts, and preview parsing errors. |
| `docs/screenshots/` | Documentation captures made with the author's archive. |

Personal archives, generated catalogs, dependencies, and compiled readers are excluded from Git. Keep the project folder and its generated catalog together for relative script and download links to work. The browser expects the catalog at `data/catalog`; changing only the configuration's catalog path does not update those browser paths.

The importer reads `activities.csv` and its referenced recordings. It does not catalog other account-export contents. It builds a replacement catalog in a staging folder before replacing the previous one. A failed build leaves the previous catalog available. Route decoding errors are recorded while the complete source files are preserved.

## Optional Mac FIT decoder

Standard FIT previews use `fit-file-parser`. Some older FIT recordings return no result from that reader. Their source files remain downloadable without a native decoder, and the catalog reports the preview issue.

The optional fallback requires macOS and an existing checkout of `nfl-fit-file-preview` with its Debug build products already built. Set `fitPreviewRepository` in `archive.config.json` to that checkout's path, relative to this project. The adapter expects these source files under `Sources/Core/`:

- `RouteModel.swift`
- `RouteGeometry.swift`
- `FITTimestampExpander.swift`
- `FITRouteDecoder.swift`

It also expects the `FITSwiftSDK`, `OrderedCollections`, and `InternalCollectionsUtilities` object files and modules under `.build/DerivedData/Build/Products/Debug/`. `scripts/build_native_fit.py` reports any missing inputs. Its Swift compilation target is macOS 15 or newer.

After building FIT Preview in its own repository, run these commands in the archive browser repository:

```sh
npm run build:fit
npm run build
npm run verify
```

The adapter is written to `.build/native-fit-reader`. The FIT Preview repository and its source files are left intact. This optional step is separate from normal cross-platform setup.

## Verification

After importing an archive:

```sh
npm run verify
npm test
```

Verification compares each activity's source fields with `activities.csv`, checks archived and decompressed bytes and SHA-256 hashes against the ZIP, and compares GPX/TCX preview coordinates, timestamps, and elevations with their original XML records. It also checks preview indices, normalized CSV rows, and local asset and recording paths. FIT preview checks validate their stored structure and indices; they do not independently decode every FIT point a second time.

The Node tests cover download paths, units, escaping, route rendering, and map lifecycle. Tests that use the local catalog are skipped when no catalog has been built. The Python tests start temporary local servers and verify process identification, port conflict diagnostics, ownership checks, interrupt and termination cleanup, private-path blocking, and port reuse. They require `lsof` and `ps`. All tests run through `npm test` without launching a browser.

The documentation example archive contains 1,014 activities from January 5, 2010, through August 16, 2021: 390 GPX, 399 FIT, and 223 TCX recordings. Two rows have no source file. With the optional native fallback, it has 1,009 route previews; three recordings contain no usable GPS track. Four older FIT recordings use the fallback. These counts describe the author's local archive, which is excluded from the Git checkout.

## Measurements and route coverage

Source activity dates in the example archive were verified as UTC against exported track timestamps. Local display uses the configured timezone, including daylight saving time. Distance uses the second source Distance column in meters; the first contains kilometers. Missing average speed is calculated from distance divided by moving time and marked in activity details. Other absent measurements stay empty.

Previews sample original GPS records, retain their source indices and timestamps, and preserve segment boundaries and coordinate extrema. Sampling affects only the display. Downloads retain the full recording.

Routes are drawn north-up over OpenStreetMap street imagery. Map tiles load from `tile.openstreetmap.org` for the viewed map and require internet access; the tile provider receives requests for those map areas. Activity records and track files are served by the local project. The browser honors normal tile caching and shows attribution. Without internet access, route geometry and elevation remain available while roads and place labels may be unavailable.

If FIT Preview is separately installed on your Mac, select a readable `.fit` file in Finder and press Space to view it there. That viewer is optional and is not required to download a FIT file or use OVERLAND TRACES.
