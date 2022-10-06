# %%
from symbol import except_clause
import sys
from warnings import filterwarnings

for x in [
    "C:/Users/wvangerwen/AppData/Roaming/3Di/QGIS3/profiles/default/python/plugins/hhnk_threedi_plugin/external-dependencies",
    "C:/Users/wvangerwen/AppData/Roaming/3Di/QGIS3/profiles/default/python",
    "C:/Users/wvangerwen/AppData/Roaming/3Di/QGIS3/profiles/default/python/plugins/ThreeDiToolbox/deps",
]:
    try:
        sys.path.remove(x)
    except:
        print(f"not in path: {x}")
import functions.folders as folders
import functions.station_cls as station_cls
import functions.station_statistics as station_statistics
import functions.irc_settings as irc_settings

import importlib

importlib.reload(folders)
importlib.reload(station_cls)  # Reload folders to skip kernel reload.
importlib.reload(station_statistics)
importlib.reload(irc_settings)
import pandas as pd
import geopandas as gpd
import os
import matplotlib.pyplot as plt

import numpy as np
from functools import reduce

RESAMPLE_TEXT = {"h": "1h", "d": "24h"}

folder = folders.Folders(os.pardir)  # create folder structure from parent dir.


# Alle stations in ruwe data.
# Hier alle stations met bijhorende metadata in plaatsen. De bijhorende timeseries moeten
# de naamgeving volgen die in folders.InputPath zijn gedefineerd.
stations_df = gpd.read_file(folder.input.ground_stations.path)

settings_all = irc_settings.IrcSettings(folder=folder)

#%%
# Combine stations into one df
organisations = ["HHNK", "HDSR", "WL", "HEA", "WF"]

gdf = station_cls.Stations_combined(
    folder=folder,
    organisations=[],
    wiwb_combined=None,
    resample_rule="d",
    settings_all=None,
).stations_df.copy()
gdf.set_index("ID", inplace=True)

stations_stats = {}
for resample_rule in ["d", "h"]:

    # Initialize stations
    wiwb_combined = station_cls.Wiwb_combined(
        folder=folder, settings=settings_all.wiwb
    )  # This can load the wiwb timeseries
    stations_combined = station_cls.Stations_combined(
        folder=folder,
        organisations=organisations,
        wiwb_combined=wiwb_combined,
        resample_rule=resample_rule,
        settings_all=settings_all,
    )
    stations_combined.load_stations()
    stations_combined.load_wiwb()

    # Calculate statistics per station.
    stations_stats[resample_rule] = {}
    for station in stations_combined:
        print(station.code)
        # if station.code == "TML0109405": #Testen met 1 station.
        stations_stats[resample_rule][station.code] = station_statistics.StationStats(
            station
        )


# %%
# Combine statistics of all stations in geodataframe

for resample_rule in ["d", "h"]:
    for code in stations_stats[resample_rule]:
        station_stats = stations_stats[resample_rule][code]

        for irc_type in station_stats.station.irc_types:
            gdf.at[code, f"bias_{irc_type}_{resample_rule}"] = station_stats.irc_stats[
                irc_type
            ].RelBiasTotal
            if irc_type == "irc_final":
                gdf.at[
                    code, f"bias_cumu_{irc_type}_{resample_rule}"
                ] = station_stats.irc_stats[irc_type].RelBiasTotalCumu

            # gdf.loc[code, f"stdev_{irc_type}_{resample_rule}"] = station_stats.irc_stats[irc_type].stdev
            # gdf.loc[code, f"stat_corr_{irc_type}"] = station_stats.irc_stats[irc_type].corr

    # Save to file
    gdf.to_file(f"../01_data/ground_stations_stats.gpkg", driver="GPKG")

# %%
from matplotlib.gridspec import GridSpec

idx = pd.IndexSlice
fig = plt.figure(figsize=(11, 16))
gs = GridSpec(4, 2, figure=fig)


for code in stations_stats[resample_rule]:
    print(code)
    fig.suptitle(f"{code}", fontsize=20)
    station_stats = stations_stats[resample_rule][code]

    for i, irc_type in enumerate(settings_all.wiwb.keys()):
        for j, resample_rule in enumerate(["h", "d"]):
            ax = fig.add_subplot(gs[i, j])
            station_stats = stations_stats[resample_rule][code]
            station_stats.plot_scatter_ax(irc_type=irc_type, ax=ax)

    stats = ["bias", "stdev"]
    time = ["h", "d"]

    indexes = pd.MultiIndex.from_product([stats, time], names=["stats", "agg"])
    columns = ["irc_realtime", "irc_early", "irc_final"]
    dfstats = pd.DataFrame(columns=columns, index=indexes)
    for irc in columns:
        for stat in stats:
            for t in time:
                dfstats.loc[idx[stat, t], irc] = round(
                    gdf.loc[code, f"{stat}_{irc}_{t}"], 2
                )
    dfstats = dfstats.reset_index(level=1)

    axtable = plt.subplot(gs[3, :])
    table = axtable.table(
        cellText=dfstats.values,
        colLabels=dfstats.columns,
        rowLabels=dfstats.index,
        cellLoc="center",
        loc="upper left",
    )

    axtable.axis("off")  # remove graph
    axtable.set_title(f"Statistieken: {code}", fontweight="bold")  # set title
    plt.tight_layout()

    fig.savefig(f"../02_img/{code}.png")

    plt.clf()


