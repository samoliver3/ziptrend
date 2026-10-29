"""Convert Census cb_2024_us_state_20m.zip to bundled GeoJSON (requires pyshp)."""
import json
from pathlib import Path
import shapefile

root = Path(__file__).resolve().parents[1]
reader = shapefile.Reader(str(root / ".tmp/states.zip"), encoding="utf-8")
features = []
for row in reader.iterShapeRecords():
    record = row.record.as_dict()
    features.append({"type": "Feature", "id": record["STUSPS"],
                     "properties": {"state": record["STUSPS"], "name": record["NAME"]},
                     "geometry": row.shape.__geo_interface__})
(root / "src/ziptrend/assets/us-states.geojson").write_text(
    json.dumps({"type": "FeatureCollection", "features": features}, separators=(",", ":")), encoding="utf-8")
print(f"Converted {len(features)} state/territory outlines.")
