from .PCANBasic import *
from .utils import *
import time

class PCANBasicWrapper:
    def __init__(self, FileConfig=None, PcanHandle="PCAN_USBBUS1", IsCanFD=False, Bitrate="PCAN_BAUD_500K", \
                 BitrateFD=b'f_clock_mhz=20, nom_brp=5, nom_tseg1=2, nom_tseg2=1, nom_sjw=1, data_brp=2, data_tseg1=3, data_tseg2=1, data_sjw=1', \
                 TxID=0x18DADBF1, RxID=0x18DAF1DB, IsExtended=True, IsFiltered=True, IsPadded=False):
        """
        Create an object starts the programm
        """

        self.comOk = False

        # Sets the PCANHandle (Hardware Channel)
        if PcanHandle in globals():
            self.PcanHandle = globals()[PcanHandle]
        else:
            print(f"Variable '{PcanHandle}' not found.")
            return

        # Sets the bitrate for normal CAN devices
        if Bitrate in globals():
            self.Bitrate = globals()[Bitrate]
        else:
            print(f"Variable '{Bitrate}' not found.")
            return

        # Sets the bitrate for CAN FD devices. 
        # Example - Bitrate Nom: 1Mbit/s Data: 2Mbit/s:
        #   "f_clock_mhz=20, nom_brp=5, nom_tseg1=2, nom_tseg2=1, nom_sjw=1, data_brp=2, data_tseg1=3, data_tseg2=1, data_sjw=1"
        self.BitrateFD = BitrateFD

        # Sets the desired connection mode (CAN = False / CAN-FD = True)
        self.IsCanFD = IsCanFD

        # Padded to zero to have 8 bytes frame
        self.IsPadded = IsPadded

        # Set Configuration
        self.TxId = TxID
        self.RxId = RxID

        self.timeout = 2
        # Filtering data
        self.IsFiltered = IsFiltered
        # extended CAN
        self.IsExtended = IsExtended

        # get the configuration from file
        if FileConfig != None:
            load_config(self, globals(), FileConfig, Encode=True)

        # CAN Message Configuration
        if self.IsExtended == True:
            self.typeExtended = PCAN_MESSAGE_EXTENDED
        else:
            self.typeExtended = PCAN_MESSAGE_STANDARD

        # Checks if PCANBasic.dll is available, if not, the program terminates
        try:
            self.m_objPCANBasic = PCANBasic()
            self.m_DLLFound = True
        except :
            print("Unable to find the library: PCANBasic.dll !")
            input("Press <Enter> to quit...")
            self.m_DLLFound = False
            return

    def initialize(self):
        """Initialize the CAN interface."""
        # Initialization of the selected channel
        if self.IsCanFD:
            print("CAN FD Initialized...")
            stsResult = self.m_objPCANBasic.InitializeFD(self.PcanHandle,self.BitrateFD)
        else:
            print("CAN HS Initialized...")
            stsResult = self.m_objPCANBasic.Initialize(self.PcanHandle,self.Bitrate)

        if stsResult != PCAN_ERROR_OK:
            print("Can not initialize. Please check the defines in the code.")
            self.get_error_text(stsResult)
            print("")
            return

        if self.__checkCanCom() and self.IsFiltered == True:
            self.set_filter(self.TxId, self.RxId)

        # Shows the current parameters configuration
        self.__ShowCurrentConfiguration()

    def __del__(self):
        self.uninitialize()
    
    def set_filter(self, start_id=0x100, end_id=0x200):
        """Set a filter to only receive messages within the specified ID range."""
        self.fromID = min(start_id, end_id)
        self.toID = max(start_id, end_id)
        
        stsResult = self.m_objPCANBasic.FilterMessages(self.PcanHandle, self.fromID, self.toID, self.typeExtended)

        if stsResult != PCAN_ERROR_OK:
            print("Error setting filter.")
            self.get_error_text(stsResult)
            return None
    
        # Clear the receive queue
        self.m_objPCANBasic.Reset(self.PcanHandle)

    def write(self, can_id, data):
        if self.IsCanFD:
            msgCanMessageFD = TPCANMsgFD()
            msgCanMessageFD.ID = can_id
            msgCanMessageFD.DLC = 15
            msgCanMessageFD.MSGTYPE = PCAN_MESSAGE_FD.value | PCAN_MESSAGE_BRS.value
            for i in range(len(data)):
                msgCanMessageFD.DATA[i] = data[i]
            stsResult = self.m_objPCANBasic.WriteFD(self.PcanHandle, msgCanMessageFD)
        else:
            msgCanMessage = TPCANMsg()
            msgCanMessage.ID = can_id
            msgCanMessage.LEN = 8 if self.IsPadded else len(data)
            msgCanMessage.MSGTYPE = self.typeExtended.value
            for i in range(len(data)):
                msgCanMessage.DATA[i] = data[i]
            stsResult = self.m_objPCANBasic.Write(self.PcanHandle, msgCanMessage)

        ## Checks if the message was sent
        if (stsResult != PCAN_ERROR_OK):
            self.get_error_text(stsResult)
            return False
        return True

    def read(self):
        """Read a CAN message."""
        sizeData = 0
        if self.IsCanFD:
            stsResult = self.m_objPCANBasic.ReadFD(self.PcanHandle)
            sizeData = stsResult[1].DLC
        else:
            stsResult = self.m_objPCANBasic.Read(self.PcanHandle)
            sizeData = stsResult[1].LEN
        if stsResult[0] == PCAN_ERROR_QRCVEMPTY:
            return None
        if stsResult[0] != PCAN_ERROR_OK:
            self.get_error_text(stsResult[0])
            return None
        return {"id" : stsResult[1].ID, "data" : stsResult[1].DATA,"len" : sizeData}

    def uninitialize(self):
        """Disconnect from the CAN interface."""
        if self.m_DLLFound:
            self.m_objPCANBasic.Uninitialize(PCAN_NONEBUS)

    def get_error_text(self,status):
        """
        Shows formatted status

        Parameters:
            status = Will be formatted
        """
        print("=========================================================================================")
        print(self.__GetFormattedError(status))
        print("=========================================================================================")
    
    def __checkCanCom(self):
        msg = 0
        self.comOk = False
        startTime = time.time()
        while ((time.time() - startTime) < self.timeout):
            msg = self.read()
            if (msg is not None):
                self.comOk = True
                break

        return self.comOk

    def __ShowCurrentConfiguration(self):
        """
        Shows/prints the configured paramters
        """
        print("Parameter values used")
        print("----------------------")
        print("* PCANHandle: " + self.__FormatChannelName(self.PcanHandle))
        print("* CanFD: " + str(self.IsCanFD))

        if self.IsCanFD:
            print("* BitrateFD: " + self.__ConvertBytesToString(self.BitrateFD))
        else:
            print("* Bitrate: " + self.__ConvertBitrateToString(self.Bitrate))

        print("* CanTx: " + str(hex(self.TxId)))
        print("* CanRx: " + str(hex(self.RxId)))
        if(self.IsFiltered == True):
            print("* Filter: ON")
            print("  - From: " + str(hex(self.fromID)))
            print("  - To  : " + str(hex(self.toID)))
        else:
            print("* Filter: OFF")
        print("")
    
    def __FormatChannelName(self, handle, IsCanFD=False):
        """
        Gets the formated text for a PCAN-Basic channel handle

        Parameters:
            handle = PCAN-Basic Handle to format
            IsCanFD = If the channel is FD capable

        Returns:
            The formatted text for a channel
        """
        handleValue = handle.value
        if handleValue < 0x100:
            devDevice = TPCANDevice(handleValue >> 4)
            byChannel = handleValue & 0xF
        else:
            devDevice = TPCANDevice(handleValue >> 8)
            byChannel = handleValue & 0xFF

        if IsCanFD:
           return ('%s:FD %s (%.2Xh)' % (self.__GetDeviceName(devDevice.value), byChannel, handleValue))
        else:
           return ('%s %s (%.2Xh)' % (self.__GetDeviceName(devDevice.value), byChannel, handleValue))

    def __GetFormattedError(self, error):
        """
        Help Function used to get an error as text

        Parameters:
            error = Error code to be translated

        Returns:
            A text with the translated error
        """
        ## Gets the text using the GetErrorText API function. If the function success, the translated error is returned.
        ## If it fails, a text describing the current error is returned.
        stsReturn = self.m_objPCANBasic.GetErrorText(error,0x09)
        if stsReturn[0] != PCAN_ERROR_OK:
            return "An error occurred. Error-code's text ({0:X}h) couldn't be retrieved".format(error)
        else:
            message = str(stsReturn[1])
            return message.replace("'","",2).replace("b","",1)

    def __GetDeviceName(self, handle):
        """
        Gets the name of a PCAN device

        Parameters:
            handle = PCAN-Basic Handle for getting the name

        Returns:
            The name of the handle
        """
        switcher = {
            PCAN_NONEBUS.value: "PCAN_NONEBUS",
            PCAN_PEAKCAN.value: "PCAN_PEAKCAN",
            PCAN_DNG.value: "PCAN_DNG",
            PCAN_PCI.value: "PCAN_PCI",
            PCAN_USB.value: "PCAN_USB",
            PCAN_VIRTUAL.value: "PCAN_VIRTUAL",
            PCAN_LAN.value: "PCAN_LAN"
        }

        return switcher.get(handle,"UNKNOWN")   

    def __ConvertBitrateToString(self, bitrate):
        """
        Convert bitrate c_short value to readable string

        Parameters:
            bitrate = Bitrate to be converted

        Returns:
            A text with the converted bitrate
        """
        m_BAUDRATES = {PCAN_BAUD_1M.value:'1 MBit/sec', PCAN_BAUD_800K.value:'800 kBit/sec', PCAN_BAUD_500K.value:'500 kBit/sec', PCAN_BAUD_250K.value:'250 kBit/sec',
                       PCAN_BAUD_125K.value:'125 kBit/sec', PCAN_BAUD_100K.value:'100 kBit/sec', PCAN_BAUD_95K.value:'95,238 kBit/sec', PCAN_BAUD_83K.value:'83,333 kBit/sec',
                       PCAN_BAUD_50K.value:'50 kBit/sec', PCAN_BAUD_47K.value:'47,619 kBit/sec', PCAN_BAUD_33K.value:'33,333 kBit/sec', PCAN_BAUD_20K.value:'20 kBit/sec',
                       PCAN_BAUD_10K.value:'10 kBit/sec', PCAN_BAUD_5K.value:'5 kBit/sec'}
        return m_BAUDRATES[bitrate.value]

    def __ConvertBytesToString(self, bytes):
        """
        Convert bytes value to string

        Parameters:
            bytes = Bytes to be converted

        Returns:
            Converted bytes value as string
        """
        return str(bytes).replace("'","",2).replace("b","",1)

# Example Usage
if __name__ == "__main__":
    PcanBasic_wrapper = PCANBasicWrapper()
    if PcanBasic_wrapper.initialize():
        print("CAN Initialized Successfully")
        PcanBasic_wrapper.write(1, [0x10, 0x03])
        message = PcanBasic_wrapper.read()
        print("Received Message:", message)
        PcanBasic_wrapper.uninitialize()