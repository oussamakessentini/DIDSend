import xml.etree.ElementTree as ET
import re
import os
from UDS.Utils import *
import pandas as pd

DIDDataExcel = None
DIDStatusExcel = None
PathToArxml  = None
PathToArxmlList = None
PathToMergedArxml = None

def merge_arxml(files, output_file):
    if not files:
        print("Error: No files provided to merge.")
        return

    # Parse the first file and get its root
    tree = ET.parse(files[0])
    root = tree.getroot()

    # Loop through the rest of the files and merge them
    for file in files[1:]:
        tree_to_merge = ET.parse(file)
        root_to_merge = tree_to_merge.getroot()

        # Append each element from the new root to the main root
        for element in root_to_merge:
            root.append(element)

    # Write the merged tree to a new file
    if output_file:
        tree.write(output_file, encoding='utf-8', xml_declaration=True)
    else:
        print("Output file is None")

def extractDataFromArxml(file_path):
    did_data = []
    rc_data = []
    # Test if file is present
    if os.path.isfile(file_path):
        # Parse ARXML File and extract data
        tree = ET.parse(file_path)
        tree, NULL = remove_namespace(tree)
        root = tree.getroot()

        did_data_map = {}
        rc_data_map = {}
        rc_dataInfo_map = {}

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
                
                if did_dataRef not in did_data_map:
                    did_data_map[did_dataRef] = {"DID": did_id}
                else:
                    print(f"reassignement of {did_dataRef} is ignored")
            
            # Retreive RC information
            if def_Val is not None and def_Val.text.endswith("Dcm/DcmConfigSet/DcmDsp/DcmDspRoutineInfo"):
                rc_dataInfo = find_recursive(data, "SHORT-NAME")

                rc_start_dataIn_size   = ''
                rc_start_dataOut_size  = ''
                rc_stop_dataIn_size    = ''
                rc_stop_dataOut_size   = ''
                rc_result_dataIn_size  = ''
                rc_result_dataOut_size = ''

                rc_start_dataIn_size = find_recursive_Value(data, "DEFINITION-REF", "DcmDspStartRoutineInSignal/DcmDspRoutineSignalLength")
                if rc_start_dataIn_size is not None:
                    rc_start_dataIn_size = (int(rc_start_dataIn_size) + 7) // 8

                rc_start_dataOut_size = find_recursive_Value(data, "DEFINITION-REF", "DcmDspStartRoutineOutSignal/DcmDspRoutineSignalLength")
                if rc_start_dataOut_size is not None:
                    rc_start_dataOut_size = (int(rc_start_dataOut_size) + 7) // 8

                rc_stop_dataIn_size = find_recursive_Value(data, "DEFINITION-REF", "DcmDspRoutineStopInSignal/DcmDspRoutineSignalLength")
                if rc_stop_dataIn_size is not None:
                    rc_stop_dataIn_size = (int(rc_stop_dataIn_size) + 7) // 8

                rc_stop_dataOut_size = find_recursive_Value(data, "DEFINITION-REF", "DcmDspRoutineStopOutSignal/DcmDspRoutineSignalLength")
                if rc_stop_dataOut_size is not None:
                    rc_stop_dataOut_size = (int(rc_stop_dataOut_size) + 7) // 8

                rc_result_dataIn_size = find_recursive_Value(data, "DEFINITION-REF", "DcmDspRoutineRequestResInSignal/DcmDspRoutineSignalLength")
                if rc_result_dataIn_size is not None:
                    rc_result_dataIn_size = (int(rc_result_dataIn_size) + 7) // 8

                rc_result_dataOut_size = find_recursive_Value(data, "DEFINITION-REF", "DcmDspRoutineRequestResOutSignal/DcmDspRoutineSignalLength")
                if rc_result_dataOut_size is not None:
                    rc_result_dataOut_size = (int(rc_result_dataOut_size) + 7) // 8
                
                if rc_dataInfo.text not in rc_dataInfo_map:
                    rc_dataInfo_map[rc_dataInfo.text] = {}
                    rc_dataInfo_map[rc_dataInfo.text]["Start DataIn"] = rc_start_dataIn_size
                    rc_dataInfo_map[rc_dataInfo.text]["Stop DataIn"] = rc_stop_dataIn_size
                    rc_dataInfo_map[rc_dataInfo.text]["Result DataIn"] = rc_result_dataIn_size
                    rc_dataInfo_map[rc_dataInfo.text]["Start DataOut"] = rc_start_dataOut_size
                    rc_dataInfo_map[rc_dataInfo.text]["Stop DataOut"] = rc_stop_dataOut_size
                    rc_dataInfo_map[rc_dataInfo.text]["Result DataOut"] = rc_result_dataOut_size
                else:
                    print(f"{rc_dataInfo} already present")


                
        # Retreive RDBI\WDBI information
        for data in root.iter("ECUC-CONTAINER-VALUE"):
            def_Val = data.find("DEFINITION-REF")
            
            if def_Val is not None and def_Val.text.endswith("Dcm/DcmConfigSet/DcmDsp/DcmDspData"):
                did_dataInfo = find_recursive(data, "SHORT-NAME")
                # Check specific DID => DcmDspData
                if did_dataInfo.text in did_data_map:
                    did_size     = find_recursive_Value(data, "DEFINITION-REF", "DcmDspDataSize")
                    did_read_fct = find_recursive_Value(data, "DEFINITION-REF", "DcmDspDataReadFnc")
                    did_write_fct = find_recursive_Value(data, "DEFINITION-REF", "DcmDspDataWriteFnc")

                    if did_size is not None:
                        # Add +7 to rounds up and get the right size (byte numbers)
                        # Note : // operator is the floor division operator => rounds down to the nearest whole number
                        did_size = (int(did_size) + 7) // 8
                    did_data_map[did_dataInfo.text]["Size"] = did_size
                    did_data_map[did_dataInfo.text]["Read"] = did_read_fct
                    did_data_map[did_dataInfo.text]["Write"] = did_write_fct

            # Retreive RC
            if def_Val is not None and def_Val.text.endswith("Dcm/DcmConfigSet/DcmDsp/DcmDspRoutine"):
                rc_start_fct  = find_recursive_Value(data, "DEFINITION-REF", "DcmDspStartRoutineFnc")
                rc_stop_fct   = find_recursive_Value(data, "DEFINITION-REF", "DcmDspStopRoutineFnc")
                rc_result_fct = find_recursive_Value(data, "DEFINITION-REF", "DcmDspRequestResultsRoutineFnc")
                rc_id         = find_recursive_Value(data, "DEFINITION-REF", "DcmDspRoutineIdentifier")
                rc_info = find_recursive_Value(data, "DEFINITION-REF", "DcmDspRoutineInfoRef")

                # Convert and clean RC ID format
                rc_id = str(hex(int(rc_id))).upper()[2:].zfill(4)
                
                # Get RC Info definition from DcmDspRoutineInfoRef
                if rc_info is not None:
                    rc_info = rc_info.split('/')[-1]
                if rc_id not in rc_data_map:
                    rc_data_map[rc_id] = {
                        "RC ID": rc_id,
                        "Start RC": rc_start_fct,
                        "Stop RC": rc_stop_fct,
                        "Result RC": rc_result_fct,
                        "ref_info": rc_info
                    }
                    rc_data_map[rc_id] |= rc_dataInfo_map[rc_info]
                else:
                    print(f"reassignement of {rc_id} is ignored")

    else:
        print(f"extractDataFromArxml: {file_path} is not present")

    did_data = list(did_data_map.values())
    rc_data = list(rc_data_map.values())
    return did_data, rc_data


