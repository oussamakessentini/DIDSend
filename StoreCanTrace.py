from UDS.UDS_Frame import UDS_Frame 
from UDS.utils import *
import pandas as pd

if __name__ == "__main__":
    FileConfig=loadConfigFilePath()

    Pcan = UDS_Frame(FileConfig=FileConfig, IsFiltered=True)

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
                user_input = input("Enter: e to exit else enter anything : ")
                if user_input == "e":
                    print("End of Program")
                    exit(0)
            except KeyboardInterrupt:
                exit(0)
            except EOFError:
                exit(0)