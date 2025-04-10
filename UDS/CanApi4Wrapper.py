from .CanApi4 import *
from .Utils import *

class CanApi4Wrapper:
    def __init__(self, device=None, client_name=None, net_name=None, IsCanFD=None, \
                 TxID=None, RxID=None, IsExtended=None, IsFiltered=None, IsPadded=None, FileConfig=None):
        self.comOk = False

        self.device = device
        self.client_name = client_name
        self.net_name = net_name
        self.client_handle = 0
        self.net_handle = 0
        self.hw_handle = 0
        self.IsCanFD = IsCanFD
        self.IsPadded = IsPadded
        self.IsFiltered = IsFiltered
        self.TxId = TxID
        self.RxId = RxID
        self.IsExtended = IsExtended

        # get the configuration from file
        if FileConfig != None:
            load_config(self, globals(), FileConfig, Encode=True)
        NoneData = []
        for itemName in self.__dict__.keys():
            if getattr(self, itemName) is None:
                NoneData.append(itemName)
        if len(NoneData) != 0:
            print (f"CanApi4Wrapper: Please define these attributes in function call or in config file: {NoneData}")
            exit(0)

        self.minRange = 0
        # CAN Message Configuration
        if self.IsExtended == True:
            self.typeExtended = CAN_MSGTYPE_EXTENDED
            self.maxRange = 0x1FFFFFFF
        else:
            self.typeExtended = CAN_MSGTYPE_STANDARD
            self.maxRange = 0x7FF
        
        try:
            self.can_api = CanApi4()
            self.m_DLLFound = True
        except :
            print("Unable to find the library: CanApi4.dll !")
            input("Press <Enter> to quit...")
            self.m_DLLFound = False
            return

    def initialize(self):
        """Initialize the CAN interface."""
        result = self.can_api.RegisterClient(self.device, self.client_name, 0)
        if result[0] != CAN_ERR_OK:
            self.get_error_text("RegisterClient", result[0])
            return False
        self.client_handle = result[1]

        result = self.can_api.ConnectToNet(self.device, self.client_handle, self.net_name)
        self.net_handle = result[1]
        if result[0] != CAN_ERR_OK:
            self.get_error_text("ConnectToNet", result[0])
            print(f"Net Handle: {self.net_handle}, Net Name: {self.net_name}")
            print("List of available net:")
            listNetwork = self.list_networks()
            while True:
                try:
                    choice = int(input("Enter the number of your selection: ").strip())  # Convert input to int
                    if choice in range(1, len(listNetwork)+1):
                        print(f"You selected: {bytes(listNetwork[choice-1]).decode()}")
                        if self.net_name != listNetwork[choice-1]:
                            result = self.can_api.ConnectToNet(self.device, self.client_handle, listNetwork[choice-1])
                            self.net_handle = result[1]
                            if result[0] != CAN_ERR_OK:
                                return False
                            else:
                                print(f"please update in config net_name with {bytes(listNetwork[choice-1]).decode()} instead of {bytes(self.net_name).decode()}")
                                self.net_name = listNetwork[choice-1]
                        break
                    else:
                        print(f"Invalid choice. Please enter a number between 1 and {len(listNetwork)}.")
                        return False
                except ValueError:
                    print("Invalid input. Please enter a number.")
                    return False
        
        # set read function to read only one frame at a time
        if self.setParam(CAN_PARAM_READ_MAX_RECORDCOUNT, CAN_PARAM_OBJCLASS_CLIENT, 1) == False:
            return False

        if self.IsFiltered == True:
            self.set_filter(self.TxId, self.RxId)
        else:
            self.set_filter(self.minRange, self.maxRange)

        self.comOk = True

        print("Connected successfully!")
        return True
    
    def set_filter(self, start_id=0x100, end_id=0x200):
        """Set a filter to only receive messages within the specified ID range."""
        result = self.can_api.ResetClientFilter(self.device, self.client_handle)
        if result != CAN_ERR_OK:
            self.get_error_text("ResetClientFilter", result)

        result = self.can_api.RegisterMessages(self.device, self.client_handle, self.net_handle, start_id, end_id, self.IsExtended)
        if result != CAN_ERR_OK:
            self.get_error_text("RegisterMessages", result)
        else:
            print(f"Filter set: Only receiving messages from 0x{start_id:X} to 0x{end_id:X}")

        # Clear the receive queue
        self.can_api.ResetClient(self.device, self.client_handle)

    def setParam(self, type, objclass, value):
        param = can_param_uint32_t()
        param.size = sizeof(param)
        param.type = type
        param.objclass = objclass
        param.objhandle = self.client_handle
        param.value = value
        result = self.can_api.SetParam(self.device, param)
        if (result != CAN_ERR_OK):
            self.get_error_text("SetParam", result)
            return False
        return True

    def set_msg_dlc(self, msg_type, size):
        max_dlc = (get_dlc_for_data_length(size) if size > 8 or not self.IsPadded else 8) if msg_type == CAN_RECORDTYPE_msg_fd.value else 8
        if self.IsPadded:
            return max_dlc
        return size if 0 <= size <= max_dlc else None

    def write(self, can_id, data):
        if not isinstance(data, list):
            print("Error: Data must be a list of bytes.")
            return False

        if self.IsCanFD:
            my_msg = can_msg_fd_t()
            my_msg.type = CAN_RECORDTYPE_msg_fd.value
            my_msg.msgtype = CAN_MSGTYPE_BRS
        else:
            my_msg = can_msg_t()
            my_msg.type = CAN_RECORDTYPE_msg.value

        my_msg.size = sizeof(my_msg)
        my_msg.id = can_id
        my_msg.msgtype |= self.typeExtended
        my_msg.dlc = self.set_msg_dlc(my_msg.type, len(data))
        my_msg.data.data[:len(data)] = data
        my_msg.client = self.client_handle
        my_msg.net = self.net_handle

        result = self.can_api.Write(self.device, my_msg)
        if result[0] != CAN_ERR_OK:
            self.get_error_text("Write", result[0])
            return False
        return True

    def read(self):
        """Read a CAN message."""
        return_value = {"id" : 0, "data" : [],"len" : 0, "timestamp" : 0}
        result = self.can_api.Read(self.device, self.client_handle, 1000)
        if result[0] == CAN_ERR_OK:
            data = bytearray(b & 0xFF for b in result[2])  # Convert negative values to unsigned
            readPointer = can_recordheader_t.from_buffer(data)
            
            if readPointer.type == CAN_RECORDTYPE_basemsg.value:

                msg = can_basemsg_t.from_buffer(data)
                return_value["id"] = msg.id
                return_value["len"] = msg.dlc
                return_value["timestamp"] = msg.timestamp
            elif readPointer.type == CAN_RECORDTYPE_msg.value:
                msg = can_msg_t.from_buffer(data)
                return_value["id"] = msg.id
                return_value["len"] = msg.dlc
                return_value["data"] = msg.data.data[:msg.dlc]
                return_value["timestamp"] = msg.timestamp
            elif readPointer.type == CAN_RECORDTYPE_msg_fd.value:
                msg = can_msg_fd_t.from_buffer(data)
                return_value["id"] = msg.id
                return_value["len"] = dlc_to_data_size(msg.dlc)
                return_value["data"] = msg.data.data[:dlc_to_data_size(msg.dlc)]
                return_value["timestamp"] = msg.timestamp
 
        if result[0] == CAN_ERR_QRCVEMPTY:
            return None
        if result[0] != CAN_ERR_OK:
            self.get_error_text("Read", result[0])
            return None
        return return_value

    def __del__(self):
        self.uninitialize()

    def uninitialize(self):
        """Disconnect from the CAN interface."""
        if self.net_handle:
            self.can_api.DisconnectFromNet(self.device, self.client_handle, self.net_handle)
        if self.client_handle:
            self.can_api.RemoveClient(self.device, self.client_handle)
        print("CAN API Uninitialized.")

    def get_error_text(self, functionName, error_code):
        """Get error description."""
        result = self.can_api.GetErrText(error_code)
        print("=========================================================================================")
        print(f"Error {functionName} Data: {bytes.decode(result[1])}")
        print("=========================================================================================")

    def list_available_nets(self):
        result = self.can_api.GetAvailableHardware(self.device)
        if result[0] == CAN_ERR_OK:
            print("Available Networks:")
            for hw in result[1]:
                print(f"Net Name: {bytes(hw.name).decode()}")
        else:
            self.get_error_text("GetAvailableHardware", result[0])

    def list_networks(self):
        listNetwork = []
        for i in range(1, 65):  # CAN handles are usually between 1 and 64
            param = can_param_string255_t()
            param.size = sizeof(param)
            param.type = CAN_PARAM_NAME
            param.objclass = CAN_PARAM_OBJCLASS_NET
            param.objhandle = i

            result = self.can_api.GetParam(pcan_usb, param)
            if result[0] == CAN_ERR_OK:
                print(f"Net {i}: {bytes(result[1].value).decode()}")
                listNetwork.append(result[1].value)
        return listNetwork
# Example Usage
if __name__ == "__main__":
    FileConfig=loadConfigFilePath()
    can_wrapper = CanApi4Wrapper(FileConfig=FileConfig, IsFiltered=False)
    if can_wrapper.initialize():
        print("CAN Initialized Successfully")
        while True:
            message = can_wrapper.read()
            if message != None:
                print("Received Message:", message)
        can_wrapper.uninitialize()