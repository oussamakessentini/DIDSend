import yaml
import os
from collections.abc import Mapping
import re
import threading
import queue
import xmltodict
from openpyxl import load_workbook
from openpyxl.styles import PatternFill
from openpyxl.formatting.rule import CellIsRule

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

def dlc_to_data_size(dlc):
    """Convert CAN FD DLC to actual data length."""
    dlc_map = {
        0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6, 7: 7, 8: 8,
        9: 12, 10: 16, 11: 20, 12: 24, 13: 32, 14: 48, 15: 64
    }
    return dlc_map.get(dlc, -1)

def get_dlc_for_data_length(data_length):
    """Return the smallest DLC value that can accommodate the given data length in CAN FD."""
    dlc_map = [
        (0, 0), (1, 1), (2, 2), (3, 3), (4, 4), (5, 5), (6, 6), (7, 7), (8, 8),
        (9, 12), (10, 16), (11, 20), (12, 24), (13, 32), (14, 48), (15, 64)
    ]

    for dlc, size in dlc_map:
        if data_length <= size:
            return dlc  # Return the DLC that fits the data length

    return -1  # If the length is out of range

def string_to_hexList(strData, symbol=''):
    data = []
    if strData:
        for group in strData.split(symbol):
            if group:
                data.extend([int(x, 16) for x in group.split() if x])
    return data

def load_config(obj_dest, globalVal, config_file, Encode=False):
    """Load configuration from a YAML file."""
    try:
        with open(config_file, "r") as file:
            config = yaml.safe_load(file)
            data = {}
            # Flatten the nested structure and set attributes
            flatten_dict(data, globalVal, config, Encode=Encode)

            for item, value in data.items():
                if isinstance(obj_dest, Mapping) and obj_dest.get(item, "") is None:
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

def loadConfigFilePath(localPath=""):
    with open(os.path.join(localPath, Global_config_file), "r") as file:
        config = yaml.safe_load(file)
        path_fileConfig = os.path.join(localPath, config["configFile"])
        return path_fileConfig

def verifyFrame(dataReceived, dataSent, size):
    resultStatus = False
    if (dataReceived[0]&dataSent[0] == dataSent[0]) and ((dataReceived[0] & 0x40) == 0x40):
        resultStatus = True
        for i in range(1, size):
            if (dataReceived[i] != dataSent[i]):
                resultStatus = False
    return resultStatus

def remove_namespace(tree):
    root = tree.getroot()
    namespace = root.tag.split('}')[0].strip('{') if '}' in root.tag else ''
    for elem in root.iter():
        elem.tag = re.sub(r'\{.*?\}', '', elem.tag)  # Remove namespace
    return tree, namespace

def restore_namespace(tree, namespace):
    if namespace:
        root = tree.getroot()
        for elem in root.iter():
            elem.tag = f'{{{namespace}}}' + elem.tag
    return tree

def find_recursive(element, tag):
    """Recherche récursive du premier élément avec le tag donné."""
    found = element.find(tag)
    if found is not None:
        return found
    for child in element:
        found = find_recursive(child, tag)
        if found is not None:
            return found
    return None

def find_recursive_Value(element, tag, value):
    """Recherche récursive du premier élément avec le tag et valeur donné."""
    found = element.find(tag)
    if found is not None and value in found.text:
        value = element.find("VALUE")
        if value is not None:
            return value.text
        else:
            value = element.find("VALUE-REF")
            if value is not None:
                return value.text
            else:
                return None
    for child in element:
        found = find_recursive_Value(child, tag, value)
        if found is not None:
            return found
    return None

class PeekableQueue(queue.Queue):
    def __init__(self):
        super().__init__()
        self.peek_lock = threading.Lock()  # Lock for safe peeking

    def peek(self):
        """Safely peek at the first item without removing it."""
        with self.peek_lock:  # Prevent other threads from peeking at the same time
            if not self.empty():
                return self.queue[0]  # Access the internal queue directly
            return None  # Return None if the queue is empty

def arxml_to_dict_xmltodict(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return xmltodict.parse(file.read())

# ----------------------------------------    
# Excel functions
# ----------------------------------------
def adjustWidth(ws):
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter  # Récupérer la lettre de la colonne (A, B, C, ...)
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(cell.value)
            except:
                pass
        adjusted_width = (max_length + 2) if max_length < 100 else 100  # Limit cell size
        ws.column_dimensions[column].width = adjusted_width

def applyPainterFormat(excel_file, column):
    # Set the colors for the painter format
    fill_green  = PatternFill(start_color="00FF00", end_color="00FF00", fill_type="solid")  # Green
    fill_orange = PatternFill(start_color="DE7B12", end_color="DE7B12", fill_type="solid")  # Orange
    fill_red    = PatternFill(start_color="FF0000", end_color="FF0000", fill_type="solid")  # Red

    status_colors = {
        "OK": fill_green,
        "ROUTINE_STARTED": fill_green,
        "ROUTINE_FINISHED_OK": fill_green,
        "ROUTINE_IN_PROGRESS": fill_orange,
        "NOK": fill_red,
    }

    # Load Excel file with openpyxl to add painter format rules
    wb = load_workbook(excel_file)

    for sheet in wb.worksheets:
        # Adjust the width of columns to adapt with the content
        adjustWidth(sheet)

        # Add color rules for the 'Status' column
        max_row = sheet.max_row
        cell_range = f"{column}2:{column}{max_row}"

        for status, fill in status_colors.items():
            sheet.conditional_formatting.add(cell_range, CellIsRule(operator='equal', formula=[f'"{status}"'], fill=fill))

    # Save the Excel file with the rules and format painter
    wb.save(excel_file)