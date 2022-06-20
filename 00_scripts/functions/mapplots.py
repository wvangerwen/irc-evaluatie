import geopandas as gpd
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.io as pio
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

pio.renderers.default = "notebook"
px.set_mapbox_access_token('pk.eyJ1IjoidGhvbWFzZGV1ciIsImEiOiJja3FtMzQwaWkwOHF6MnZsaTM4M3BlcXRnIn0.2xsdzK4AO26jfoTrQGF_RQ')

gdf = gpd.read_file("../01_data/ground_stations_stats.gpkg")
gdf = gdf.to_crs(4326)

def getcolordict(bins, stat):
    n = len(bins - 1)
    if stat == "stdev":
        cmap = plt.cm.get_cmap("Reds", n)
    if stat == "corr":
        cmap = plt.cm.get_cmap("Greens", n)
    if stat == "bias":
        cmap = plt.cm.get_cmap("PiYG", n)        
    color_list = [mcolors.rgb2hex(cmap(i)) for i in range(cmap.N)]

    bins = pd.cut(bins, bins=bins).astype(str)
    colordict = {bin: color for bin, color in zip(bins[1:], color_list)}
    colordict["outlier"] = "grey"
    return colordict

def mapplot(gdf, column):
    if "stdev" in column:
        stat = "stdev"
        bins = np.arange(0, 1.1, 0.1)
        colordict = getcolordict(bins, stat)
    if "corr" in column:
        stat = "corr"
        bins = np.arange(0, 1.1, 0.1)
        colordict = getcolordict(bins, stat)
    if "bias" in column:
        stat = "bias"
        bins = np.arange(-50, 60, 10)
        colordict = getcolordict(bins, stat)
    gdf["mybins"] = pd.cut(gdf[column], bins=bins)
    gdf["mybinsstr"] = gdf["mybins"].astype(str).replace("nan", "outlier")
    gdf = gdf.sort_values(by="mybins")
    fig = px.scatter_mapbox(gdf, 
                            lat=gdf.geometry.y, 
                            lon=gdf.geometry.x, 
                            color="mybinsstr",
                            color_discrete_map=colordict,
                            hover_name="ID",
                            hover_data=["WEERGAVENAAM", "organisation", "Type", column],
                            labels={"mybinsstr": stat},
                            title=column.replace("_", " "),
                            zoom=6,
                            mapbox_style="dark"
                            )
    fig.update_layout(margin=dict(l=0,r=0,b=0,t=50))
    fig.update_traces(marker=dict(size=12))
    return fig

def plotirc(irc_type, stat):
    cols = [col for col in gdf.columns if irc_type in col and stat in col]
    figs = []
    for col in cols:
        figs.append(mapplot(gdf, col))
    return figs