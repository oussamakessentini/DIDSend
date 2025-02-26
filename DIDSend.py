import sys
import os
from UDS.PCANBasic import *
from UDS.UDS_Frame import UDS_Frame 

PROJECT = 'PR105'

if __name__ == "__main__":

    if(PROJECT == 'PR105'):
        TxId = 0x6B4
        RxId = 0x694
        Pcan = UDS_Frame(PCAN_USBBUS1, False, PCAN_BAUD_500K, TxId, RxId, False, True)

        # print(Pcan.ReadDID("F41C"))
        # print(Pcan.ReadDID("D863"))
        # Pcan.checkCanCom()
        print(Pcan.ReadDID("0101"))
    else:
        TxId = 0x18DADBF1
        RxId = 0x18DAF1DB
        Pcan = UDS_Frame(PCAN_USBBUS1, False, PCAN_BAUD_500K, TxId, RxId, True, True)

        Pcan.StartSession(3)
        print(Pcan.ReadDID("8281"))
