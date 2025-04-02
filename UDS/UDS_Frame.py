from .PCANBasicWrapper import PCANBasicWrapper
from .CanApi4Wrapper import CanApi4Wrapper
from .Utils import *
import pandas as pd
import time

class UDS_Frame():

    # Shows if DLL was found
    m_DLLFound = False

    def __init__(self, IsCanFD=None, TxID=None, RxID=None, IsExtended=None, IsFiltered=None, IsPadded=None, PcanLib=None, FileConfig=None):
        """
        Create an object starts the programm
        """
        self.comOk = False
        # Set Configuration
        self.TxId = TxID
        self.RxId = RxID
        self.timeout = 2
        self.IsFiltered = IsFiltered
        self.PcanLib = PcanLib
        self.IsCanFD = IsCanFD
        # Create a shared queue
        self.q = PeekableQueue()
        self.m_DLLFound = ''

        # get the configuration from file
        if FileConfig != None:
            load_config(self, globals(), FileConfig)
        NoneData = []
        for itemName in self.__dict__.keys():
            if getattr(self, itemName) is None:
                NoneData.append(itemName)
        if len(NoneData) != 0:
            print (f"UDS_Frame: Please define these attributes in function call or in config file: {NoneData}")
            exit(0)

        if self.PcanLib == "PCANBasicLib":
            # load PCanBasic Wrapper
            self.m_objWrapper = PCANBasicWrapper(FileConfig=FileConfig, TxID=TxID, RxID=RxID, IsCanFD=IsCanFD, IsExtended=IsExtended, IsPadded=IsPadded, IsFiltered=IsFiltered)
        elif self.PcanLib == "CanApi4Lib":
            # load CanApi4 Wrapper
            self.m_objWrapper = CanApi4Wrapper(FileConfig=FileConfig, TxID=TxID, RxID=RxID, IsCanFD=IsCanFD, IsExtended=IsExtended, IsPadded=IsPadded, IsFiltered=IsFiltered)
        else:
            print ("Please define the correct PCANLib to use (PCANBasic or CanApi4) ")
            exit(0)

        if self.m_objWrapper.m_DLLFound == False:
            print("Can Wrapper class instanciation error")

        stsResult = self.m_objWrapper.initialize()
        if stsResult == False:
            print("Can Wrapper initialisation error")

        self.comOk = self.m_objWrapper.comOk

    def __del__(self):
        if self.m_objWrapper is not None:
            del self.m_objWrapper
    
    def __get_uds_nrc_description(self, nrc_byte):
        """
        Returns the description of the given UDS NRC byte.

        :param nrc_byte: The NRC byte (integer or hex) to check.
        :return: Description of the NRC byte or an error message if not found.
        """
        uds_nrc_codes = {
            0x10: "General reject",
            0x11: "Service not supported",
            0x12: "Sub-function not supported",
            0x13: "Invalid message length/format",
            0x14: "Response too long",
            0x21: "Busy-repeat request",
            0x22: "Conditions not correct",
            0x24: "Request sequence error",
            0x25: "No response from subnet component",
            0x26: "Failure prevents execution of requested action",
            0x31: "Request out of range",
            0x33: "Security access denied",
            0x35: "Invalid key",
            0x36: "Exceeded number of attempts",
            0x37: "Required time delay has not expired",
            0x70: "Upload/download not accepted",
            0x71: "Transfer data suspended",
            0x72: "Programming failure",
            0x73: "Wrong block sequence counter",
            0x78: "Request received - response pending",
            0x7E: "Sub function not supported in active session",
            0x7F: "Service not supported in active session",
            0x81: "RPM too high/low",
            0x82: "RPM too high/low",
            0x83: "Engine is running/not running",
            0x84: "Engine is running/not running",
            0x85: "Engine run time too low",
            0x86: "Temperature too high/low",
            0x87: "Temperature too high/low",
            0x88: "Speed too high/low",
            0x89: "Speed too high/low",
            0x8A: "Throttle pedal too high/low",
            0x8B: "Throttle pedal too high/low",
            0x8C: "Transmission range not in neutral/gear",
            0x8D: "Transmission range not in neutral/gear",
            0x8F: "Brake switches not closed",
            0x90: "Shifter lever not in park",
            0x91: "Torque converter clutch locked",
            0x92: "Voltage too high/low",
            0x93: "Voltage too high/low",
            0xF0: "Manufacturer specific conditions not correct",
            0xF1: "Manufacturer specific conditions not correct",
            0xF2: "Manufacturer specific conditions not correct",
            0xF3: "Manufacturer specific conditions not correct",
            0xF4: "Manufacturer specific conditions not correct",
            0xF5: "Manufacturer specific conditions not correct",
            0xF6: "Manufacturer specific conditions not correct",
            0xF7: "Manufacturer specific conditions not correct",
            0xF8: "Manufacturer specific conditions not correct",
            0xF9: "Manufacturer specific conditions not correct",
            0xFA: "Manufacturer specific conditions not correct",
            0xFB: "Manufacturer specific conditions not correct",
            0xFC: "Manufacturer specific conditions not correct",
            0xFD: "Manufacturer specific conditions not correct",
            0xFE: "Manufacturer specific conditions not correct",
        }

        # Convert to integer if input is a string with "0x"
        if isinstance(nrc_byte, str) and nrc_byte.startswith("0x"):
            nrc_byte = int(nrc_byte, 16)

        # Lookup the NRC byte
        return uds_nrc_codes.get(nrc_byte, "Unknown NRC code")
    
    def __get_UDS_type_frame(self, id_byte, Frame, negativeRequest=False):
        decodeFrame = f"{Frame[1]:02X}{Frame[2]:02X}" if len(Frame) > 2 and negativeRequest == False else ""
        uds_service_classes = {
            0x10: lambda: "SessionControlClass",
            0x50: lambda: "SessionControlClassResponse",

            0x27: lambda: "SecurityAccessClass",
            0x67: lambda: "SecurityAccessClassResponse",

            0x11: lambda: "EcuResetClass",
            0x51: lambda: "EcuResetClassResponse",

            0x19: lambda: "ReadDtcInformationClass",
            0x59: lambda: "ReadDtcInformationClassResponse",

            0x14: lambda: "ClearDiagnosticInformationClass",
            0x54: lambda: "ClearDiagnosticInformationClassResponse",

            0x22: lambda: f"ReadDataByIdentifierClass {decodeFrame}",
            0x62: lambda: f"ReadDataByIdentifierClassResponse {decodeFrame}",

            0x2E: lambda: f"WriteDataByIdentifierClass {decodeFrame}",
            0x6E: lambda: f"WriteDataByIdentifierClassResponse {decodeFrame}",

            0x2F: lambda: "IoControlClass",
            0x6F: lambda: "IoControlClassResponse",

            0x31: lambda: "RoutineControlClass",
            0x71: lambda: "RoutineControlClassResponse",

            0x36: lambda: "DataTransferClass",
            0x76: lambda: "DataTransferClassResponse",

            0x37: lambda: "TransferExitClass",
            0x77: lambda: "TransferExitClassResponse",

            0x34: lambda: "RequestDownloadClass",
            0x74: lambda: "RequestDownloadClassResponse",

            0x01: lambda: "RequestCurrentPowertrainDataClass",
            0x41: lambda: "RequestCurrentPowertrainDataClassResponse",

            0x02: lambda: "RequestPowertrainFreezeFrameDataClass",
            0x42: lambda: "RequestPowertrainFreezeFrameDataClassResponse",

            0x3E: lambda: "TesterPresentClass",
            0x7E: lambda: "TesterPresentClassResponse",
        }

        # Convert to integer if input is a string with "0x"
        if isinstance(id_byte, str) and id_byte.startswith("0x"):
            id_byte = int(id_byte, 16)

        # Lookup the NRC byte
        return uds_service_classes.get(id_byte, lambda: "Unknown id class")()

    def __get_uds_rc_status_desc(self, rc_st_byte):
        """
        Returns the description of the given UDS RC byte.

        :param rc_st_byte: The RC status byte (integer or hex) to check.
        :return: Description of the RC status byte.
        """
        uds_rc_st_codes = {
            0x1: "ROUTINE_IN_PROCESS",
            0x2: "ROUTINE_FINISHED_OK",
            0x3: "ROUTINE_FINISHED_NOT_OK",
        }

        # Convert to integer if input is a string with "0x"
        if isinstance(rc_st_byte, str) and rc_st_byte.startswith("0x"):
            rc_st_byte = int(rc_st_byte, 16)

        # Lookup the NRC byte
        return uds_rc_st_codes.get(rc_st_byte, "Unknown RC status code")

    def ReadMessages(self):
        """
        Function for reading CAN messages
        """
        ## We read at least one time the queue looking for messages. If a message is found, we look again trying to 
        ## find more. If the queue is empty or an error occurr, we get out from the dowhile statement.
        return self.m_objWrapper.read()

    def WriteMessages(self, id, data):
        '''
        Function for writing CAN messages
        '''
        return self.m_objWrapper.write(id, data)

    def getFrameFromId(self, canId):
        """
        Retrieve CAN message from CAN ID

        Parameters:
            canId (int): hex value without "0x" (e.g., "596").

        Returns:
            Can Message data object.
        """
        msg = 0
        if (self.IsFiltered == True) and isBetween(canId, self.TxId, self.RxId):
            print("Warning : this Can ID is filtered.")
            return None
        else:
            startTime = time.time()
            while ((time.time() - startTime) < self.timeout):
                msg = self.ReadMessages()
                if (msg is not None) and (msg['id'] == canId):
                    break
                elif self.IsFiltered == True:
                    time.sleep(0.1)
        return msg

    def StartSession(self, number):
        if self.comOk == False:
            print ("No Communication established")
            exit(0)
        
        data = []
        data.append(0x10)
        data.append(number)
        msg = self.WriteReadRequest(data)

        if (msg["status"] == True):
            print (f"Session {number} activated...")
            return True
        print(f"StartSession {number} : Time out No Response")
        return False

    def StartReset(self, rstReq):
        retState = False
        if self.comOk == False:
            print ("No Communication established")
            exit(0)
        
        data = []
        data.append(0x11)
        data.append(rstReq)
        msg = self.WriteReadRequest(data)

        if (msg["status"] == True):
            print("StartReset : OK")
            retState = True
        else:
            print("StartReset : NOK, " + msg["response"])
            retState = False

        return retState

    def __decodeFrame(self, data, size):
        returnValue = ""
        if data[0] == 0x7F:
            returnValue += f"Negative response: Error code 0x{data[2]:02X}: {self.__get_uds_nrc_description(data[2])} for {self.__get_UDS_type_frame(data[1], data, negativeRequest=True)}"
        else:
            returnValue += self.__get_UDS_type_frame(data[0], data)
        if len(data) != size:
            returnValue += f", Needed {size} Bytes, received only {len(data)} Bytes"
        
        return returnValue

    def startCanStoringTrace(self, df=None, InHex=True, decodeFrame=True):
        if not isinstance(df, pd.DataFrame):
            print("The object is NOT a pandas DataFrame.")
            return
        
        row = { "id": "", \
                "Data": [], \
                "Type": "", \
                "Size": 0, \
                "Comments": ""}
        try:
            self.running = True  # Flag to control the worker loop
            worker_thread = threading.Thread(target=self.__ReadMessagesThread, daemon=True)
            worker_thread.start()
            while True:
                if decodeFrame:
                    msg = self.__ReadUDSRequest(SendMultiFrameReaquest=False, isWorkingInThread=True)
                    if msg['status'] == True:
                        row["Type"] = "TX" if self.TxId == msg["id"] else "RX" if self.RxId == msg["id"] else ""
                        row["id"] = msg['id'] if InHex == False else format_hex(msg['id'])
                        row["Data"] = msg['data'] if InHex == False else [format_hex(item) for item in msg['data']]
                        row["Size"] = msg['size']
                        row["Comments"] = self.__decodeFrame(msg['data'], msg['size'])
                        print(row)
                        df.loc[len(df)] = row
                    elif  msg['id'] != 0:
                        row["Type"] = "TX" if self.TxId == msg["id"] else "RX" if self.RxId == msg["id"] else ""
                        row["id"] = msg['id'] if InHex == False else format_hex(msg['id'])
                        row["Data"] = msg['data'] if InHex == False else [format_hex(item) for item in msg['data']]
                        row["Size"] = msg['size']
                        row["Comments"] = "invalid Frame:" + self.__decodeFrame(msg['data'], msg['size'])
                        print(row)
                        df.loc[len(df)] = row
                else:
                    msg = self.ReadMessages()
                    if (msg is not None):
                        if (len(msg['data']) > 0):
                            row["Type"] = "TX" if self.TxId == msg["id"] else "RX" if self.RxId == msg["id"] else ""
                            row["id"] = msg['id'] if InHex == False else format_hex(msg['id'])
                            row["Data"] = msg['data'] if InHex == False else [format_hex(item) for item in msg['data']]
                            row["Size"] = len(msg['data'])
                            row["Comments"] = ""
                            print(row)
                            df.loc[len(df)] = row
        except Exception as e:
            print(f"Exception: {e}")
        finally:
            self.running = False  # Flag to control the worker loop
            worker_thread.join()
    
    def __WriteUDSRequest(self, data):
        max_Frame = 64 if self.IsCanFD else 8
        if len(data) < max_Frame:  # Single Frame
            total_length = len(data)
            if total_length < 8:
                sf_message = [total_length] + data
            else:
                sf_message = [total_length>>8, total_length&0xFF] + data
            self.WriteMessages(self.TxId, sf_message)
        else:  # Multi-Frame Communication
            total_length = len(data)
            ff_payload = data[:max_Frame - 2]
            first_frame = [0x10 | ((total_length >> 8) & 0x0F), total_length & 0xFF] + ff_payload
            self.WriteMessages(self.TxId, first_frame)

            # Wait for Flow Control (FC)
            start_time = time.time()
            while time.time() - start_time < self.timeout:
                fc_message = self.ReadMessages()
                if fc_message and fc_message['id'] == self.RxId and fc_message['data'][0] == 0x30:
                    block_size = fc_message['data'][1]
                    st_min = fc_message['data'][2]
                    break
                elif self.IsFiltered == True:
                    time.sleep(0.1)
            else:
                raise RuntimeError("No Flow Control received.")

            # Send Consecutive Frames
            seq_number = 1
            data_remaining = data[max_Frame - 2:]  # Remaining data after the First Frame
            while data_remaining:
                cf_payload = data_remaining[:max_Frame - 1]
                cf_message = [0x20 | seq_number] + cf_payload
                self.WriteMessages(self.TxId, cf_message)
                data_remaining = data_remaining[max_Frame - 1:]
                seq_number = (seq_number + 1) % 16  # Sequence number wraps around

                # Wait for separation time (STmin)
                time.sleep(st_min / 1000.0)

    def __ReadMessagesThread(self):
        """Worker function that runs in a separate thread"""
        while self.running:
            msg = self.ReadMessages()
            if (msg is not None):
                if (len(msg['data']) > 0):
                    self.q.put(msg)

    def __ReadUDSRequest(self, SendMultiFrameReaquest=True, isWorkingInThread=False):
        response = {"id": 0, "data": [], "status": False, "size": 0}
        frameReceived = False
        dataRemaining = 0
        responseCmdWait = 0
        FrameConsumed = True
        start_time = time.time()
        while time.time() - start_time < self.timeout:
            if isWorkingInThread:
                msg = self.q.peek()
                FrameConsumed = True
            else:
                msg = self.ReadMessages()
            if (msg is not None):
                if (len(msg['data']) > 0):
                    if (msg['data'][0]&0xF0 == 0x0):
                        response["id"] = msg['id']
                        if ((msg['len']) <= 8):
                            response["size"] = msg['data'][0]
                            response["data"] = msg['data'][1:1+response["size"]]
                        else:
                            response["size"] = ((msg['data'][0] & 0xF) << 8) + msg['data'][1]
                            response["data"] = msg['data'][2:2+response["size"]]
                        frameReceived = True
                    elif (msg['data'][0]&0xF0 == 0x10):
                        response["id"] = msg['id']
                        response["size"] = ((msg['data'][0] & 0xF) << 8) + msg['data'][1]
                        dataRemaining = response["size"]
                        response["data"].extend(msg['data'][2:])
                        dataRemaining -= len(response["data"])
                        responseCmdWait = 1
                        if SendMultiFrameReaquest:
                            self.WriteMessages(self.TxId, [0x30])
                    elif (msg['data'][0]&0xF0 == 0x20) and (response["id"] == msg['id']):
                        if (msg['data'][0]&0xF == responseCmdWait):
                            if dataRemaining < len(msg['data']):
                                response["data"].extend(msg['data'][1:1+dataRemaining])
                                dataRemaining = 0
                            else:
                                response["data"].extend(msg['data'][1:])
                                dataRemaining -= len(msg['data'][1:])
                            if dataRemaining == 0 and len(response["data"]) == response["size"]:
                                frameReceived = True
                                responseCmdWait = 0
                            responseCmdWait += 1
                            responseCmdWait %= 16
                        else:
                            FrameConsumed = False
                            # counter of multi frame is not correct
                            break
                    # ignore MultiFrameReaquest when it is not sended
                    elif msg['data'][0] == 0x30:
                        # a multi frame is received
                        pass
                    else:
                        # unknown frame received
                        FrameConsumed = False
                        break
                    if (isWorkingInThread and FrameConsumed):
                        self.q.get()
                        self.q.task_done()
                    if (frameReceived):
                        response["status"] = True
                        break
        return response

    def WriteReadRequest(self, data, InHex=True):
        return_value = {"request" : data if InHex == False else [format_hex(item) for item in data], "response" : [],"status" : False}
        if self.comOk == False:
            print ("No Communication established")
            exit(0)
        try:
            self.__WriteUDSRequest(data)
            start_time = time.time()
            while time.time() - start_time < self.timeout:
                msg = self.__ReadUDSRequest()
                if (msg['id'] == self.RxId):
                    if (msg['data'][0] == 0x7F) and (msg['data'][1] == data[0]):
                        error_code = msg['data'][2]
                        if error_code != 0x78:
                            raise RuntimeError(f"Negative response: Error code 0x{error_code:02X}: " + self.__get_uds_nrc_description(error_code))
                    elif verifyFrame(msg['data'], data, min(msg['size'], len(data))):
                        if len(msg['data']) < msg['size']:
                            raise RuntimeError(f"Data missing: not all data received only {len(msg['data'])} bytes is received expected {msg['size']} bytes")
                        return_value["response"] = msg['data'] if InHex == False else [format_hex(item) for item in msg['data']]
                        return_value["status"] = True
                        break
            if time.time() - start_time > self.timeout:
                raise TimeoutError(f"Time out No Response")
        except Exception as e:
            return_value["response"] = e
            return_value["status"] = False

        return return_value

    def RcRequest(self, message, InHex=True):
        return_value = {"request" : message if InHex == False else [format_hex(item) for item in message], "response" : [],"status" : False}
        if self.comOk == False:
            print ("No Communication established")
            exit(0)
        try:
            self.WriteMessages(self.TxId, message)

            start_time = time.time()
            while time.time() - start_time < self.timeout:
                rc_msg = self.ReadMessages()
                if (rc_msg is not None):
                    if((rc_msg['id'] == self.RxId) and\
                       (rc_msg['data'][1] == 0x71) and\
                       (rc_msg['data'][3] == message[3]) and\
                       (rc_msg['data'][4] == message[4])):
                        # Check RC type request
                        if(message[2] == 0x1):
                            return "ROUTINE_STARTED"
                        elif(message[2] == 0x2):
                            return "ROUTINE_STOPPED"
                        else:
                            return self.__get_uds_rc_status_desc(rc_msg['data'][5])

                    elif((rc_msg['id'] == self.RxId) and\
                         (rc_msg['data'][1] == 0x7F) and\
                         (rc_msg['data'][2] == 0x31)):
                        return ('ResultRc Error : ' + self.__get_uds_nrc_description(rc_msg['data'][3]))
                    else:
                        return ('ResultRc Error : ', format_hex(rc_msg['data'][1]), format_hex(rc_msg['data'][2]), self.__get_uds_nrc_description(rc_msg['data'][3]))
            if time.time() - start_time > self.timeout:
                raise TimeoutError(f"Time out No Response")
            
        except Exception as e:
            return_value["response"] = e
            return_value["status"] = False

        return return_value

    def ReadDID(self, DID, decode=None):
        """
        Read data from a specified DID using UDS ReadDataByIdentifier (0x22) with multi-frame support.

        Parameters:
            DID (str): The 2-byte Data Identifier (e.g., "F190").

        Returns:
            list: List of bytes if the read was successful.
            None: If an error occurs.
        """
        if self.comOk == False:
            print ("No Communication established")
            exit(0)
        try:
            if len(DID) != 4 or not all(c in "0123456789ABCDEFabcdef" for c in DID):
                raise ValueError(f"Invalid DID: {DID}. It must be a 4-character hex string.")

            iDid = int(DID,16)
            iDidHigh = (iDid & 0xFF00) >> 8
            iDidLow = iDid & 0xFF
            message = [0x22, iDidHigh, iDidLow]
            data = self.WriteReadRequest(message, InHex=True if decode is None else False)
            if data["status"] == True:
                if decode is None:
                    return data["response"][3:]
                else:
                    return bytes(data["response"][3:]).decode(decode, errors='ignore').rstrip('\x00')
            else:
                return [f"Read {DID}", data["response"]]

        except Exception as e:
            return [f"Read {DID}", e]

    def WriteDID(self, DID, data):
        """
        Writes data to a specified DID using UDS WriteDataByIdentifier (0x2E) with multi-frame support.

        Parameters:
            DID (str): The 2-byte Data Identifier (e.g., "3481").
            data (list): A list of bytes to write to the DID.

        Returns:
            bool: True if the write was successful, False otherwise.
        """
        if self.comOk == False:
            print ("No Communication established")
            exit(0)
        try:
            if len(DID) != 4 or not all(c in "0123456789ABCDEFabcdef" for c in DID):
                raise ValueError(f"Invalid DID: {DID}. It must be a 4-character hex string.")

            if len(data) == 0 or len(data) > 4095:
                raise ValueError(f"Invalid data length: {len(data)}. Must be between 1 and 4095 bytes.")

            # Convert DID to bytes
            iDid = int(DID, 16)
            did_high = (iDid & 0xFF00) >> 8
            did_low = iDid & 0x00FF

            # Construct the first message payload
            message = [0x2E, did_high, did_low] + data
            data = self.WriteReadRequest(message)
            if data["status"] == True:
                return [f"Write {DID}", True]
            else:
                return [f"Write {DID}", False, data["response"]]

        except Exception as e:
            return [f"Write {DID}", False, e]

    def StartRC(self, DID, data=None):
        """
        Start routine controle using UDS (0x31).

        Parameters:
            DID (str): The 2-byte Data Identifier (e.g., "3481").
            data (list): A list of bytes as argument for the routine control.

        Returns:
            bool: True if the write was successful, False otherwise.
        """
        if self.comOk == False:
            print ("No Communication established")
            exit(0)
        try:
            if len(DID) != 4 or not all(c in "0123456789ABCDEFabcdef" for c in DID):
                raise ValueError(f"Invalid DID: {DID}. It must be a 4-character hex string.")

            # Convert DID to bytes
            iDid = int(DID, 16)
            did_high = (iDid & 0xFF00) >> 8
            did_low = iDid & 0x00FF

            # Message payload
            startRcMsgPL  = [0x31, 0x01, did_high, did_low]

            # Construct the message payload
            if(data is None):
                message = [len(startRcMsgPL)] + startRcMsgPL
            else:
                if len(data) == 0 or len(data) > 4095:
                    raise ValueError(f"Invalid data length: {len(data)}. Must be between 1 and 4095 bytes.")
                message = [len(startRcMsgPL + data)] + startRcMsgPL + data

            data = self.RcRequest(message)
            return data

        except Exception as e:
            return [f"Write {DID}", False, e]

    def StopRC(self, DID):
        """
        Stop routine controle using UDS (0x31).

        Parameters:
            DID (str): The 2-byte Data Identifier (e.g., "3481").

        Returns:
            bool: True if the write was successful, False otherwise.
        """
        if self.comOk == False:
            print ("No Communication established")
            exit(0)
        try:
            if len(DID) != 4 or not all(c in "0123456789ABCDEFabcdef" for c in DID):
                raise ValueError(f"Invalid DID: {DID}. It must be a 4-character hex string.")

            # Convert DID to bytes
            iDid = int(DID, 16)
            did_high = (iDid & 0xFF00) >> 8
            did_low = iDid & 0x00FF

            # Message payload
            stopRcMsgPL   = [0x31, 0x02, did_high, did_low]

            # Construct the message payload
            message = [len(stopRcMsgPL)] + stopRcMsgPL

            data = self.RcRequest(message)
            return data

        except Exception as e:
            return [f"Write {DID}", False, e]

    def ResultRC(self, DID):
        """
        Result routine controle using UDS (0x31).

        Parameters:
            DID (str): The 2-byte Data Identifier (e.g., "3481").

        Returns:
            bool: True if the write was successful, False otherwise.
        """
        if self.comOk == False:
            print ("No Communication established")
            exit(0)
        try:
            if len(DID) != 4 or not all(c in "0123456789ABCDEFabcdef" for c in DID):
                raise ValueError(f"Invalid DID: {DID}. It must be a 4-character hex string.")

            # Convert DID to bytes
            iDid = int(DID, 16)
            did_high = (iDid & 0xFF00) >> 8
            did_low = iDid & 0x00FF

            # Message payload
            resultRcMsgPL = [0x31, 0x03, did_high, did_low]

            # Construct the message payload
            message = [len(resultRcMsgPL)] + resultRcMsgPL

            data = self.RcRequest(message)
            return data
        
        except Exception as e:
            return [f"Write {DID}", False, e]
