import pandas as pd
import os
import functions.fews_xml_reader as fews_xml_reader
from functools import reduce
import numpy as np
import geopandas as gpd
from pathlib import Path
import hhnk_research_tools as hrt
from shapely.geometry import Point


RESAMPLE_TEXT = {"h": "1h", "d": "24h"}


class Station:
    """Individual station with related timeseries."""

    def __init__(self, folder, row, resample_rule, df, irc_types):
        self.row = row
        self.name = row["WEERGAVENAAM"]
        self.code = row["ID"]
        self.organisation = row["organisation"]
        self.geometry = row["geometry"]
        self.resample_rule = resample_rule
        self.irc_types = irc_types

        # Timeseries
        self.df = df

    @property
    def resample_text(self):
        return RESAMPLE_TEXT[self.resample_rule]

    def __repr__(self):
        return "." + " .".join([i for i in dir(self) if not i.startswith("__")])


class Stations_organisation:
    """All stations of a single organisation with related timeseries."""

    def __init__(self, folder, organisation, settings):
        self.organisation = organisation
        self.folder = folder
        self.settings = settings

        self.out_path = self.set_out_path()

        # self.df_mask, self.df_value = self.load_ts_raw(date_col, skiprows, sep)

    def load_ts_raw(self) -> pd.DataFrame:
        """Load raw data. Returns a mask and value dataframe
        including all stations for that organisation #TODO only works for HHNK data."""

        if self.organisation == "HHNK":
            df = pd.read_csv(
                self.settings["raw_filepath"],
                sep=self.settings["sep"],
                skiprows=self.settings["skiprows"],
            )  # , parse_dates=[date_col])

            df.rename(
                {
                    self.settings["date_col"]: "datetime",
                    "P.meting.1m": "value",
                    "P.meting.1m quality": "flag",
                },
                inplace=True,
                axis=1,
            )

            # Set datetime as index
            df["datetime"] = pd.to_datetime(df["datetime"]) - pd.Timedelta(
                f"01:00:00"
            )  # change time to utc
            df.set_index("datetime", inplace=True)

            df = df.iloc[1:]  # Skip first row.

            # Create a mask df from the flags
            df_mask = df.iloc[:, 1::2].copy()  # flags

            # Replace string values with mask, to identify which timeseries we do use.
            masked_values = {"original reliable": False, "completed unreliable": True}
            df_mask.replace(masked_values, inplace=True)

            # Rename columns to match value df
            df_mask.columns = df_mask.keys().str.replace(" quality", "").values
            df_value = df.iloc[:, 0::2].copy()  # values

            # Set obtype to float
            def str_to_float(x):
                try:
                    return float(x.replace(",", "."))
                except:
                    return float(x)

            df_value = df_value.applymap(str_to_float)
            df_value.astype(float)

            # make sure negative values are masked
            df_mask = (df_value < 0) | (df_mask)
            locations = None

        if self.organisation in ["HDSR", "WL"]:
            df_value, df_flag, locations = fews_xml_reader.fews_xml_to_df(
                self.settings["raw_filepath"]
            )

            if len(df_value.columns.levels[1]) != 1:
                raise Exception("More than one parameter in the xml. Not implemented.")

            # Drop parameter column from multiindex
            df_value = df_value.droplevel(level=1, axis=1)
            df_flag = df_flag.droplevel(level=1, axis=1)

            df_mask = df_flag != 0

        if self.organisation == "HEA":
            resample_rule_hea = {
                "5m.Totaal.O": "5min",
                "Totals.5m.O": "5min",
                "Totaal.60.O": "h",
            }

            df_mask_dict = {}
            df_value_dict = {}
            for raw_fp in Path(self.settings["raw_filepath"]).glob("*csv"):

                # Get metadata from headers of csv
                df_meta = pd.read_csv(
                    raw_fp, sep=self.settings["sep"], nrows=8
                ).set_index("ts_id")
                station_id = df_meta.loc["site_no"].values[0]
                station_param = df_meta.loc["ts_name"].values[0]

                # Load timeseries
                df = pd.read_csv(
                    raw_fp, sep=self.settings["sep"], skiprows=self.settings["skiprows"]
                )  # , parse_dates=[date_col])

                df.rename(
                    {
                        self.settings["date_col"]: "datetime",
                        "Value": "value",
                        "Quality Code": "flag",
                    },
                    inplace=True,
                    axis=1,
                )

                # Set datetime as index
                df["datetime"] = pd.to_datetime(
                    df["datetime"], format="%d-%m-%Y %H:%M:%S"
                )
                df.set_index("datetime", inplace=True)
                df.drop("Timeseries Comment", axis=1, inplace=True)

                # Resample
                df = df.resample(resample_rule_hea[station_param]).sum()

                # Split into mask and value series
                df_value_single = df["value"].copy()  # values
                df_value_single.name = station_id

                # Create a mask df from the flags
                df_mask_single = df["flag"].copy()  # flags

                # Replace string values with mask, to identify which timeseries we do use.
                masked_values = {200: False, "0": True}
                df_mask_single.replace(masked_values, inplace=True)

                # make sure negative values are masked
                df_mask_single = (df_value_single < 0) | (df_mask_single)
                df_mask_single.name = station_id

                df_value_dict[station_id] = df_value_single.copy()
                df_mask_dict[station_id] = df_mask_single.copy()

            df_value = self.merge_df_datetime(df_value_dict)
            df_mask = self.merge_df_datetime(df_mask_dict)

            # Fill nan values so resample works properly
            if self.organisation == "HEA":
                fillna_value = False  # HEA doesnt have equidistant timeseries, so missing data is not filtered
            else:
                fillna_value = True
            df_mask.fillna(
                fillna_value, inplace=True
            )  # Resample doesnt handle Nan values well.

            locations = pd.read_excel(self.settings["metadata_file"])

        if self.organisation == "WF":

            df = pd.read_excel(
                self.settings["raw_filepath"],
                skiprows=self.settings["skiprows"],
                engine="openpyxl",
            )  # , parse_dates=[date_col])

            df.loc[2, self.settings["date_col"]] = self.settings["date_col"]
            df.columns = df.iloc[2]

            # Get location information (only weergavenaam and ID. We need xy..)
            meta_rows = [0, 1, 2]
            locations = df.loc[meta_rows].T[[1, 2]].iloc[1:]
            locations.rename({1: "WEERGAVENAAM", 2: "ID"}, axis=1, inplace=True)

            df.drop([0, 1, 2], axis=0, inplace=True)

            df.rename(
                {
                    self.settings["date_col"]: "datetime",
                    "P.meting.1m": "value",
                    "P.meting.1m quality": "flag",
                },
                inplace=True,
                axis=1,
            )

            # Set datetime as index
            df["datetime"] = pd.to_datetime(
                df["datetime"].apply(lambda x: x[3:]), format="%d-%m-%Y %H:%M"
            )
            df.set_index("datetime", inplace=True)

            # Convert CET/CEST to UTC
            df = df.tz_localize("CET", ambiguous="infer").tz_convert("UTC")
            df = df.tz_localize(None)  # remove tz info so we can merge.

            df_value = df
            df_value.astype(float)

            # Create mask and make sure negative values are masked
            df_mask = df_value.isna()
            df_mask = (df_value < 0) | (df_mask)

        return df_mask, df_value, locations

    @staticmethod
    def merge_df_datetime(dict_df):
        """Combine all dataframes in a dictionary into one single df."""
        return reduce(
            lambda left, right: pd.merge(
                left, right, left_index=True, right_index=True, how="outer"
            ),
            dict_df.values(),
        )

    def set_out_path(self):
        """set output paths of resampled dataframes"""
        out_path = {}
        out_path["value"] = {}
        out_path["mask"] = {}
        for resample_rule in ["h", "d"]:
            out_path["value"][resample_rule] = self.folder.input.paths["station"][
                "resampled"
            ].full_path(f"{self.organisation}_p_{RESAMPLE_TEXT[resample_rule]}.parquet")
            out_path["mask"][resample_rule] = self.folder.input.paths["station"][
                "resampled"
            ].full_path(
                f"{self.organisation}_mask_{RESAMPLE_TEXT[resample_rule]}.parquet"
            )
        return out_path

    def resample(self, overwrite=True):
        """Resample measured values to hour and day data. Save to file"""

        cont = [True]
        # First check if all output already exists
        if overwrite == False:
            for resample_rule in ["h", "d"]:
                if os.path.exists(self.out_path["value"][resample_rule]):
                    cont.append(False)

        if np.all(cont) == True:
            # Load raw values
            df_mask, df_value, locations = self.load_ts_raw()

            for resample_rule in ["h", "d"]:
                # Resample
                df_value_resampled = pd.DataFrame(
                    df_value.resample(resample_rule).sum()
                )
                df_mask_resampled = pd.DataFrame(df_mask.resample(resample_rule).sum())

                # Recreate mask
                df_mask_resampled = df_mask_resampled != 0

                # Save to file
                df_value_resampled.to_parquet(self.out_path["value"][resample_rule])
                df_mask_resampled.to_parquet(self.out_path["mask"][resample_rule])
            return locations

    def load(self, resample_rule="h"):
        """Load timeseres from file"""
        self.df_value = pd.read_parquet(self.out_path["value"][resample_rule])
        self.df_mask = pd.read_parquet(self.out_path["mask"][resample_rule])

    # Toevoegen locaties van xml aan de gpkg
    def add_locations_to_gpkg(self, locations):
        """Add locations from xml to the stations gpkg"""
        if locations is not None:  # For HHNK the locations are None
            stations_df = gpd.read_file(self.folder.input.ground_stations.path)
            stations_df_orig = stations_df.copy()

            # XML files here
            if self.organisation in ["HDSR", "WL"]:
                for loc in locations:
                    loc = locations[loc]
                    if loc.loc_id not in stations_df["ID"].values:
                        stations_df = stations_df.append(
                            {
                                "WEERGAVENAAM": loc.name,
                                "ID": loc.loc_id,
                                "organisation": self.organisation,
                                "use": True,
                                "geometry": loc.geometry,
                            },
                            ignore_index=True,
                        )

            # HEA is a separate file.
            elif self.organisation == "HEA":
                locations["geometry"] = locations.apply(
                    lambda x: Point(x.site_x, x.site_y), axis=1
                )

                locations.rename(
                    {
                        "site_name": "WEERGAVENAAM",
                        "Site_id": "ID",
                    },
                    inplace=True,
                    axis=1,
                )
                locations["organisation"] = self.organisation
                locations["use"] = True
                locations = hrt.df_add_geometry_to_gdf(locations, "geometry")
                stations_df = pd.merge(stations_df, locations, how="outer")[
                    stations_df.columns
                ]

            if len(stations_df_orig) != len(stations_df):
                print(
                    f"Update ground stations gpkg -- {self.folder.input.ground_stations.path}"
                )
                stations_df.to_file(
                    self.folder.input.ground_stations.path, driver="GPKG"
                )

    def __repr__(self):
        return "." + " .".join([i for i in dir(self) if not i.startswith("__")])


