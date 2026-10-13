# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A walkable 3D scene of the Moscow Kremlin and Red Square that runs straight from `index.html` in a browser (no build step, no package manager, no tests). Three.js r128 is loaded as a global script from cdnjs, so the page needs network access. All UI text, comments and section headers are German; keep it that way.

## Commands

```bash
open index.html                                                        # run
python3 tools/build_data.py osm/kreml.json osm/extra.json kreml-data.js   # regenerate footprint data
```

`kreml-data.js` is generated. Change `tools/build_data.py` and regenerate instead of editing it.

The OSM dumps in `osm/` came from the Overpass API (bbox `55.7462,37.6085,55.7580,37.6270`, `out geom`). `overpass-api.de` rejected the default curl request with 406; it worked with `-A "<some agent>" -H "Accept: */*"` and `--data-urlencode "data=..."`.

### Checking a change

There is no test suite. Two URL hashes exist for verification:

- `index.html#map` overlays the walk grid: white = reachable, orange = free but unreachable, dark = blocked. Use it after touching footprints, gates or blocking.
- `index.html#cam=x,z,yaw,pitch,dist` places the avatar and camera for a reproducible view.

Headless screenshot (software WebGL is slow: one frame takes 1–2 minutes, so poll for the file rather than relying on a short timeout, and run shots one at a time):

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --user-data-dir=<tmpdir> \
  --enable-unsafe-swiftshader --use-angle=swiftshader --window-size=1400,900 --virtual-time-budget=9000 \
  --enable-logging=stderr --screenshot=out.png "file://$PWD/index.html#cam=240,-225,2.3,0.3,130"
```

JS errors show up as `CONSOLE` lines in stderr. Globals (`infos`, `walkTo`, `fig`, `figures`, `reach`, `blocked`) are reachable from an appended `<script>` for scripted checks, e.g. walking to every listed place and asserting `fig.path.length > 0`.

## Coordinate system

One convention runs through the Python tool, the data file and the scene:

- Local metres, origin at Cathedral Square (lat 55.7506, lon 37.6175). **x = east, z = south**, y = up.
- A footprint ring is a flat array `[x0, z0, x1, z1, ...]`.
- Each building carries `r = [cx, cz, w, d, a]`, its minimum-area bounding rectangle; `a` is the angle of the rectangle's long/“u” axis in the x–z plane, limited to ±45°.
- `frame(x, z, a)` returns a group whose **local +x points along `a`** and local +z is the perpendicular (it sets `rotation.y = -a`). Hand-built models are authored in that frame; churches have their apses toward local +x (east).
- Geometry helpers `box`, `cyl`, `cone`, `hip` take `y` as the **bottom** of the part, not its centre.

## Architecture

`kreml-data.js` defines `window.KREML` with `B` (buildings, incl. the Kremlin wall as `k: 'wall'`), `GR`/`WD` (grass, wood), `SQ` (named squares), `WA` (water, clipped), `BR` (bridge), `gates`. `tools/build_data.py` stitches multipolygon rings, simplifies them, assigns holes, and cuts the Grand Kremlin Palace outline into three entries: the main palace plus tagged parts `t: 'facets'` and `t: 'depo'`.

`index.html` is one script, organised by `// ---------- Name ----------` section comments. The flow:

1. **Generic pass over `K.B`.** Every footprint is rasterised into the walk grid. Then, unless its key is in `SKIP`, it is extruded with a windowed wall material; `k: 'wall'` entries become red walls with instanced merlons. The key is `b.t || b.id` (OSM id, or the tag for the cut-out palace parts).
2. **Per-building tables**, all keyed the same way:
   - `INFO`: name, subtitle, text, list colour and `grp` (which sidebar group; entries without `grp` get no label and no list entry).
   - `OV`: display overrides for extruded footprints (height, wall colour, roof material, sloped-roof size, window grid).
   - `TOWERS`: wall towers → model type (`gate`, `sq`, `rd`, `boro`, `tsar`), year, text, star, clock. Heights come from the data.
   - `SKIP`: footprints that are not extruded because a hand-built model replaces them. They still block the grid.
3. **Hand-built models** (cathedrals, Ivan the Great, towers, St Basil's, mausoleum, …) are placed with `R(key)` (the footprint's rectangle) and `frame(...)`. Several named buildings are an extruded footprint *plus* add-ons in a frame (Senate dome, GKP main block and Terem, GUM/museum towers).
4. **Walk grid.** 2 m cells over x −470…540, z −640…430. `blocked` is 1 for footprints/water and 2 for a one-cell clearance ring; the bridge polygon and three hand-placed gate corridors (`carve(...)`: Spasskaya, Nikolskaya, Borovitskaya) are opened afterwards. `reach` is a flood fill from `START`. Trinity Gate is deliberately closed because its route is a raised bridge.
5. **Navigation.** A click raycasts against `groundMesh` and `solids`; `walkTo` runs A* (`findPath`) to `freeCell(...)`, the nearest *reachable* cell, so clicking a roof or an enclosed courtyard still yields a route. The path is string-pulled with `los`.
6. **Figures.** `makeFigure(style)` builds a jointed figure from a style object (colours, tie/sweatshirt, hair, beard) and returns `{ g, limbs, path, phase }`. `figures` holds all of them; `fig` is the selected one (button or click on a figure). `walkTo` and the camera act on `fig`.
7. **Loop.** Moves every figure along its own `path`, poses its `limbs` (hips, knees, shoulders, elbows), follows `fig` with an orbit camera, and re-centres the shadow camera on it.

### Adding or changing a building

- Register anything clickable with `register(obj, info, x, z, labelY)`; `frame(...)` and `extrude(...)` already push to `solids`.
- A new hand-built replacement needs its key in `SKIP`; a restyled footprint needs an `OV` entry; either needs an `INFO` entry with `grp` to appear in the list.
- Objects without an OSM footprint (Tsar Bell, Tsar Cannon) must block their own cells with `raster({ o: [...] }, 1)` **before** the “Raster fertigstellen” section.
- Re-check `#map` afterwards: a new footprint can seal a passage through the clearance ring.

## Three.js r128 pitfalls already hit

- `MeshLambertMaterial` has no `flatShading`; use `flatOf(mat)`, which returns a cached flat-shaded Phong equivalent.
- Extruded wall UVs are in metres, so `wallMat` sets `repeat = 1/cellSize`, `flipY = false` and a negative `offset.y` so windows start at ground level and stay upright. `texBox` (box geometry) uses plain per-face repeat counts instead.
- `slopedRoof` fakes a hipped roof with an inward bevel on a near-zero-depth extrusion; very narrow wings can produce artefacts, so it is opt-in per building via `OV[...].s`.
- A non-uniformly scaled partial sphere must be tilted in the geometry (`geo.rotateX`) before the mesh is scaled, otherwise it sinks into the matching ellipsoid (see the avatar's hair).

## Attribution

Footprints are © OpenStreetMap contributors (ODbL); the credit line in the page and the header comment in `kreml-data.js` must stay.
