import yaml
import os
from collections.abc import Mapping

Global_config_file = "Config.yml"

def format_hex(n):
    return f"0x{n:02X}"

def is_hex(s):
    try:
        int(s, 16)  # Try converting to an integer with base 16
        return True
    except ValueError:
        return False
    
def is_int(s):
    try:
        int(s)  # Try converting to an integer with base 16
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

            for item, value in data.items():
                if isinstance(obj_dest, Mapping) and obj_dest[item] is None:
                    obj_dest[item] = value
                elif hasattr(obj_dest, item) and getattr(obj_dest, item) is None:
                    setattr(obj_dest, item, value)
    except Exception as e:
        print(f"Cannot Access Config file {config_file} Exception: {str(e)}" )
        config = {}
    return config

def find_and_update_key(data, key, new_value):
    """
    Recursively search for a key in a nested dictionary and update its value.
    Returns True if the key was found and updated, otherwise False.
    """
    if isinstance(data, dict):
        for k, v in data.items():
            if k == key:
                data[k] = new_value
                return True  # Stop searching once updated
            elif isinstance(v, dict):  # Recursively search in nested dicts
                if find_and_update_key(v, key, new_value):
                    return True
            elif isinstance(v, list):  # Handle lists of dictionaries
                for item in v:
                    if isinstance(item, dict) and find_and_update_key(item, key, new_value):
                        return True
    return False  # Key not found

def update_config_value(config_file, key, new_value):
    """
    Load the YAML file, update the given key wherever it is found, and save the changes.
    """
    try:
        yaml.preserve_quotes = True
        with open(config_file, "r") as file:
            config = yaml.safe_load(file) or {}

        if find_and_update_key(config, key, new_value):
            with open(config_file, "w") as file:
                yaml.dump(config, file, default_flow_style=False, sort_keys=False)
            print(f"Updated '{key}' to {new_value} in {config_file}")
        else:
            print(f"Key '{key}' not found in {config_file}")

    except Exception as e:
        print(f"Error updating YAML: {e}")

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
        path_fileConfig = os.path.join(dir_name + "/../", config["configFile"])
        return path_fileConfig

def verifyFrame(dataReceived, dataSent, size):
    resultStatus = False
    if (dataReceived[0]&dataSent[0] == dataSent[0]) and ((dataReceived[0] & 0x40) == 0x40):
        resultStatus = True
        for i in range(1, size):
            if (dataReceived[i] != dataSent[i]):
                resultStatus = False
    return resultStatus