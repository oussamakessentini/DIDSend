import xml.etree.ElementTree as ET
import os
import re


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

def modify_arxml(file_path):
    # Parse the XML file
    tree = ET.parse(file_path)
    tree, namespace = remove_namespace(tree)
    root = tree.getroot()
    
    # Iterate through all elements to find the relevant tags
    for param in root.iter("ECUC-NUMERICAL-PARAM-VALUE"):
        definition_ref = param.find("DEFINITION-REF")
        value = param.find("VALUE")
        
        if definition_ref is not None and value is not None and value.text is not None:
            if "DcmDspDataByteSize" in definition_ref.text:
                definition_ref.text = definition_ref.text.replace("DcmDspDataByteSize", "DcmDspDataSize")
                value.text = str(int(value.text) * 8) if value.text.isdigit() else value.text
            elif "DcmDspDidByteOffset" in definition_ref.text:
                definition_ref.text = definition_ref.text.replace("DcmDspDidByteOffset", "DcmDspDidDataPos")
                value.text = str(int(value.text) * 8) if value.text.isdigit() else value.text
    
    # Restore namespace
    # tree = restore_namespace(tree, namespace)
    
    # Save modified file
    modified_file = file_path.replace(".arxml", "_modified.arxml")
    tree.write(file_path, encoding="utf-8", xml_declaration=True)
    print(f"Modified file saved as {file_path}")

# Example usage
dir_name = os.path.dirname(os.path.abspath(__file__))
path_file = os.path.join(dir_name, "../BmsGen2_Copy/Software/Config/RtaCar/ecu_config/bsw/HV_BMS_Project_Dcm_EcucValues.arxml")
modify_arxml(path_file)