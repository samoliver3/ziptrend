import pandas as pd
import pytest
from ziptrend.data import prepare_data, locate, time_bins, period_snapshot
from ziptrend.demo import demo_data
from ziptrend.geography import selected_boundaries, map_view


def test_calendar_gaps_and_interval_aggregation():
    data = pd.DataFrame({"zip": ["02108"] * 3, "date": pd.to_datetime(["2024-01-01", "2024-01-20", "2024-03-01"]), "value": [10, 20, 30]})
    assert len(time_bins(data, "month")) == 3
    assert period_snapshot(data, "2024-02-01").empty
    assert period_snapshot(data, "2024-01-01").value.tolist() == [20]
    assert period_snapshot(data, "2024-01-01", method="sum").value.tolist() == [30]
    assert period_snapshot(data, "2024-01-01", method="mean").value.tolist() == [15]
    assert period_snapshot(data, "2024-01-01", "year").value.tolist() == [30]


def test_state_view_does_not_zoom_to_only_uploaded_zip_points():
    raw, lookup = demo_data()
    data = locate(prepare_data(raw, zip_column="zip", date_column="date", value_column="population"), lookup)
    co = data[data.state == "CO"]
    boundaries = selected_boundaries(["CO"])
    center, zoom = map_view(co, boundaries)
    other_center, other_zoom = map_view(co[co.zip == "80202"], boundaries)
    assert (center, zoom) == (other_center, other_zoom)
    assert -106 < center["lon"] < -105
    assert 38 < center["lat"] < 40
    assert 4 < zoom < 6
    map_chart = pytest.importorskip("ziptrend.charts", exc_type=ImportError).map_chart
    snapshot = period_snapshot(co, "2023-01-01")
    limits = (snapshot.value.min(), snapshot.value.max())
    fig = map_chart(snapshot, "Concentration heatmap", limits, states=["CO"], view_data=co)
    assert fig.layout.coloraxis.cmax == co[co.date == "2023-01-01"].value.max()
    assert len(fig.layout.map.layers) == 2
    assert fig.layout.map.layers[0].source["features"][0]["id"] == "CO"
    empty = map_chart(snapshot.iloc[:0], states=["CO"], view_data=co)
    assert empty.layout.map.center.lon == center["lon"]


def test_alaska_view_handles_date_line():
    bounds = selected_boundaries(["AK"])
    center, zoom = map_view(pd.DataFrame(), bounds)
    assert center["lon"] < -140
    assert zoom > 1
