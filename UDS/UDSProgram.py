import time
import logging
from enum import Enum
from dataclasses import dataclass
from typing import Dict, Optional
from UDS.UDSInterface import TesterPresentThread, UDSInterface
from UDS.Utils import *
import intelhex

import binascii

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ecu_programming.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class UDSProgrammingError(Exception):
    """Base exception for UDS programming errors"""
    pass

class SecurityAccessError(UDSProgrammingError):
    """Security access related errors"""
    pass

class DataTransferError(UDSProgrammingError):
    """Data transfer related errors"""
    pass

class TimeoutError(UDSProgrammingError):
    """Timeout related errors"""
    pass

# class UDSState(Enum):
#     """Programming session states"""
#     DEFAULT = 1
#     PROGRAMMING = 2
#     SECURITY_ACCESS = 3
#     TRANSFER_DATA = 4
#     TRANSFER_EXIT = 5

# @dataclass
# class UDSConfig:
#     """Configuration for UDS communication"""
#     interface: str = 'can0'
#     request_id: int = 0x7E0
#     response_id: int = 0x7E8
#     programming_session_timeout: float = 2.0      # seconds
#     security_access_timeout: float = 1.0         # seconds
#     data_transfer_timeout: float = 5.0           # seconds
#     max_retries: int = 3
#     block_size: int = 1024                       # bytes per transfer
#     security_level: int = 1                      # Default security level
#     key_algorithm: str = 'xor_ff'                # Simple XOR algorithm for example

# class UDSClient:
#     def __init__(self, config: UDSConfig):
#         self.config = config
#         self.state = UDSState.DEFAULT
#         self.current_security_level = 0
#         self._last_request_time = 0
#         self._last_response_time = 0
        
#         # Set up CAN and ISO-TP stack
#         self.can_bus = can.interface.Bus(
#             channel=config.interface,
#             bustype='socketcan'
#         )
        
#         self.tp = isotp.socket()
#         self.tp.set_opts(
#             txpad=0x00,
#             rxpad=0x00,
#             tx_stmin=0,
#             rx_stmin=0,
#             rx_ext_address=0,
#             tx_ext_address=0
#         )
#         self.tp.bind(self.can_bus, txid=config.request_id, rxid=config.response_id)
    
#     def __del__(self):
#         if hasattr(self, 'tp'):
#             self.tp.close()
#         if hasattr(self, 'can_bus'):
#             self.can_bus.shutdown()
    
#     def _send_request(self, data: bytes, timeout: float) -> bytes:
#         """Send UDS request and wait for response"""
#         try:
#             self.tp.send(data)
#             start_time = time.time()
            
#             while time.time() - start_time < timeout:
#                 if self.tp.available():
#                     response = self.tp.recv()
#                     if response:
#                         return response
#                 wait_ms(10)
            
#             raise TimeoutError(f"No response received within {timeout:.2f} seconds")
        
#         except Exception as e:
#             raise UDSProgrammingError(f"Communication error: {str(e)}")
    
#     def _validate_response(self, request: bytes, response: bytes) -> None:
#         """Validate the UDS response"""
#         if len(response) < 1:
#             raise UDSProgrammingError("Empty response received")
            
#         # Check for negative response
#         if response[0] == 0x7F:
#             error_code = response[2] if len(response) > 2 else 0
#             raise UDSProgrammingError(f"Negative response received. Service: 0x{request[0]:02X}, Error: 0x{error_code:02X}")
            
#         # Check SID (should be request SID + 0x40)
#         expected_sid = request[0] + 0x40
#         if response[0] != expected_sid:
#             raise UDSProgrammingError(f"Unexpected response SID. Expected: 0x{expected_sid:02X}, Got: 0x{response[0]:02X}")
    
#     def _generate_key(self, seed: bytes) -> bytes:
#         """Generate security key from seed (example implementation)"""
#         if self.config.key_algorithm == 'xor_ff':
#             # Simple XOR with 0xFF for demonstration
#             return bytes([b ^ 0xFF for b in seed])
#         else:
#             raise SecurityAccessError(f"Unsupported key algorithm: {self.config.key_algorithm}")
    
#     def change_session(self, session_type: int) -> None:
#         """Change diagnostic session (10)"""
#         request = bytes([0x10, session_type])
        
#         for attempt in range(self.config.max_retries):
#             try:
#                 response = self._send_request(request, self.config.programming_session_timeout)
#                 self._validate_response(request, response)
                
#                 if session_type == 0x02:  # Programming session
#                     self.state = UDSState.PROGRAMMING
#                 else:
#                     self.state = UDSState.DEFAULT
#                 logger.info(f"Session changed to 0x{session_type:02X}")
#                 return
                
#             except (UDSProgrammingError, TimeoutError) as e:
#                 logger.warning(f"Session change attempt {attempt + 1} failed: {str(e)}")
#                 if attempt == self.config.max_retries - 1:
#                     raise UDSProgrammingError(f"Failed to change session after {self.config.max_retries} attempts")

