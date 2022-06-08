# -*- coding: utf-8 -*-
"""
Created on Fri Aug 13 13:18:54 2021

@author: wietse.vangerwen

Each class has a file as its attributes and a file as a new class. 
self.base is the directory in which it is located

"""
# First-party imports
import os
import glob
from pathlib import Path

# # Third-party imports
# from threedigrid.admin.gridadmin import GridH5Admin
# from threedigrid.admin.gridresultadmin import GridH5ResultAdmin

import hhnk_research_tools as hrt

from hhnk_research_tools.variables import (
    file_types_dict,
    GDB,
    SHAPE,
    SQLITE,
    TIF,
    NC,
    H5,
)

import fiona
import geopandas as gpd
import pandas as pd
import numpy as np


class File:
    def __init__(self, file_path):
        self.file_path = file_path
        self.pl = Path(file_path)

    @property
    def exists(self):
        return self.pl.exists()

    @property
    def name(self):
        return self.pl.stem

    @property
    def path(self):
        return self.file_path

    def __str__(self):
        return self.file_path

    def __repr__(self):
        if self.exists:
            exists = "exists"
        else:
            exists = "doesn't exist"

        return f"{self.name} @ {self.file_path} ({exists})"


class FileGDB(File):
    """.layers gives overview of layers
    .load loads the layer """
    def __init__(self, file_path):
        super().__init__(file_path)
    
    def load(self, layer=None):
        """Load layer as geodataframe, if no layer provided an input box is return"""
        if layer==None:
            print(self.layers())
            layer=input('Select layer:')
        return gpd.read_file(self.file_path, layer=layer)

    def layers(self):
        """Return available layers in file gdb"""
        return fiona.listlayers(self.file_path)


class Raster(File):
    def __init__(self, raster_path):
        super().__init__(raster_path)

    def load(self, return_array=True):
        if self.exists:
            self.array, self.nodata, self.metadata = hrt.load_gdal_raster(
                raster_source=self.file_path, return_array=return_array
            )
            return self.array, self.nodata, self.metadata
        else:
            print("Doesn't exist")


class Folder:
    """Base folder class for creating, deleting and see if folder exists"""

    def __init__(self, base):
        self.base = base
        self.pl = Path(base)  # pathlib path

        self.files = {}
        self.olayers = {}
        self.space = "\t\t\t\t"

    @property
    def structure(self):
        return ""

    @property
    def content(self):
        return os.listdir(self.base)

    @property
    def path(self):
        return self.base

    @property
    def name(self):
        return self.pl.stem

    @property
    def folder(self):
        return os.path.basename(self.base)

    @property
    def exists(self):
        return self.pl.exists()

    @property
    def show(self):
        print(self.__repr__())

    @property
    def attributes(self):
        return ""

    def create(self, parents=True):
        """Create folder, if parents==False path wont be 
        created if parent doesnt exist."""
        if parents==False:
            if not self.pl.parent.exists():
                print(f'{self.path} not created, parent doesnt exist.')
                return
        self.pl.mkdir(parents=parents, exist_ok=True)
    
    def find_ext(self, ext):
        """ finds files with a certain extension"""
        return glob.glob(self.base +f'/*.{ext}')

    def full_path(self, name):
        """returns the full path of a file or a folder when only a name is known"""
        return str(self.pl / name)

    def add_file(self, objectname, filename, ftype="file"):
        """ftype options are: file, filegdb, raster"""
        if ftype == "file":
            new_file = File(self.full_path(filename))
        elif ftype == "filegdb":
            new_file = FileGDB(self.full_path(filename))
        elif ftype == "raster":
            new_file = Raster(self.full_path(filename))

        self.files[objectname] = new_file
        setattr(self, objectname, new_file)

    def add_layer(self, objectname, layer):
        self.olayers[objectname] = layer
        setattr(self, objectname, layer)


    def __str__(self):
        return self.base

    def __repr__(self):
        return f"""{self.name} @ {self.path}
                    Folders:\t{self.structure}
                    Files:\t{list(self.files.keys())}
                    Layers:\t{list(self.olayers.keys())}
                    Attributes:\t{self.attributes}
                """


