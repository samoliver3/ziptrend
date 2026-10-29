"""Streamlit entry point, also installed with the package."""
import hashlib
import pandas as pd
import plotly.express as px
import streamlit as st
from ziptrend.data import read_data, prepare_data, locate, trends, time_bins, period_snapshot
from ziptrend.demo import demo_data
from ziptrend.charts import map_chart, COLORS
from ziptrend.selection import parse_zip_list

st.set_page_config(page_title="ZIPtrend · Geography over time", page_icon="◈", layout="wide")
# Let Streamlit pair foregrounds and surfaces for the active light/dark theme.
# Fixed light surfaces break contrast when the browser selects a dark theme.
st.markdown("""<style>
h1 {letter-spacing: -1.5px;}
[data-testid="stMetric"] {
    padding:18px;
    border:1px solid currentColor;
    border-color:color-mix(in srgb, currentColor 25%, transparent);
    border-radius:14px;
}
[data-testid="stCaptionContainer"] {color:inherit; opacity:1;}
/* A timeline selects one bin, not a cumulative range. Keep its rail neutral. */
[data-testid="stSlider"]:has(input[aria-label="Map timeline"])
    [data-rac][data-orientation="horizontal"] > div:first-child:not([data-rac]) {
    background:color-mix(in srgb, currentColor 25%, transparent) !important;
}
</style>""", unsafe_allow_html=True)
st.caption("ZIPTREND  /  U.S. DATA EXPLORER")
st.title("Every ZIP has a story.")
st.write("Explore where values concentrate and how they change over time.")


@st.cache_data(show_spinner=False)
def resolve_geography(data):
    return locate(data)


def guess(columns, names):
    return next((i for i, c in enumerate(columns) if str(c).lower() in names), 0)


def zip_picker(label, options, key):
    """Searchable selection with bulk entry and a predictable clear action."""
    st.session_state[key] = [z for z in st.session_state.get(key, []) if z in options]
    with st.expander("Paste a ZIP list", expanded=False):
        pasted = st.text_area("ZIPs separated by commas, spaces, or newlines", key=f"{key}_paste",
                              placeholder="02108, 80202, 80203")
        if st.button("Add ZIP list", key=f"{key}_add"):
            accepted, rejected = parse_zip_list(pasted, options)
            st.session_state[key] = list(dict.fromkeys(st.session_state[key] + accepted))
            if rejected:
                st.warning("Not available in the current filters or invalid: " + ", ".join(rejected[:20]))
            if accepted:
                st.success(f"Added {len(accepted)} matching ZIP(s).")
    if st.button("Clear ZIP selection", key=f"{key}_clear"):
        st.session_state[key] = []
    selected = st.multiselect(label, options, key=key, placeholder="Type a ZIP or prefix to search…",
                              help="Type to narrow the list; select multiple ZIPs. Use Paste a ZIP list for bulk entry.")
    st.caption(f"{len(selected):,} selected · {len(options):,} available")
    return selected


