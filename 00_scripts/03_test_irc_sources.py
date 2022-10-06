
# %% start is same as 02_calculation_station_stats
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
# Check with FEWS



def load_df(fpath, colname=None, skiprows=0, sep=";"):
    df = pd.read_csv(folder.input.full_path(fpath), sep=sep, skiprows=skiprows)
    if "Unnamed: 2" in df.keys():
        df=df.drop("Unnamed: 2",axis=1)

    df.rename({"Unnamed: 0":"CET/CEST"},axis=1,inplace=True)
    if colname:
        df.rename({"RadarSpatialInterpolation":colname},axis=1,inplace=True)
        try:
            df=df.drop("RadarSpatialInterpolation.1", axis=1)
        except:
            pass
        # df=df.replace(",",".")
        df[colname] =  df[colname].str.replace(",",".").astype(float)

    df["datetime"] = pd.to_datetime(
                    df["CET/CEST"], format="%d-%m-%Y %H:%M"
                )

    df.set_index("datetime", inplace=True)
    df=df.drop("CET/CEST", axis=1)


    df = df.tz_localize("CET", ambiguous="infer").tz_convert("UTC")
    df = df.tz_localize(None)  # remove tz info so we can merge.

    return df

station_code = "mpn-as-2371"
# station_code = "mpn-a-4156"
# station_code = "mpn-as-2416"
# station_code = "mpn-as-2418"




#Load files
# df_m = load_df(fpath=f"test_irc_sources/test_{station_code}_meting1min.csv")
# df_r5m = load_df(fpath=f"test_irc_sources/test_{station_code}_radar5min.csv", colname="radar5min", skiprows=4, sep="\t")
df_r5m_raw = load_df(fpath=f"test_irc_sources/test_{station_code}_radar5min_final_raw.csv", colname="radar5min_final_raw", skiprows=5, sep="\t")
# df_r1h = load_df(fpath=f"test_irc_sources/test_{station_code}_radar1h.csv", colname="radar1h", skiprows=4, sep="\t")
df_r1h_raw = load_df(fpath=f"test_irc_sources/test_{station_code}_radar1h_final_raw.csv", colname="radar1h_final_raw", skiprows=5, sep="\t")
# df_r24h = load_df(fpath=f"test_irc_sources/test_{station_code}_radar24h.csv", colname="radar24h", skiprows=4, sep="\t")

resample_rule = "d"
# df_mr = df_m.resample(resample_rule).sum()
# df_r5mr = df_r5m.resample(resample_rule).sum()
df_r5mr_raw = df_r5m_raw.resample(resample_rule).sum()
# df_r1hr = df_r1h.resample(resample_rule).sum()
df_r1hr_raw = df_r1h_raw.resample(resample_rule).sum()
# df_r24hr = df_r24h.resample(resample_rule).sum()
try:
    df_eval = stations_stats[resample_rule][station_code.upper()].df.loc[df_r1hr_raw.index] #Statistics from irc analysis
except:
    df_eval = stations_stats[resample_rule][station_code.upper()].df.loc[df_r1hr_raw.index[1:]] #Statistics from irc analysis

#Combine tables
df_merge = df_r5mr_raw
for df_temp in [df_r5mr, df_r1hr, df_r24hr, df_r1hr_raw, df_eval]:
# for df_temp in [df_r1hr_raw, df_eval]:
    df_merge = pd.merge(df_merge, df_temp, left_index=True, right_index=True)
df_merge

#Add cumsum as last row
summ = df_merge.cumsum().iloc[-1]
summ.name = "sum"
df_merge = df_merge.append(summ)

df_merge = df_merge.astype(float).round(2)
df_merge

print(station_code)
# df_merge[["station", "radar5min_final_raw", "radar1h_final_raw", "irc_final"]]
df_merge[['station', 'radar5min', 'radar1h', 'radar24h', 'radar5min_final_raw',
       'radar1h_final_raw', 'irc_realtime', 'irc_early',
       'irc_final', 'irc_realtime_beta',]]
# %%^

a=pd.read_parquet(r"E:\github\wvangerwen\irc-evaluatie\01_data\p_raw_wiwb\HDSR_irc_early_raw_2022-01-01_2022-06-01.parquet")