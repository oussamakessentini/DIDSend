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
    # test if file present
    if os.path.isfile(file_path):
        # parse ARXML File and extract data
        tree = ET.parse(file_path)
        tree, NULL = remove_namespace(tree)
        root = tree.getroot()

        for did in root.iter("ECUC-CONTAINER-VALUE"):
            did_Val = did.find("DEFINITION-REF")
            did_shortName = did.find("SHORT-NAME")
            if did_Val is not None and did_Val.text.endswith("Dcm/DcmConfigSet/DcmDsp/DcmDspData"):
                did_size = find_recursive_Value(did, "DEFINITION-REF", "DcmDspDataSize")
                did_ReadFunction = find_recursive_Value(did, "DEFINITION-REF", "DcmDspDataReadFnc")
                did_WriteFunction = find_recursive_Value(did, "DEFINITION-REF", "DcmDspDataWriteFnc")
                did_id = did_shortName.text[-4:]
                size = ""
                Read = ""
                Write = ""
                if did_size is not None:
                    size = int(int(did_size)/8)
                if did_ReadFunction is not None:
                    Read = did_ReadFunction
                if did_WriteFunction is not None:
                    Write = did_WriteFunction
                did_data.append({"DID": did_id, "Size" : size, "Read": Read, "Write": Write})
    else:
        print(f"extract_did_data: {file_path} is not present")
    
    return did_data

def writeIntoExcel(data, StatusPath, dataPath):
    # Write Excel
    data_read = []
    data_write = []
    for row in data:
        if (row['Read'] != ''):
            data_read.append({'DID': row['DID'], 'Resultat': '', 'Data': '', 'Error': '', 'Size': row['Size']})
        if (row['Write'] != ''):
            dataToWrite = ";".join('0' for _ in range(int(row['Size'])))
            data_write.append({'DID': row['DID'], 'Status': '', 'Error': '', 'Data': dataToWrite, 'Size': row['Size']})
    df_read = pd.DataFrame(data_read)
    df_write = pd.DataFrame(data_write)
    df_data = pd.DataFrame(data)

    with pd.ExcelWriter(StatusPath, engine='openpyxl', mode='w') as writer:
            df_read.to_excel(writer, sheet_name='DID Read', index=False)
            df_write.to_excel(writer, sheet_name='DID Write', index=False)
    
    with pd.ExcelWriter(dataPath, engine='openpyxl', mode='w') as writer:
            df_data.to_excel(writer, sheet_name='DID List', index=False)


if __name__ == "__main__":
    # replace local variable with the config 
    dir_name = os.path.dirname(os.path.abspath(__file__))
    FileConfig = loadConfigFilePath(dir_name)
    load_config(globals(), globals(), FileConfig)

    path_DIDStatus = os.path.join(dir_name, DIDStatusExcel)
    path_DIDData = os.path.join(dir_name, DIDDataExcel)
    path_arxml = os.path.join(dir_name, PathToArxml)

    # extract DID data Write and Read Access
    DIDList = extractDataFromArxml(path_arxml)

    writeIntoExcel(DIDList, DIDStatusExcel, DIDDataExcel)
    