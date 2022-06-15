# %%
import functions.folders as folders
import functions.station_cls as station_cls
import functions.station_statistics as station_statistics
import importlib
importlib.reload(folders)
importlib.reload(station_cls) #Reload folders to skip kernel reload.
importlib.reload(station_statistics)
import pandas as pd
import geopandas as gpd
import os
import matplotlib.pyplot as plt
import re
import itertools
import numpy as np
from functools import reduce

RESAMPLE_TEXT = {'h':'1h',
                'd':'24h'}


folder = folders.Folders(os.pardir) #create folder structure from parent dir. 


#Alle stations in ruwe data.
# Hier alle stations met bijhorende metadata in plaatsen. De bijhorende timeseries moeten
# de naamgeving volgen die in folders.InputPath zijn gedefineerd. 
stations_df = gpd.read_file(folder.input.ground_stations.path)


ORG_SETTINGS = {'HHNK':
                    {'raw_filepath': folder.input.paths['station']['raw'].full_path('HHNK_neerslagmeters_20220101_20220513_1min.csv'),
                    'skiprows': 0,
                    'sep': ';',
                    'date_col':'Unnamed: 0'},
                'HDSR':
                    {'raw_filepath': folder.input.paths['station']['raw'].full_path('HDSR_neerslagdata_2022_5min.xml')},
                'WL':
                    {'raw_filepath': folder.input.paths['station']['raw'].full_path('WL_neerslagdata_202205141515_5min.xml')},
                'HEA':
                    {'raw_filepath': folder.input.paths['station']['raw'].full_path('HEA_P_2022'),
                    'skiprows': 9,
                    'sep': ';',
                    'date_col':'Timestamp',
                    'metadata_file': folder.input.full_path('HEA_P_metadata2.xlsx'),},
                }

WIWB_SETTINGS = {'irc_early':
                    {'raw_filepaths':folder.input.paths['wiwb']['raw'].pl.glob('*irc_early*.parquet')},
                'irc_realtime':
                    {'raw_filepaths':folder.input.paths['wiwb']['raw'].pl.glob('*irc_realtime*.parquet')},
                'irc_final':
                   {'raw_filepaths':folder.input.paths['wiwb']['raw'].pl.glob('*irc_final*.parquet')},
                }

# %%
# Resample data

#Station 
# for organisation in ORG_SETTINGS:
for organisation in ['HEA']:
    stations_organisation = station_cls.Stations_organisation(folder=folder,          
                                organisation=organisation,
                                settings=ORG_SETTINGS[organisation])

    #Resample timeseries to hour and day values.
    locations = stations_organisation.resample(overwrite=True)

    #Add locations from xml to the gpkg
    stations_organisation.add_locations_to_gpkg(locations)

#Wiwb
wiwb_combined = station_cls.Wiwb_combined(folder=folder, settings=WIWB_SETTINGS)
wiwb_combined.resample(overwrite=True)

# %%
self=stations_organisation

df_mask, df_value, locations = self.load_ts_raw()

for resample_rule in ['h', 'd']:
    #Resample
    df_value_resampled= pd.DataFrame(df_value.resample(resample_rule).sum())
    df_mask_resampled = pd.DataFrame(df_mask.resample(resample_rule).sum())

    #Recreate mask
    df_mask_resampled = df_mask_resampled != 0

    #Save to file
    df_value_resampled.to_parquet(self.out_path['value'][resample_rule])
    df_mask_resampled.to_parquet(self.out_path['mask'][resample_rule])

#%%
#Combine stations into one df
organisations=['HHNK', 'HDSR', 'WL', 'HEA']

gdf = station_cls.Stations_combined(folder=folder, organisations=[], wiwb_combined=None, resample_rule='d').stations_df.copy()
gdf.set_index('ID', inplace=True)

for resample_rule in ["d", "h"]:

    #Initialize stations
    wiwb_combined = station_cls.Wiwb_combined(folder=folder, settings=WIWB_SETTINGS) #This can load the wiwb timeseries
    stations_combined = station_cls.Stations_combined(folder=folder, organisations=organisations, wiwb_combined=wiwb_combined, resample_rule=resample_rule)
    stations_combined.load_stations()
    stations_combined.load_wiwb()


    #Calculate statistics per station.
    stations_stats = {}
    for station in stations_combined:
        # if station.code == 'MPN-A-4156': #Testen met 1 station.
        if True:
            stations_stats[station.code] = station_statistics.StationStats(station)
            # break

    # Combine statistics of all stations in geodataframe
    for code in stations_stats:
        station_stats = stations_stats[code]

# %%
        for irc_type in station_stats.station.irc_types:
            gdf.loc[code, f'rel_bias_{irc_type}_{resample_rule}'] = station_stats.irc_stats[irc_type].RelBiasTotal
    
    #  plot some station statistics of indiviual station
    # for irc_type in WIWB_SETTINGS.keys():
    for irc_type in ['irc_final']: 
        for code in stations_stats:
            station_stats = stations_stats[code]
            fig = station_stats.plot_scatter(irc_type=irc_type) #TODO hide fig
            fig.savefig(f"../02_img/{irc_type}/{code}_{resample_rule}.png")

gdf.to_file(f"../01_data/ground_stations_stats.gpkg", driver="GPKG")
    
# %%
self = stations_combined

for index, row in self.stations_df.iterrows():
    # if row['ID'] in self.df_value.columns:
        # self.get_station(self.folder, row)



    irc_types = [i for i in self.df_irc]
    dict_station = {}
    dict_station['station'] = self.df[row['ID']].rename('station')
    for irc_type in irc_types:
        dict_station[irc_type] = self.df_irc[irc_type][row['WEERGAVENAAM']].rename(irc_type)
    print(dict_station.keys())

    dict_station['mask'] = self.df_mask[row['ID']].rename('mask')


# %%
if True:
        dict_values={}
        dict_mask={}
        for organisation in self.stations_org:
            stat = self.stations_org[organisation]
            stat.load(resample_rule=self.resample_rule)

            dict_values[stat.organisation] = stat.df_value
            dict_mask[stat.organisation] = stat.df_mask

        self.df_value = self.merge_df_datetime(dict_df=dict_values)
        self.df_mask = self.merge_df_datetime(dict_df=dict_mask)
        self.df_mask = self.df_mask==True #Fill nanvalues.