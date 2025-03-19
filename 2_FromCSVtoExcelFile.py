import pandas as pd
import csv
import ast  # To safely convert string representation of list/dict
from UDS.utils import *

DIDStatusCsv = "DIDStatus.csv"
DIDStatusExcel = 'DID_Status_PR128.xlsx'

if __name__ == "__main__":
    # replace local variable with the config 
    FileConfig = loadConfigFilePath()
    load_config(globals(), globals(), FileConfig)
    
    # Open and read the CSV file
    with open(DIDStatusCsv, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file, delimiter=';')  # Use semicolon as delimiter

        data_read = []
        data_write = []
        for row in reader:
            # Convert the 'Variable' column from a string to a Python list
            row['Variable'] = ast.literal_eval(row['Variable'])  # Safely convert string to list
            if (row['Read'] == 'True'):
                data_read.append({'DID': row['DID'], 'Resultat': '', 'Data': '', 'Error': '', 'Size': row['DID_SIZE']})
            if (row['Write'] == 'True'):
                data = ";".join('0' for _ in range(int(row['DID_SIZE'])))
                data_write.append({'DID': row['DID'], 'Status': '', 'Error': '', 'Data': data, 'Size': row['DID_SIZE']})
        df_read = pd.DataFrame(data_read)
        df_write = pd.DataFrame(data_write)

        with pd.ExcelWriter(DIDStatusExcel, engine='openpyxl', mode='w') as writer:
                df_read.to_excel(writer, sheet_name='DID Read', index=False)
                df_write.to_excel(writer, sheet_name='DID Write', index=False)



