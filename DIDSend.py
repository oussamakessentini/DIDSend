import sys
import os
import time
from UDS.PCANBasic import *
from UDS.UDS_Frame import UDS_Frame 

PROJECT = 'PR105'

if __name__ == "__main__":

    if(PROJECT == 'PR105'):
        TxId = 0x6B4
        RxId = 0x694
        Pcan = UDS_Frame(PCAN_USBBUS1, False, PCAN_BAUD_500K, TxId, RxId, False, True)

        # print(Pcan.getFrameFromId(596))
        Pcan.StartSession(3) # Extended session
        # Pcan.StartReset(2) # SW Reset + NvM record
        # Pcan.StartReset(3) # SW Reset

        # print(Pcan.ReadDID("F41C"))
        # print(Pcan.ReadDID("D863"))
        # print(Pcan.ReadDID("0101"))
        # print(Pcan.ReadDID("E323"))
        # print(Pcan.WriteDID("E323", [0xA9, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5,\
        #                              0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5,\
        #                              0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5,\
        #                              0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5,\
        #                              0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5,\
        #                              0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5,\
        #                              0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5,\
        #                              0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5,\
        #                              0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5,\
        #                              0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5,\
        #                              0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5,\
        #                              0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5,\
        #                              0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5,\
        #                              0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5,\
        #                              0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5,\
        #                              0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5,\
        #                              0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5,\
        #                              0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5,\
        #                              0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5,\
        #                              0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5]))
        # Pcan.StartReset(2) # SW Reset + NvM record
        # Wait 5s at startup
        # time.sleep(7)
        # print(Pcan.ReadDID("E323"))
        print(Pcan.StartRC('DDE1', [0x01]))
        print(Pcan.StartRC('DD3A'))
        print(Pcan.StopRC('DD3A'))
        print(Pcan.ResultRC('DD3A'))
        
    else:
        TxId = 0x18DADBF1
        RxId = 0x18DAF1DB
        Pcan = UDS_Frame(PCAN_USBBUS1, False, PCAN_BAUD_500K, TxId, RxId, True, True)

        Pcan.StartSession(3)
        print(Pcan.ReadDID("8281"))
