# %%
import functions.wiwb as wiwb
import pandas as pd
import plotly.express as px
import geopandas as gpd

from datetime import datetime, timedelta
import datetime

import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

import os
os.environ["WIWB_USERNAME"] = "wsbd"
os.environ["WIWB_PASSWORD"] = "4B83lSttDBity1kBtYzO"



start_date = datetime.datetime(2022,1,1)
end_date= datetime.datetime(2022,6,1)

locs = gpd.read_file("../01_data/ground_stations.gpkg")
locs = locs[locs['use']==True]

DATA_SOURCES = {'irc_realtime':"KNMI IRC Realtime",
                'irc_early':"KNMI IRC Early Reanalysis",
                'irc_final':"KNMI IRC Final Reanalysis"}

MAX_END_DATE = {'irc_realtime':datetime.datetime.now() - datetime.timedelta(hours=1),
                'irc_early':datetime.datetime.now() - datetime.timedelta(days=4),
                'irc_final':datetime.datetime.now() - datetime.timedelta(days=30)}

ORGANISATIONS=['HHNK', 'HDSR', 'WL', 'HEA']
# ORGANISATIONS=['HEA']

# %%

for organisation in ORGANISATIONS:
    locs_organisation = locs[locs['organisation']==organisation]
    points, extent = wiwb.get_points_from_gdf(locs_organisation)


    df_wiwb_all = {}
    for data_source in DATA_SOURCES:
        output_path = f"../01_data/p_raw_wiwb/{organisation}_{data_source}_raw_{start_date.strftime('%Y-%m-%d')}_{end_date.strftime('%Y-%m-%d')}.parquet"
        if not os.path.exists(output_path):
            print(f"Starting {organisation} - {data_source}")
            current = start_date
            df_wiwb = pd.Series(dtype="float64")

            while current < end_date:
                end = current + datetime.timedelta(days=10)
                if end < MAX_END_DATE[data_source]:
                    print(f"    downloading from {current} to {end}", end="\r")

                    try:
                        df_temp = wiwb.download_wiwb(data_source=DATA_SOURCES[data_source], 
                                                    points=points, 
                                                    start=current, 
                                                    end=end, 
                                                    extent=extent)
                    except:
                        continue

                    if df_wiwb.empty:
                        df_wiwb = df_temp.copy()
                    else:
                        df_wiwb = df_wiwb.append(df_temp)

                current = end

            df_wiwb_all[data_source] = df_wiwb.copy()

    
            pd.DataFrame(df_wiwb_all[data_source]).to_parquet(output_path)
print('DONE')
