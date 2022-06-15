# %%
import functions.wiwb as wiwb
import pandas as pd
import plotly.express as px
import geopandas as gpd

from datetime import datetime, timedelta
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

import os
os.environ["WIWB_USERNAME"] = "wsbd"
os.environ["WIWB_PASSWORD"] = "4B83lSttDBity1kBtYzO"


# %%

start = datetime(2021,6,1)


locs = gpd.read_file("../01_data/ground_stations.gpkg")
locs = locs[locs['use']==True]
points, extent = wiwb.get_points_from_gdf(locs)
wiwb_realtime = pd.Series(dtype="float64")
wiwb_early = pd.Series(dtype="float64")
wiwb_final = pd.Series(dtype="float64")

# %%
current = start
while current < datetime(2022,6,1):
    end = current + timedelta(days=10)
    print(f"downloading from {current} to {end}", end="\r")

    try:
        df_realtime = wiwb.download_wiwb(data_source="KNMI IRC Realtime", 
                                    points=points, 
                                    start=current, 
                                    end=end, 
                                    extent=extent)
    except:
        continue

    if wiwb_realtime.empty:
        wiwb_realtime = df_realtime.copy()
    else:
        wiwb_realtime = wiwb_realtime.append(df_realtime)

    try:
        df_early = wiwb.download_wiwb("KNMI IRC Early Reanalysis", points, current, end, extent)
    except:
        continue
    if wiwb_early.empty:
        wiwb_early = df_early.copy()
    else:
       wiwb_early = wiwb_early.append(df_early)

    try:
        df_final = wiwb.download_wiwb("KNMI IRC Final Reanalysis", points, current, end, extent)
    except:
        continue
    if wiwb_final.empty:
        wiwb_final = df_final.copy()
    else:
        wiwb_final = wiwb_final.append(df_final)

    current = end

# %%

pd.DataFrame(wiwb_realtime).to_parquet(f"../01_data/p_raw_wiwb/irc_realtime_raw_{start.strftime('%Y-%m-%d')}_{end.strftime('%Y-%m-%d')}.parquet")
pd.DataFrame(wiwb_early).to_parquet(f"../01_data/p_raw_wiwb/irc_early_raw_{start.strftime('%Y-%m-%d')}_{end.strftime('%Y-%m-%d')}.parquet")
pd.DataFrame(wiwb_final).to_parquet(f"../01_data/p_raw_wiwb/irc_final_raw_{start.strftime('%Y-%m-%d')}_{end.strftime('%Y-%m-%d')}.parquet")
# %%
