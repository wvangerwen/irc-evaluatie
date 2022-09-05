import matplotlib.pyplot as plt
import pandas as pd
import re

class IrcStats():
    """Statistics per irc type"""
    def __init__(self, stationstats, irc_type):
        self.stationstats = stationstats

        self.irc_type = irc_type
        self.residuals = stationstats.df[irc_type] - stationstats.df['station']
        self.gauge_mean = stationstats.df['station'].mean()
        self.irc_mean = stationstats.df[irc_type].mean()
         #?
        self.BiasTotal = self.residuals.mean()
        self.gauge_cumu = stationstats.df['station'].cumsum()
        self.irc_cumu = stationstats.df[irc_type].cumsum()
        self.biastotalcumu = (self.irc_cumu - self.gauge_cumu).mean()
        self.corr = round(stationstats.df['station'].corr(stationstats.df[irc_type]), 2)
        self.stdev = self.residuals.std()

        if self.gauge_mean==0:
            self.CV = 0
            self.RelBiasTotal = 0   
        else: 
            self.CV = round(stationstats.df['station'].std()/self.gauge_mean, 2)
            self.RelBiasTotal = round(self.BiasTotal/self.gauge_mean * 100, 1) #Relative bias %.
            
        if self.gauge_cumu.mean()==0:
            self.relbiastotalcumu = 0
        else:
            self.relbiastotalcumu =  round(self.biastotalcumu / self.gauge_cumu.mean() * 100, 1)


    def __repr__(self):
        return '.'+' .'.join([i for i in dir(self) if not i.startswith('__')])


class StationStats():
    """Statistics calculation for a station with timeseries already loaded. 
    self.df is the table with all relevant timeseries
    
    station -> Station() defined in station_cls.py. Obtained by looping over station_cls.Stations_combined
    e.g. for station in stations_combined:"""
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
            self.irc_stats[irc_type] = IrcStats(stationstats=self, irc_type=irc_type)
                

    def plot_scatter(self, irc_type):
        """Scatterplot comparing radar composite to ground station measurements"""
        #Init figure
        
        fig, ax = plt.subplots(figsize=[10,6])
        ax = plt.gca()

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
        return fig

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