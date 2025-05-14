from UDS.UDS_Frame import UDS_Frame
import pandas as pd
from UDS.Utils import *
from openpyxl import load_workbook
from openpyxl.styles import PatternFill
from openpyxl.formatting.rule import CellIsRule, FormulaRule
import time

project = None
DiagSeqExcel = None

def processDiagSeqs(Uds):
    # Read all sheets into a dictionary
    excel_data: dict[str, pd.DataFrame] = pd.read_excel(DiagSeqExcel, sheet_name=None, dtype=str, na_values=[], keep_default_na=False)

    # Iterate through all sheets
    for sheet_name, df in excel_data.items():
        print(f"Sheet: {sheet_name}")
        
        # Loop over the sheet "DID Read" line by line
        for index, line in df.iterrows():

            if(line['Command'] == 'RDBI'):
                status, data, error = Uds.Pcan_ReadDID(line['DID'], line['Size'])
                df.at[index, 'Data'] = data

            elif(line['Command'] == 'WDBI'):
                status, error = Uds.Pcan_WriteDID(line['DID'], str(line['Data']))

            elif(line['Command'] == 'RC_S'):
                status, data, error = Uds.Pcan_StartRC(str(line['DID']))

            elif(line['Command'] == 'RC_R'):
                status, data, error = Uds.Pcan_ResultRC(str(line['DID']))

            elif(line['Command'].lower() == 'wait'):
                time.sleep(float(line['Data']))
                status = 'OK'

            else:
                print('Command not reconized : ' + str(line)) # for debug
            
            # Update the line with the results
            df.at[index, 'Status'] = status
            df.at[index, 'Error']  = error

            # Clear data
            status = ''
            data   = ''
            error  = ''

        # Save all modified sheets back to the same or a new Excel file
        with pd.ExcelWriter(DiagSeqExcel, engine='openpyxl') as writer:
            for sheet_name, df in excel_data.items():
                df.to_excel(writer, sheet_name=sheet_name, index=False)

        # Set the colors of the painter format with rules
        applyPainterFormat(DiagSeqExcel, 'E')

        # print(f"{DiagSeqExcel} updated successfully")
    
    print("Processing diagnostic sequences OK")


if __name__ == "__main__":

    dir_name = os.path.dirname(os.path.abspath(__file__))
    FileConfig = loadConfigFilePath(dir_name)
    load_config(globals(), globals(), FileConfig)

    if(project == 'PR105'):
        Uds = UDS_Frame(FileConfig=FileConfig)
        
        # Activate extented session before executing Excel file
        Uds.StartSession(3)

        # Execute all the diagnostic sequences
        processDiagSeqs(Uds)

    elif(project == 'PR128'):
        Uds = UDS_Frame(FileConfig=FileConfig)

        # Activate extented session before executing Excel file
        Uds.StartSession(3)

        # Execute all the diagnostic sequences
        # processDiagSeqs(Uds)
    else:
        print('Please add your project configuration')
