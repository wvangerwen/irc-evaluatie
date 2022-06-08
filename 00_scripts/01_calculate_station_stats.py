# %%
import functions.folders as folders
import functions.station_cls as station_cls
import functions.fews_xml_reader as fews_xml_reader
import importlib
importlib.reload(folders)
importlib.reload(station_cls) #Reload folders to skip kernel reload.
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


# %% Resample data

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

irc_type='irc_early'
resample_rule='h'

#Initialize stations
wiwb_combined = station_cls.Wiwb_combined(folder=folder, wiwb_settings=WIWB_SETTINGS) #This can load the wiwb timeseries
stations_combined = station_cls.Stations_combined(folder=folder, organisations=organisations, wiwb_combined=wiwb_combined, resample_rule=resample_rule)
stations_combined.load_stations()
stations_combined.load_wiwb()


#Initialize WIWB
for station in stations_combined:
    print(station.code)
    break




# %% STATISTICS

class IrcStats():
    """Statistics per irc type"""
    def __init__(self, tsstats, irc_type):
        self.irc_type = irc_type
        self.residuals = tsstats.df[irc_type] - tsstats.df['station']
        self.gauge_mean = tsstats.df['station'].mean()
        self.irc_mean = tsstats.df[irc_type].mean()
        self.CV = round(tsstats.df['station'].std()/self.gauge_mean, 2) #?
        self.BiasTotal = self.residuals.mean()
        self.RelBiasTotal = round(self.BiasTotal/self.gauge_mean *100,2) #Relative bias %.

    def __repr__(self):
        return '.'+' .'.join([i for i in dir(self) if not i.startswith('__')])


class TsStats():
    """Load specific timeseries of station and plot their values and statistics. 
    self.df is the table with all relevant timeseries"""
    def __init__(self, station):
        self.station = station

        #Skip dates that dont have any (or enough) data
        self.df_yesdata = self.get_df_yesdata() #Filter table when True, we can use the value.
        self.df = self.station.df[self.df_yesdata].copy() #remove nodata rows

        #Classify the station timeseries
        self.classes = self.create_classes()
        self.df['class'] = self.df['station'].apply(self.classify_ts)

        #Statistics
        self.irc_stats={}
        for irc_type in self.station.irc_types:
            self.irc_stats[irc_type] = IrcStats(tsstats=self, irc_type=irc_type)
                

    def plot_scatter(self, irc_type):
        """Scatterplot comparing radar composite to ground station measurements"""
        #Init figure
        
        fig, ax=plt.subplots(figsize=[10,6])
        ax=plt.gca()

        # Plot values
        scatter = plt.scatter(x=self.df['station'], y=self.df[irc_type], c=self.df['class'])

        handles, labels = scatter.legend_elements() #TODO add number of features in certain class.
        labels = [self.classes.set_index('value').loc[int(re.findall(r'[0-9]+', i)[0])]['legend'] for i in labels] #Get legend label from dataframe based on the class.
        legend = ax.legend(handles, labels, loc="lower right", title="Class")
        ax.add_artist(legend)

        # set axes
        plt.xlim(xmin=0)
        plt.ylim(ymin=0)
        ax.grid()

        # straight line
        line = plt.plot(ax.get_xlim(), ax.get_xlim(), label='_nolegend_')

        #Add text        
        scatter_text = f"""CV = {self.irc_stats[irc_type].CV} \nRel. bias = {self.irc_stats[irc_type].RelBiasTotal}%"""

        plt.text(0.02, 0.98, scatter_text, horizontalalignment='left',
            verticalalignment='top', transform=ax.transAxes,
            bbox=dict(facecolor='white', alpha=0.9))


        fig.suptitle(f"{self.station.name} - {self.station.organisation}", fontsize=20)
        plt.title(f"{irc_type} - {self.station.resample_text}", y=1, fontsize=16)


        if self.station.resample_text=='1h':
            timestr = 'Uur'
        elif self.station.resample_text=='24h':
            timestr='Dag'
        plt.xlabel(f'{timestr}som regenmeter [mm]', fontsize=16)
        plt.ylabel(f'{timestr}som radar [mm]', fontsize=16)
 

    def create_classes(self):
        """Table used to classify the station p values"""
        classes = pd.DataFrame(columns=['value','range', 'legend'])

        if self.station.resample_text == '1h':
            classes.loc[len(classes)] = [0,[0, 0.1], '<0.1 mm']
            classes.loc[len(classes)] = [1,[0.1,4], '0.1-4 mm']
            classes.loc[len(classes)] = [2,[4,99999], '>4 mm']

        elif self.station.resample_text == '24h':
            classes.loc[len(classes)] = [0,[0, 0.1], '<0.1 mm']
            classes.loc[len(classes)] = [1,[0.1,5], '0.1-5 mm']
            classes.loc[len(classes)] = [2,[5,10], '5-10 mm']
            classes.loc[len(classes)] = [3,[10,99999], '>10 mm']
        return classes
        

    def classify_ts(self, x):
        """Return the value of the class based on measured value"""
        for index, row in self.classes.iterrows():
            if row['range'][0] <= x and x < row['range'][1]:
                return row['value'] #index value
        return None


    def get_df_yesdata(self):
        """Check if any input table has nodata, values are True when there is a value"""
        #Check missing values
        df_yesdata = self.station.df.notna()
        #Check negative values
        df_yesdata['abovezero'] = self.station.df['station'] >= 0
        #Check mask
        df_yesdata['mask'] = self.station.df['mask'] == False
        return df_yesdata.all(axis=1)
    

    def __repr__(self):
        return '.'+' .'.join([i for i in dir(self) if not i.startswith('__')])


self=TsStats(station)

# self.plot_scatter()

# %%

