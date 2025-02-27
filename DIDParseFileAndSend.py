from UDS.PCANBasic import *
from UDS.UDS_Frame import UDS_Frame
import pandas as pd
from Utils import *

PROJECT = 'PR128'

def Pcan_ReadDID(Pcan, did):
    retVal = Pcan.ReadDID(did)

    if is_hex(retVal[0]) == True:
        result = "OK"
        data = ";".join(format_hex(int(x, 16)) for x in retVal)
        Error = ""
    else:
        result = "KO"
        data = ""
        Error = str(retVal[1])
    return result, data, Error

def Pcan_WriteDID(Pcan, did, dataraw):
    data = [int(x, 16) for x in dataraw.split(";")]
    retVal = Pcan.WriteDID(did, data)
    if retVal[1] == True:
        status = "Success"
        Error = ""
    else:
        status = "Failed"
        Error = str(retVal[2])
    # Retourne un tuple (status, error)
    return status, Error

def parseAndSend(Pcan):
    # Chemin vers le fichier Excel
    fichier_excel = 'DID_Status.xlsx'

    # Charger les feuilles "DID Read" et "DID Write" dans des DataFrames
    df_read = pd.read_excel(fichier_excel, sheet_name='DID Read', dtype=str)
    df_write = pd.read_excel(fichier_excel, sheet_name='DID Write', dtype=str)

    # Parcourir la feuille "DID Read" ligne par ligne
    for index, ligne in df_read.iterrows():
        # Appeler la fonction Pcan.ReadDID avec le DID de la ligne
        resultat, data, error = Pcan_ReadDID(Pcan, ligne['DID'])
        
        # Mettre à jour la ligne avec les résultats
        df_read.at[index, 'Resultat'] = resultat
        df_read.at[index, 'Data'] = data
        df_read.at[index, 'Error'] = error

    # Parcourir la feuille "DID Write" ligne par ligne
    for index, ligne in df_write.iterrows():
        # Appeler la fonction Pcan.WriteDID avec le DID et la Data de la ligne
        status, error = Pcan_WriteDID(Pcan, ligne['DID'], ligne['Data'])
        
        # Mettre à jour la ligne avec les résultats
        df_write.at[index, 'Status'] = status
        df_write.at[index, 'Error'] = error

    # Sauvegarder les modifications dans le même fichier Excel
    with pd.ExcelWriter(fichier_excel, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
        df_read.to_excel(writer, sheet_name='DID Read', index=False)
        df_write.to_excel(writer, sheet_name='DID Write', index=False)

    print(f"Le fichier {fichier_excel} a été mis à jour avec succès.")

if __name__ == "__main__":

    if(PROJECT == 'PR105'):
        TxId = 0x6B4
        RxId = 0x694
        Pcan = UDS_Frame(PCAN_USBBUS1, False, PCAN_BAUD_500K, TxId, RxId, False, True)

        # print(Pcan.getFrameFromId(596))
        Pcan.StartSession(3)
        # Pcan.StartReset(2)
        # Pcan.StartReset(3)
        # print(Pcan.ReadDID("F41C"))
        # print(Pcan.ReadDID("D863"))
        # print(Pcan.ReadDID("0101"))
        parseAndSend(Pcan)
        
    else:
        TxId = 0x18DADBF1
        RxId = 0x18DAF1DB
        Pcan = UDS_Frame(PCAN_USBBUS1, False, PCAN_BAUD_500K, TxId, RxId, True, True)

        Pcan.StartSession(3)
        # print(Pcan.ReadDID("8281"))
        parseAndSend(Pcan)