class ECUProgrammer:
    def __init__(self, uds_client: UDSInterface):
        self.Uds = uds_client
        self.programming_session_timeout: float = 2.0   # seconds
        self.security_access_timeout: float = 1.0       # seconds
        self.data_transfer_timeout: float = 5.0         # seconds
        self.max_retries: int = 3
        self.block_size: int = 243                      # bytes per transfer
        self.security_level: int = 1                    # Default security level
        self.key_algorithm: str = 'xor_ff'              # Simple XOR algorithm for example
        self.block_number: int = 1


    def load_hex_file(self, file_path: str, offset: int = 0) -> Dict[int, bytes]:
        """
        Load an Intel HEX file and return a dictionary of {adjusted_address: data_chunk},
        applying an optional address offset.

        :param file_path: Path to the Intel HEX file
        :param offset: Address offset to apply to each segment
        :return: Dict mapping adjusted start addresses to byte chunks
        """
        data = {}
        ih = intelhex.IntelHex(file_path)

        # Display all the Hex segments
        segments = ih.segments()
        print("All segments:", [(hex(start), hex(end)) for start, end in segments])

        for start, end in ih.segments():
            segment_data = ih.tobinarray(start=start, end=end - 1)
            adjusted_start = start + offset
            data[adjusted_start] = bytes(segment_data)
            if(offset > 0):
                print(f"[HEX] Segment 0x{start:08X}–0x{end - 1:08X} ➜ Adjusted 0x{adjusted_start:08X}, Size: {len(segment_data)}")

        return data
    
    def program_data(self, address: int, data: bytes) -> None:
        """Program data to ECU memory"""
        try:
            for idx in range(0, len(data), self.block_size):
                block = data[idx:idx + self.block_size]
                self.Uds.TransferData(self.block_number, block, address)

                # Check block number overflow
                if self.block_number < 0xFF:
                    self.block_number += 1
                else:
                    self.block_number = 0
                
                # logger.info(f"Block : {hex(self.block_number)} => Progress: {min(i + self.block_size, len(data))}/{len(data)} bytes")
            
            logger.info(f"Successfully programmed {len(data)} bytes at 0x{address:08X}")
            
        except Exception as e:
            logger.error(f"Programming failed: {str(e)}")
            raise

    def program_hex_file(self, hex_file_path: str) -> None:
        """Program Intel HEX file to ECU"""
        logger.info(f"Starting programming process for {hex_file_path}")
        
        # try:
        # Load HEX file data
        firmware_data = self.load_hex_file(hex_file_path)
        
        if not firmware_data:
            raise UDSProgrammingError("No data found in HEX file")

        # Enter programming session
        # self.change_session(0x02)
        self.Uds.StartSession(0x02)

        # Start TesterPresent background thread
        tp = TesterPresentThread(self.Uds, interval=0.5)
        tp.start()
        
        self.Uds.ReadDID('F080')
        self.Uds.ReadDID('F0FE')
        
        tp.pause()
        SA_OK = False
        while (SA_OK == False):
            # Request security access
            SA_OK = self.Uds.SecurityAccess(self.security_level)
            wait_ms(500)
        
        self.security_level = 2
        # Manually provide a 32-bit (4-byte) key
        key = bytes([0xFF, 0xFF, 0xFF, 0xFF])  # Replace with real OEM-calculated key

        if(self.Uds.SecurityAccess(self.security_level, key) == True):
            print('')
            self.Uds.StartRC('FF00', [0x82, 0xf0, 0x5a])
            
            rc_ok = False
            while (rc_ok == False):
                # Request security access
                status, resp, error = self.Uds.ResultRC('FF00')

                if(status == 'ROUTINE_FINISHED_OK'):
                    rc_ok = True
                else:
                    wait_ms(500)

        program_ok = False
        # Program each segment
        for address, data in firmware_data.items():
            if(address >= 0x4000): # Skip the first segment
                if program_ok == False:
                    program_ok = self.Uds.RequestDownload(address, len(data))
                if program_ok == True:
                    data_bytes = bytes(data)
                    logger.info(f"Programming segment at 0x{address:08X} ({len(data_bytes)} bytes)")
                    self.program_data(address, data_bytes)
                    # if address >= 0x10800:
                    #     break
        
        self.Uds.RequestTransferExit()

        self.Uds.StartRC('FF04')
        
        rc_ok = False
        while (rc_ok == False):
            wait_ms(100)            
            status, resp, error = self.Uds.ResultRC('FF04')
            print('status = ', status)
            if(status == 'ROUTINE_FINISHED_OK'):
                rc_ok = True
            print('')
        
        wait_ms(50)

        program_ok = self.Uds.RequestDownload_2()

        payload = [0x36, 0x01, 0xff, 0xff, 0x00, 0x00, 0x13, 0x09, 0x15, 0x11, 0x22, 0x09, 0x01, 0x00, 0x00, 0x24, 0x05, 0x25, 0xfe, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0x5c, 0xe3, 0x6e, 0x50, 0xad]
        respData = self.Uds.WriteReadRequest(payload)

        wait_ms(50)
        
        self.Uds.StartSession(1)
        
        logger.info("Programming completed successfully")
            
        # except Exception as e:
        #     logger.error(f"Programming failed: {str(e)}")
        #     raise


# if __name__ == "__main__":
#     # Configuration for your specific ECU
#     config = UDSConfig(
#         interface='can0',           # CAN interface name
#         request_id=0x7E0,           # ECU request ID
#         response_id=0x7E8,          # ECU response ID
#         programming_session_timeout=2.0,
#         security_access_timeout=1.0,
#         data_transfer_timeout=5.0,
#         max_retries=3,
#         block_size=1024,
#         security_level=1,           # ECU security level
#         key_algorithm='xor_ff'      # Replace with your ECU's key algorithm
#     )
