from io import StringIO, BytesIO
import pandas as pd
import pytest
from ziptrend import read_data, prepare_data, summarize, trends, locate
from ziptrend.demo import demo_data


def prepared(rows):
    return prepare_data(pd.DataFrame(rows, columns=["zip", "date", "value"]), zip_column="zip", date_column="date", value_column="value")


@pytest.mark.parametrize("extension,separator", [("csv", ","), ("tsv", "\t"), ("txt", "|")])
def test_delimited_leading_zero(extension, separator):
    data = read_data(StringIO(separator.join(["zip", "date", "value"]) + "\n" + separator.join(["02108", "2024-01-01", "10"])), filename=f"data.{extension}")
    assert data.iloc[0]["zip"] == "02108"


def test_excel_and_json():
    raw, _ = demo_data()
    buffer = BytesIO()
    raw.head().to_excel(buffer, index=False)
    assert len(read_data(buffer, filename="demo.xlsx")) == 5
    assert len(read_data(StringIO('[{"zip":"02108","date":"2024-01-01","value":2}]'), filename="demo.json")) == 1


def test_normalization_and_year():
    result = prepared([(2108.0, "2024", "1,200"), ("80202-1234", "2024-02-01", 100)])
    assert result.zip.tolist() == ["02108", "80202"]
    assert result.value.tolist() == [1200, 100]
    assert result.date.iloc[0] == pd.Timestamp("2024-01-01")


@pytest.mark.parametrize("row", [("bad", "2024", 2), ("02108", "not-date", 2), ("02108", "2024", float("inf")), ("02108", "45292", 2)])
def test_invalid_input(row):
    with pytest.raises(ValueError):
        prepared([row])


def test_duplicates():
    raw = pd.DataFrame({"zip": ["02108"] * 2, "date": ["2024"] * 2, "value": [2, 3]})
    with pytest.raises(ValueError, match="Repeated"):
        prepare_data(raw, zip_column="zip", date_column="date", value_column="value")
    result = prepare_data(raw, zip_column="zip", date_column="date", value_column="value", duplicate="sum")
    assert result.value.tolist() == [5]


def test_latest_does_not_sum_population_over_time():
    data = prepared([("02108", "2024-01-01", 10), ("02108", "2024-01-31", 12), ("02116", "2024-01-01", 20)])
    data["state"] = "MA"
    assert summarize(data).value.sum() == 32
    assert trends(data, group="state").value.tolist() == [32]
    assert summarize(data, "sum").value.sum() == 42
    assert summarize(data, "mean").value.sum() == 31


def test_missing_geography_preserves_observations():
    data = prepared([("02108", "2024", 1), ("99999", "2024", 2)])
    lookup = pd.DataFrame({"zip": ["02108"], "state": ["MA"], "latitude": [42.3], "longitude": [-71.0]})
    result = locate(data, lookup)
    assert len(result) == 2
    assert result.state.isna().sum() == 1


def test_charts_and_demo():
    map_chart = pytest.importorskip("ziptrend.charts", exc_type=ImportError).map_chart
    raw, lookup = demo_data()
    data = locate(prepare_data(raw, zip_column="zip", date_column="date", value_column="population"), lookup)
    snapshot = summarize(data)
    for style in ["ZIP markers", "Concentration heatmap"]:
        figure = map_chart(snapshot, style)
        assert len(figure.data[0].lat) == 16
