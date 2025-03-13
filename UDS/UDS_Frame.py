import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from PCANBasicWrapper import PCANBasicWrapper
from CanApi4Wrapper import CanApi4Wrapper
import time
from Utils import *

class UDS_Frame():

    # Shows if DLL was found
    m_DLLFound = False

    def __init__(self, IsCanFD=False, TxID=0x18DADBF1, RxID=0x18DAF1DB, IsExtended=True, IsFiltered=True, IsPadded=False, PcanLib="CanApi4Lib", FileConfig=None):
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

        # get the configuration from file
        if FileConfig != None:
            load_config(self, globals(), FileConfig)

        if self.PcanLib == "PCANBasicLib":
            # load PCanBasic Wrapper
            self.m_objWrapper = PCANBasicWrapper(FileConfig=FileConfig, TxID=TxID, RxID=RxID, IsCanFD=IsCanFD, IsExtended=IsExtended, IsPadded=IsPadded, IsFiltered=IsFiltered)
        elif self.PcanLib == "CanApi4Lib":
            # load CanApi4 Wrapper
            self.m_objWrapper = CanApi4Wrapper(FileConfig=FileConfig, TxID=TxID, RxID=RxID, IsCanFD=IsCanFD, IsExtended=IsExtended, IsPadded=IsPadded, IsFiltered=IsFiltered)
        else:
            print ("Please define the correct PCANLib to use (PCANBasic or CanApi4) ")
            return

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
        data.append(0x2)
        data.append(0x10)
        data.append(number)
        self.WriteMessages(self.TxId, data)

        startTime = time.time()
        while ((time.time() - startTime) < self.timeout):
            msg = self.ReadMessages()
            if (msg != None) and (msg['data'][1] == 0x50) and (msg['data'][2] == number):
                print ("Session activated...")
                return True
            elif self.IsFiltered == True:
                time.sleep(0.1)
        print("StartSession : Time out No Response")
        return False

    def StartReset(self, rstReq):
        retState = False
        if self.comOk == False:
            print ("No Communication established")
            exit(0)
        
        data = []
        data.append(0x2)
        data.append(0x11)
        data.append(rstReq)
        self.WriteMessages(self.TxId, data)

        startTime = time.time()
        while ((time.time() - startTime) < self.timeout):
            msg = self.ReadMessages()
            if (msg is not None) and (msg['id'] == self.RxId):
                if (msg['data'][1] == 0x51) and (msg['data'][2] == rstReq):
                    print("StartReset : OK")
                    retState = True
                    break
                elif (msg['data'][1] == 0x7F) and (msg['data'][2] == 0x11):
                    print("StartReset : NRC 0x71")
                    retState = False
                    break
                elif self.IsFiltered == True:
                    print("StartReset : Wait")
                    time.sleep(0.01)
                break
        
        return retState

    def ReadDID(self, DID):
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
            message = [3] + [0x22, iDidHigh, iDidLow]
            self.WriteMessages(self.TxId, message)
            
            startTime = time.time()
            DataSizeRemaining = 0
            DataSize = 0
            response = []
            resp_ok = False

            while ((time.time() - startTime) < self.timeout):
                msg = self.ReadMessages()
                # print(msg)
                if (msg is not None) and (msg['id'] == self.RxId):
                    
                    if(msg['data'][1] == 0x62) and (msg['data'][2] == iDidHigh) and (msg['data'][3] == iDidLow):
                        resp_ok = True
                        DataSizeRemaining = msg['data'][0]
                        DataSize = DataSizeRemaining - 3
                        for i in range(4, DataSizeRemaining + 1):
                            response.append(format_hex(msg['data'][i]))
                        DataSizeRemaining = 0
                        break

                    # Check if the response is multi frame and extract the data
                    elif (msg['data'][2] == 0x62) and (msg['data'][3] == iDidHigh) and (msg['data'][4] == iDidLow):
                        resp_ok = True
                        if ((msg['data'][0] >> 4) == 0x1):
                            # Consecutive frame => parsing...
                            DataSizeRemaining = ((msg['data'][0] & 0x0F) << 8) | msg['data'][1]
                            DataSize = DataSizeRemaining - 3

                            for i in range(5, 8):
                                response.append(format_hex(msg['data'][i]))
                            # print(response)
                            DataSizeRemaining -= 6 # remove the first frame data (6 bytes)
                            # print(DataSizeRemaining)
                            sf_message = [0x30] # Request the next data
                            self.WriteMessages(self.TxId, sf_message)

                    # Retrive the next consecutive data
                    elif (msg['data'][0] >= 0x20) and (msg['data'][0] <= 0x2F):
                        range_temp = 0
                        if(DataSizeRemaining >= 7) :
                            range_temp = 7
                            DataSizeRemaining -= 7
                        else:
                            range_temp = DataSizeRemaining
                        
                        for i in range(0, range_temp):
                            response.append(format_hex(msg['data'][i+1]))
                        # print(range_temp, DataSizeRemaining)

                        # Check end of data to end the loop
                        if(range_temp == DataSizeRemaining) or (DataSizeRemaining == 0):
                            DataSizeRemaining = 0
                            break

                    elif (msg['data'][1] == 0x7F):
                        error_code = msg['data'][3]
                        if error_code != 0x78:
                            raise RuntimeError(f"Negative response: Error code 0x{error_code:02X}: " + self.__get_uds_nrc_description(error_code))

                elif self.IsFiltered == True:
                    time.sleep(0.1)
            if (DataSizeRemaining != 0):
                raise RuntimeError(f"Data missing: not all data received only {len(response)} bytes is received expected {DataSize} bytes")
            elif(resp_ok == True):
                return response
            else:
                raise TimeoutError(f"Time out No Response")
        
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

            if len(message) < 8:  # Single Frame
                sf_message = [len(message)] + message
                self.WriteMessages(self.TxId, sf_message)
            else:  # Multi-Frame Communication
                total_length = len(message)
                ff_payload = message[:6]
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
                else:
                    raise RuntimeError("No Flow Control received.")

                # Send Consecutive Frames
                seq_number = 1
                data_remaining = message[6:]  # Remaining data after the First Frame
                while data_remaining:
                    cf_payload = data_remaining[:7]
                    cf_message = [0x20 | seq_number] + cf_payload
                    self.WriteMessages(self.TxId, cf_message)
                    data_remaining = data_remaining[7:]
                    seq_number = (seq_number + 1) % 16  # Sequence number wraps around

                    # Wait for separation time (STmin)
                    time.sleep(st_min / 1000.0)

            # Wait for Positive Response (0x6E)
            start_time = time.time()
            while time.time() - start_time < self.timeout:
                response = self.ReadMessages()
                if response and response['id'] == self.RxId:
                    if response['data'][1] == 0x6E and response['data'][2] == did_high and response['data'][3] == did_low:
                        return [f"Write {DID}", True]
                    elif response['data'][1] == 0x7F:
                        error_code = response['data'][3]
                        raise RuntimeError(f"Negative response: Error code 0x{error_code:02X}: " + self.__get_uds_nrc_description(error_code))

            raise TimeoutError(f"Time out No Response")
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
            resultRcMsgPL = [0x31, 0x03, did_high, did_low]

            # Construct the message payload
            if(data is None):
                message = [len(startRcMsgPL)] + startRcMsgPL
            else:
                if len(data) == 0 or len(data) > 4095:
                    raise ValueError(f"Invalid data length: {len(data)}. Must be between 1 and 4095 bytes.")
                message = [len(startRcMsgPL + data)] + startRcMsgPL + data

            self.WriteMessages(self.TxId, message)
            rc_start = True
            
            start_time = time.time()
            while time.time() - start_time < self.timeout:
                rc_msg = self.ReadMessages()
                if (rc_msg is not None):
                    # print(rc_msg)
                    if((rc_msg['id'] == self.RxId) and\
                       (rc_msg['data'][1] == 0x71) and\
                       (rc_msg['data'][3] == did_high) and\
                       (rc_msg['data'][4] == did_low)):

                        if(rc_start == True):
                            if(data is not None):
                                if(rc_msg['data'][5] != data[0]):
                                    print('Error StartRC : wrong received data')
                                    break
                            # Request routine control result
                            message = [len(resultRcMsgPL)] + resultRcMsgPL

                            self.WriteMessages(self.TxId, message)
                            rc_start = False
                        else:
                            return self.__get_uds_rc_status_desc(rc_msg['data'][5])

                    elif((rc_msg['id'] == self.RxId) and\
                         (rc_msg['data'][1] == 0x7F) and\
                         (rc_msg['data'][2] == 0x31)):
                        return ('StartRc Error : ' + self.__get_uds_nrc_description(rc_msg['data'][3]))
                    else:
                        return ('StartRc Error : ', format_hex(rc_msg['data'][1]), format_hex(rc_msg['data'][2]), self.__get_uds_nrc_description(rc_msg['data'][3]))
                else:
                    time.sleep(0.1)
            raise TimeoutError(f"Time out No Response")
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

            self.WriteMessages(self.TxId, message)
            
            start_time = time.time()
            while time.time() - start_time < self.timeout:
                rc_msg = self.ReadMessages()
                if (rc_msg is not None):
                    # print(rc_msg)
                    if((rc_msg['id'] == self.RxId) and\
                       (rc_msg['data'][1] == 0x71) and\
                       (rc_msg['data'][3] == did_high) and\
                       (rc_msg['data'][4] == did_low)):

                        return 'ROUTINE_STOPPED_OK'

                    elif((rc_msg['id'] == self.RxId) and\
                         (rc_msg['data'][1] == 0x7F) and\
                         (rc_msg['data'][2] == 0x31)):
                        return ('StopRc Error : ' + self.__get_uds_nrc_description(rc_msg['data'][3]))
                    else:
                        return ('StopRc Error : ', format_hex(rc_msg['data'][1]), format_hex(rc_msg['data'][2]), self.__get_uds_nrc_description(rc_msg['data'][3]))
                else:
                    time.sleep(0.1)
            raise TimeoutError(f"Time out No Response")
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

            self.WriteMessages(self.TxId, message)
            rc_start = True
            
            start_time = time.time()
            while time.time() - start_time < self.timeout:
                rc_msg = self.ReadMessages()
                if (rc_msg is not None):
                    # print(rc_msg)
                    if((rc_msg['id'] == self.RxId) and\
                       (rc_msg['data'][1] == 0x71) and\
                       (rc_msg['data'][3] == did_high) and\
                       (rc_msg['data'][4] == did_low)):
                        return self.__get_uds_rc_status_desc(rc_msg['data'][5])

                    elif((rc_msg['id'] == self.RxId) and\
                         (rc_msg['data'][1] == 0x7F) and\
                         (rc_msg['data'][2] == 0x31)):
                        return ('ResultRc Error : ' + self.__get_uds_nrc_description(rc_msg['data'][3]))
                    else:
                        return ('ResultRc Error : ', format_hex(rc_msg['data'][1]), format_hex(rc_msg['data'][2]), self.__get_uds_nrc_description(rc_msg['data'][3]))
                else:
                    time.sleep(0.1)
            raise TimeoutError(f"Time out No Response")
        except Exception as e:
            return [f"Write {DID}", False, e]
