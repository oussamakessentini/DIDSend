import os
from UDS.UDSInterface import * 
from UDS.Utils import *
import pandas as pd

if __name__ == "__main__":
    dir_name = os.path.dirname(os.path.abspath(__file__))
    FileConfig = loadConfigFilePath(dir_name)

    Pcan = UDSInterface(FileConfig=FileConfig, IsFiltered=True)

    InHex = True

    FileTraceCanName = "TraceCanExcel"

    # Create an initial DataFrame
    df = pd.DataFrame(columns=["id", "Data", "Type", "Size", "Comments"])
    IndexFile = 1

    while True:
        try:
            Pcan.startCanStoringTrace(df)
        except Exception as e:
            print(f"error {e}")
        except KeyboardInterrupt:
            FileTraceCanNameTemp = FileTraceCanName+f"_{IndexFile}.xlsx"
            IndexFile+=1
            print(f"Storing trace to {FileTraceCanNameTemp}")
            with pd.ExcelWriter(FileTraceCanNameTemp, engine='openpyxl', mode='w') as writer:
                df.to_excel(writer, sheet_name='Trace', index=False)
            df = df.drop(df.index)

            try:
                user_input = input("Enter: c and Enter to continue else Enter to exit")
                if user_input != "c":
                    print("End of Program")
                    exit(0)
            except KeyboardInterrupt:
                exit(0)
            except EOFError:
                exit(0)