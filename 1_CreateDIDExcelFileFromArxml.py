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
    # test if file present
    if os.path.isfile(file_path):
        # parse ARXML File and extract data
        tree = ET.parse(file_path)
        tree, NULL = remove_namespace(tree)
        root = tree.getroot()

        for data in root.iter("ECUC-CONTAINER-VALUE"):
            def_Val = data.find("DEFINITION-REF")
            did_shortName = data.find("SHORT-NAME")
            # Retreive RDBI\WDBI
            if def_Val is not None and def_Val.text.endswith("Dcm/DcmConfigSet/DcmDsp/DcmDspData"):
                did_size = find_recursive_Value(data, "DEFINITION-REF", "DcmDspDataSize")
                did_ReadFunction = find_recursive_Value(data, "DEFINITION-REF", "DcmDspDataReadFnc")
                did_WriteFunction = find_recursive_Value(data, "DEFINITION-REF", "DcmDspDataWriteFnc")
                did_id = did_shortName.text[-4:]
                size = ""
                Read = ""
                Write = ""
                if did_size is not None:
                    # Add +7 to rounds up and get the right size (byte numbers)
                    # Note : // operator is the floor division operator => rounds down to the nearest whole number
                    size = (int(did_size) + 7) // 8
                if did_ReadFunction is not None:
                    Read = did_ReadFunction
                if did_WriteFunction is not None:
                    Write = did_WriteFunction
                did_data.append({"DID": did_id, "Size" : size, "Read": Read, "Write": Write})
            
            # Retreive RC
            if def_Val is not None and def_Val.text.endswith("Dcm/DcmConfigSet/DcmDsp/DcmDspRoutine"):
                rc_start = find_recursive_Value(data, "DEFINITION-REF", "DcmDspStartRoutineFnc")
                rc_stop = find_recursive_Value(data, "DEFINITION-REF", "DcmDspStopRoutineFnc")
                rc_result = find_recursive_Value(data, "DEFINITION-REF", "DcmDspRequestResultsRoutineFnc")
                rc_id = find_recursive_Value(data, "DEFINITION-REF", "DcmDspRoutineIdentifier")
                start_fct = ""
                stop_fct = ""
                result_fct = ""
                if rc_start is not None:
                    start_fct = rc_start
                if rc_stop is not None:
                    stop_fct = rc_stop
                if rc_result is not None:
                    result_fct = rc_result

                rc_data.append({"RC ID": str(hex(int(rc_id))).upper()[2:].zfill(4), "Start RC": start_fct, "Stop RC": stop_fct, "Result RC": result_fct})
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
    