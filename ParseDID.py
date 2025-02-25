import xml.etree.ElementTree as ET
import re
import os

dir_name = os.path.dirname(os.path.abspath(__file__))
path_DIDList = os.path.join(dir_name, "../../../Outputs/Log/DIDStatus.csv")
path_Rte = os.path.join(dir_name, "../../../Inputs/DEXT/BMS_AW010700.arxml")
path_Connection = os.path.join(dir_name, "../../../Inputs/DEXT/Dext_Connections.arxml")
# path_ConnectionAdded = os.path.join(dir_name, "../../../Inputs/Arxml/BSW/DcmDID_Connectivity.arxml")

enum_pattern_ReadWriteDID = re.compile(
    r'<SHORT-NAME>DCM_DID_(\w{4})_([R|W]\w*)<\/SHORT-NAME>',
    re.MULTILINE
)

def extractOsTaskWithIndex(file_path):
    with open(file_path, 'r') as file:
        content = file.read()
    
    enums = {}
    for match in enum_pattern_ReadWriteDID.finditer(content):
        did_name = match.group(1)
        FunctionName = match.group(2)

        enums.setdefault(did_name, {'Read': False, 'Write': False})
        
        if FunctionName == "Read":
            enums[did_name]["Read"] = True
        elif FunctionName == "Write":
            enums[did_name]["Write"] = True
        else:
            continue

    return enums

def remove_namespace(tree):
    root = tree.getroot()
    for elem in root.iter():
        elem.tag = re.sub(r'\{.*?\}', '', elem.tag)  # Supprimer les namespaces
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

def extract_did_data(file_path):
    tree = ET.parse(file_path)
    tree = remove_namespace(tree)
    root = tree.getroot()
    
    did_data = []
    
    for did in root.iter("DIAGNOSTIC-DATA-IDENTIFIER"):
        did_short_name = did.find("SHORT-NAME")
        if did_short_name is not None:
            did_name = did_short_name.text[-4:]
            
            for diag_param in did.iter("DIAGNOSTIC-PARAMETER"):  
                element_short_name = find_recursive(diag_param, "SHORT-NAME")
                bit_offset = find_recursive(diag_param, "BIT-OFFSET")
                
                if element_short_name is not None and bit_offset is not None:
                    did_data.append({
                        "DID_SHORT_NAME": did_name,
                        "DATA_ELEMENT_SHORT_NAME": element_short_name.text,
                        "BIT_OFFSET": bit_offset.text
                    })
    
    return did_data

def extract_did_connection(file_path):
    tree = ET.parse(file_path)
    tree = remove_namespace(tree)
    root = tree.getroot()
    
    connection_data = []
    
    for connection in root.iter("ASSEMBLY-SW-CONNECTOR"):
        connection_short_name = connection.find("SHORT-NAME")
        if connection_short_name is not None and "DCM_DID" in connection_short_name.text:
            target_p_port_ref = find_recursive(connection, "TARGET-P-PORT-REF")
            target_r_port_ref = find_recursive(connection, "TARGET-R-PORT-REF")
            readLink = False
            WriteLink = False
            if "DCM_DID" in target_p_port_ref.text:
                match = re.search(r'DCM_DID_(\w{4})_([\w_]+)', target_p_port_ref.text)
                WriteLink = True
            elif "DCM_DID" in target_r_port_ref.text:
                match = re.search(r'DCM_DID_(\w{4})_([\w_]+)', target_r_port_ref.text)
                readLink = True
            else:
                match = None
            if match:
                did_index = match.group(1)
                did_name = match.group(2)

            connection_data.append({
                    "DID_INDEX": did_index,
                    "DID_NAME": did_name,
                    "TARGET-P-PORT-REF": target_p_port_ref.text if target_p_port_ref is not None else None,
                    "TARGET-R-PORT-REF": target_r_port_ref.text if target_r_port_ref is not None else None,
                    "WRITE-CONNECTION": WriteLink,
                    "READ-CONNECTION": readLink
                })
            
    return connection_data

def merge_did_and_assembly(DIDList, DID_Variable, DID_Connection):
    merged_data = []
    for did in DID_Variable:
        item = {
            "DID_INDEX": did["DID_SHORT_NAME"],
            "DID_VAR_NAME": did["DATA_ELEMENT_SHORT_NAME"],
            "BIT_OFFSET": did["BIT_OFFSET"],
            "Read": DIDList[did["DID_SHORT_NAME"]]["Read"],
            "Write": DIDList[did["DID_SHORT_NAME"]]["Write"]
        }
        for assembly in DID_Connection:
            if did["DID_SHORT_NAME"] == assembly["DID_INDEX"] and did["DATA_ELEMENT_SHORT_NAME"] == assembly["DID_NAME"]:
                if assembly["WRITE-CONNECTION"] == True:
                    if "TARGET-REF" not in item:
                        item["TARGET-REF"] = assembly["TARGET-P-PORT-REF"]
                    elif item["TARGET-REF"] != assembly["TARGET-P-PORT-REF"]:
                        item["TARGET-REF"] = f"error {item["TARGET-REF"]} != {assembly["TARGET-P-PORT-REF"]}"
                    item["TARGET-R-PORT-REF"] = assembly["TARGET-R-PORT-REF"]
                if assembly["READ-CONNECTION"] == True:
                    if "TARGET-REF" not in item:
                        item["TARGET-REF"] = assembly["TARGET-R-PORT-REF"]
                    elif item["TARGET-REF"] != assembly["TARGET-R-PORT-REF"]:
                        item["TARGET-REF"] = f"error {item["TARGET-REF"]} != {assembly["TARGET-R-PORT-REF"]}"
                    item["TARGET-P-PORT-REF"] = assembly["TARGET-P-PORT-REF"]
        merged_data.append(item)
    return merged_data

def writeIntoCSV(data):
    try:
        with open(path_DIDList, "w") as f:
            f.write("DID;Variable_Name;Bit_Offset;Target_Ref;Port_Provider;Port_Request;Read;Write\n")
            for item in data:
                f.write(f"{item.get('DID_INDEX', '')};{item.get('DID_VAR_NAME', '')};{item.get('BIT_OFFSET', '')};{item.get('TARGET-REF', '')};{item.get('TARGET-P-PORT-REF', '')};{item.get('TARGET-R-PORT-REF', '')};{item.get('Read', '')};{item.get('Write', '')}\n")
    except Exception as e:
        print(str(e))

if __name__ == "__main__":
    DIDList = extractOsTaskWithIndex(path_Rte)
    DID_Variable = extract_did_data(path_Rte)
    DID_Connection = extract_did_connection(path_Connection)
    # DID_Connection.extend(extract_did_connection(path_ConnectionAdded))
    merged_info = merge_did_and_assembly(DIDList, DID_Variable, DID_Connection)
    writeIntoCSV(merged_info)
