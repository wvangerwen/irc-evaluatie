# %%
import sys
for x in ['C:/Users/wvangerwen/AppData/Roaming/3Di/QGIS3/profiles/default/python/plugins/hhnk_threedi_plugin/external-dependencies',
 'C:/Users/wvangerwen/AppData/Roaming/3Di/QGIS3/profiles/default/python',
 'C:/Users/wvangerwen/AppData/Roaming/3Di/QGIS3/profiles/default/python/plugins/ThreeDiToolbox/deps']:
    try:
        sys.path.remove(x)
    except:
        print(f'not in path: {x}')
import functions.folders as folders
import functions.station_cls as station_cls
import functions.irc_settings as irc_settings

import importlib
importlib.reload(folders)
importlib.reload(station_cls) #Reload folders to skip kernel reload.
importlib.reload(irc_settings)
import os


folder = folders.Folders(os.pardir) #create folder structure from parent dir. 

settings_all = irc_settings.IrcSettings(folder=folder)

# %%
# Resample data

#Station 
for organisation in settings_all.org:
# for organisation in ['HHNK']:
    stations_organisation = station_cls.Stations_organisation(folder=folder,          
                                organisation=organisation,
                                settings=settings_all.org[organisation])

    #Resample timeseries to hour and day values.
    locations = stations_organisation.resample(overwrite=False)

    #Add locations from xml to the gpkg
    stations_organisation.add_locations_to_gpkg(locations)

#Wiwb
wiwb_combined = station_cls.Wiwb_combined(folder=folder, settings=settings_all.wiwb)
wiwb_combined.resample(overwrite=True)

