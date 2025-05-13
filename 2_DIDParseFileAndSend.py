from UDS.UDS_Frame import UDS_Frame
import pandas as pd
from UDS.Utils import *
from openpyxl import load_workbook
from openpyxl.styles import PatternFill
from openpyxl.formatting.rule import CellIsRule

project = None
DIDStatusExcel = None

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
        adjusted_width = (max_length + 2) if max_length < 100 else 100  # Ajouter un peu d'espace
        ws.column_dimensions[column].width = adjusted_width

def Pcan_ReadDID(Pcan, did, size):
    retVal = Pcan.ReadDID(did)

    if is_hex(retVal[0]) == True:
        data = ";".join(format_hex(int(x, 16)) for x in retVal)
        if is_int(size):
            if (len(retVal) == int(size)):
                result = "OK"
                Error = ""
            else:
                result = "NOK"
                Error = f"Data received with incorrect size, data size received {len(retVal)}, data size expected {size}"
        else:
            result = "NOK"
            Error = f"size is not an integer {size}"
    else:
        result = "NOK"
        data = ""
        Error = str(retVal[1])
    return result, data, Error

def Pcan_WriteDID(Pcan, did, dataraw=None):
    # Clean raw data
    data = [int(x, 16) for x in dataraw.split(";") if x]
    # Process diagnostic request
    retVal = Pcan.WriteDID(did, data)
    # Process the result
    if retVal[1] == True:
        status = "OK"
        Error = ""
    else:
        status = "NOK"
        Error = str(retVal[2])
    # Return a tuple (status, error)
    return status, Error

def Pcan_StartRC(Pcan, rcdid, dataraw=None):
    # Clean raw data
    data = [int(x, 16) for x in dataraw.split(";") if x]
    # Process diagnostic request
    retVal = Pcan.StartRC(rcdid, data)
    # Process the result
    if retVal == 'ROUTINE_STARTED':
        status = "OK"
        Error = ""
    else:
        status = "NOK"
        Error = str(retVal)
    # Return a tuple (status, error)
    return status, Error

def Pcan_ResultRC(Pcan, rcdid):
    # Process diagnostic request
    retVal = Pcan.ResultRC(rcdid)
    # Process the result
    if retVal == 'ROUTINE_FINISHED_OK' or retVal == 'ROUTINE_IN_PROCESS':
        status = "OK"
        Error = ""
    else:
        status = "NOK"
        Error = str(retVal)
    # Return a tuple (status, error)
    return status, Error

def parseAndSend(Pcan):
    # Load Excel sheets "DID Read", "DID Write", "RC Start", "RC Result" and avoid NaN in empty cells
    df_did_read  = pd.read_excel(DIDStatusExcel, sheet_name='DID Read',  dtype=str, na_values=[], keep_default_na=False)
    df_did_write = pd.read_excel(DIDStatusExcel, sheet_name='DID Write', dtype=str, na_values=[], keep_default_na=False)
    df_rc_start  = pd.read_excel(DIDStatusExcel, sheet_name='RC Start',  dtype=str, na_values=[], keep_default_na=False)
    df_rc_result = pd.read_excel(DIDStatusExcel, sheet_name='RC Result', dtype=str, na_values=[], keep_default_na=False)

    # Loop over the sheet "DID Read" line by line
    for index, line in df_did_read.iterrows():
        # Call the function Pcan.ReadDID with the DID of the line
        status, data, error = Pcan_ReadDID(Pcan, line['DID'], line['Size'])
        
        # Update the line with the results
        df_did_read.at[index, 'Status'] = status
        df_did_read.at[index, 'Data']   = data
        df_did_read.at[index, 'Error']  = error

    # Loop over the sheet "DID Write" line by line
    for index, line in df_did_write.iterrows():
        # Call the function Pcan.WriteDID with the DID of the line
        status, error = Pcan_WriteDID(Pcan, line['DID'], line['Data'])
        
        # Update the line with the results
        df_did_write.at[index, 'Status'] = status
        df_did_write.at[index, 'Error']  = error

    # Loop over the sheet "RC Start" line by line
    for index, line in df_rc_start.iterrows():
        # Call the function Pcan.StartRC with the RC DID of the line
        status, error = Pcan_StartRC(Pcan, line['RC ID'], line['Data In'])
        
        # Update the line with the results
        df_rc_start.at[index, 'Status'] = status
        df_rc_start.at[index, 'Error']  = error
    
    for index, line in df_rc_result.iterrows():
        # Call the function Pcan.ResultRC with the RC DID of the line
        status, error = Pcan_ResultRC(Pcan, line['RC ID'])
        
        # Update the line with the results
        df_rc_result.at[index, 'Status'] = status
        df_rc_result.at[index, 'Error']  = error
    
    # Save the modifications in the Excel file
    with pd.ExcelWriter(DIDStatusExcel, engine='openpyxl', mode='w') as writer:
        df_did_read.to_excel(writer,  sheet_name='DID Read',  index=False)
        df_did_write.to_excel(writer, sheet_name='DID Write', index=False)
        df_rc_start.to_excel(writer,  sheet_name='RC Start',  index=False)
        df_rc_result.to_excel(writer, sheet_name='RC Result', index=False)

    # Load Excel file with openpyxl to add painter format rules
    wb = load_workbook(DIDStatusExcel)
    ws_did_read  = wb['DID Read']
    ws_did_write = wb['DID Write']
    ws_rc_start  = wb['RC Start']
    ws_rc_result = wb['RC Result']

    # Adjust the width of columns to adapt with the content
    adjustWidth(ws_did_read)
    adjustWidth(ws_did_write)
    adjustWidth(ws_rc_start)
    adjustWidth(ws_rc_result)

    # Set the colors for the painter format
    fill_green = PatternFill(start_color="00FF00", end_color="00FF00", fill_type="solid")  # Green
    fill_red = PatternFill(start_color="FF0000", end_color="FF0000", fill_type="solid")    # Red

    # Add conditional format rules for the column "Status"
    for ws in [ws_did_read, ws_did_write, ws_rc_start, ws_rc_result]:
        max_row = ws.max_row
        cell_range = f"B2:B{max_row}"
        # Rule 1: if the value is "OK" => green
        ws.conditional_formatting.add(cell_range, CellIsRule(operator='equal', formula=['"OK"'], fill=fill_green))
        # Rule 2: if the value is "NOK" => red
        ws.conditional_formatting.add(cell_range, CellIsRule(operator='equal', formula=['"NOK"'], fill=fill_red))

    # Save the Excel file with the rules and format painter
    wb.save(DIDStatusExcel)

    print(f"{DIDStatusExcel} updated successfully")


if __name__ == "__main__":

    dir_name = os.path.dirname(os.path.abspath(__file__))
    FileConfig = loadConfigFilePath(dir_name)
    load_config(globals(), globals(), FileConfig)

    if(project == 'PR105'):
        Pcan = UDS_Frame(FileConfig=FileConfig)
        
        # Activate extented session before executing Excel file
        Pcan.StartSession(3)

        # Execute all the diagnostic services
        parseAndSend(Pcan)

    elif(project == 'PR128'):
        Pcan = UDS_Frame(FileConfig=FileConfig)

        # Activate extented session before executing Excel file
        Pcan.StartSession(3)

        # Execute all the diagnostic services
        parseAndSend(Pcan)
    else:
        print('Please add your project configuration')
