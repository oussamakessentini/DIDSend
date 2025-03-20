from UDS.UDS_Frame import UDS_Frame 
from UDS.utils import *
import pandas as pd

if __name__ == "__main__":
    FileConfig=loadConfigFilePath()

    Pcan = UDS_Frame(FileConfig=FileConfig, IsFiltered=True)

    InHex = True

    FileTraceCanName = "TraceCanExcel"

    # Create an initial DataFrame
    df = pd.DataFrame(columns=["ID", "Raw_Data", "Type", "Size", "Comments"])
    IndexFile = 1

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
            FileTraceCanNameTemp = FileTraceCanName+f"_{IndexFile}.xlsx"
            IndexFile+=1
            print(f"Storing trace to {FileTraceCanNameTemp}")
            with pd.ExcelWriter(FileTraceCanNameTemp, engine='openpyxl', mode='w') as writer:
                df.to_excel(writer, sheet_name='Trace', index=False)
            df = df.drop(df.index)

            user_input = input("Enter: e to exit else enter anything")
            if user_input == "e":
                print("End of Program")
                exit(0)