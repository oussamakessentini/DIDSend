import xml.etree.ElementTree as ET
import re
import os
from UDS.Utils import *
import pandas as pd

DIDDataExcel = None
DIDStatusExcel = None
PathToArxml = None

def extractDataFromArxml(file_path):
    did_data = []
    rc_data = []
    # Test if file is present
    if os.path.isfile(file_path):
        # Parse ARXML File and extract data
        tree = ET.parse(file_path)
        tree, NULL = remove_namespace(tree)
        root = tree.getroot()

        for data in root.iter("ECUC-CONTAINER-VALUE"):
            def_Val = data.find("DEFINITION-REF")
            # Get DID ID and DID Info
            if def_Val is not None and def_Val.text.endswith("Dcm/DcmConfigSet/DcmDsp/DcmDspDid"):
                did_id = find_recursive_Value(data, "DEFINITION-REF", "DcmDspDidIdentifier")
                # Convert and clean DID ID format
                did_id = str(hex(int(did_id))).upper()[2:].zfill(4)

                did_dataRef = find_recursive_Value(data, "DEFINITION-REF", "DcmDspDidDataRef")
                # Get DID data Ref definition from DcmDspDidDataRef
                did_dataRef = did_dataRef.split('/')[-1]

                # Retreive RDBI\WDBI information
                for data_s in root.iter("ECUC-CONTAINER-VALUE"):
                    def_Val = data_s.find("DEFINITION-REF")
                    
                    if def_Val is not None and def_Val.text.endswith("Dcm/DcmConfigSet/DcmDsp/DcmDspData"):
                        did_dataInfo = find_recursive(data_s, "SHORT-NAME")
                        # Check specific DID => DcmDspData
                        if did_dataInfo.text == did_dataRef:
                            did_size = find_recursive_Value(data_s, "DEFINITION-REF", "DcmDspDataSize")
                            did_read_fct = find_recursive_Value(data_s, "DEFINITION-REF", "DcmDspDataReadFnc")
                            did_wead_fct = find_recursive_Value(data_s, "DEFINITION-REF", "DcmDspDataWriteFnc")

                            if did_size is not None:
                                # Add +7 to rounds up and get the right size (byte numbers)
                                # Note : // operator is the floor division operator => rounds down to the nearest whole number
                                did_size = (int(did_size) + 7) // 8

                            did_data.append({"DID": did_id, "Size" : did_size, "Read": did_read_fct, "Write": did_wead_fct})
                            break
            
            # Retreive RC
            if def_Val is not None and def_Val.text.endswith("Dcm/DcmConfigSet/DcmDsp/DcmDspRoutine"):
                rc_start_fct = find_recursive_Value(data, "DEFINITION-REF", "DcmDspStartRoutineFnc")
                rc_stop_fct = find_recursive_Value(data, "DEFINITION-REF", "DcmDspStopRoutineFnc")
                rc_result_fct = find_recursive_Value(data, "DEFINITION-REF", "DcmDspRequestResultsRoutineFnc")
                rc_id = find_recursive_Value(data, "DEFINITION-REF", "DcmDspRoutineIdentifier")
                # Convert and clean RC ID format
                rc_id = str(hex(int(rc_id))).upper()[2:].zfill(4)
                rc_info = find_recursive_Value(data, "DEFINITION-REF", "DcmDspRoutineInfoRef")
                # Get RC Info definition from DcmDspRoutineInfoRef
                rc_info = rc_info.split('/')[-1]
                
                # Retreive RC information
                for data_s in root.iter("ECUC-CONTAINER-VALUE"):
                    def_Val = data_s.find("DEFINITION-REF")
                    
                    if def_Val is not None and def_Val.text.endswith("Dcm/DcmConfigSet/DcmDsp/DcmDspRoutineInfo"):
                        rc_dataInfo = find_recursive(data_s, "SHORT-NAME")
                        # Check specific RC => DcmDspRoutineInfo
                        if rc_dataInfo.text == rc_info:

                            rc_start_dataIn_size = find_recursive_Value(data_s, "DEFINITION-REF", "DcmDspStartRoutineInSignal/DcmDspRoutineSignalLength")
                            if rc_start_dataIn_size is not None:
                                rc_start_dataIn_size = (int(rc_start_dataIn_size) + 7) // 8

                            rc_start_dataOut_size = find_recursive_Value(data_s, "DEFINITION-REF", "DcmDspStartRoutineOutSignal/DcmDspRoutineSignalLength")
                            if rc_start_dataOut_size is not None:
                                rc_start_dataOut_size = (int(rc_start_dataOut_size) + 7) // 8

                            rc_stop_dataIn_size = find_recursive_Value(data_s, "DEFINITION-REF", "DcmDspRoutineStopInSignal/DcmDspRoutineSignalLength")
                            if rc_stop_dataIn_size is not None:
                                rc_stop_dataIn_size = (int(rc_stop_dataIn_size) + 7) // 8

                            rc_stop_dataOut_size = find_recursive_Value(data_s, "DEFINITION-REF", "DcmDspRoutineStopOutSignal/DcmDspRoutineSignalLength")
                            if rc_stop_dataOut_size is not None:
                                rc_stop_dataOut_size = (int(rc_stop_dataOut_size) + 7) // 8

                            rc_result_dataIn_size = find_recursive_Value(data_s, "DEFINITION-REF", "DcmDspRoutineRequestResInSignal/DcmDspRoutineSignalLength")
                            if rc_result_dataIn_size is not None:
                                rc_result_dataIn_size = (int(rc_result_dataIn_size) + 7) // 8

                            rc_result_dataOut_size = find_recursive_Value(data_s, "DEFINITION-REF", "DcmDspRoutineRequestResOutSignal/DcmDspRoutineSignalLength")
                            if rc_result_dataOut_size is not None:
                                rc_result_dataOut_size = (int(rc_result_dataOut_size) + 7) // 8
                            
                            rc_data.append({"RC ID": rc_id, "Start RC": rc_start_fct, "Start DataIn": rc_start_dataIn_size, "Start DataOut": rc_start_dataOut_size, \
                                                            "Stop RC": rc_stop_fct, "Stop DataIn": rc_stop_dataIn_size, "Stop DataOut": rc_stop_dataOut_size, \
                                                            "Result RC": rc_result_fct, "Result DataIn": rc_result_dataIn_size, "Result DataOut": rc_result_dataOut_size})
                            break
    else:
        print(f"extractDataFromArxml: {file_path} is not present")
    
    return did_data, rc_data

