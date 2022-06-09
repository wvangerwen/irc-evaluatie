# %%
import functions.folders as folders
import functions.station_cls as station_cls
import functions.station_statistics as station_statistics
import functions.fews_xml_reader as fews_xml_reader
import importlib
importlib.reload(folders)
importlib.reload(station_cls) #Reload folders to skip kernel reload.
importlib.reload(station_statistics)
import pandas as pd
import geopandas as gpd
import os
import matplotlib.pyplot as plt
import re
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
                    {'raw_filepath': folder.input.paths['station']['raw'].full_path('WL_neerslagdata_202205141515_5min.xml')}
                }

WIWB_SETTINGS = {'irc_early':
                    {'raw_filepath':folder.input.paths['wiwb']['raw'].full_path('HHNK_HDSR_WL_irc_early_2022-05-21_2022-05-21.parquet')},
                'irc_realtime':
                    {'raw_filepath':folder.input.paths['wiwb']['raw'].full_path('HHNK_HDSR_WL_irc_realtime_2022-05-21_2022-05-21.parquet')},
                }


# Resample data

#Station 
for organisation in ORG_SETTINGS:
    stations_organisation = station_cls.Stations_organisation(folder=folder,          
                                organisation=organisation)

    #Resample timeseries to hour and day values.
    locations = stations_organisation.resample(**ORG_SETTINGS[organisation], overwrite=False)

    #Add locations from xml to the gpkg
    stations_organisation.add_xml_locations_to_gpkg(locations)

#Wiwb
wiwb_combined = station_cls.Wiwb_combined(folder=folder, wiwb_settings=WIWB_SETTINGS)
wiwb_combined.resample(overwrite=True)


# %% LOAD ALL TIMESERIES

#Combine stations into one df
organisations=['HHNK', 'HDSR', 'WL']

resample_rule='d'

#Initialize stations
wiwb_combined = station_cls.Wiwb_combined(folder=folder, wiwb_settings=WIWB_SETTINGS) #This can load the wiwb timeseries
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

gdf = stations_combined.stations_df.copy()
gdf.set_index('ID', inplace=True)


for code in stations_stats:
    station_stats = stations_stats[code]

    for irc_type in station_stats.station.irc_types:
        gdf.loc[code, f'rel_bias_{irc_type}'] = station_stats.irc_stats[irc_type].RelBiasTotal


#  plot some station statistics of indiviual station
for code in stations_stats:
    station_stats = stations_stats[code]
    station_stats.plot_scatter(irc_type = 'irc_early')
    