with st.sidebar:
    st.header("Your data")
    uploaded = st.file_uploader("Upload observations", type=["csv", "tsv", "txt", "xlsx", "xls", "json", "jsonl"])
    raw_demo, demo_lookup = demo_data()
    st.download_button("Download sample CSV", raw_demo.to_csv(index=False), "sample_population.csv", "text/csv")
    lookup_file = st.file_uploader("Optional offline ZIP lookup", type=["csv"], help="Columns: zip, state (two-letter code), latitude, longitude. One row per ZIP.")
    try:
        if uploaded is None:
            raw = raw_demo
            source_key = "demo"
            st.info("Showing fictional sample population, 2023–2025.")
        else:
            source_key = hashlib.sha256(uploaded.getvalue()).hexdigest()[:12]
            sheet = 0
            delimiter = None
            if uploaded.name.lower().endswith((".xlsx", ".xls")):
                sheet = st.selectbox("Worksheet", pd.ExcelFile(uploaded).sheet_names)
            if uploaded.name.lower().endswith((".txt", ".csv")):
                delimiter = {"Auto": None, "Comma": ",", "Tab": "\t", "Semicolon": ";", "Pipe": "|"}[st.selectbox("Delimiter", ["Auto", "Comma", "Tab", "Semicolon", "Pipe"])]
            raw = read_data(uploaded, sheet_name=sheet, delimiter=delimiter)
        columns = list(raw.columns)
        if len(columns) < 3:
            st.error("Provide at least a ZIP, date, and numeric value column.")
            st.stop()
        zip_col = st.selectbox("ZIP column", columns, index=guess(columns, {"zip", "zipcode", "zip_code", "postal_code"}), key=f"zip_{source_key}")
        date_col = st.selectbox("Date column", columns, index=guess(columns, {"date", "month", "year"}), key=f"date_{source_key}")
        val_col = st.selectbox("Measure", columns, index=guess(columns, {"population", "value", "count"}), key=f"value_{source_key}")
        date_format = st.text_input("Date format (optional)", placeholder="%m/%d/%Y", help="Use %Y for years. ISO YYYY-MM-DD is recommended; otherwise automatic parsing uses month-first dates.")
        duplicates = st.selectbox("Repeated ZIP/date rows", ["error", "sum", "mean", "last"])
        data = prepare_data(raw, zip_column=zip_col, date_column=date_col, value_column=val_col,
                            date_format=date_format or None, duplicate=duplicates)
        if lookup_file:
            data = locate(data, read_data(lookup_file))
        elif uploaded is None:
            data = locate(data, demo_lookup)
        else:
            with st.spinner("Finding ZIP geography…"):
                data = resolve_geography(data)
    except Exception as exc:
        st.error(f"Unable to load data: {exc}")
        st.caption("ZIP lookup needs internet on first use. Upload an offline lookup if unavailable.")
        st.stop()
    st.divider()
    st.header("Explore")
    states = st.multiselect("States · empty means all", sorted(data.state.dropna().unique()), key=f"states_{source_key}")
    regional = data[data.state.isin(states)] if states else data
    zip_mode = st.selectbox("ZIP filter", ["Include selected ZIPs", "Exclude selected ZIPs"])
    zips = zip_picker("ZIP codes · empty means all", sorted(regional.zip.unique()), f"zips_{source_key}")
    if zips:
        matches = regional.zip.isin(zips)
        regional = regional[matches if zip_mode == "Include selected ZIPs" else ~matches]
    frequency = st.selectbox("Time interval", ["month", "year", "day"])
    method = st.selectbox("Aggregation", ["latest", "mean", "sum"], help="Aggregate observations per ZIP within each time interval. Latest is suitable for population snapshots; sum for additive observations such as transactions.")
    st.caption("State totals represent only ZIPs in your data. Missing periods are not filled.")

if regional.empty:
    st.info("No observations match these filters.")
    st.stop()
unknown = regional.loc[regional[["latitude", "longitude", "state"]].isna().any(axis=1), "zip"].unique()
if len(unknown):
    st.warning(f"{len(unknown)} ZIP(s) lack complete geography: {', '.join(unknown[:15])}. They remain in ZIP trends and exports; missing coordinates cannot appear on the map.")

dates = sorted(regional.date.dt.date.unique())
window = (dates[0], dates[-1])
with st.sidebar.expander("Optional date-range filter"):
    limit_dates = st.checkbox("Limit date range", value=False)
    if limit_dates and len(dates) > 1:
        window = st.select_slider("Date range", options=dates, value=window,
                                  key=f"range_{source_key}_{','.join(states)}_{','.join(zips)}_{zip_mode}")
    st.caption("Limits the timeline, trend charts, and exports. Use the slider below the map to step through time.")
filtered = regional[regional.date.dt.date.between(*window)]
series = trends(filtered, frequency, method)