def writeIntoExcel(did_data, rc_data, StatusPath, dataPath):
    # Write DID data into the Excel file
    did_read  = []
    did_write = []
    rc_start  = []
    rc_result = []

    df_did_data = pd.DataFrame(did_data)
    df_rc_data  = pd.DataFrame(rc_data)
    
    with pd.ExcelWriter(dataPath, engine='openpyxl', mode='w') as writer:
        # Write DID data into the Excel file
        df_did_data.to_excel(writer, sheet_name='DID List', index=False)
        # Write RC data into the Excel file
        df_rc_data.to_excel(writer, sheet_name='RC List', index=False)

    for row in did_data:
        if (row['Read'] != '' and row['Read'] is not None and row['Size'] is not None):
            did_read.append({'DID': row['DID'], 'Status': '', 'Data': '', 'Error': '', 'Size': row['Size']})
        if (row['Write'] != '' and row['Write'] is not None and row['Size'] is not None):
            dataToWrite = ";".join('0' for _ in range(int(row['Size'])))
            did_write.append({'DID': row['DID'], 'Status': '', 'Error': '', 'Data': dataToWrite, 'Size': row['Size']})

    for row in rc_data:
        if (row['Start RC'] != '' and row['Start RC'] is not None):
            rc_start.append({'RC ID': row['RC ID'], 'Status': '', 'Data In': row['Start DataIn'], 'Error': ''})
        if (row['Result RC'] != '' and row['Result RC'] is not None):
            rc_result.append({'RC ID': row['RC ID'], 'Status': '', 'Data Out': row['Result DataOut'], 'Error': ''})
    
    df_did_read  = pd.DataFrame(did_read)
    df_did_write = pd.DataFrame(did_write)
    df_rc_start  = pd.DataFrame(rc_start)
    df_rc_result = pd.DataFrame(rc_result)
    
    with pd.ExcelWriter(StatusPath, engine='openpyxl', mode='w') as writer:
        df_did_read.to_excel(writer,  sheet_name='DID Read',  index=False)
        df_did_write.to_excel(writer, sheet_name='DID Write', index=False)
        df_rc_start.to_excel(writer,  sheet_name='RC Start',  index=False)
        df_rc_result.to_excel(writer, sheet_name='RC Result', index=False)


