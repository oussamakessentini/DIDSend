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
    loop_nb = 0
    loop_start_idx = 0
    max_loop = 1
    status = ''
    data   = ''
    error  = ''

    # Read all sheets into a dictionary
    excel_data: dict[str, pd.DataFrame] = pd.read_excel(DiagSeqExcel, sheet_name=None, dtype=str, na_values=[], keep_default_na=False)

    # Iterate through all sheets
    for sheet_name, df in excel_data.items():
        # Check Sheet name is starting with "DIAG_SEQ"
        if(sheet_name.startswith("DIAG_SEQ")):
            print(f"Processing {sheet_name}...")
            
            while loop_nb < max_loop:
                # print(f"🔁 loop_nb = {loop_nb} max_loop = {max_loop}")

                # Loop over the sheet "DID Read" line by line from a specific index
                for index, line in df.iloc[loop_start_idx:].iterrows():

                    if(line['Command'] == 'LOOP_START'):
                        max_loop = int(line['Data'])
                        loop_start_idx = index + 1

                    elif(line['Command'] == 'LOOP_END'):
                        loop_nb += 1
                        if(loop_nb < max_loop):
                            # break the loop for a new re-run
                            # print(loop_nb) # For debug
                            break
                        else:
                            # End the loop and continue
                            continue
                    
                    elif(line['Command'] == 'RDBI'):
                        status, data, error = Uds.Pcan_ReadDID(line['DID'], line['Size'])
                        df.at[index, 'Data'] = data

                    elif(line['Command'] == 'WDBI'):
                        status, error = Uds.Pcan_WriteDID(line['DID'], str(line['Data']))

                    elif(line['Command'] == 'RC_START'):
                        status, data, error = Uds.Pcan_StartRC(str(line['DID']), str(line['Data']))

                    elif(line['Command'] == 'RC_STOP'):
                        status, data, error = Uds.Pcan_StopRC(str(line['DID']))

                    elif(line['Command'] == 'RC_RESULT'):
                        status, data, error = Uds.Pcan_ResultRC(str(line['DID']))

                    elif(line['Command'] == 'CLEAR_DTC'):
                        status, error = Uds.Pcan_ClearDTC(str(line['Data']))

                    elif(line['Command'].lower() == 'wait'):
                        time.sleep(float(line['Data']))
                        status = 'OK'

                    else:
                        status = 'NOK'
                        error = 'Command not reconized : ' + str(line['Command'])
                    
                    # Update the line with the results
                    df.at[index, 'Status'] = status
                    df.at[index, 'Error']  = error

                    # Clear data
                    status = ''
                    data   = ''
                    error  = ''

                    # Detect latest command in the Excel sheet
                    if(index >= df.index.max()):
                        loop_nb += 1

            # Save all modified sheets back to the same or a new Excel file
            with pd.ExcelWriter(DiagSeqExcel, engine='openpyxl') as writer:
                for sheet_name, df in excel_data.items():
                    df.to_excel(writer, sheet_name=sheet_name, index=False)

            # Set the colors of the painter format with rules
            applyPainterFormat(DiagSeqExcel, 'E')

            # print(f"{DiagSeqExcel} updated successfully")
        else:
            continue # Excel sheet name not correct
    print("\nDiagnostic sequences processing => Done \n")


def processProgSeqs(Uds):
    status = ''
    data   = ''
    error  = ''
    # Read all sheets into a dictionary
    excel_data: dict[str, pd.DataFrame] = pd.read_excel(DiagSeqExcel, sheet_name=None, dtype=str, na_values=[], keep_default_na=False)

    # Iterate through all sheets
    for sheet_name, df in excel_data.items():
        # Check Sheet name is starting with "PROG_SEQ"
        if(sheet_name.startswith("PROG_SEQ")):
            print(f"Processing {sheet_name}...")
            # Loop over the sheet "DID Read" line by line
            for index, line in df.iterrows():

                if(line['Command'] == 'SW_RESET'):
                    if(line['DID'] == '1101'):
                        status, error = Uds.StartReset(0x1)
                    elif(line['DID'] == '1102'):
                        status, error = Uds.StartReset(0x2)
                    elif(line['DID'] == '1103'):
                        status, error = Uds.StartReset(0x3)
                    else:
                        print(f"{sheet_name} line : {index} => Reset command not reconized")

                elif(line['Command'].endswith("SESSION")):
                    if(line['DID'] == '1001'):
                        status, error = Uds.StartSession(0x1)
                    elif(line['DID'] == '1002'):
                        status, error = Uds.StartSession(0x2)
                    elif(line['DID'] == '1003'):
                        status, error = Uds.StartSession(0x3)
                    else:
                        print(f"{sheet_name} line : {index} => Session command not reconized")

                elif(line['Command'] == 'RDBI'):
                    status, data, error = Uds.Pcan_ReadDID(line['DID'], line['Size'])
                    df.at[index, 'Data'] = data
                
                elif(line['Command'] == 'WDBI'):
                    status, error = Uds.Pcan_WriteDID(line['DID'], str(line['Data']))

                elif(line['Command'] == 'RC_START'):
                    status, data, error = Uds.Pcan_StartRC(str(line['DID']), str(line['Data']))

                elif(line['Command'] == 'RC_RESULT'):
                    status, data, error = Uds.Pcan_ResultRC(str(line['DID']))
                
                elif((line['Command'] == 'REQUEST_DOWNLOAD') or
                     (line['Command'] == 'SECURE_ACCESS') or
                     (line['Command'] == 'TESTER_PRESENT') or
                     (line['Command'] == 'TRANSFERT_DATA')):
                    status, error = Uds.Pcan_WriteData(str(line['Data']))

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
        else:
            continue # Excel sheet name not correct
    print("\nProgrammation sequences processing => Done \n")


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

        # Execute all the programmation sequences
        processProgSeqs(Uds)

    elif(project == 'PR128'):
        Uds = UDS_Frame(FileConfig=FileConfig)

        # Activate extented session before executing Excel file
        Uds.StartSession(3)

        # Execute all the diagnostic sequences
        # processDiagSeqs(Uds)

        # Execute all the programmation sequences
        # processProgSeqs(Uds)
    else:
        print('Please add your project configuration')
