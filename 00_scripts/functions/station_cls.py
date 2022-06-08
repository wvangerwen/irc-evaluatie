import pandas as pd
import os
import functions.fews_xml_reader as fews_xml_reader
from functools import reduce
import numpy as np
import geopandas as gpd
from pathlib import Path

class Station():
    """Individual station with related timeseries."""
    def __init__(self, folder, row, df_mask, df):
        self.row=row
        self.name = row['WEERGAVENAAM']
        self.code = row['ID']
        self.organisation = row['organisation']
        self.geometry = row['geometry']
        self.data_types = folder.input.data_types #['station', 'irc_realtime_current', 'irc_r...

        self.df_mask=df_mask
        self.df = df


    def __repr__(self):
        return '.'+' .'.join([i for i in dir(self) if not i.startswith('__')])

class Stations_organisation():
    """All stations of a single organisation with related timeseries."""
    def __init__(self, folder, organisation, ):
        self.organisation = organisation
        self.folder = folder

        self.out_path = self.set_out_path()

        # self.df_mask, self.df_value = self.load_ts_raw(date_col, skiprows, sep)
        
    def load_ts_raw(self, raw_filepath, skiprows=1, sep=';', date_col='Unnamed: 0') -> pd.DataFrame:
        """Load raw data. Returns a mask and value dataframe
        including all stations for that organisation #TODO only works for HHNK data."""

        if self.organisation=='HHNK':
            df = pd.read_csv(raw_filepath, sep=sep, skiprows=skiprows)#, parse_dates=[date_col])

            df.rename({date_col:'datetime', 
                        'P.meting.1m':'value',
                        'P.meting.1m quality':'flag'}, 
                        inplace=True,axis=1)

            #Set datetime as index
            df['datetime'] = pd.to_datetime(df['datetime'])
            df.set_index('datetime', inplace=True)

            df=df.iloc[1:] #Skip first row.

            # Create a mask df from the flags
            df_mask = df.iloc[:,1::2].copy() # flags

            #Replace string values with mask, to identify which timeseries we do use. 
            masked_values = {'original reliable': False,
                    'completed unreliable': True}
            df_mask.replace(masked_values, inplace=True)


            #Rename columns to match value df
            df_mask.columns = df_mask.keys().str.replace(' quality', '').values
            df_value = df.iloc[:,0::2].copy() # values

            #Set obtype to float
            def str_to_float(x):
                try: 
                    return float(x.replace(',', '.'))
                except:
                    return float(x)
            df_value = df_value.applymap(str_to_float)
            df_value.astype(float)

            #make sure negative values are masked
            df_mask = (df_value<0) | (df_mask)
            locations=None

        if self.organisation in ['HDSR', 'WL']:
            df_value, df_flag, locations = fews_xml_reader.fews_xml_to_df(raw_filepath)

            if len(df_value.columns.levels[1])!= 1:
                raise Exception('More than one parameter in the xml. Not implemented.')

            #Drop parameter column from multiindex
            df_value = df_value.droplevel(level=1, axis=1)
            df_flag = df_flag.droplevel(level=1, axis=1)

            df_mask = df_flag != 0

        return df_mask, df_value, locations

    def set_out_path(self):
        """set output paths of resampled dataframes"""
        RESAMPLE_TEXT = {'h':'1h',
                        'd':'24h'}

        out_path = {}
        out_path['value']={}
        out_path['mask']={}
        for resample_rule in ['h', 'd']:
            out_path['value'][resample_rule] = self.folder.input.paths['station']['resampled'].full_path(f'{self.organisation}_p_{RESAMPLE_TEXT[resample_rule]}.parquet')
            out_path['mask'][resample_rule] = self.folder.input.paths['station']['resampled'].full_path(f'{self.organisation}_mask_{RESAMPLE_TEXT[resample_rule]}.parquet')
        return out_path

    def resample(self, raw_filepath, skiprows=None, sep=None, date_col=None, overwrite=True):
        """Resample measured values to hour and day data. Save to file"""

        cont = [True]
        #First check if all output already exists
        if overwrite==False:
            for resample_rule in ['h', 'd']:
                if os.path.exists(self.out_path['value'][resample_rule]):
                    cont.append(False)

        if np.all(cont) == True:
            #Load raw values
            df_mask, df_value, locations = self.load_ts_raw(raw_filepath=raw_filepath, 
                                                    skiprows=skiprows, 
                                                    sep=sep, 
                                                    date_col=date_col)

            for resample_rule in ['h', 'd']:
                #Resample
                df_value_resampled= pd.DataFrame(df_value.resample(resample_rule).sum())
                df_mask_resampled = pd.DataFrame(df_mask.resample(resample_rule).sum())

                #Recreate mask
                df_mask_resampled = df_mask_resampled != 0

                #Save to file
                df_value_resampled.to_parquet(self.out_path['value'][resample_rule])
                df_mask_resampled.to_parquet(self.out_path['mask'][resample_rule])
            return locations


    def load(self, resample_rule='h'):
        """Load timeseres from file"""
        self.df_value = pd.read_parquet(self.out_path['value'][resample_rule])
        self.df_mask = pd.read_parquet(self.out_path['mask'][resample_rule])


    #Toevoegen locaties van xml aan de gpkg
    def add_xml_locations_to_gpkg(self, locations):
        """Add locations from xml to the stations gpkg"""
        stations_df = gpd.read_file(self.folder.input.ground_stations.path)
        if locations: #For HHNK the locations are None
            stations_df_orig = stations_df.copy()
            for loc in locations:
                loc = locations[loc]
                if loc.loc_id not in stations_df['ID'].values:
                    stations_df=stations_df.append({'WEERGAVENAAM':loc.name,
                                    'ID':loc.loc_id,
                                    'organisation':self.organisation,
                                    'use':True,
                                    'geometry':loc.geometry,
                                    }, ignore_index=True)

            if len(stations_df_orig) != len(stations_df):
                print(f'Update ground stations gpkg -- {self.folder.input.ground_stations.path}')
                stations_df.to_file(self.folder.input.ground_stations.path, driver='GPKG')     


