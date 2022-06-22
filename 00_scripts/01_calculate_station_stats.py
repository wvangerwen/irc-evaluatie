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

WIWB_SETTINGS = {'irc_realtime':
                    {'raw_filepaths':folder.input.paths['wiwb']['raw'].pl.glob('*irc_realtime*.parquet')},
                 'irc_early':
                    {'raw_filepaths':folder.input.paths['wiwb']['raw'].pl.glob('*irc_early*.parquet')},
                'irc_final':
                   {'raw_filepaths':folder.input.paths['wiwb']['raw'].pl.glob('*irc_final*.parquet')},
                }

# %%
# Resample data

#Station 
for organisation in ORG_SETTINGS:
# for organisation in ['HHNK']:
    stations_organisation = station_cls.Stations_organisation(folder=folder,          
                                organisation=organisation,
                                settings=ORG_SETTINGS[organisation])

    #Resample timeseries to hour and day values.
    locations = stations_organisation.resample(overwrite=False)

    #Add locations from xml to the gpkg
    stations_organisation.add_locations_to_gpkg(locations)

#Wiwb
wiwb_combined = station_cls.Wiwb_combined(folder=folder, settings=WIWB_SETTINGS)
wiwb_combined.resample(overwrite=True)



#%%
#Combine stations into one df
organisations=['HHNK', 'HDSR', 'WL', 'HEA']

gdf = station_cls.Stations_combined(folder=folder, organisations=[], wiwb_combined=None, resample_rule='d').stations_df.copy()
gdf.set_index('ID', inplace=True)

stations_stats = {}
for resample_rule in ["d", "h"]:

    #Initialize stations
    wiwb_combined = station_cls.Wiwb_combined(folder=folder, settings=WIWB_SETTINGS) #This can load the wiwb timeseries
    stations_combined = station_cls.Stations_combined(folder=folder, organisations=organisations, wiwb_combined=wiwb_combined, resample_rule=resample_rule)
    stations_combined.load_stations()
    stations_combined.load_wiwb()


    #Calculate statistics per station.
    stations_stats[resample_rule]={}

    for station in stations_combined:
        # if station.code == 'MPN-A-4156': #Testen met 1 station.
        if True:
            stations_stats[resample_rule][station.code] = station_statistics.StationStats(station)
            # break

# %%
# Combine statistics of all stations in geodataframe
for resample_rule in ["d", "h"]:

    for code in stations_stats[resample_rule]:
        station_stats = stations_stats[resample_rule][code]


        for irc_type in station_stats.station.irc_types:
            gdf.loc[code, f'stat_rel_bias_{irc_type}_{resample_rule}'] = station_stats.irc_stats[irc_type].RelBiasTotal
            gdf.loc[code, f'stat_rel_bias_cumu_{irc_type}_{resample_rule}'] = station_stats.irc_stats[irc_type].relbiastotalcumu
            gdf.loc[code, f'stat_stdev_{irc_type}_{resample_rule}'] = station_stats.irc_stats[irc_type].stdev
            gdf.loc[code, f'stat_corr_{irc_type}'] = station_stats.irc_stats[irc_type].corr

# Save to file
gdf.to_file(f"../01_data/ground_stations_stats.gpkg", driver="GPKG")

# %%
plt.ioff()

for code in stations_stats[resample_rule]:
    print(code)
    for resample_rule in ["d", "h"]:
    #  plot some station statistics of indiviual station
        for irc_type in WIWB_SETTINGS.keys():
            station_stats = stations_stats[resample_rule][code]
            fig = station_stats.plot_scatter(irc_type=irc_type)
            fig.savefig(f"../02_img/{irc_type}/{code}_{resample_rule}.png")
            
            plt.close(fig)

# %%
