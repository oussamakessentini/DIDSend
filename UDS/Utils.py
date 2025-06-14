import shutil
import time
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
import subprocess
import logging
from typing import List, Optional, Tuple, Union
from Lib.Pdx_Odx import *

Global_config_file = "Config.yml"

def format_hex(item):
    if isinstance(item, int):
        return f"0x{item:02X}"
    elif isinstance(item, (bytes, bytearray)) and len(item) == 1:
        return f"0x{item[0]:02X}"
    else:
        raise ValueError(f"Cannot format item: {item}")

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

def str_to_hexList(strData, symbol=''):
    data = []
    def is_hex_string(s: str) -> bool:
        if len(s) % 2 != 0:
            return False  # Hex data must be even-length for byte pairs
        try:
            bytes.fromhex(s)  # Will raise ValueError if not valid hex
            return True
        except ValueError:
            return False
        
    if len(strData) > 1:
        if(symbol != ''):
            for group in strData.split(symbol):
                if group:
                    data.extend([int(x, 16) for x in group.split() if x])
        else:
            if is_hex_string(strData):
                # Treat as hex string and convert every 2 characters into a byte
                data = [int(strData[i:i+2], 16) for i in range(0, len(strData), 2)]
            else:
                # Treat as regular string and convert each character to its ASCII value
                data = [ord(intData) for intData in strData]
    else:
        data = [int(strData)]
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
                if isinstance(value, list):
                    val = value
                elif value in globalVal:
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
    if ((dataReceived[0] & dataSent[0]) == dataSent[0]) and ((dataReceived[0] & 0x40) == 0x40):
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


def wait_ms(ms: int):
    """Wait for the given duration in milliseconds without blocking other threads."""
    time.sleep(ms / 1000.0)

# Convert int value into bytes + truncate the value to lower 24 bits (3 bytes)
def int_to_3bytes(value: int) -> List[str]:
    value = value & 0xFFFFFF
    byte_seq = value.to_bytes(3, byteorder='big')
    return list(byte_seq)

# Convert int value into bytes + truncate the value to lower 16 bits (2 bytes)
def int_to_2bytes(value: int) -> List[str]:
    value = value & 0xFFFF
    byte_seq = value.to_bytes(2, byteorder='big')
    return list(byte_seq)

# Checksum CRC-16-CCITT (Polynomial 0x1021)
def crc16_ccitt(data):
    poly = 0x1021 # ✅ Polynomial 0x1021
    crc = 0x0000  # ✅ Initial value 
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ poly
            else:
                crc <<= 1
            crc &= 0xFFFF
    return crc

def crc16_x25(data: bytes) -> int:
    """
    Calculate CRC-16/X-25 (DECT-R) checksum.
    
    Parameters:
        data: Input data as bytes
        
    Returns:
        16-bit CRC checksum (int)
    """
    poly = 0x1021  # ✅ Polynomial (0x1021, but we use reversed 0x8408)
    crc = 0xFFFF   # ✅ Initial value (will be inverted to 0x0000 after first step)
    
    for byte in data:
        crc ^= byte
        for idx in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0x8408  # Reversed polynomial
            else:
                crc >>= 1
    
    crc ^= 0xFFFF  # Final XOR
    return crc & 0xFFFF  # Ensure 16-bit result

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

# ----------------------------------------    
# ULP (Motorola S-record) functions
# ----------------------------------------
def run_srec_cat(
    srec_cat_path: str,
    input_files: List[Tuple[str, str]],  # [(filename, format), ...]
    output_file: str,
    output_format: str,
    output_options: Optional[List[str]] = None,
    global_options: Optional[List[str]] = None
) -> bool:
    """
    Runs srec_cat.exe with full support for chaining multiple inputs, formats, and advanced options.

    Args:
        srec_cat_path (str): Path to srec_cat.exe.
        input_files (List[Tuple[str, str]]): List of input files with formats (e.g., [('input.bin', 'Binary')]).
        output_file (str): Path to the output file.
        output_format (str): Output format (e.g., 'Intel', 'Srec', 'Binary').
        output_options (List[str], optional): Additional options for output file (e.g., address range, offset).
        global_options (List[str], optional): Additional global options (e.g., --fill, --output-block-size).

    Returns:
        bool: True if successful, False otherwise.
    """
    if not os.path.isfile(srec_cat_path):
        logging.error(f"srec_cat.exe not found: {srec_cat_path}")
        return False

    for file_path, _ in input_files:
        if not os.path.isfile(file_path):
            logging.error(f"Input file not found: {file_path}")
            return False

    command = [srec_cat_path]

    # Add input files and their formats
    for file_path, fmt in input_files:
        command.extend([file_path, f"-{fmt}"])

    # Add global options if provided
    if global_options:
        command.extend(global_options)

    # Add output file and format
    command.extend(['-o', output_file, f'-{output_format}'])

    # Add additional output options if provided
    if output_options:
        command.extend(output_options)

    # Execute the command
    try:
        result = subprocess.run(
            command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        logging.info("srec_cat executed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        logging.error("srec_cat execution failed.")
        logging.error(f"Command: {' '.join(command)}")
        logging.error(f"Return Code: {e.returncode}")
        logging.error(f"Stdout: {e.stdout}")
        logging.error(f"Stderr: {e.stderr}")
        return False
    except Exception as ex:
        logging.exception(f"Unexpected error while running srec_cat: {ex}")
        return False

# ----------------------------------------    
# PDX functions
# ----------------------------------------
def extractPdxFileInfo(pdx_file):
    odxC = Pdx_Odx()
    pdxDict = {}
    odxfDataFile = ''
    pdxfBinFile = ''
    pdx_temp_path = os.path.dirname(os.path.abspath(__file__)) + "_Temp/"
    # print(pdx_temp_path)
    if os.path.exists(pdx_temp_path):
        shutil.rmtree(pdx_temp_path)
        # print("\nRemove old PDX file\n")
    
    if pdx_file.lower().endswith(".pdx"):
        odxC.pdx_unzip(pdx_file, pdx_temp_path)
        odxfDataFile = odxC.getFilePath(pdx_temp_path, None, '.odx-f')
        pdxfBinFile  = odxC.getFilePath(pdx_temp_path, None, '.bin')
        # print(odxDataFile)
        try:
            pdxDict = odxC.getPdxData(odxfDataFile)
            # print(pdxDict)
        except:
            print("Error : PDX file data extraction")
    else:
        # Clear old PDX read data :
        print("[Warning] Read PDX => PDX file not found =>", pdx_file)
    
    # Delete the temporary folder
    # shutil.rmtree(pdx_temp_path)

    return pdxfBinFile, odxfDataFile, pdxDict
