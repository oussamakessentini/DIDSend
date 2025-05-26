from .PCANBasicWrapper import PCANBasicWrapper
from .CanApi4Wrapper import CanApi4Wrapper
from .Utils import *
import pandas as pd
import time
import logging
from enum import Enum, IntEnum
from typing import Optional, Union, List, Tuple
import threading


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('ULP_UDS_Programmer')

class UDSInterface():

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
        self.IsFiltered = IsFiltered
        self.PcanLib = PcanLib
        self.IsCanFD = IsCanFD
        # Create a shared queue
        self.q = PeekableQueue()
        self.m_DLLFound = ''
        self.lock = threading.Lock()

        # get the configuration from file
        if FileConfig != None:
            load_config(self, globals(), FileConfig)
        NoneData = []
        for itemName in self.__dict__.keys():
            if getattr(self, itemName) is None:
                NoneData.append(itemName)
        if len(NoneData) != 0:
            print (f"UDSInterface: Please define these attributes in function call or in config file: {NoneData}")
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

    def __WriteUDSRequest(self, data, timeout=2):
        max_Frame = 64 if self.IsCanFD else 8
        total_length = len(data)
        if total_length < max_Frame:  # Single Frame
            
            if total_length < 8:
                sf_message = [total_length] + data
            else:
                sf_message = [total_length >> 8, total_length & 0xFF] + data
            self.WriteMessages(self.TxId, sf_message)
        else:  # Multi-Frame Communication
            ff_payload = data[:max_Frame - 2]
            first_frame = [0x10 | ((total_length >> 8) & 0x0F), total_length & 0xFF] + ff_payload
            # print("first_frame = ", first_frame)
            self.WriteMessages(self.TxId, first_frame)

            # Wait for Flow Control (FC)
            start_time = time.time()
            while time.time() - start_time < timeout:
                fc_message = self.ReadMessages()
                if fc_message and fc_message['id'] == self.RxId and fc_message['data'][0] == 0x30:
                    # block_size = fc_message['data'][1]
                    st_min = fc_message['data'][2]
                    break
                elif self.IsFiltered == True:
                    time.sleep(0.05)
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

    def __ReadUDSRequest(self, SendMultiFrameReaquest=True, isWorkingInThread=False, timeout=2):
        response = {"id": 0, "data": [], "status": False, "size": 0}
        frameReceived = False
        dataRemaining = 0
        responseCmdWait = 0
        FrameConsumed = True
        start_time = time.time()
        while time.time() - start_time < timeout:
            if isWorkingInThread:
                msg = self.q.peek()
                FrameConsumed = True
            else:
                msg = self.ReadMessages()
            if (msg is not None):
                if (len(msg['data']) > 0):
                    if (msg['data'][0] & 0xF0 == 0x0):
                        response["id"] = msg['id']
                        if ((msg['len']) <= 8):
                            response["size"] = msg['data'][0]
                            response["data"] = msg['data'][1:1+response["size"]]
                        else:
                            response["size"] = ((msg['data'][0] & 0xF) << 8) + msg['data'][1]
                            response["data"] = msg['data'][2:2+response["size"]]
                        frameReceived = True
                    elif (msg['data'][0] & 0xF0 == 0x10):
                        response["id"] = msg['id']
                        response["size"] = ((msg['data'][0] & 0xF) << 8) + msg['data'][1]
                        dataRemaining = response["size"]
                        response["data"].extend(msg['data'][2:])
                        dataRemaining -= len(response["data"])
                        responseCmdWait = 1
                        if SendMultiFrameReaquest:
                            self.WriteMessages(self.TxId, [0x30, 0x00, 0x00])
                    elif (msg['data'][0] & 0xF0 == 0x20) and (response["id"] == msg['id']):
                        if (msg['data'][0] & 0xF == responseCmdWait):
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
                    # Ignore MultiFrameReaquest when it is not sended
                    elif msg['data'][0] == 0x30:
                        # a multi frame is received
                        pass
                    else:
                        # Unknown frame received
                        FrameConsumed = False
                        break
                    if (isWorkingInThread and FrameConsumed):
                        self.q.get()
                        self.q.task_done()
                    if (frameReceived):
                        response["status"] = True
                        break
        return response

    def WriteReadRequest(self, data, resp_req=True, timeout=2):
        return_value = {"request" : [format_hex(item) for item in data], "response" : [],"status" : False}

        if self.comOk == False:
            print ("No Communication established")
            exit(0)
        
        with self.lock:
            try:
                self.__WriteUDSRequest(data, timeout)

                # Response not required
                if not resp_req:
                    return None
                
                start_time = time.time()
                while time.time() - start_time < timeout:

                    msg = self.__ReadUDSRequest()

                    if (msg['id'] == self.RxId):

                        if (msg['data'][0] == 0x7F) and (msg['data'][1] == data[0]):
                            error_code = msg['data'][2]
                            
                            if error_code != 0x78:
                                raise RuntimeError(f"Negative response: Error code 0x{error_code:02X}: " + self.__get_uds_nrc_description(error_code))
                            
                        elif verifyFrame(msg['data'], data, min(msg['size'], len(data))):
                            if len(msg['data']) < msg['size']: 
                                raise RuntimeError(f"Missing Data : Not all the expected {msg['size']} bytes data are received only {len(msg['data'])} bytes")
                            
                            return_value["response"] = [format_hex(item) for item in msg['data']]
                            return_value["status"] = True
                            break
                        
                        elif (msg['data'][0] == 0x74) and (msg['data'][1] == 0x10):
                            return_value["response"] = [format_hex(item) for item in msg['data']]
                            return_value["status"] = True
                            break

                        elif (msg['data'][0] == 0x76):
                            return_value["response"] = [format_hex(item) for item in msg['data']]
                            return_value["status"] = True
                            break

                        elif (msg['data'][0] == 0x77):
                            return_value["response"] = [format_hex(item) for item in msg['data']]
                            return_value["status"] = True
                            break
                        else:
                            print('WriteReadRequest Error : ', [format_hex(item) for item in msg['data']])

                
                if time.time() - start_time > timeout:
                    raise TimeoutError(f"Time out No Response")
                
            except Exception as e:
                return_value["response"] = e
                return_value["status"] = False
        # print(return_value)
        return return_value

    def RcRequest(self, message, timeout=2):
        # Set the return structure values
        return_value = {"request" : [format_hex(item) for item in message], "response" : [],"status" : False}
        if self.comOk == False:
            print ("No Communication established")
            exit(0)

        with self.lock:
            try:
                self.WriteMessages(self.TxId, message)

                start_time = time.time()
                while time.time() - start_time < timeout:
                    rc_msg = self.ReadMessages()

                    if (rc_msg is not None):
                        if((rc_msg['id'] == self.RxId) and\
                            (rc_msg['data'][1] == 0x71) and\
                            (rc_msg['data'][3] == message[3]) and\
                            (rc_msg['data'][4] == message[4])):

                            # Check RC type request
                            if(rc_msg['data'][2] == 0x1): # RC Start
                                return_value["response"] = [format_hex(item) for item in rc_msg['data']]
                                return_value["status"] = True
                                break

                            elif(rc_msg['data'][2] == 0x2): # RC Stop
                                return_value["response"] = [format_hex(item) for item in rc_msg['data']]
                                return_value["status"] = True
                                break

                            elif(rc_msg['data'][2] == 0x3): # RC Result
                                if(rc_msg['data'][0] >= 5):
                                    return_value["response"] = [format_hex(item) for item in rc_msg['data']]
                                    return_value["status"] = True
                                    break

                                elif(rc_msg['data'][0] == 4):
                                    return_value["response"] = [format_hex(item) for item in rc_msg['data']]
                                    return_value["status"] = True
                                    break

                                else:
                                    # 'ResultRc Error : Uncorrect size'
                                    return_value["response"] = [format_hex(item) for item in rc_msg['data']]
                                    return_value["status"] = False
                                    break
                            else:
                                # 'ResultRc Error : Undefined'
                                return_value["response"] = [format_hex(item) for item in rc_msg['data']]
                                return_value["status"] = False
                                break

                        elif((rc_msg['id'] == self.RxId) and\
                                (rc_msg['data'][1] == 0x7F) and\
                                (rc_msg['data'][2] == 0x31)):
                            # return 'NOK', rc_msg['data'], ('ResultRc Error : ' + self.__get_uds_nrc_description(rc_msg['data'][3]))
                            return_value["response"] = [format_hex(item) for item in rc_msg['data']]
                            return_value["status"] = False
                            break
                        else:
                            return_value["response"] = [format_hex(item) for item in rc_msg['data']]
                            return_value["status"] = False
                            break
                            # return 'NOK', rc_msg['data'], ('ResultRc Error : ', format_hex(rc_msg['data'][1]), format_hex(rc_msg['data'][2]), self.__get_uds_nrc_description(rc_msg['data'][3]))
                        
                if time.time() - start_time > timeout:
                    raise TimeoutError(f"Time out No Response")

            except Exception as e:
                return_value["response"] = e
                return_value["status"] = False
        
        print(return_value) # For debug
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

            data = self.WriteReadRequest(message)

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

    def WriteData(self, data):

        if self.comOk == False:
            print ("No Communication established")
            exit(0)
        try:
            if len(data) == 0 or len(data) > 4095:
                raise ValueError(f"Invalid data length: {len(data)}. Must be between 1 and 4095 bytes.")
            
            resp = self.WriteReadRequest(data)

            if resp["status"] == True:
                return [f'OK', '', 'Detail : ' + str(resp["response"])]
            else:
                return [f'NOK', '', 'WriteData Error : ' + str(self.__get_uds_nrc_description(resp["response"][3])) + ' => ' + str(resp["response"])]

        except Exception as e:
            return [f'NOK', '', e]

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
            if(data is None or len(data) == 0):
                message = [len(startRcMsgPL)] + startRcMsgPL
            else:
                if len(data) == 0 or len(data) > 4095:
                    raise ValueError(f"Invalid data length: {len(data)}. Must be between 1 and 4095 bytes.")
                else:
                    message = [len(startRcMsgPL + data)] + startRcMsgPL + data
            
            resp = self.RcRequest(message)
            
            if resp["status"] == True:
                if(resp["response"][0] == '0x04'):
                    return [f'OK', '', 'Remark : No output byte']
                else:
                    return [f'OK', '', 'Output data : ' + str(resp["response"][5:])]
            else:
                return [f'NOK', '', 'ResultRc Error : ' + str(self.__get_uds_nrc_description(resp["response"][3])) + ' => ' + str(resp["response"])]

        except Exception as e:
            return [f'NOK', '', e]

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

            resp = self.RcRequest(message)
            
            if resp["status"] == True:
                return [f'OK', '', str(resp["response"])]
            else:
                return [f'NOK', '', 'ResultRc Error : ' + str(self.__get_uds_nrc_description(resp["response"][3])) + ' => ' + str(resp["response"])]
        
        except Exception as e:
            return [f'NOK', '', e]

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

            resp = self.RcRequest(message)
            
            if resp["status"] == True:
                if(resp["response"][0] == 4):
                    return [f'OK', '', 'Remark : No output byte']
                else:
                    return [str(self.__get_uds_rc_status_desc(resp["response"][5])), '', '']
            else:
                return [f'NOK', '', 'ResultRc Error : ' + str(self.__get_uds_rc_status_desc(resp["response"][3])) + ' => ' + str(resp["response"])]
        
        except Exception as e:
            return [f'NOK', '', e]

    def ClearDTC(self, data):

        if self.comOk == False:
            print ("No Communication established")
            exit(0)
        try:
            if len(data) == 0 or len(data) > 3:
                raise ValueError(f"Invalid data length: {len(data)}. Must be between 1 and 3 bytes.")

            # Construct the first message payload
            message = [0x14] + data

            data = self.WriteReadRequest(message)

            if data["status"] == True:
                return [f"ClearDTC", True]
            else:
                return [f"ClearDTC", False, data["response"]]

        except Exception as e:
            return [f"ClearDTC Exception : ", False, e]

    def SecurityAccess(self, level: int, key: Optional[bytes] = None) -> bool:
        """Perform security access (request seed or send key)"""
        try:
            # Request seed (odd level)
            if level % 2 == 1:
                respData = self.WriteReadRequest([UDSService.SECURITY_ACCESS, level])
                if len(respData['response']) < 3:
                    raise ValueError("Invalid seed response length")
                
                # seed = response[]  # Skip SID and subfunction
                logger.info(f"Received seed: {respData['response']} => {respData['status']}")
                # Here you would typically compute the key from the seed
                # For this example, we'll just return True
                self.security_level = level
                return True
            
            # Send key (even level)
            elif key is not None:
                respData = self.WriteReadRequest([UDSService.SECURITY_ACCESS, level, 0xFF, 0xFF, 0xFF, 0xFF])
                print(str(respData['response']))
                self.security_level = level
                if(respData['status'] == True):
                    logger.info("Security access granted")
                    return True
                else:
                    logger.info("Security access failed")
                    return False
            
            else:
                raise ValueError("Key required for even security access levels")
        
        except Exception as e:
            logger.error(f"Security access failed: {str(e)}")
            return False
    
    def RequestDownload(
        self,
        memory_address: int,
        memory_size: int,
        address_format: int = 0x44,
        data_format: int = 0x00,
        segment_name: str = None
    ) -> bytes:
        """
        Sends a RequestDownload (SID 0x34) with configurable address and size formats.

        Parameters:
            memory_address (int): Starting address of memory region.
            memory_size (int): Size in bytes to download.
            address_format (int): ALFID byte, upper nibble = address length in bytes,
                                lower nibble = size length in bytes.
            data_format (int): Data format identifier (usually 0x00 for default).
            segment_name (str): Optional name for logging clarity.
        """

        address_length = (address_format >> 4) & 0x0F
        size_length = address_format & 0x0F

        if not (1 <= address_length <= 4 and 1 <= size_length <= 4):
            raise ValueError("Address and size format must be 1–4 bytes")

        addr_bytes = memory_address.to_bytes(address_length, 'big')
        size_bytes = memory_size.to_bytes(size_length, 'big')

        payload = list(bytes([0x34, data_format, address_format])) + list(addr_bytes) + list(size_bytes)

        segment_info = f" for segment '{segment_name}'" if segment_name else ""
        logger.info(
            f"RequestDownload{segment_info}: "
            f"Addr=0x{memory_address:X} (len={address_length}), "
            f"Size=0x{memory_size:X} (len={size_length})"
        )
        payload = [0x34, 0x82, 0x11, 0x00, 0x00]
        respData = self.WriteReadRequest(payload)
        print(respData)
        return True
    
    def RequestDownload_2(
        self,
    ) -> bytes:
        respData = self.WriteReadRequest([0x34, 0x83, 0x11, 0x00, 0x00])
        print(respData)
        return True
    
    def TransferData(self, block_number: int, data: bytes, address: int) -> bool:
        # """Transfer data block"""
        try:
            payload_1 = [0x36, block_number] + int_to_3bytes(address)
            payload_1.append(len(data))
            # print("payload_1 = ", [format_hex(item) for item in payload_1])
            # print("payload_1 = ", payload_1)
            # print("payload_1 = ", bytearray(payload_1))

            # print("Block H = ", data.hex())
            # print("Block = ", data)
            # print("Block len = ", len(data))
            payload = bytearray(payload_1) + bytearray(data)
            # print("payload = ", payload.hex())
            # print("payload len = ",len(payload))
            
            # Calculate Payload + Data Block CRC
            payload_crc = crc16_x25(payload) # Calculate CRC for block data
            payload_crc = ((payload_crc & 0xFF) << 8) | ((payload_crc >> 8) & 0xFF)
            payload_crc = int_to_2bytes(payload_crc)
            # print('block crc =', payload_crc)

            # Add CRC to the payload
            final_payload = payload + bytearray(payload_crc)
            # print(final_payload.hex())
            
            respData = self.WriteReadRequest(list(final_payload))
            # print(respData["response"])


            if len(respData["response"]) >= 2 and \
            int(respData["response"][0], 16) == 0x76 and \
            int(respData["response"][1], 16) == block_number:
                return True
            else:
                logger.error(f"TransferData failed response: {respData['response']}")
                exit()
                return False
            
        except Exception as e:
            logger.error(f"TransferData error: {str(e)} {respData['response']}")
            exit()
            return False
    
    def RequestTransferExit(self) -> bool:
        """Request transfer exit (finish download)"""
        try:
            respData = self.WriteReadRequest([0x37])
            print(respData)
            if respData["status"] == True:
                return True
            else:
                logger.error(f"Request transfer exit failed: {respData['response']}")
                return False
        except Exception as e:
            logger.error(f"Request transfer exit failed: {str(e)} {respData['response']}")
            return False

    def StartSession(self, number):
        status = 'NOK'
        error = ''
        if self.comOk == False:
            print ("No Communication established")
            exit(0)
        
        data = []
        data.append(0x10)
        data.append(number)
        respData = self.WriteReadRequest(data)

        if (respData["status"] == True):
            if(number == 1):
                print (f"Default session activated...")
            elif(number == 2):
                print (f"Programmation session activated...")
            elif(number == 3):
                print (f"Extended session activated...")
            else:
                print (f"Session number : {number} not identified")
            status = 'OK'
        else:
            status = 'NOK'
            error = str(respData['response'])
        return status, error

    def StartReset(self, rstReq):
        status = 'NOK'
        error = ''
        if self.comOk == False:
            print ("No Communication established")
            exit(0)
        
        data = []
        data.append(0x11)
        data.append(rstReq)
        respData = self.WriteReadRequest(data)

        if (respData["status"] == True):
            status = 'OK'
        else:
            status = 'NOK'
            error = str(respData['response'])

        return status, error

    def Pcan_ReadDID(self, did, size):
        retVal = self.ReadDID(did)

        if is_hex(retVal[0]) == True:
            data = ";".join(format_hex(int(x, 16)) for x in retVal or [])

            if((size is not None) and (size != '')):
                if is_int(size):
                    if (len(retVal) == int(size)):
                        result = "OK"
                        Error = ""
                    else:
                        result = "NOK"
                        Error = f"Data received with incorrect size, data size received {len(retVal)}, data size expected {size}"
                else:
                    result = "NOK"
                    Error = f"Size is not an integer {size}"
            else:
                result = "OK"
                Error = f"Remark : Size check not performed => No Size value defined"
        else:
            result = "NOK"
            data = ""
            Error = str(retVal[1])
        return result, data, Error

    def Pcan_WriteDID(self, did, dataraw=None):
        # Clean raw data
        data = string_to_hexList(dataraw, ';')
        # Process diagnostic request
        retVal = self.WriteDID(did, data)
        # Process the result
        if retVal[1] == True:
            status = "OK"
            Error = ""
        else:
            status = "NOK"
            Error = str(retVal[2])
        # Return a tuple (status, error)
        return status, Error

    def Pcan_WriteData(self, dataraw=None):
        # Clean raw data
        data = string_to_hexList(dataraw, ';')

        # Process diagnostic request
        return self.WriteData(data)

    def Pcan_StartRC(self, rcdid, dataraw=None):
        # Clean raw data
        data = string_to_hexList(dataraw, ';')

        # Process diagnostic request
        return self.StartRC(rcdid, data)

    def Pcan_StopRC(self, rcdid):
        # Process diagnostic request
        return self.StopRC(rcdid)

    def Pcan_ResultRC(self, rcdid):
        # Process diagnostic request
        return  self.ResultRC(rcdid)
    
    def Pcan_ClearDTC(self, dataraw=None):
        # Clean raw data
        data = string_to_hexList(dataraw, ';')

        # Process diagnostic request
        retVal = self.ClearDTC(data)
        # Process the result
        if retVal[1] == True:
            status = "OK"
            Error = ""
        else:
            status = "NOK"
            Error = str(retVal[2])
        # Return a tuple (status, error)
        return status, Error



    def getFrameFromId(self, canId, timeout=2):
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
            while ((time.time() - startTime) < timeout):
                msg = self.ReadMessages()
                if (msg is not None) and (msg['id'] == canId):
                    break
                elif self.IsFiltered == True:
                    time.sleep(0.1)
        return msg

    def __decodeFrame(self, data, size):
        returnValue = ""
        if data[0] == 0x7F:
            returnValue += f"Negative response: Error code 0x{data[2]:02X}: {UDSNegativeResponseCode(data[2]).name} for {self.__get_UDS_type_frame(data[1], data, negativeRequest=True)}"
        else:
            returnValue += self.__get_UDS_type_frame(data[0], data)
        if len(data) != size:
            returnValue += f", Needed {size} Bytes, received only {len(data)} Bytes"
        
        return returnValue

    def startCanStoringTrace(self, df=None, decodeFrame=True):
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
                        row["id"] = format_hex(msg['id'])
                        row["Data"] = [format_hex(item) for item in msg['data']]
                        row["Size"] = msg['size']
                        row["Comments"] = self.__decodeFrame(msg['data'], msg['size'])
                        print(row)
                        df.loc[len(df)] = row
                    elif  msg['id'] != 0:
                        row["Type"] = "TX" if self.TxId == msg["id"] else "RX" if self.RxId == msg["id"] else ""
                        row["id"] = format_hex(msg['id'])
                        row["Data"] = [format_hex(item) for item in msg['data']]
                        row["Size"] = msg['size']
                        row["Comments"] = "invalid Frame:" + self.__decodeFrame(msg['data'], msg['size'])
                        print(row)
                        df.loc[len(df)] = row
                else:
                    msg = self.ReadMessages()
                    if (msg is not None):
                        if (len(msg['data']) > 0):
                            row["Type"] = "TX" if self.TxId == msg["id"] else "RX" if self.RxId == msg["id"] else ""
                            row["id"] = format_hex(msg['id'])
                            row["Data"] = [format_hex(item) for item in msg['data']]
                            row["Size"] = len(msg['data'])
                            row["Comments"] = ""
                            print(row)
                            df.loc[len(df)] = row
        except Exception as e:
            print(f"Exception: {e}")
        finally:
            self.running = False  # Flag to control the worker loop
            worker_thread.join()
 
