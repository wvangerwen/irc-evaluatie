# %%

from zlib import DEFLATED
import functions.folders as folders
import functions.station_cls as station_cls
import importlib
importlib.reload(folders)
importlib.reload(station_cls) #Reload folders to skip kernel reload.
import functions.folders as folders
import pandas as pd
import geopandas as gpd
import os
import matplotlib.pyplot as plt
import re

folder = folders.Folders(os.pardir) #create folder structure from parent dir. 

#Alle stations in ruwe data.
# Hier alle stations met bijhorende metadata in plaatsen. De bijhorende timeseries moeten
# de naamgeving volgen die in folders.InputPath zijn gedefineerd. 
stations_df = gpd.read_file(folder.input.ground_stations.path)


# %%

for index, row in stations_df.iterrows():
    if row['ID'] =='MPN-A-4149':
        break
#Init station
station = station_cls.Station(folder, row)

#Load raw
p_raw = station.load_ts_raw()

#Resample
p_1h = p_raw['value'].resample('h').sum()
p_24h = p_raw['value'].resample('d').sum()

# Write to file
station.to_file(df=p_1h, output_path=station.path['station']['1h'])
station.to_file(df=p_24h, output_path=station.path['station']['24h'])



# %% STATISTICS


class TsStats():
    def __init__(self, station, time_resolution='1h'):
        self.station = station
        self.data_type_irc = 'irc_realtime_current'
        self.time_resolution = time_resolution
        self.df_station = station.load_ts(data_type='station', time_resolution=self.time_resolution)
        self.df_irc = station.load_ts(data_type=self.data_type_irc, time_resolution=self.time_resolution)

        #Classify the station timeseries
        self.df_class = self.create_df_class()
        self.classes = self.df_station['value'].apply(self.classify_ts)


        #Statistics
        self.residuals = self.df_irc['value'] - self.df_station['value']
        self.gauge_mean = self.df_station['value'].mean()
        self.irc_mean = self.df_irc['value'].mean()
        self.CV = self.df_station['value'].std()/self.gauge_mean #?
        self.BiasTotal = self.residuals.mean()
        self.RelBiasTotal = round(self.BiasTotal/self.gauge_mean *100,2)
        

    def plot_scatter(self):
        #Init figure
        fig, ax=plt.subplots(figsize=[10,10])
        ax=plt.gca()

        # Plot values
        scatter = plt.scatter(x=self.df_station['value'], y=self.df_irc['value'], c=self.classes)

        handles, labels = scatter.legend_elements()
        labels = [self.df_class.set_index('value').loc[int(re.findall(r'[0-9]+', i)[0])]['legend'] for i in labels] #Get legend label from dataframe based on the class.
        legend = ax.legend(handles, labels, loc="lower right", title="Class")
        ax.add_artist(legend)

        # set axes
        plt.xlim(xmin=0)
        plt.ylim(ymin=0)
        ax.grid()

        # straight line
        line = plt.plot(ax.get_xlim(), ax.get_xlim(), label='_nolegend_')

        #Add text        
        scatter_text = f"""CV = {self.CV} \nRel. bias = {self.RelBiasTotal}"""

        plt.text(0.02, 0.98, scatter_text, horizontalalignment='left',
            verticalalignment='top', transform=ax.transAxes,
            bbox=dict(facecolor='white', alpha=0.9))

        fig.suptitle(f"{self.station.name} - {self.station.organisation}", fontsize=20)
        plt.title(f"{self.data_type_irc} - {self.time_resolution}", y=1.05, fontsize=16)


        if self.time_resolution=='1h':
            timestr = 'Uur'
        elif self.time_resolution=='24h':
            timestr='Dag'
        plt.xlabel(f'{timestr}som regenmeter [mm]', fontsize=16)
        plt.ylabel(f'{timestr}som radar [mm]', fontsize=16)
 

    def create_df_class(self):
        """Table used to classify the station p values"""
        df_class = pd.DataFrame(columns=['value','range', 'legend'])

        if self.time_resolution == '1h':
            df_class.loc[len(df_class)] = [0,[0, 0.1], '<0.1 mm']
            df_class.loc[len(df_class)] = [1,[0.1,4], '0.1-4 mm']
            df_class.loc[len(df_class)] = [2,[4,99999], '>4 mm']

        elif self.time_resolution == '24h':
            df_class.loc[len(df_class)] = [0,[0, 0.1], '<0.1 mm']
            df_class.loc[len(df_class)] = [1,[0.1,5], '0.1-5 mm']
            df_class.loc[len(df_class)] = [2,[5,10], '5-10 mm']
            df_class.loc[len(df_class)] = [3,[10,99999], '>10 mm']
        return df_class
        

    def classify_ts(self, x):
        """Return the value of the class based on measured value"""
        for index, row in self.df_class.iterrows():
            if row['range'][0] < x and x < row['range'][1]:
                return row['value'] #index value
        return None

self=TsStats(station)


self.plot_scatter()