# class ThreediResult(Folder):
#     """Class for threediresults. Results can be accessed with the .grid method."""

#     def __init__(self, base):
#         super().__init__(base)

#         # Files
#         self.add_file("grid_path", "results_3di.nc")
#         self.add_file("admin_path", "gridadmin.h5")

#     @property
#     def grid(self):
#         return GridH5ResultAdmin(self.admin_path.file_path, self.grid_path.file_path)

#     @property
#     def admin(self):
#         return GridH5Admin(self.admin_path.file_path)




class Folders(Folder):
    __doc__ = f"""
        
        --------------------------------------------------------------------------
        An object to ease the accessibility, creation and checks of folders and
        files in the polder structure.
        
        Usage as follows:
            - Access class with te path to the main folder (e.g., C:\Poldermodellen\Heiloo)
            - Find your way through by using folder.show
            - Check if a file or folder exists using .exists
            - Create a non-existing revision folder using folder.threedi_results.batch['new_folder'].create()
            - Show all (needed) files using .files
            - Show all (needed) layers using .layers
            - Return a path of a file using either str() or .path
        
        Example code:
            folder = Folders('C:/Poldermodellen/Heiloo')
            
            folder.show
           
            Output: 
                Heiloo @ C:/Poldermodellen/Heiloo
                                Folders:	  
                           				Folders
                           				├── source_data
                           				├── model
                           				├── threedi_results
                           				└── output
                           
                                Files:	[]
                                Layers:	[]
        
            
            folder.source_data.show
            
            Output: 
            
                01_Source_data @ C:/Poldermodellen/Heiloo/01_Source_data
                                    Folders:	  
                               				source_data
                               				└── modelbuilder
                               
                                    Files:	['damo', 'hdb', 'datachecker', ...]
                                    Layers:	['datachecker_fixed_drainage', ...]
            
        """

    def __init__(self, base, create=True):
        super().__init__(base)

        # Input
        self.input = InputPath(self.base)
        self.output = OutputPath(self.base)


    @property
    def structure(self):
        return f"""  
               {self.space}Folders
               {self.space}├── input
               {self.space}├── output
               """


class InputPath(Folder):
    """
    Paths to source data
    """

    def __init__(self, base):
        super().__init__(os.path.join(base, "01_data"))

        #Input from different sources
        self.paths = {}
        self.data_types =  ['station', 'wiwb']
        self.irc_types = ['irc_realtime_current', 'irc_realtime_beta_202201', 'irc_realtime_beta_202204', 'irc_final_current', 'irc_final_beta_202204']
        self.time_resolutions = ['1h', '24h']

        self.paths['station'] = {}
        self.paths['station']['raw'] = Folder(base=os.path.join(self.base, f"p_raw_station"))
        self.paths['station']['resampled'] = Folder(base=os.path.join(self.base, f"p_resampled_station"))

        self.paths['wiwb'] = {}
        self.paths['wiwb']['raw'] = Folder(base=os.path.join(self.base, f"p_raw_wiwb"))
        self.paths['wiwb']['resampled'] = Folder(base=os.path.join(self.base, f"p_resampled_wiwb"))

        # for data_type in self.data_types:
        #     self.paths[data_type] = {}
        #     for time_resolution in self.time_resolutions:
        #         # self.paths[data_type][time_resolution] = Folder(base=os.path.join(self.base, f"p_{time_resolution}_{data_type}"))
        #         # self.paths[data_type][time_resolution].create()


        
        # Files
        self.add_file("ground_stations", 'ground_stations.gpkg', ftype='file')


    @property
    def structure(self):
        return f"""  
               {self.space}01_data
               {self.space}└── p_stations_raw
               """


class OutputPath(Folder):
    """
    Paths to output
    """
    def __init__(self, base):
        super().__init__(os.path.join(base, "02_output"))
        self.inundatie_peilgebied = Folder(base=os.path.join(self.base, 'inundatie_peilgebied'))

        self.add_file('inundatie_polder', 'inundatie_polder.gpkg',ftype='file')

    @property
    def structure(self):
        return f"""  
               {self.space}02_output
               {self.space}└── pgb_source
               """