# -----------------------------------------------------------------------------------

# -----------------------------------------------------------------------------------

# class UDSNegativeResponseError(Exception):
#     """Exception for UDS negative responses"""
#     def __init__(self, service_id: int, error_code: int, error_name: str):
#         self.service_id = service_id
#         self.error_code = error_code
#         self.error_name = error_name
#         super().__init__(f"Negative response to service 0x{service_id:02X}: {error_name} (0x{error_code:02X})")

class UDSService(IntEnum):
    """UDS service identifiers"""
    DIAGNOSTIC_SESSION_CONTROL = 0x10
    ECU_RESET = 0x11
    SECURITY_ACCESS = 0x27
    COMMUNICATION_CONTROL = 0x28
    TESTER_PRESENT = 0x3E
    ACCESS_TIMING_PARAMETER = 0x83
    SECURED_DATA_TRANSMISSION = 0x84
    CONTROL_DTC_SETTING = 0x85
    RESPONSE_ON_EVENT = 0x86
    LINK_CONTROL = 0x87
    READ_DATA_BY_IDENTIFIER = 0x22
    READ_MEMORY_BY_ADDRESS = 0x23
    READ_SCALING_DATA_BY_IDENTIFIER = 0x24
    READ_DATA_BY_PERIODIC_IDENTIFIER = 0x2A
    DYNAMICALLY_DEFINE_DATA_IDENTIFIER = 0x2C
    WRITE_DATA_BY_IDENTIFIER = 0x2E
    WRITE_MEMORY_BY_ADDRESS = 0x3D
    CLEAR_DIAGNOSTIC_INFORMATION = 0x14
    READ_DTC_INFORMATION = 0x19
    INPUT_OUTPUT_CONTROL_BY_IDENTIFIER = 0x2F
    ROUTINE_CONTROL = 0x31
    REQUEST_DOWNLOAD = 0x34
    REQUEST_UPLOAD = 0x35
    TRANSFER_DATA = 0x36
    REQUEST_TRANSFER_EXIT = 0x37
    REQUEST_FILE_TRANSFER = 0x38