map_tab, trends_tab, table_tab = st.tabs(["Geography", "Trends & comparison", "Data & export"])
with map_tab:
    mode = st.radio("Map style", ["ZIP markers", "Concentration heatmap"], horizontal=True)
    fixed_scale = st.checkbox("Keep color scale fixed over time", value=False,
                              help="Off: rescale to the current filtered interval. On: use all intervals within the current state/ZIP filters for easier time comparisons.")
    summary_area = st.container()
    map_area = st.container()
    periods = [value.to_pydatetime() for value in time_bins(filtered, frequency)]
    timeline_key = "timeline_" + hashlib.sha256(str((source_key, frequency, window, states, zips, zip_mode)).encode()).hexdigest()[:16]
    period_label = lambda value: value.strftime({"month": "%B %Y", "year": "%Y", "day": "%b %d, %Y"}[frequency])
    if len(periods) > 1:
        period = st.select_slider("Map timeline", options=periods, value=periods[-1],
                                  format_func=period_label, key=timeline_key,
                                  help=f"Each step shows one {frequency}. Empty intervals remain visible; missing observations are never carried forward.")
    else:
        period = periods[0]
        st.caption(f"Map timeline: {period_label(period)} — only one interval available.")
    snapshot = period_snapshot(filtered, period, frequency, method)
    with summary_area:
        st.subheader(f"{' · '.join(states) if states else 'United States'} · {period_label(period)}")
        metrics = st.columns(3)
        metrics[0].metric("ZIPs in this interval", f"{snapshot.zip.nunique():,}")
        metrics[1].metric(f"{val_col} · sum across ZIPs", f"{snapshot.value.sum():,.0f}" if not snapshot.empty else "No data")
        metrics[2].metric("Aggregation", method.title())
        st.caption(f"{method.title()} per ZIP within this {frequency}. Cool blue → warm pink/red means lower → higher values. Select markers to add ZIPs to the comparison.")
    mapped = snapshot.dropna(subset=["latitude", "longitude"])
    options = sorted(filtered.zip.unique())
    focus_key = f"inspect_{source_key}"
    map_key = "map_" + hashlib.sha256(str((source_key, mode, period, window, method, options, states)).encode()).hexdigest()[:16]

    def add_map_selection():
        points = st.session_state[map_key].selection.points
        selected = [point["customdata"][0] for point in points if point.get("customdata")]
        st.session_state[focus_key] = list(dict.fromkeys(st.session_state.get(focus_key, []) + selected))

    with map_area:
        render_mode = mode
        if snapshot.empty:
            st.info("No observations in this interval. Move the timeline to another interval.")
        elif mapped.empty:
            st.info("No coordinates available in this interval. Trends remain available.")
        if mode == "Concentration heatmap" and (mapped.value < 0).any():
            st.info("This interval contains negative values; showing ZIP markers instead of a concentration heatmap.")
            render_mode = "ZIP markers"
        scale_values = series[series.zip.isin(filtered.dropna(subset=["latitude", "longitude"]).zip)].value if fixed_scale else mapped.value
        limits = (float(scale_values.min()), float(scale_values.max())) if not scale_values.empty else None
        if limits and limits[0] == limits[1]:
            padding = abs(limits[0]) * 0.05 or 1
            limits = (limits[0] - padding, limits[1] + padding)
        fig = map_chart(mapped, render_mode, limits, states=states, view_data=filtered)
        st.plotly_chart(fig, width="stretch", on_select=add_map_selection if mode == "ZIP markers" else "ignore",
                        selection_mode="points", key=map_key)
    st.caption("Colors use only the current state/ZIP filters" + (" across all timeline intervals." if fixed_scale else " and the displayed interval; the scale can change as you slide.") + " Heatmap intensity blends nearby values and varies with zoom; it is not population per unit area. Empty intervals show no values.")
    st.caption("State outlines: U.S. Census Bureau, 2024 (generalized). ZIP boundaries are not included. Basemap © OpenStreetMap contributors © CARTO. ZIP centroids: GeoNames via pgeocode (CC BY 4.0).")
    st.subheader("Inspect ZIP codes")
    st.caption("Search or paste ZIPs to compare their histories. Clicking map markers adds ZIPs here. This selection affects only the comparison below; use the sidebar ZIP filter to filter the whole dashboard.")
    focus = zip_picker("Inspect ZIP codes", options, focus_key)
    if focus:
        focus_data = series[series.zip.isin(focus)]
        st.plotly_chart(px.line(focus_data, x="period", y="value", color="zip", markers=True, title=f"Selected ZIPs · {val_col}", labels={"value": str(val_col), "period": "Date", "zip": "ZIP"}), width="stretch")
    else:
        st.info("Select ZIP codes above or click map markers to compare their trends.")

with trends_tab:
    group = st.radio("Compare", ["zip", "state"], horizontal=True)
    lines = trends(filtered, frequency, method, group)
    st.plotly_chart(px.line(lines, x="period", y="value", color=group, markers=True,
                            labels={"value": str(val_col), "period": "Date"}), width="stretch")
    st.caption("Lines connect available observations; gaps do not mean zero. State curves sum the available ZIP values in each period; coverage can vary.")
    st.plotly_chart(px.bar(snapshot.sort_values("value", ascending=False).head(25), x="zip", y="value", color="value",
                           color_continuous_scale=COLORS, title=f"Top ZIPs · {period_label(period)}" ).update_xaxes(type="category"), width="stretch")
with table_tab:
    st.write("Observations in selected date range")
    st.dataframe(filtered, hide_index=True, width="stretch")
    st.download_button("Export filtered observations", filtered.to_csv(index=False), "ziptrend_observations.csv", "text/csv")
    st.download_button("Export displayed map interval", snapshot.to_csv(index=False), f"ziptrend_{period:%Y-%m-%d}.csv", "text/csv")

