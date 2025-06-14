import time
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Optional
from UDS.BinaryParser import *
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

class UDSState(Enum):
    """Programming session states"""
    DEFAULT = 1
    PROGRAMMING = 2
    SECURITY_ACCESS = 3
    TRANSFER_DATA = 4
    TRANSFER_EXIT = 5

class DataBlockSize(Enum):
    """Programming block sizes"""
    BLOCK_256  = 0x100
    BLOCK_512  = 0x200
    BLOCK_1024 = 0x400
    BLOCK_2048 = 0x800

@dataclass
class UDSPdxProgConfig:
    """Configuration for UDS communication"""
    programming_session_timeout: float = 2.0  # seconds
    security_access_timeout: float = 1.0      # seconds
    data_transfer_timeout: float = 5.0        # seconds
    max_retries: int = 3
    block_size: int = DataBlockSize.BLOCK_2048.value - 3 # Subtract : Max-1, service ID, block number bytes
    security_level: int = 1                              # Default security level
    key_algorithm: str = 'xor_ff'                        # Simple XOR algorithm for example

class ECUProgrammer:
    def __init__(self, UdsClient: UDSInterface, progConfig: UDSPdxProgConfig):
        self.Uds = UdsClient
        self.programming_session_timeout: float = progConfig.programming_session_timeout
        self.security_access_timeout: float = progConfig.security_access_timeout
        self.data_transfer_timeout: float = progConfig.data_transfer_timeout
        self.max_retries: int = progConfig.max_retries
        self.block_size: int = progConfig.block_size
        self.security_level: int = progConfig.security_level
        self.key_algorithm: str = progConfig.key_algorithm
        self.block_number: int = 1
        self.start_address: str = ''
        self.segment_size: int = 0
        self.data_offset: int = 0


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
    
    def program_data(self, address: int, data: bytes, directFlow: bool = False) -> None:
        """Program data to ECU memory"""
        try:
            for idx in range(0, len(data), self.block_size):
                block = data[idx:idx + self.block_size]
                # Check directflow => No address + No Ckecksum
                if directFlow == True:
                    self.Uds.TransferData(self.block_number, block, 0)
                else:
                    self.Uds.TransferData(self.block_number, block, address)

                # Check block number overflow
                if self.block_number < 0xFF:
                    self.block_number += 1
                else:
                    self.block_number = 0
                
                logger.info(f"Block : {hex(self.block_number)} => Progress: {min(idx + self.block_size, len(data))}/{len(data)} bytes")
            
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

    def program_pdx_bin_file(self, bin_file_path: str, pdxInfo: dict) -> None:
        """Program Bin file to ECU"""
        logger.info(f"Starting programming process for {bin_file_path}")
        
        # try:
        print("bin_file_path = ", bin_file_path)

        with BinaryParser(bin_file_path, '<') as parser:

            self.Uds.ReadDID('F02B')
            self.Uds.ReadDID('F01A')

            self.Uds.StartReset(0x2)
            
            wait_ms(7000)

            # Enter programming session
            self.Uds.StartSession(0x02)

            # Start TesterPresent background thread
            tp = TesterPresentThread(self.Uds, interval=0.5)
            tp.start()

            SA_OK = False
            while (SA_OK == False):
                # Request security access
                SA_OK = self.Uds.SecurityAccess(self.security_level)
                wait_ms(500)
            
            self.security_level = 2
            # Manually provide a 32-bit (4-byte) key
            key = bytes([0xFF, 0xFF, 0xFF, 0xFF])  # Replace with real OEM-calculated key

            if(self.Uds.SecurityAccess(self.security_level, key) == True):
            
                cks_count = len(pdxInfo['CHECKSUMS'])
                # print("Number of CHECKSUM IDs:", cks_count)

                # Step 1: Remove all non-hex characters except letters/numbers
                hex_string = ''.join(re.findall(r'[A-Fa-f0-9]+', pdxInfo['CHECKSUMS'][cks_count-1]['CHECKSUM-RESULT']['VALUE']))

                # Step 2: Convert to bytes
                retVal = self.Uds.WriteDID('F01B',
                                           str_to_hexList(pdxInfo['TOB']) +
                                           str_to_hexList(pdxInfo['POB']) +
                                           str_to_hexList(hex_string))

                if(retVal[1] == True):
                    seg_count = len(pdxInfo['SEGMENTS'])
                    print("Number of segments =", seg_count)

                    retVal = self.Uds.WriteDID('F03C', str_to_hexList(pdxInfo['TOB']) + str_to_hexList(pdxInfo['POB']) + str_to_hexList('00'))
                    # print(retVal)

                    retVal = self.Uds.WriteDID('F03B', str_to_hexList(pdxInfo['TOB']) + str_to_hexList(pdxInfo['POB']) + str_to_hexList('0000'))
                    # print(retVal)

                    retVal = self.Uds.StartRC('0702', str_to_hexList(pdxInfo['TOB']) + str_to_hexList(pdxInfo['POB']), timeout=20)
                    # print(retVal)

                    tp.pause()

                    seg_data = {}
                    isCompressed = True # TODO

                    # Iterate only over the values in key 'b'
                    for seg in pdxInfo['SEGMENTS']:
                        self.block_number = 1
                        # print(seg) # For Debug

                        # Read segment data
                        # Convert to hex value
                        self.start_address = int(seg['SOURCE-START-ADDRESS'], 16)
                        # print(hex(self.start_address))

                        # Get segment size
                        if(isCompressed == True):
                            self.segment_size = seg['COMPRESSED-SIZE']
                            seg_data[seg['ID']] = parser._read_data(self.data_offset, seg['COMPRESSED-SIZE'])
                        else:
                            self.segment_size = seg['UNCOMPRESSED-SIZE']
                            seg_data[seg['ID']] = parser._read_data(self.data_offset, seg['UNCOMPRESSED-SIZE'])

                        # print("Segment size = ", len(seg_data[seg['ID']]))

                        reqDL = self.Uds.RequestDownload(self.start_address,
                                                         seg['UNCOMPRESSED-SIZE'],
                                                         address_format=0x34,
                                                         data_format=0x10,
                                                         segment_name=seg['ID'])
                        if reqDL == True:
                            logger.info(f"Programming segment at 0x{self.start_address:08X} ({len(seg_data[seg['ID']])} bytes)")
                            self.program_data(self.start_address, seg_data[seg['ID']], True)
                            print(f"\nTransfert Exit => {seg['ID']}\n")
                            self.Uds.RequestTransferExit()
                            # Update data offset value
                            self.data_offset = self.data_offset + self.segment_size
                        else:
                            raise UDSProgrammingError("RequestDownload => failed")

                    if not seg_data:
                        raise UDSProgrammingError("No data found in HEX file")
                    
                    retData = []

                    retData = self.Uds.StartRC('0708', str_to_hexList(pdxInfo['TOB']) +
                                                       str_to_hexList(pdxInfo['POB']) , timeout=25)
                    if(retData[0] != 'OK'): raise UDSProgrammingError("StartRC('0708') => Failed")

                    retData = self.Uds.StartRC('0703', str_to_hexList('0000'), timeout=25)
                    if(retData[0] != 'OK'): raise UDSProgrammingError("StartRC('0703') => Failed")

                    retData = self.Uds.StartRC('0705', str_to_hexList('0000'), timeout=25)
                    if(retData[0] != 'OK'): raise UDSProgrammingError("StartRC('0705') => Failed")

                    retData = self.Uds.StartRC('0709', str_to_hexList('0000'), timeout=25)
                    if(retData[0] != 'OK'): raise UDSProgrammingError("StartRC('0709') => Failed")

                    retData = self.Uds.StartRC('0704', str_to_hexList(pdxInfo['TOB']) +
                                                       str_to_hexList(pdxInfo['POB']) , timeout=25)
                    if(retData[0] != 'OK'): raise UDSProgrammingError("StartRC('0704') => Failed")

                    retData = self.Uds.StartRC('0706', str_to_hexList(pdxInfo['TOB']) +
                                                       str_to_hexList(pdxInfo['POB']) , timeout=25)
                    if(retData[0] != 'OK'): raise UDSProgrammingError("StartRC('0706') => Failed")

                    retData = self.Uds.StartRC('070A', str_to_hexList(pdxInfo['TOB']) +
                                                       str_to_hexList(pdxInfo['POB']) , timeout=25)
                    if(retData[0] != 'OK'): raise UDSProgrammingError("StartRC('070A') => Failed")

                    extra_data = pdxInfo['SW_REFERENCE'].replace('REF.', "") # ASCII => PBMS_XXXX
                    print("PDX SW_REFERENCE = ", extra_data)

                    retData = self.Uds.WriteDID('F01C',
                                                str_to_hexList(pdxInfo['TOB']) +
                                                str_to_hexList(pdxInfo['POB']) +
                                                [len(extra_data)//2] +
                                                str_to_hexList(extra_data + '30303030'))
                    # print(retData)

                    wait_ms(50)
                        
                    retData = self.Uds.StartReset(0x1)
                    # print(retData)
                        
                    logger.info("Programming completed successfully")
                    
                else:
                    raise UDSProgrammingError("Write F01B => Failed")
            
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
