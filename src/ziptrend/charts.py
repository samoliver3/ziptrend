try:
    import plotly.express as px
except ImportError as exc:
    raise ImportError('ziptrend.charts requires plotly. Install it with: pip install "ziptrend[app]"') from exc
from .geography import selected_boundaries, map_view

COLORS = ["#2466a8", "#67b7cb", "#e3e8ef", "#ec8eb6", "#ad164c"]


def map_chart(data, mode="ZIP markers", color_range=None, *, states=(), view_data=None):
    boundaries = selected_boundaries(states)
    center, zoom = map_view(data if view_data is None else view_data, boundaries)
    options = dict(lat="latitude", lon="longitude", center=center, zoom=zoom,
                   map_style="carto-positron", color_continuous_scale=COLORS,
                   range_color=color_range, height=530)
    if mode == "Concentration heatmap":
        fig = px.density_map(data, z="value", radius=32, hover_name="zip", **options)
    else:
        fig = px.scatter_map(data, color="value", hover_name="zip",
                             hover_data={"state": True, "value": ":,.2f", "latitude": False, "longitude": False},
                             custom_data=["zip"], **options)
        fig.update_traces(marker={"size": 15})
        fig.update_layout(clickmode="event+select")
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), coloraxis_colorbar_title="Value")
    if boundaries["features"]:
        # White halo keeps the dark state outline visible over both data and basemap.
        fig.update_layout(map_layers=[
            dict(sourcetype="geojson", source=boundaries, type="line", color="white", line=dict(width=5)),
            dict(sourcetype="geojson", source=boundaries, type="line", color="#18324d", line=dict(width=2.5)),
        ])
    return fig