class Stations_combined():
    """Class that combines the resampled timeseries of all organisations."""
    def __init__(self, folder, organisations, wiwb_combined):
        self.folder = folder
        self.organisations=organisations
        self.stations_org={} #dict with classes of all organisations
        self.stations_df = self.load_stations_gdf()
        self.wiwb_combined = wiwb_combined

        for organisation in self.organisations:
            self.stations_org[organisation] = Stations_organisation(folder=self.folder,
                                    organisation=organisation)

    # def load_stations(self, resample_rule):
    #     """load timeseries from all stations"""
    #     for organisation in self.stations_org:
    #         stat = self.stations_org[organisation]
    #         stat.load(resample_rule=resample_rule)


    def load_stations_gdf(self):
        gdf = gpd.read_file(self.folder.input.ground_stations.path)
        return gdf[gdf['use']==True]


    def merge_df_datetime(self, dict_df):
        """Combine all dataframes in a dictionary into one single df."""
        return reduce(lambda left,right: pd.merge(left,right,left_index=True, right_index=True, how='outer'), dict_df.values())   


    def load_stations(self, resample_rule):
        """Load all stations then combine all dataframes from different organisations into one df. Requires 'self.load' to be run."""

        #Load and combine
        dict_values={}
        dict_mask={}
        for organisation in self.stations_org:
            stat = self.stations_org[organisation]
            stat.load(resample_rule=resample_rule)

            dict_values[stat.organisation] = stat.df_value
            dict_mask[stat.organisation] = stat.df_mask

        self.df_value = self.merge_df_datetime(dict_df=dict_values)
        self.df_mask = self.merge_df_datetime(dict_df=dict_mask)
        self.df_mask = self.df_mask==True #Fill nanvalues.


    def load_wiwb(self, resample_rule):
        """Load timeseries of wiwb results at station location"""
        
        self.df_irc = {}
        for irc_type in self.wiwb_combined.wiwb_settings:
            self.df_irc[irc_type] = pd.read_parquet(self.wiwb_combined.out_path[irc_type][resample_rule])


    @property
    def df(self):
        """filtered table with measured values"""
        return self.df_value[~self.df_mask]


    def get_station(self, folder, row):
        df_mask = self.df_mask[row['ID']]

        dict_station = {}

        dict_station['station'] = self.df[row['ID']].rename('station')
        for irc_type in self.df_irc:
            dict_station[irc_type] = self.df_irc[irc_type][row['WEERGAVENAAM']].rename(irc_type)

        df_timeseries = self.merge_df_datetime(dict_station)

        return Station(folder, row, df_mask=df_mask, df = df_timeseries)


    def __iter__(self):
        """when iterating over 'self' this will yield the station classes."""
        for index, row in self.stations_df.iterrows():
            
            if row['ID'] in self.df_value.columns:
                yield self.get_station(self.folder, row)
            else:
                print(f"{row['ID']} -- Missing timeseries")
                pass

    def __repr__(self):
        return '.'+' .'.join([i for i in dir(self) if not i.startswith('__')])
        
class Wiwb_combined():
    def __init__(self, folder, wiwb_settings):
        self.folder = folder
        self.wiwb_settings = wiwb_settings

        self.out_path = self.set_out_path()


    def set_out_path(self):
        RESAMPLE_TEXT = {'h':'1h',
                        'd':'24h'}

        out_path = {}
        for irc_type in self.wiwb_settings:
            out_path[irc_type] = {}
            for resample_rule in ['h', 'd']:
                out_path[irc_type][resample_rule] = self.folder.input.paths['wiwb']['resampled'].full_path(f'{irc_type}_{RESAMPLE_TEXT[resample_rule]}.parquet')
        return out_path


    def resample(self, overwrite=True):
        """Resample wiwb values to hour and day data. Save to file"""

        for irc_type in self.wiwb_settings:
            cont = [True]

            #First check if all output already exists
            if overwrite==False:
                for resample_rule in ['h', 'd']:
                    if os.path.exists(self.out_path[resample_rule]):
                        cont.append(False)

            if np.all(cont) == True:
                #Load raw values
                df_value = pd.read_parquet(self.wiwb_settings[irc_type]['raw_filepath']).unstack(level=1).droplevel(0, axis=1)

                for resample_rule in ['h', 'd']:
                    #Resample
                    df_value_resampled= pd.DataFrame(df_value.resample(resample_rule).sum())

                    #Save to file
                    df_value_resampled.to_parquet(self.out_path[irc_type][resample_rule])