class Stations_combined:
    """Class that combines the resampled timeseries of all organisations."""

    def __init__(
        self, folder, organisations, wiwb_combined, resample_rule, settings_all
    ):
        self.folder = folder
        self.organisations = organisations
        self.stations_org = {}  # dict with classes of all organisations
        self.stations_df = self.load_stations_gdf()
        self.wiwb_combined = wiwb_combined
        self.resample_rule = resample_rule
        self.settings_all = settings_all

        for organisation in self.organisations:
            self.stations_org[organisation] = Stations_organisation(
                folder=self.folder,
                organisation=organisation,
                settings=settings_all.org[organisation],
            )

    def load_stations_gdf(self):
        gdf = gpd.read_file(self.folder.input.ground_stations.path)
        return gdf[gdf["use"] == True]

    @staticmethod
    def merge_df_datetime(dict_df):
        """Combine all dataframes in a dictionary into one single df."""
        return reduce(
            lambda left, right: pd.merge(
                left, right, left_index=True, right_index=True, how="outer"
            ),
            dict_df.values(),
        )

    def load_stations(self):
        """Load all stations then combine all dataframes from different organisations into one df. Requires 'self.load' to be run."""

        # Load and combine
        dict_values = {}
        dict_mask = {}
        for organisation in self.stations_org:
            stat = self.stations_org[organisation]
            stat.load(resample_rule=self.resample_rule)

            dict_values[organisation] = stat.df_value
            dict_mask[organisation] = stat.df_mask

        self.df_value = self.merge_df_datetime(dict_df=dict_values)
        self.df_mask = self.merge_df_datetime(dict_df=dict_mask)
        self.df_mask = self.df_mask == True  # Fill nanvalues.

    def load_wiwb(self):
        """Load timeseries of wiwb results at station location"""

        self.df_irc = {}
        for irc_type in self.wiwb_combined.settings:
            self.df_irc[irc_type] = pd.read_parquet(
                self.wiwb_combined.out_path[irc_type][self.resample_rule]
            )

    @property
    def df(self):
        """filtered table with measured values"""
        return self.df_value[~self.df_mask]

    def get_station(self, row):
        """Get all timeseries of the station and combine them in one dataframe"""
        irc_types = [i for i in self.df_irc]
        dict_station = {}
        dict_station["station"] = self.df[row["ID"]].rename("station")
        for irc_type in irc_types:
            dict_station[irc_type] = self.df_irc[irc_type][row["WEERGAVENAAM"]].rename(
                irc_type
            )
        dict_station["mask"] = self.df_mask[row["ID"]].rename("mask")

        # Combine all dataframes into one.
        df_timeseries = self.merge_df_datetime(dict_station)

        return Station(
            self.folder, row, self.resample_rule, df=df_timeseries, irc_types=irc_types
        )

    def __iter__(self):
        """when iterating over 'self' this will yield the station classes."""
        for index, row in self.stations_df.iterrows():

            if row["ID"] in self.df_value.columns:
                if row["WEERGAVENAAM"] in self.df_irc["irc_early"]:
                    yield self.get_station(row)
                else:
                    print(f"{row['ID']} -- Missing wiwb timeseries")

            else:
                print(f"{row['ID']} -- Missing timeseries")
                pass

    def __repr__(self):
        return "." + " .".join([i for i in dir(self) if not i.startswith("__")])


