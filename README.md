# Moskauer Kreml und Roter Platz in 3D

Begehbare 3D-Szene im Browser (Three.js): `index.html` öffnen. Klick setzt das Ziel der Figur, Ziehen dreht die Kamera, Mausrad zoomt.

## Dateien

| Datei | Inhalt |
|---|---|
| `index.html` | Szene, Gebäudemodelle, Figur, Wegsuche |
| `kreml-data.js` | Grundrisse in lokalen Meterkoordinaten (erzeugt, nicht von Hand ändern) |
| `tools/build_data.py` | Erzeugt `kreml-data.js` aus den OSM-Rohdaten |
| `osm/kreml.json`, `osm/extra.json` | Overpass-Abzüge (Gebäude, Mauern, Wasser; Parks, Plätze, Gebäudeteile) |

## Daten neu erzeugen

```bash
python3 tools/build_data.pyexport GITHUB_PERSONAL_ACCESS_TOKEN=$(gh auth token) osm/kreml.json osm/extra.json kreml-data.js
```

## Prüfansichten

- `index.html#map` zeigt das Wegenetz (weiß erreichbar, orange unerreichbar, dunkel gesperrt).
- `index.html#cam=x,z,yaw,pitch,dist` setzt Figur und Kamera.

Grundrisse © OpenStreetMap-Mitwirkende (ODbL).