def writeIntoExcel(did_data, rc_data, StatusPath, dataPath):
    # Write DID data into the Excel file
    did_read  = []
    did_write = []
    for row in did_data:
        if (row['Read'] != ''):
            did_read.append({'DID': row['DID'], 'Resultat': '', 'Data': '', 'Error': '', 'Size': row['Size']})
        if (row['Write'] != ''):
            dataToWrite = ";".join('0' for _ in range(int(row['Size'])))
            did_write.append({'DID': row['DID'], 'Status': '', 'Error': '', 'Data': dataToWrite, 'Size': row['Size']})
    df_read  = pd.DataFrame(did_read)
    df_write = pd.DataFrame(did_write)
    df_did_data = pd.DataFrame(did_data)
    df_rc_data  = pd.DataFrame(rc_data)

    with pd.ExcelWriter(StatusPath, engine='openpyxl', mode='w') as writer:
            df_read.to_excel(writer, sheet_name='DID Read', index=False)
            df_write.to_excel(writer, sheet_name='DID Write', index=False)
    
    with pd.ExcelWriter(dataPath, engine='openpyxl', mode='w') as writer:
            # Write DID data into the Excel file
            df_did_data.to_excel(writer, sheet_name='DID List', index=False)
            # Write RC data into the Excel file
            df_rc_data.to_excel(writer, sheet_name='RC List', index=False)

if __name__ == "__main__":
    # Replace local variable with the config 
    dir_name = os.path.dirname(os.path.abspath(__file__))
    FileConfig = loadConfigFilePath(dir_name)
    load_config(globals(), globals(), FileConfig)

    path_DIDStatus = os.path.join(dir_name, DIDStatusExcel)
    path_DIDData = os.path.join(dir_name, DIDDataExcel)
    path_arxml = os.path.join(dir_name, PathToArxml)

    # Extract DID\RC data :
    DIDList, RCList = extractDataFromArxml(path_arxml)

    writeIntoExcel(DIDList, RCList, DIDStatusExcel, DIDDataExcel)
    