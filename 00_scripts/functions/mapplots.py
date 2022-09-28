import geopandas as gpd
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.io as pio
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

pio.renderers.default = "notebook"
px.set_mapbox_access_token(
    "pk.eyJ1IjoidGhvbWFzZGV1ciIsImEiOiJja3FtMzQwaWkwOHF6MnZsaTM4M3BlcXRnIn0.2xsdzK4AO26jfoTrQGF_RQ"
)

gdf = gpd.read_file("../01_data/ground_stations_stats.gpkg")
gdf = gdf.to_crs(4326)


def getcolordict(bins):
    n = len(bins - 1)
    cmap = plt.cm.get_cmap("coolwarm", n)
    color_list = [mcolors.rgb2hex(cmap(i)) for i in range(cmap.N)]

    bins = pd.cut(bins, bins=bins).astype(str)
    colordict = {bin: color for bin, color in zip(bins[1:], color_list)}
    colordict["outlier"] = "black"
    return colordict


def returntitle(col):
    coltotitle = {
        "bias_cumu_irc_final_d": "BIAS Cumulatief (%); IRC Final",
        "bias_irc_realtime_d": "BIAS (%); IRC Realtime",
        "bias_irc_early_d": "BIAS (%); IRC Early Reanalysis",
        "bias_irc_final_d": "BIAS (%); IRC Final Reanalysis",
    }
    return coltotitle.get(col)


def mapplot(gdf, column):
    bins = np.arange(-50, 60, 10)  # -50 tot +50 als color-range
    colordict = getcolordict(bins)
    gdf["mybins"] = pd.cut(gdf[column], bins=bins)
    gdf["mybinsstr"] = gdf["mybins"].astype(str).replace("nan", "outlier")
    gdf = gdf.sort_values(by="mybins")
    title = returntitle(column)
    bins = gdf[~gdf.mybinsstr.str.contains("outlier")]
    outliers = gdf[gdf.mybinsstr.str.contains("outlier")]
    fig = px.scatter_mapbox(
        bins,
        lat=bins.geometry.y,
        lon=bins.geometry.x,
        color="mybinsstr",
        color_discrete_map=colordict,
        hover_name="ID",
        hover_data=["WEERGAVENAAM", "organisation", "Type", column],
        labels={"mybinsstr": "BIAS in bins (%)", column: title},
        title=title,
        zoom=6,
    )
    figoutlier = px.scatter_mapbox(
        outliers,
        lat=outliers.geometry.y,
        lon=outliers.geometry.x,
        hover_name="ID",
        hover_data=["WEERGAVENAAM", "organisation", "Type", column],
        labels={"mybinsstr": "BIAS in bins (%)", column: title},
        title=title,
        zoom=6,
    )
    figoutlier.update_traces(marker=dict(symbol="triangle", color="grey", size=8))
    figoutlier["data"][0]["showlegend"] = True
    figoutlier["data"][0]["name"] = "Outlier"
    fig.update_traces(marker=dict(size=10))
    fig.add_trace(figoutlier.data[0])
    fig.update_layout(margin=dict(l=0, r=0, b=0, t=50))

    return fig


def plotirc():
    figs = []
    cols = [
        "bias_cumu_irc_final_d",
        "bias_irc_realtime_d",
        "bias_irc_early_d",
        "bias_irc_final_d",
    ]
    for col in cols:
        figs.append(mapplot(gdf, col))
    return figs, cols
