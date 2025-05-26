from UDS.UDSInterface import *
import pandas as pd
from UDS.Utils import *
from openpyxl import load_workbook
from openpyxl.styles import PatternFill
from openpyxl.formatting.rule import CellIsRule

project = None
DIDStatusExcel = None

def parseAndSend(Uds):
    # Load Excel sheets "DID Read", "DID Write", "RC Start", "RC Result" and avoid NaN in empty cells
    df_did_read  = pd.read_excel(DIDStatusExcel, sheet_name='DID Read',  dtype=str, na_values=[], keep_default_na=False)
    df_did_write = pd.read_excel(DIDStatusExcel, sheet_name='DID Write', dtype=str, na_values=[], keep_default_na=False)
    df_rc_start  = pd.read_excel(DIDStatusExcel, sheet_name='RC Start',  dtype=str, na_values=[], keep_default_na=False)
    df_rc_result = pd.read_excel(DIDStatusExcel, sheet_name='RC Result', dtype=str, na_values=[], keep_default_na=False)

    # Loop over the sheet "DID Read" line by line
    for index, line in df_did_read.iterrows():
        # Call the function Uds.Pcan_ReadDID with the DID of the line
        status, data, error = Uds.Pcan_ReadDID(line['DID'], line['Size'])
        
        # Update the line with the results
        df_did_read.at[index, 'Status'] = status
        df_did_read.at[index, 'Data']   = data
        df_did_read.at[index, 'Error']  = error

    # Loop over the sheet "DID Write" line by line
    for index, line in df_did_write.iterrows():
        # Call the function Uds.Pcan_WriteDID with the DID of the line
        status, error = Uds.Pcan_WriteDID(line['DID'], line['Data'])
        
        # Update the line with the results
        df_did_write.at[index, 'Status'] = status
        df_did_write.at[index, 'Error']  = error

    # Loop over the sheet "RC Start" line by line
    for index, line in df_rc_start.iterrows():
        # Call the function Uds.Pcan_StartRC with the RC DID of the line
        status, data, error = Uds.Pcan_StartRC(line['RC ID'], line['Data In'])
        
        # Update the line with the results
        df_rc_start.at[index, 'Status'] = status
        df_rc_start.at[index, 'Error']  = error
    
    for index, line in df_rc_result.iterrows():
        # Call the function Uds.Pcan_ResultRC with the RC DID of the line
        status, data, error = Uds.Pcan_ResultRC(line['RC ID'])

        # Update the line with the results
        df_rc_result.at[index, 'Status'] = status
        df_rc_result.at[index, 'Error']  = error
    
    # Save the modifications in the Excel file
    with pd.ExcelWriter(DIDStatusExcel, engine='openpyxl', mode='w') as writer:
        df_did_read.to_excel(writer,  sheet_name='DID Read',  index=False)
        df_did_write.to_excel(writer, sheet_name='DID Write', index=False)
        df_rc_start.to_excel(writer,  sheet_name='RC Start',  index=False)
        df_rc_result.to_excel(writer, sheet_name='RC Result', index=False)

    # Set the colors of the painter format with rules
    applyPainterFormat(DIDStatusExcel, 'B')
    
    print(f"{DIDStatusExcel} updated successfully")


if __name__ == "__main__":

    dir_name = os.path.dirname(os.path.abspath(__file__))
    FileConfig = loadConfigFilePath(dir_name)
    load_config(globals(), globals(), FileConfig)

    if(project == 'PR105'):
        Uds = UDSInterface(FileConfig=FileConfig)
        
        # Activate extented session before executing Excel file
        Uds.StartSession(3)

        # Execute all the diagnostic services
        parseAndSend(Uds)

    elif(project == 'PR128'):
        Uds = UDSInterface(FileConfig=FileConfig)

        # Activate extented session before executing Excel file
        Uds.StartSession(3)

        # Execute all the diagnostic services
        parseAndSend(Uds)
    else:
        print('Please add your project configuration')
