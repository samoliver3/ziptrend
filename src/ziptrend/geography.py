"""Bundled state outlines and stable viewports independent of time-bin coverage."""
import json
import math
from functools import lru_cache
from importlib.resources import files


@lru_cache(maxsize=1)
def state_boundaries():
    return json.loads(files("ziptrend").joinpath("assets/us-states.geojson").read_text(encoding="utf-8"))


def selected_boundaries(states):
    return {"type": "FeatureCollection", "features": [feature for feature in state_boundaries()["features"]
                                                        if feature["id"] in states]}


def coordinates(nested):
    if len(nested) >= 2 and isinstance(nested[0], (int, float)):
        yield nested[:2]
    else:
        for item in nested:
            yield from coordinates(item)


def map_view(data, boundaries):
    points = [p for feature in boundaries["features"] for p in coordinates(feature["geometry"]["coordinates"])]
    if not points:
        points = data[["longitude", "latitude"]].dropna().values.tolist()
    if not points:
        return {"lat": 39, "lon": -98}, 3
    # Use the smallest longitude arc, including Alaska's Aleutian islands.
    longs = sorted({p[0] % 360 for p in points})
    gaps = [(longs[(i + 1) % len(longs)] + (360 if i == len(longs) - 1 else 0) - value, i)
            for i, value in enumerate(longs)]
    _, gap = max(gaps)
    west = longs[(gap + 1) % len(longs)]
    shifted = [p[0] % 360 + (360 if p[0] % 360 < west else 0) for p in points]
    east = max(shifted)
    south, north = min(p[1] for p in points), max(p[1] for p in points)
    def mercator_y(lat):
        return math.log(math.tan(math.pi / 4 + math.radians(max(-85, min(85, lat))) / 2))
    # Fit a state tightly while leaving padding for labels and the color legend.
    fraction = max((east - west) / 360, (mercator_y(north) - mercator_y(south)) / (2 * math.pi), 0.0001)
    zoom = max(0, min(11, math.log2(520 / (512 * fraction * 1.25))))
    center = {"lat": math.degrees(2 * math.atan(math.exp((mercator_y(north) + mercator_y(south)) / 2)) - math.pi / 2),
              "lon": ((west + east) / 2 + 180) % 360 - 180}
    return center, zoom
