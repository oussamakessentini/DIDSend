import time
import os
from UDS.UDSInterface import * 
from UDS.Utils import *

project = None

if __name__ == "__main__":
    dir_name = os.path.dirname(os.path.abspath(__file__))
    FileConfig=loadConfigFilePath(dir_name)
    load_config(globals(), globals(), FileConfig)
    
    if(project == 'PR105'):
        Pcan = UDSInterface(FileConfig=FileConfig)

        # print(Pcan.getFrameFromId(596))
        Pcan.StartSession(3) # Extended session
        # Pcan.StartReset(2) # SW Reset + NvM record
        # Pcan.StartReset(3) # SW Reset
        print(Pcan.ReadDID("DF73"))
        print(Pcan.ReadDID("DF74"))
        # print(Pcan.StartRC('DDE1', [0x01]))
        # print(Pcan.StartRC('DD3A'))
        # print(Pcan.StopRC('DD3A'))
        # print(Pcan.ResultRC('DD3A'))
        
    else:
        Pcan = UDSInterface(FileConfig=FileConfig)
        Pcan.StartSession(3)
        print("8281 " + str(Pcan.ReadDID("8281")))
        print("8282 " + str(Pcan.ReadDID("8282")))
        print("8283 " + str(Pcan.ReadDID("8283")))
        print("8284 " + str(Pcan.ReadDID("8284")))
        print("8285 " + str(Pcan.ReadDID("8285")))
        print("8286 " + str(Pcan.ReadDID("8286")))
        print("8287 " + str(Pcan.ReadDID("8287")))
        print("828B " + str(Pcan.ReadDID("828B")))
        print("828C " + str(Pcan.ReadDID("828C")))
        print("828F " + str(Pcan.ReadDID("828F")))
        print(Pcan.WriteDID("8282", [1,3,2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0\
                                    ,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0\
                                    ,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0\
                                    ,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0\
                                    ,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0\
                                    ,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]))
        print(Pcan.WriteDID("8283", [1]))
        print(Pcan.WriteDID("8285", [2]))
        print(Pcan.WriteDID("8286", [3]))
        print("F012 " + str(Pcan.ReadDID("F012")))
        print("F180 " + str(Pcan.ReadDID("F180")))
        print("F182 " + str(Pcan.ReadDID("F182")))
        print("F187 " + str(Pcan.ReadDID("F187")))
        print("F188 " + str(Pcan.ReadDID("F188")))
        print("F18A " + str(Pcan.ReadDID("F18A")))
        print("F195 " + str(Pcan.ReadDID("F195")))
        print("F1A1 " + str(Pcan.ReadDID("F1A1")))

        Pcan.StartSession(2)
        time.sleep(2)
        print(Pcan.WriteReadRequest([0x3E, 0x00]))
        print("F012 " + str(Pcan.ReadDID("F012")))
        print("F180 " + str(Pcan.ReadDID("F180")))
        print("F182 " + str(Pcan.ReadDID("F182")))
        print("F187 " + str(Pcan.ReadDID("F187")))
        print("F188 " + str(Pcan.ReadDID("F188")))
        print("F18A " + str(Pcan.ReadDID("F18A")))
        print("F195 " + str(Pcan.ReadDID("F195")))
        print("F1A1 " + str(Pcan.ReadDID("F1A1")))
        # print("F012 " + str(Pcan.ReadDID("F012")))
        # print("F18A " + str(Pcan.ReadDID("F18A")))
        # print("F191 " + str(Pcan.ReadDID("F191")))
        # print("F1A1 " + str(Pcan.ReadDID("F1A1")))
        # print("F187 " + str(Pcan.ReadDID("F187")))
        # print("F190 " + str(Pcan.ReadDID("F190")))
        # print("F18F " + str(Pcan.ReadDID("F18F")))
        # print("F18C " + str(Pcan.ReadDID("F18C")))
        # print("F011 " + str(Pcan.ReadDID("F011")))
        # print("F062 " + str(Pcan.ReadDID("F062")))
        # print("FD06 " + str(Pcan.ReadDID("FD06")))
        # print("F180 " + str(Pcan.ReadDID("F180")))
        # print("FD01 " + str(Pcan.ReadDID("FD01")))
        print("FD02 " + str(Pcan.ReadDID("FD02")))

        print(Pcan.WriteReadRequest([0x19, 0x02, 0xFF]))
        print("8282 " + str(Pcan.ReadDID("8282")))
        print(Pcan.WriteDID("F062", [3]))
        print(Pcan.WriteDID("826A", [2]))