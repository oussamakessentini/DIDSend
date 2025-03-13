import yaml
import os
from collections.abc import Iterable

Global_config_file = "Config.yml"

def format_hex(n):
    return f"0x{n:02X}"

def is_hex(s):
    try:
        int(s, 16)  # Try converting to an integer with base 16
        return True
    except ValueError:
        return False
    
def isBetween(A, B, C):
    Mi = min(B, C)
    Ma = max(B, C)
    return Mi <= A <= Ma

def load_config(obj_dest, globalVal, config_file, Encode=False):
    """Load configuration from a YAML file."""
    try:
        with open(config_file, "r") as file:
            config = yaml.safe_load(file)
            data = {}
            # Flatten the nested structure and set attributes
            flatten_dict(data, globalVal, config, Encode=Encode)

            for item in data:
                if isinstance(obj_dest, Iterable):
                    if item in obj_dest:
                        obj_dest[item] = data[item]
                else:
                    if hasattr(obj_dest, item):
                        setattr(obj_dest,item, data[item])
    except Exception as e:
        print(f"Cannot Access Config file {config_file} Exception: {str(e)}" )
        config = {}
    return config

def flatten_dict(obj_dest, globalVal, dictionary, Encode=False):
    """Recursively flatten a nested dictionary into class attributes."""
    for key, value in dictionary.items():
        try:
            if isinstance(value, dict):
                flatten_dict(obj_dest, globalVal, value, Encode=Encode)  # Recursive call for nested dicts
            else:
                if value in globalVal:
                    val = globalVal[value]
                else:
                    val = value.encode() if Encode and isinstance(value, str) else value
                obj_dest[key] = val
        except Exception as e:
            print(f"Cannot set var Exception: {str(e)}" )

def loadConfigFilePath():
    with open(Global_config_file, "r") as file:
        config = yaml.safe_load(file)
        dir_name = os.path.dirname(os.path.abspath(__file__))
        path_fileConfig = os.path.join(dir_name, config["configFile"])
        print (path_fileConfig)
        return path_fileConfig