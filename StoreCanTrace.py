from UDS.UDS_Frame import UDS_Frame 
from UDS.utils import *
import pandas as pd

if __name__ == "__main__":
    FileConfig=loadConfigFilePath()

    Pcan = UDS_Frame(FileConfig=FileConfig, IsFiltered=True)

    InHex = True

    TraceCanExcel = "TraceCanExcel.xlsx"

    # Create an initial DataFrame
    df = pd.DataFrame(columns=["ID", "Raw_Data", "Type", "Size", "Comments"])

    while True:
        try:
            msg = Pcan.ReadMessages()
            if (msg is not None):
                row = {"ID": msg["id"] if InHex == False else format_hex(msg["id"]), \
                       "Raw_Data": msg["data"] if InHex == False else [format_hex(item) for item in msg["data"]],\
                        "Type": "TX" if Pcan.TxId == msg["id"] else "RX" if Pcan.RxId == msg["id"] else "", \
                        "Size": msg["len"], \
                        "Comments": ""}
                print(row)
                df.loc[len(df)] = row
        except KeyboardInterrupt:
            print(f"Storing trace to {TraceCanExcel}")
            with pd.ExcelWriter(TraceCanExcel, engine='openpyxl', mode='w') as writer:
                df.to_excel(writer, sheet_name='Trace', index=False)
            exit(0)