"""Small, deterministic, fictional observations with offline geography."""
import math
import pandas as pd


def demo_data():
    places = [
        ("80202", "CO", 39.752, -104.999, 15000), ("80203", "CO", 39.731, -104.982, 21000),
        ("80205", "CO", 39.758, -104.966, 31000), ("80301", "CO", 40.049, -105.219, 25000),
        ("80903", "CO", 38.839, -104.815, 18000), ("80521", "CO", 40.592, -105.106, 34000),
        ("10001", "NY", 40.750, -73.997, 27000), ("10002", "NY", 40.717, -73.988, 75000),
        ("11201", "NY", 40.694, -73.990, 65000), ("90012", "CA", 34.062, -118.239, 38000),
        ("94103", "CA", 37.773, -122.411, 32000), ("02108", "MA", 42.357, -71.064, 4500),
        ("02116", "MA", 42.350, -71.076, 24000), ("98101", "WA", 47.611, -122.334, 16000),
        ("60601", "IL", 41.886, -87.619, 17000), ("77002", "TX", 29.756, -95.365, 15000),
    ]
    lookup = pd.DataFrame(places, columns=["zip", "state", "latitude", "longitude", "base"])
    rows = []
    for i, date in enumerate(pd.date_range("2023-01-01", periods=36, freq="MS")):
        for j, (zipcode, state, lat, lon, base) in enumerate(places):
            rows.append((zipcode, date, round(base * (1 + i * (0.001 + j * 0.0001)) + math.sin(i / 3 + j) * base * 0.006)))
    return pd.DataFrame(rows, columns=["zip", "date", "population"]), lookup.drop(columns="base")
