import sys
import os
script_dir = os.path.dirname( __file__ )
sys.path.append( script_dir )
from UDS.UDS_Frame import UDS_Frame 
from ParseDID import extractOsTaskWithIndex

dir_name = os.path.dirname(os.path.abspath(__file__))
path_DIDSend = os.path.join(dir_name, "../../../Outputs/Log/DIDSendTest.csv")

def writeDataIntoCSV(data):
    try:
        with open(path_DIDSend, "w") as f:
            f.write("DID;Read;Write\n")
            for (key, val) in data.items():
                f.write(f"{key};{val.get('Read', '')};{val.get('Write', '')}\n")
    except Exception as e:
        print(str(e))

# Pcan = UDS_Frame()

from ctypes import *

__m_dllBasic = windll.LoadLibrary("C:\\Program Files\\PEAK-System\\PEAK-Drivers 4\\Tools\\PcanApi.dll")
import pefile

dll_path = "C:\\Program Files\\PEAK-System\\PEAK-Drivers 4\\Tools\\PcanApi.dll"

# Load the DLL file
pe = pefile.PE(dll_path)

# Get exported functions
if hasattr(pe, "DIRECTORY_ENTRY_EXPORT"):
    for exp in pe.DIRECTORY_ENTRY_EXPORT.symbols:
        print(f"Function: {exp.name.decode() if exp.name else 'Unnamed'} at 0x{exp.address:X}")
else:
    print("No exported functions found.")
print(__m_dllBasic.PCAN_Status())
i=1
# Pcan.WriteMessages(Pcan.TxId, [2, 0x3E, 0x00])
# print(Pcan.ReadMessages())
# Pcan.StartSession(3)
# print(Pcan.ReadDID("8281"))
# print(Pcan.ReadDID("8282"))
# print(Pcan.ReadDID("8283"))
# print(Pcan.ReadDID("8284"))
# print(Pcan.ReadDID("8285"))
# print(Pcan.ReadDID("8286"))
# print(Pcan.ReadDID("8287"))
# print(Pcan.ReadDID("828B"))
# print(Pcan.ReadDID("828C"))
# print(Pcan.ReadDID("828F"))

# print(Pcan.WriteDID("8282", [0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0, 0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0,
#                        0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0, 0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0,
#                        0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0, 0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0,
#                        0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0, 0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0,
#                        0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0, 0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0,
#                        0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0, 0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0,
#                        0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0, 0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0,
#                        0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0, 0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0]))
# print(Pcan.WriteDID("8283", [0x01]))
# print(Pcan.WriteDID("8285", [0x02]))
# print(Pcan.WriteDID("8286", [0x03]))

# print(Pcan.ReadDID("8282"))
# print(Pcan.ReadDID("8283"))
# print(Pcan.ReadDID("8285"))
# print(Pcan.ReadDID("8286"))

# data = extractOsTaskWithIndex()
# dataResult = {}

# for key, value in data.items():
#     requestData = [0]
#     dataResult.setdefault(key, {'Read': '', 'Write': ''})
#     if value['Read']:
#         responseRead = Pcan.ReadDID(key)
#     if type(responseRead[1]) is list:
#         requestData = responseRead[1]
#         dataResult[key]['Read'] = "Sucess"
#     else:
#         dataResult[key]['Read'] = responseRead[1]
#     if value['Write']:
#         responseWrite = Pcan.WriteDID(key, requestData)
#         if responseWrite[1]:
#             dataResult[key]['Write'] = "Sucess"
#         else:
#             dataResult[key]['Write'] = responseWrite[2]

# # writeDataIntoCSV(dataResult)