class ControllableThread(threading.Thread):
    def __init__(self, name: Optional[str] = None, interval: float = 0.2):
        super().__init__(name=name or "ControllableThread", daemon=True)
        self._logger = logging.getLogger(name)
        self._pause_event = threading.Event()
        self._stop_event = threading.Event()
        self._pause_event.set()  # Thread starts unpaused
        self._lock = threading.Lock() # or test : threading.Lock()
        self.interval = interval

    def run(self):
        self.on_start()
        while not self._stop_event.is_set():
            self._pause_event.wait()  # Wait here if paused
            with self._lock:
                self.on_tick()
            time.sleep(self.interval)
        self.on_stop()

    def pause(self):
        with self._lock:
            if self._pause_event.is_set():
                print(f"[{self.name}] Pausing")
                self._pause_event.clear()

    def resume(self):
        with self._lock:
            if not self._pause_event.is_set():
                print(f"[{self.name}] Resuming")
                self._pause_event.set()

    def stop(self):
        with self._lock:
            print(f"[{self.name}] Stopping")
            self._stop_event.set()
            self._pause_event.set()  # Unpause in case it's waiting
    
    def on_tick(self):
        raise NotImplementedError("Define behavior for each tick")

    def on_start(self):
        pass

    def on_stop(self):
        pass

    
    def _handle_error(self, error: Exception) -> None:
        """Default error handler - can be overridden by subclasses"""
        self._logger.error(f"Error in {self._name}: {str(error)}", exc_info=True)

    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
    
    @property
    def is_paused(self) -> bool:
        """Check if processing is paused"""
        return self._pause_event.is_set()

    @property
    def is_running(self) -> bool:
        """Check if thread is running"""
        return self._worker_thread is not None and self._worker_thread.is_alive()