class Wiwb_combined:
    def __init__(self, folder, settings):
        self.folder = folder
        self.settings = settings

        self.out_path = self.set_out_path()

    def set_out_path(self):

        out_path = {}
        for irc_type in self.settings:
            out_path[irc_type] = {}
            for resample_rule in ["h", "d"]:
                out_path[irc_type][resample_rule] = self.folder.input.paths["wiwb"][
                    "resampled"
                ].full_path(f"{irc_type}_{RESAMPLE_TEXT[resample_rule]}.parquet")
        return out_path

    @staticmethod
    def merge_df_datetime(dict_df):
        """Combine all dataframes in a dictionary into one single df."""
        return reduce(
            lambda left, right: pd.merge(
                left, right, left_index=True, right_index=True, how="outer"
            ),
            dict_df.values(),
        )

    def resample(self, overwrite=True):
        """Resample wiwb values to hour and day data. Save to file"""

        for irc_type in self.settings:
            cont = [True]

            # First check if all output already exists
            if overwrite == False:
                for resample_rule in ["h", "d"]:
                    if os.path.exists(self.out_path[resample_rule]):
                        cont.append(False)

            if np.all(cont) == True:
                # Load raw values
                df_value_dict = {}
                for raw_filepath in self.settings[irc_type]["raw_filepaths"]:
                    df_value_dict[raw_filepath] = (
                        pd.read_parquet(raw_filepath)
                        .unstack(level=1)
                        .droplevel(0, axis=1)
                    )

                df_value = self.merge_df_datetime(df_value_dict)

                for resample_rule in ["h", "d"]:
                    # Resample
                    df_value_resampled = pd.DataFrame(
                        df_value.resample(resample_rule).sum()
                    )

                    # Save to file
                    df_value_resampled.to_parquet(
                        self.out_path[irc_type][resample_rule]
                    )

    def __repr__(self):
        return "." + " .".join([i for i in dir(self) if not i.startswith("__")])
