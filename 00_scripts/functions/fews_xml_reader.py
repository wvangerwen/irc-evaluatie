from lxml import etree
import pandas as pd
from shapely.geometry import Point

def fews_xml_to_df(timeseries_source):
    """https://stackoverflow.com/questions/69461864/loading-a-delft-fews-series-xml-document-into-a-pandas-dataframe"""
    with open(timeseries_source) as f:
        # load the FEWS Series xml document
        tree = etree.parse(f)

    # relabel the None namespace to 'fews', so we can refer to it in xpath expressions
    nsmap = tree.getroot().nsmap.copy()
    nsmap['fews'] = nsmap.pop(None)
    # obtain the series in the document
    series = tree.xpath('//fews:series', namespaces=nsmap)

    # create and fill a new dataframe
    df_value = pd.DataFrame()
    df_flag = pd.DataFrame()

    class Location_header_xml():
        def __init__(self, s):
            self.loc_id = s.xpath('fews:header/fews:locationId/text()', namespaces=nsmap)[0]
            self.parameter_id = s.xpath('fews:header/fews:parameterId/text()', namespaces=nsmap)[0]
            self.name = s.xpath('fews:header/fews:stationName/text()', namespaces=nsmap)[0]
            self.x = float(s.xpath('fews:header/fews:x/text()', namespaces=nsmap)[0])
            self.y = float(s.xpath('fews:header/fews:y/text()', namespaces=nsmap)[0])
            self.geometry = Point(self.x, self.y)
        
        def __repr__(self):
            return f"""Location:   {self.loc_id}
    parameter:  {self.parameter_id}
    name:       {self.name}
    x:          {self.x}
    y:          {self.y}
    geometry:   {self.geometry}"""

    locations = {}

    for s in series:
        location = Location_header_xml(s)
        # location and parameter names are in the header on the series

        # etree.tostring(s) is the literal xml for just the series,
        # which read_xml accepts as source data for a new dataframe
        series_df = pd.read_xml(etree.tostring(s), xpath='//fews:series/fews:event', namespaces=nsmap)
        # combine the date and time columns into a single datetime and set it as the index for the dataframe
        series_df['datetime'] = pd.to_datetime((series_df['date'] + ' ' + series_df['time']))
        series_df.set_index(['datetime'], inplace=True)
        # take the value and flag columns and add them to the dataframe being constructed
        df_value[location.loc_id, location.parameter_id] = series_df['value']
        df_flag[location.loc_id, location.parameter_id] = series_df['flag']

        #Add location to overview 
        # #FIXME doesnt work for multiple params on same location
        locations[location.loc_id] = location

    # turn the columns labeled with tuples into a proper multi-index on the dataframe
    df_value.columns = pd.MultiIndex.from_tuples(df_value.columns, names=['location', 'parameter'])
    df_flag.columns = pd.MultiIndex.from_tuples(df_flag.columns, names=['location', 'parameter'])

    return df_value, df_flag, locations