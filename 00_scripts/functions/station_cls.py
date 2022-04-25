import pandas as pd
import os

class Station():
    """Individual station with related timeseries."""
    def __init__(self, folder, row):
        self.row=row
        self.name = row['WEERGAVENAAM']
        self.code = row['ID']
        self.organisation = row['organisation']
        self.geometry = row['geometry']
        self.data_types = folder.input.data_types #['station', 'irc_realtime_current', 'irc_r...

        self.path = {}
        self.path['raw'] = os.path.join(folder.input.path, f"p_raw_station", f'{self.code}_p_raw_station.csv')

        for data_type in folder.input.data_types:
            self.path[data_type] = {}
            for time_resolution in folder.input.time_resolutions:
                self.path[data_type][time_resolution] = os.path.join(folder.input.paths[data_type][time_resolution].path, f'{self.code}_p_{time_resolution}_{data_type}.csv')


    def load_ts_raw(self, date_col='Unnamed: 0', skiprows=1, sep=';'):
        """Load raw data. #TODO only works for HHNK data."""
        filepath = self.path['raw']
        df = pd.read_csv(filepath, sep=sep, skiprows=skiprows)#, parse_dates=[date_col])
        df.rename({date_col:'date', 
                    'P.meting.1m':'value',
                    'P.meting.1m quality':'flag'}, 
                    inplace=True,axis=1)

        #Set datetime as index
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)

        #Set obtype to float
        def str_to_float(x):
            try: 
                return x.replace(',', '.')
            except:
                return x
        df['value'] = df['value'].apply(str_to_float)
        df['value'].astype(float)

        return df

    def load_ts(self, filepath=None, data_type=None, time_resolution=None):
        """Load timeseries"""
        if filepath is None:
            filepath = self.path[data_type][time_resolution]
        df=pd.read_csv(filepath)
        
        #Set datetime as index
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        return df

    def to_file(self, df, output_path):
        print(f'Create - {output_path}')
        df.to_csv(output_path)


        