class TesterPresentThread(ControllableThread):
    def __init__(self, uds_client, interval=0.2):
        super().__init__(name="TesterPresentThread", interval=interval)
        self.Uds = uds_client
        self.interval = interval
        # self.running = threading.Event()
        # self.running.set()
        # self.daemon = True  # Auto-stop on main exit

    def on_tick(self):
        try:
            respData = self.Uds.WriteReadRequest([UDSService.TESTER_PRESENT, 0x00])
            logger.debug(f"Sent TesterPresent Request = {respData['request']} \ Response = {respData['response']}")
        except Exception as e:
            logger.warning(f"TesterPresent failed: {e}")

    def on_start(self):
        print("[TesterPresent] Started")

    def on_stop(self):
        print("[TesterPresent] Stopped")

    # def run(self):
    #     logger.info("Starting TesterPresent rolling task")
    #     while self.running.is_set():
    #         try:
    #             respData = self.Uds.WriteReadRequest([UDSService.TESTER_PRESENT, 0x00])
    #             # print(str(respData['response']))
    #             logger.debug(f"Sent TesterPresent Request = {respData['request']} \ Response = {respData['response']}")
    #         except Exception as e:
    #             logger.warning(f"TesterPresent failed: {e}")
    #         time.sleep(self.interval)

    # def stop(self):
    #     logger.info("Stopping TesterPresent rolling task")
    #     self.running.clear()
