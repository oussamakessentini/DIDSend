# Diag UDS Tools

## Overview
Diag UDS Tools is a set of tools for executing UDS (Unified Diagnostic Services) diagnostics. These tools include management of DID (Diagnostic Information), execution of routine control commands, handling of diagnostic trouble codes (DTC), and much more. This project is under development, and new features will be added in the future.

## Features
- **Parse ARXML and extract DID**: Convert ARXML files into CSV files containing DIDs to read and write.
- **Convert CSV to Excel**: Convert the generated CSV file into an Excel file with blank sheets for DID read and write operations.
- **Parse and send DID**: Analyze the Excel file and send requests based on the status and comments generated during UDS operations.
- **Store CAN frames**: Save the CAN frames exchanged during the execution into a separate file.

## TO DO List
1. Add routine control in Excel file and extract them from the project
2. Add Binary flash to UDS class
3. Add DTC Managing (Erase DTC, Display DTC)

## Installation
### Prerequisites
- **Required Software**: Python, PCAN Developer 4, PCAN 5
- **Required Hardware**: PEAK

## Usage
### User Guide
How to use the tool:

1. **Execute the script with `Run_python_script.bat`**

    The `Run_python_script.bat` file allows you to select and execute the available Python scripts. When executed, you will see the following menu:

    ```bash
    Select a Python script to execute:
    [1] CreateDIDCsvFileFromArxml.py
    [2] FromCSVtoExcelFile.py
    [3] DIDParseFileAndSend.py
    [4] DIDSend.py
    [5] StoreCanTrace.py
    ```

2. **Create a CSV file from ARXML with `CreateDIDCsvFileFromArxml.py`**

    This script analyzes ARXML files, extracts a list of DIDs to read and write, and generates a CSV file containing these details.

    Example execution:
    ```bash
    python 1_CreateDIDCsvFileFromArxml.py
    ```

3. **Convert CSV to Excel with `FromCSVtoExcelFile.py`**

    This script takes the previously generated CSV file and converts it into an Excel file with blank pages for DIDs to read and write.

    Example execution:
    ```bash
    python 2_FromCSVtoExcelFile.py
    ```

4. **Parse and send requests with `DIDParseFileAndSend.py`**

    This script analyzes the generated Excel file, fills in the status and comments during the execution of UDS requests, and sends them.

    Example execution:
    ```bash
    python 3_DIDParseFileAndSend.py
    ```

5. **Send custom requests with `DIDSend.py`**

    This script allows you to manually use the UDS class to send custom requests to ECUs.

    Example execution:
    ```bash
    python DIDSend.py
    ```

6. **Store CAN frames with `StoreCanTrace.py`**

    This script allows you to save CAN frames exchanged during diagnostic operations into a separate file.

    Example execution:
    ```bash
    python StoreCanTrace.py
    ```

### Configuration File

Here is an example of the `Config.yml` configuration file used by the tools:

```yml
project: PR128
DIDStatusCsv: DIDStatus_PR128.csv
DIDStatusExcel: DIDStatus_PR128.xlsx
PathToDextArxml: ../BmsGen2/Inputs/DEXT/BMS_AW010700.arxml
pathToAssemblyConnectionDID: ../BmsGen2/Inputs/DEXT/Dext_Connections.arxml
CanConfig:
  TxId: 0x18DADBF1
  RxId: 0x18DAF1DB
  IsCanFD: False
  IsExtended: True
  IsFiltered: True
  IsPadded: True
  timeout: 10
  PcanLib: CanApi4Lib
  # PcanLib: PCANBasicLib
  PCANBasicConfig:
    PcanHandle: PCAN_USBBUS1
    Bitrate: PCAN_BAUD_500K
    BitrateFD: f_clock_mhz=20, nom_brp=5, nom_tseg1=2, nom_tseg2=1, nom_sjw=1, data_brp=2, data_tseg1=3, data_tseg2=1, data_sjw=1
  CanApi4Config:
    device: pcan_usb
    client_name: PythonClient
    net_name: ch1_500kb
