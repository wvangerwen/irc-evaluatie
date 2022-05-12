from datetime import timedelta, datetime
import pandas as pd
import logging
from wiwb_downloader import GridDownloader
import numpy as np
import geopandas as gpd

def format_datetime(value: datetime) -> str:
    """Format datetime into string to use in wiwb download.

    Parameters
    ----------
    value : datetime
        datetime value to format

    Returns
    -------
    str
        string in format %Y-%m-%d %H:%M
    """
    return value.strftime('%Y-%m-%d %H:%M')

def get_points():
    """Make a dictionary with name: Point out of the gpkg

    Returns
    -------
    dict[str:Point]
        dict of locations with shapely Point objects as values.
    extent[list]
        list with extent xmin, ymin, xmax, ymax based on geometries
    """
    locs = gpd.read_file("../01_data/ground_stations.gpkg")
    extent = [locs.geometry.x.min(), locs.geometry.y.min(), locs.geometry.x.max(), locs.geometry.y.max()]
    return locs.set_index("WEERGAVENAAM")["geometry"].to_dict(), extent


def add_columns_for_points(df: pd.DataFrame, cells: dict, points: dict):
    """Replace a dataframe with cells with a dataframe with a column for every point
    and where the value is retried from the corresponding grid cell.

    Parameters
    ----------
    df : DataFrame
        dataframe of radar precipitation values with cells as columns
    cells : dict[str:Point]
        The cell names with their corresponding shapely coordinate points.
    points : dict[str:Point]
        Dict of point names with corresponding shapely coordinate points.

    Returns
    -------
    DataFrame
        New dataframe with the point keys as columns.
    """
    new_df_list = []
    for name, point in points.items():
        for i, cell in cells.items():
            if point.within(cell):
                break       
        new_df_list.append(df[i].rename(name))
    new_df = pd.concat(new_df_list, axis=1)
    return new_df

def download_wiwb(data_source: str, points: dict, start: datetime, end: datetime, extent: list) -> pd.Series:
    """Download grid data from the wiwb and parse to series with multiindex (datetime, location).

    Parameters
    ----------
    data_source : str
        data source name for wiwb download
    points : dict[str, Point]
        dict of locations for return dataframe
    start : datetime
        start time for download
    end : datetime
        end time for download

    Returns
    -------
    pd.Series
        stacked dataframe with (datetime, location) index and precipitation as values.

    Raises
    ------
    ValueError
        Fail when no data is returned from the wiwb.
    """
    downloader = GridDownloader(data_source=data_source,
                            extent=extent,
                            type='grids',
                            start_date=format_datetime(start),
                            end_date=format_datetime(end),
                            args={
                                "Variables": [
                                    "P"
                                ]
                                })
    df = downloader.download(return_df=True)
    df.set_index('StartDate', inplace=True)
    cells = downloader.cells
    df = add_columns_for_points(df, cells, points)
    df = df.replace(-999.0, np.nan).dropna(how='all')
    if df.empty:
        raise ValueError(f"No data from source: {data_source}")
    df = df.astype(np.float32)
    new_index = pd.date_range(name='DateTime',start=start,end=end-timedelta(minutes=5),freq='5T')
    df = df.reindex(new_index, method='nearest')
    logging.info(f"shape: {df.shape}")
    df = df.stack().rename('neerslag')
    df.index.names = ['DateTime','Locatie']
    df.sort_index(inplace=True)
    logging.info(f"sum of values: {df.sum()}")
    return df
