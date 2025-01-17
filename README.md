# lp_merger

lp_merger is a python script which allows partial conflict resolution of Light Placer configs.
This tool is useful to people who want to be able to run LPO, CS Light, and Placed Light alongside
each other without getting too many lights on one mesh (which results in overexposure).

# Requirements

- [python 3.12](https://www.python.org/downloads/) or newer
- Familiarity with CLI tools


# Usage

```
usage: lp_merger.py [-h]
                    [--add-flags [{IgnoreScale,NoExternalEmittance,PortalStrict,RandomAnimStart,Shadow,Simple,SyncAddonNodes,UpdateOnCellTransition,UpdateOnWaiting} ...]]
                    [--remove-flags [{IgnoreScale,NoExternalEmittance,PortalStrict,RandomAnimStart,Shadow,Simple,SyncAddonNodes,UpdateOnCellTransition,UpdateOnWaiting} ...]]
                    [paths ...]

positional arguments:
  paths                 list of paths to json files under 'Data/lightplacer/'. Earlier files win conflicts

options:
  -h, --help            show this help message and exit
  --add-flags [{IgnoreScale,NoExternalEmittance,PortalStrict,RandomAnimStart,Shadow,Simple,SyncAddonNodes,UpdateOnCellTransition,UpdateOnWaiting} ...]
                        Flags to include in all lights
  --remove-flags [{IgnoreScale,NoExternalEmittance,PortalStrict,RandomAnimStart,Shadow,Simple,SyncAddonNodes,UpdateOnCellTransition,UpdateOnWaiting} ...]
                        Flags to omit from all lights

redirect stdout to a new json file and load it in 'Data/lightplacer/' instead of input jsons
```

The `--add-flags` and `--remove-flags` argument will add or remove flags to every single
light in merged configs. If neither arguments are passed, original flags are retained.
I recommend adding `NoExternalEmittance` to all lights to fix bugs and inconsistencies with
the emittance of placed objects.

The first file passed in as an argument will win conflicts for any addonNodes, meshes, or
visualEffects. E.g. if file1 has addonNode 49 with 2 lights attached to it, and file2 has
addonNode 49 with 3 lights attached to it, the lights/settings from file1 are used for
addonNode 49, the lights/settings from file2 are ignored for addonNode 49. The output would
contain only the lights/settings for addonNode 49 from file1. This is consistent with
models and visualEffects as well. You can pass any number of files as arguments.

Output will be to the console, so if you want to save the output, you'll need to redirect
stdout. See the windows/linux usage sections below for examples.

Once you have generated a new json file, you'll want to put it in `Data/LightPlacer`,
and deactivate or delete all the lightplacer configs that you used during merging.

## Windows
```
python3 lp_merger.py C:\path\to\file1.json C:\path\to\file2.json > new_file.json
```

## Linux
```
python3 lp_merger.py /path/to/file1.json /path/to/file2.json > new_file.json
```
