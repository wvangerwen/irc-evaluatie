class IrcSettings:
    def __init__(self, folder):
        self.org = {
            "HHNK": {
                "raw_filepath": folder.input.paths["station"]["raw"].full_path(
                    "HHNK_neerslagmeters_20220101_20220513_1min.csv"
                ),
                "skiprows": 0,
                "sep": ";",
                "date_col": "Unnamed: 0",
            },
            "HDSR": {
                "raw_filepath": folder.input.paths["station"]["raw"].full_path(
                    "HDSR_neerslagdata_2022_5min.xml"
                )
            },
            "WL": {
                "raw_filepath": folder.input.paths["station"]["raw"].full_path(
                    "WL_neerslagdata_202205141515_5min.xml"
                )
            },
            "HEA": {
                "raw_filepath": folder.input.paths["station"]["raw"].full_path(
                    "HEA_P_2022"
                ),
                "skiprows": 9,
                "sep": ";",
                "date_col": "Timestamp",
                "metadata_file": folder.input.full_path("HEA_P_metadata2.xlsx"),
            },
            "WF": {
                "raw_filepath": folder.input.paths["station"]["raw"].full_path(
                    "wf_neerslag.xlsx"
                ),
                "skiprows": 0,
                "date_col": "CET/CEST",
            },
            
            "WAM":{
                "raw_filepath": folder.input.paths["station"]["raw"].full_path(
                    "WAM"
                ),
                "skiprows": 0,
                "sep":",",
                "date_col": "start_date",
            },
        }

        self.wiwb = {
            "irc_realtime": {
                "raw_filepaths": [
                    i
                    for i in folder.input.paths["wiwb"]["raw"].pl.glob(
                        "*irc_realtime_raw*.parquet"
                    )
                ]
            },
            "irc_early": {
                "raw_filepaths": [
                    i
                    for i in folder.input.paths["wiwb"]["raw"].pl.glob(
                        "*irc_early_raw*.parquet"
                    )
                ]
            },
            "irc_final": {
                "raw_filepaths": [
                    i
                    for i in folder.input.paths["wiwb"]["raw"].pl.glob(
                        "*irc_final_raw*.parquet"
                    )
                ]
            },
            "irc_realtime_beta": {
                "raw_filepaths": [
                    i
                    for i in folder.input.paths["wiwb"]["raw"].pl.glob(
                        "*irc_realtime_beta_raw*.parquet"
                    )
                ]
            },
            # "irc_early_beta": {
            #     "raw_filepaths": [
            #         i
            #         for i in folder.input.paths["wiwb"]["raw"].pl.glob(
            #             "*irc_early_beta_raw*.parquet"
            #         )
            #     ]
            # },
            # "irc_final_beta": {
            #     "raw_filepaths": [
            #         i
            #         for i in folder.input.paths["wiwb"]["raw"].pl.glob(
            #             "*irc_final_beta_raw*.parquet"
            #         )
            #     ]
            # },
        }
