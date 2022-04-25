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
    if row['ID'] =='MPN-AS-2371':
        break
#Init station
station = station_cls.Station(folder, row)

#TODO raw data staat in de gitignore. Dus dit stukje hieronder gaat niet werken. 
#Load raw
p_raw = station.load_ts_raw()

#Resample
df_p = {}
df_p['1h'] = p_raw['value'].resample('h').sum()
df_p['24h']= p_raw['value'].resample('d').sum()

# Write to file
station.to_file(df=df_p['1h'], output_path=station.path['station']['1h'])
station.to_file(df=df_p['24h'], output_path=station.path['station']['24h'])

# %% CREATE TEST DATASET OF IRC RESULTS

print('Creating test dataset')
for index, data_type in enumerate(['irc_realtime_current',
    'irc_realtime_beta_202201',
    'irc_realtime_beta_202204',
    'irc_final_current',
    'irc_final_beta_202204']):
    for time_resolution in ['1h', '24h']:

        df= df_p[time_resolution].copy()

        df= df * float(f"1.{index+1}") #Multiply original values by 1.1, 1.2, etc
        station.to_file(df = df, output_path=station.path[data_type][time_resolution])

# %% STATISTICS


class TsStats():
    """Load specific timeseries of station and plot their values and statistics. """
    def __init__(self, station, time_resolution='1h'):
        self.station = station
        self.data_type_irc = 'irc_realtime_current'
        self.time_resolution = time_resolution
        self.df_station = station.load_ts(data_type='station', time_resolution=self.time_resolution)
        self.df_irc = station.load_ts(data_type=self.data_type_irc, time_resolution=self.time_resolution)


        #Classify the station timeseries
        self.classes = self.create_classes()
        self.df_class = self.df_station['value'].apply(self.classify_ts)

        #Skip dates that dont have any (or enough) data
        self.df_nodata = self.get_df_nodata()
        self.remove_nodata_rows()

        #Statistics
        self.residuals = self.df_irc['value'] - self.df_station['value']
        self.gauge_mean = self.df_station['value'].mean()
        self.irc_mean = self.df_irc['value'].mean()
        self.CV = round(self.df_station['value'].std()/self.gauge_mean, 2) #?
        self.BiasTotal = self.residuals.mean()
        self.RelBiasTotal = round(self.BiasTotal/self.gauge_mean *100,2) #Relative bias
        

    def plot_scatter(self):
        """Scatterplot comparing radar composite to ground station measurements"""
        #Init figure
        
        fig, ax=plt.subplots(figsize=[10,6])
        ax=plt.gca()

        # Plot values
        scatter = plt.scatter(x=self.df_station['value'], y=self.df_irc['value'], c=self.df_class)

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
        scatter_text = f"""CV = {self.CV} \nRel. bias = {self.RelBiasTotal}%"""

        plt.text(0.02, 0.98, scatter_text, horizontalalignment='left',
            verticalalignment='top', transform=ax.transAxes,
            bbox=dict(facecolor='white', alpha=0.9))

        fig.suptitle(f"{self.station.name} - {self.station.organisation}", fontsize=20)
        plt.title(f"{self.data_type_irc} - {self.time_resolution}", y=1, fontsize=16)


        if self.time_resolution=='1h':
            timestr = 'Uur'
        elif self.time_resolution=='24h':
            timestr='Dag'
        plt.xlabel(f'{timestr}som regenmeter [mm]', fontsize=16)
        plt.ylabel(f'{timestr}som radar [mm]', fontsize=16)
 

    def create_classes(self):
        """Table used to classify the station p values"""
        classes = pd.DataFrame(columns=['value','range', 'legend'])

        if self.time_resolution == '1h':
            classes.loc[len(classes)] = [0,[0, 0.1], '<0.1 mm']
            classes.loc[len(classes)] = [1,[0.1,4], '0.1-4 mm']
            classes.loc[len(classes)] = [2,[4,99999], '>4 mm']

        elif self.time_resolution == '24h':
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

    def get_df_nodata(self):
        """Check if any input table has nodata"""
        #TODO check for negative values? For the test dataset this is already done in station.load_ts_raw
        return self.df_station.notna() | self.df_irc.notna()
    
    def remove_nodata_rows(self):
        """Filter nodata values"""
        self.df_station = self.df_station[self.df_nodata]
        self.df_irc = self.df_irc[self.df_nodata]
        self.df_class = self.df_class[self.df_nodata['value']]


self=TsStats(station)

self.plot_scatter()

# %%

