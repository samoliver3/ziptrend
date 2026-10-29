from pathlib import Path
import pytest

pytest.importorskip("plotly")
AppTest = pytest.importorskip("streamlit.testing.v1").AppTest


def test_demo_dashboard_and_filters():
    app = AppTest.from_file(str(Path(__file__).parents[1] / "src/ziptrend/app.py"), default_timeout=30).run()
    assert not app.exception
    assert len(app.select_slider) == 1
    assert app.metric[0].value == "16"
    next(widget for widget in app.multiselect if widget.label.startswith("States")).set_value(["CO"]).run()
    assert not app.exception
    assert app.metric[0].value == "6"
    next(widget for widget in app.multiselect if widget.label.startswith("ZIP codes")).set_value(["80202"]).run()
    assert not app.exception
    assert app.metric[0].value == "1"
    app.radio[0].set_value("Concentration heatmap").run()
    assert not app.exception
    next(widget for widget in app.selectbox if widget.label == "Time interval").set_value("year").run()
    assert not app.exception


def test_multiple_zip_inspection_bulk_entry_and_exclusion():
    app = AppTest.from_file(str(Path(__file__).parents[1] / "src/ziptrend/app.py"), default_timeout=30).run()
    inspector = next(widget for widget in app.multiselect if widget.label == "Inspect ZIP codes")
    inspector.set_value(["02108", "80202"]).run()
    assert not app.exception
    assert app.session_state["inspect_demo"] == ["02108", "80202"]
    app.text_area(key="inspect_demo_paste").set_value("80203, 02108\n99999").run()
    app.button(key="inspect_demo_add").click().run()
    assert app.session_state["inspect_demo"] == ["02108", "80202", "80203"]
    assert any("99999" in warning.value for warning in app.warning)
    app.button(key="inspect_demo_clear").click().run()
    assert app.session_state["inspect_demo"] == []
    next(widget for widget in app.multiselect if widget.label == "ZIP codes · empty means all").set_value(["02108", "80202"]).run()
    assert app.metric[0].value == "2"
    next(widget for widget in app.selectbox if widget.label == "ZIP filter").set_value("Exclude selected ZIPs").run()
    assert not app.exception
    assert app.metric[0].value == "14"


def test_map_summary_uses_timeline_bin():
    app = AppTest.from_file(str(Path(__file__).parents[1] / "src/ziptrend/app.py"), default_timeout=30).run()
    next(widget for widget in app.multiselect if widget.label == "ZIP codes · empty means all").set_value(["02108"]).run()
    from datetime import datetime, date
    app.select_slider[0].set_value(datetime(2023, 2, 1)).run()
    from ziptrend.demo import demo_data
    raw, _ = demo_data()
    expected = raw[(raw.zip == "02108") & (raw.date.dt.date == date(2023, 2, 1))].population.iloc[0]
    assert app.metric[1].value == f"{expected:,.0f}"
    assert len(app.select_slider) == 1
    next(widget for widget in app.selectbox if widget.label == "Time interval").set_value("year").run()
    app.select_slider[0].set_value(datetime(2023, 1, 1)).run()
    expected = raw[(raw.zip == "02108") & (raw.date.dt.date == date(2023, 12, 1))].population.iloc[0]
    assert app.metric[1].value == f"{expected:,.0f}"
    assert not app.exception