def remove_duplicates(input_file, output_file):
    # Check if the input file exists
    if not os.path.isfile(input_file):
        print(f"Error: The file '{input_file}' does not exist.")
        return

    # Check if the input file has the correct extension
    if not input_file.lower().endswith(('.xlsx', '.xls')):
        print(f"Error: The file '{input_file}' is not a valid Excel file.")
        return

    try:
        # Read the Excel file
        df = pd.read_excel(input_file)

        # Remove duplicate rows
        df_cleaned = df.drop_duplicates()

        # Save the cleaned DataFrame back to Excel
        df_cleaned.to_excel(output_file, index=False)
        print(f"Cleaned file saved as '{output_file}'.")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    # Replace local variable with the config 
    dir_name = os.path.dirname(os.path.abspath(__file__))
    FileConfig = loadConfigFilePath(dir_name)
    load_config(globals(), globals(), FileConfig)

    # Initialize path for ARXML and lists
    path_arxml = None
    DIDList = []
    RCList = []
    file_list = []

    # path_DIDStatus = os.path.join(dir_name, DIDStatusExcel)
    # path_DIDData   = os.path.join(dir_name, DIDDataExcel)

    if(PathToArxml is not None):
        path_arxml = os.path.join(dir_name, PathToArxml)

        # Extract DID\RC data :
        DIDList, RCList = extractDataFromArxml(path_arxml)

    elif (PathToArxmlList is not None):

        file_list = [os.path.join(dir_name, PathToFile) for PathToFile in PathToArxmlList]

        # Extract DID\RC data :
        for file_path in file_list:
            DIDListTemp, RCListTemp = extractDataFromArxml(file_path)
            DIDList.extend(DIDListTemp)
            RCList.extend(RCListTemp)

    else:
        print('Error : Please review the project Config file fields')

    writeIntoExcel(DIDList, RCList, DIDStatusExcel, DIDDataExcel)
    
    # remove_duplicates(DIDDataExcel, DIDDataExcel)
