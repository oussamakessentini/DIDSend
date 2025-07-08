import time
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Optional
from collections import defaultdict
from UDS.BinaryParser import *
from UDS.UDSInterface import TesterPresentThread, UDSInterface
from UDS.Utils import *
import intelhex

import binascii

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
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
        self.data_format: int = 0
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
            # print(self.block_size, hex(self.block_size))
            for idx in range(0, len(data), self.block_size):
                block = data[idx:idx + self.block_size]

                # Check directflow => No address + No Ckecksum
                if directFlow == True:
                    self.Uds.TransferData(self.block_number, block, 0)
                else:
                    self.Uds.TransferData(self.block_number, block, address, True)
                    # Update address offset
                    address = address + self.block_size

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

    def program_ulp_files(self, files_list: List[str]) -> None:
        """Program Intel HEX file to ECU"""
        
        # try:
        output_file = ""
        current_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        hex_file = ''
        self.block_size = 243

        for idx, file in enumerate(files_list):

            hex_file = remove_extension(file) + '.hex'

            run_srec_cat(
                srec_cat_path = current_path + "\\Tools\\srecord-1.65.0-win64\\bin\\srec_cat.exe",
                input_files = [(file, "Motorola")],
                output_file = hex_file,
                output_format = "Intel"
            )

            logger.info(f"Starting programming process for {os.path.basename(file)}")

            # Load HEX file data
            firmware_data = self.load_hex_file(hex_file)
            
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

            self.Uds.SecurityAccess_negociation(1, 2 , sa_debug=True) 

            print('')
            self.Uds.StartRC('FF00', [0x82, 0xf0, 0x5a])
            
            rc_ok = False
            while (rc_ok == False):
                # Request security access
                status, resp, error = self.Uds.ResultRC('FF00')

                if(status == 'ROUTINE_FINISHED_OK'):
                    rc_ok = True
                else:
                    wait_ms(300)
            
            reqDL = False
            self.block_number = 1
            # Program each segment
            for address, data in firmware_data.items():
                if reqDL == False:
                    reqDL = self.Uds.RequestDownload(data_format=0x82,
                                                    addr_len_format=0x11,
                                                    memory_addr=0x00,
                                                    memory_size=0x00)
                if reqDL == True:
                    if address > 0:
                        data_bytes = bytes(data)
                        logger.info(f"Programming segment at 0x{address:08X} ({len(data_bytes)} bytes)")
                        self.program_data(address, data_bytes)
            
            self.Uds.RequestTransferExit()

            self.Uds.StartRC('FF04')
            
            rc_ok = False
            while (rc_ok == False):          
                status, resp, error = self.Uds.ResultRC('FF04')
                if(status == 'ROUTINE_FINISHED_OK'):
                    rc_ok = True
                else:
                    wait_ms(300)

            reqDL = self.Uds.RequestDownload(data_format=0x83,
                                            addr_len_format=0x11,
                                            memory_addr=0x00,
                                            memory_size=0x00)
            if reqDL == True:
                payload = [0x36, 0x01, 0xff, 0xff, 0x00, 0x00, 0x13, 0x09, 0x15, 0x11, 0x22, 0x09, 0x01, 0x00, 0x00, 0x24, 0x05, 0x25, 0xfe, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0x5c, 0xe3, 0x6e, 0x50, 0xad]
                respData = self.Uds.WriteReadRequest(payload)
                if respData['status'] == False: raise UDSProgrammingError("No data found in HEX file")

            wait_ms(50)
            
            self.Uds.StartSession(1)
            
            logger.info(f"{os.path.basename(file)} => Programmed successfully")

            wait_ms(7000)
            
        # except Exception as e:
        #     logger.error(f"Programming failed: {str(e)}")
        #     raise

    def program_pdx_files(self, files_list: List[str]) -> None:
        """Program PDX files to ECU"""

        # try:

        DataBlockInfo = defaultdict(list)
        pdx_bin_files = []

        for idx, file in enumerate(files_list):
            pdxfBinFile, odxfDataFile, pdxDict = extractPdxFileInfo(file)
            pdx_bin_files.append(pdxfBinFile)
            DataBlockInfo[idx] = pdxDict

        # General info
        print("\nPDX General information :\n")
        print(f"ODX-F Template = {pdxDict['ODXF_TEMPLATE']}")
        print(f"Download type = {pdxDict['DOWNLOAD_TYPE']}")
        print(f"ECU = {pdxDict['ECU']} [Type {pdxDict['ECU_TYPE']}]")
        print("Expected idents :")
        print(f"  Hardware = {pdxDict['HARDWARE']}")
        print(f"  Boot Software = {pdxDict['BOOT_SOFTWARE']}")

        print("")

        for key, blockDict in DataBlockInfo.items():
            # print("PDX File :", os.path.basename(file)) #TODO Fix PDX name
            for idx in range (0, len(blockDict['DATA_BLOCKS'])):
                # print(blockDict['DATA_BLOCKS'][idx])
                print(f"Type and position : {swTypeDesc(blockDict['DATA_BLOCKS'][idx]['SW_REFERENCE'])} #{idx + 1}")
                print("Reference : "
                      f"{blockDict['DATA_BLOCKS'][idx]['SW_REFERENCE']} "
                      f"{blockDict['DATA_BLOCKS'][idx]['SW_INDEX']} "
                      f"{blockDict['DATA_BLOCKS'][idx]['SW_PRODUCT_ID']}")

                if(idx < len(blockDict['CHECKSUMS'])):
                    print(f"Fingerprint : {blockDict['CHECKSUMS'][idx]['CHECKSUM-RESULT']}")
                else:
                    print(f"Fingerprint : {blockDict['CHECKSUMS'][0]['CHECKSUM-RESULT']}")
                
                if(idx < len(blockDict['SECURITYS'])):
                    print(f"Signature : {blockDict['SECURITYS'][idx]['FW-SIGNATURE']}")
                else:
                    print(f"Signature : {blockDict['SECURITYS'][0]['FW-SIGNATURE']}")

                print(f"CS_Version : {blockDict['DATA_BLOCKS'][idx]['CS_VERSION']}")
            
            print("")

        # Check the PDX files and programmation method
        if len(pdx_bin_files) > 1:
            print(f"Multi PDX binaries detected :")
            logger.info(f"Starting programming process of the following PDX binary files :")
            for file in pdx_bin_files:
                print(f' - {os.path.basename(file)}')
        else:
            logger.info(f"Starting programming process of {os.path.basename(pdx_bin_files[0])}")
            print(f"PDX binary detected => {os.path.basename(pdx_bin_files[0])}.")

        # Start Programming sequence
        self.Uds.ReadDID('F02B')

        # Enter extented session
        self.Uds.StartSession(0x03)

        # Start TesterPresent background thread
        tp = TesterPresentThread(self.Uds, interval=0.5)
        tp.start()

        self.Uds.ReadDID('F01A')

        self.Uds.StartReset(0x2)
        
        wait_ms(7000)

        # Enter programming session
        self.Uds.StartSession(0x02)

        self.Uds.SecurityAccess_negociation(1, 2 , sa_debug=True)

        tp.pause()

        pdxInfo = {}
        dataBlock_TOB = {}
        dataBlock_POB = {}

        for idx, file in enumerate(pdx_bin_files):

            pdxInfo = DataBlockInfo[idx]
            # print(pdxInfo)
            print('')
            # Write target fingerprint X -------------------------------------------------
            logger.info(f"Software reference : {pdxInfo['DATA_BLOCKS'][0]['SW_REFERENCE']}")
            logger.info(f" => Write target fingerprint")

            cks_count = len(pdxInfo['CHECKSUMS'])
            # print("Number of CHECKSUM IDs:", cks_count)

            # Remove all non-hex characters except letters/numbers
            checksum_hex_str = ''.join(re.findall(r'[A-Fa-f0-9]+', pdxInfo['CHECKSUMS'][cks_count-1]['CHECKSUM-RESULT']))

            # Get TOB \ POB data
            dataBlock_TOB[idx] = pdxInfo['DATA_BLOCKS'][0]['TOB']
            dataBlock_POB[idx] = pdxInfo['DATA_BLOCKS'][0]['POB']
            # print(dataBlock_TOB[idx], dataBlock_POB[idx])

            retData = self.Uds.WriteDID('F01B',
                                        str_to_hexList(dataBlock_TOB[idx]) +
                                        str_to_hexList(dataBlock_POB[idx]) +
                                        str_to_hexList(checksum_hex_str))
            if(retData[1] != True): raise UDSProgrammingError(f"Write F01B => Failed => response {retData[2]}")
            # ---------------------------------------------------------------------------
            logger.info(f" => Number of segments : {len(pdxInfo['SEGMENTS'])}")

            # Write target signature X ---------------------------------------------
            logger.info(f" => Write target signature")
            retData = self.Uds.WriteDID('F03C', str_to_hexList(dataBlock_TOB[idx]) + str_to_hexList(dataBlock_POB[idx]) + str_to_hexList('00'))
            # print(retData)
            
            # Write target CS_Version X --------------------------------------------
            logger.info(f" => Write target CS_Version")
            retData = self.Uds.WriteDID('F03B', str_to_hexList(dataBlock_TOB[idx]) + str_to_hexList(dataBlock_POB[idx]) + str_to_hexList('0000'))
            # print(retData)

        retData = []
        seg_data = {}
        isCompressed = False

        for idx, file in enumerate(pdx_bin_files):
            print("\nCurrent PDX file =", os.path.basename(pdx_bin_files[idx]),'\n')
            self.data_offset = 0

            pdxInfo = DataBlockInfo[idx]

            # ----------------------------------------------------------------------------
            retData = self.Uds.StartRC('0702', str_to_hexList(dataBlock_TOB[idx]) + str_to_hexList(dataBlock_POB[idx]), timeout=20)
            if(retData[0] != 'OK'): raise UDSProgrammingError(f"StartRC('0708') => Failed => response {retData[2]}")
            # print(retVal)

            for seg in pdxInfo['SEGMENTS']:
                self.block_number = 1
                # print(seg) # For Debug

                if(seg['ENCRYPT-COMPRESS-METHOD'] != '00'):
                    self.data_format = int(seg['ENCRYPT-COMPRESS-METHOD'], 16)
                    isCompressed = True

                with BinaryParser(file, '<') as parser:
                    # Get segment size
                    if(isCompressed == True):
                        self.segment_size = seg['COMPRESSED-SIZE']
                        seg_data[seg['ID']] = parser._read_data(self.data_offset, seg['COMPRESSED-SIZE'])
                    else:
                        self.segment_size = seg['UNCOMPRESSED-SIZE']
                        seg_data[seg['ID']] = parser._read_data(self.data_offset, seg['UNCOMPRESSED-SIZE'])
                
                print("Segment information :")
                print(f" => Segment ID : {seg['ID']}")
                print(f" => Segment Compressed : {isCompressed}")
                print(f" => Segment start address : 0x{seg['SOURCE-START-ADDRESS']}")
                print(f" => Segment size : {self.segment_size}")

                # Read segment start address
                self.start_address = int(seg['SOURCE-START-ADDRESS'], 16)
                # Convert int to bytes (using only required number of bytes) then each byte to 2-digit hex string
                startAddr_hexList = int_to_byteList(self.start_address, 4)

                # Calculate minimum number of bytes needed
                sizeAddr_nbytes = max(1, (self.segment_size.bit_length() + 7) // 8)

                # Convert int to bytes (using only required number of bytes) then each byte to 2-digit hex string
                sizeAddr_hexList = int_to_byteList(self.segment_size, sizeAddr_nbytes)

                # For debug
                # print("startAddr_hexList =", startAddr_hexList)
                # print("sizeAddr_hexList  =", sizeAddr_hexList)

                addr_length_fmt = (len(startAddr_hexList) << 4) | len(sizeAddr_hexList)

                reqDL = self.Uds.RequestDownload(self.data_format,
                                                 addr_len_format=addr_length_fmt,
                                                 memory_addr=self.start_address,
                                                 memory_size=self.segment_size,
                                                 segment_name=seg['ID'],
                                                 ALFID_reversed=True)

                if reqDL == True:
                    logger.info(f"Programming segment at 0x{self.start_address:08X} ({len(seg_data[seg['ID']])} bytes)")
                    self.program_data(self.start_address, seg_data[seg['ID']], True)

                    print(f"\nTransfert Exit => {seg['ID']}\n")
                    self.Uds.RequestTransferExit()

                    # Update data offset value
                    self.data_offset = self.data_offset + self.segment_size
                else:
                    raise UDSProgrammingError("RequestDownload => failed")
                
            retData = self.Uds.StartRC('0708', str_to_hexList(dataBlock_TOB[idx]) +
                                                str_to_hexList(dataBlock_POB[idx]) , timeout=25)
            if(retData[0] != 'OK'): raise UDSProgrammingError(f"StartRC('0708') => Failed => response {retData[2]}")
            # ----------------------------------------------------------------------------

        if not seg_data:
            raise UDSProgrammingError("No data found in HEX binary file")
        
        retData = self.Uds.StartRC('0703', str_to_hexList('0000'), timeout=25)
        if(retData[0] != 'OK'): raise UDSProgrammingError(f"StartRC('0703') => Failed => response {retData[2]}")

        retData = self.Uds.StartRC('0705', str_to_hexList('0000'), timeout=25)
        if(retData[0] != 'OK'): raise UDSProgrammingError(f"StartRC('0705') => Failed => response {retData[2]}")

        retData = self.Uds.StartRC('0709', str_to_hexList('0000'), timeout=25)
        if(retData[0] != 'OK'): raise UDSProgrammingError(f"StartRC('0709') => Failed => response {retData[2]}")
    
        for idx, file in enumerate(pdx_bin_files):

            pdxInfo = DataBlockInfo[idx]

            extra_data = pdxInfo['DATA_BLOCKS'][0]['SW_REFERENCE'].replace('REF.', "") # ASCII => PBMS_XXXX

            # Check integrity code in the executing flash memory X -----------------------
            print('')
            logger.info(f"Software reference : {extra_data}")
            logger.info(f" => Check integrity code in the executing flash memory")

            retData = self.Uds.StartRC('0704', str_to_hexList(dataBlock_TOB[idx]) +
                                                str_to_hexList(dataBlock_POB[idx]) , timeout=25)
            if(retData[0] != 'OK'): logger.error(f"ECU programming failed: StartRC('0704') => Failed => response {retData[2]}")

            retData = self.Uds.StartRC('0706', str_to_hexList(dataBlock_TOB[idx]) +
                                                str_to_hexList(dataBlock_POB[idx]) , timeout=25)
            if(retData[0] != 'OK'): raise UDSProgrammingError(f"StartRC('0706') => Failed => response {retData[2]}")

            retData = self.Uds.StartRC('070A', str_to_hexList(dataBlock_TOB[idx]) +
                                                str_to_hexList(dataBlock_POB[idx]) , timeout=25)
            if(retData[0] != 'OK'): raise UDSProgrammingError(f"StartRC('070A') => Failed => response {retData[2]}")
            # ----------------------------------------------------------------------------

            # Write traceability information X -------------------------------------------
            logger.info(f" => Write traceability information")

            # print("PDX SW_REFERENCE =", extra_data, '\n') # For debug
        
            retData = self.Uds.WriteDID('F01C',
                                        str_to_hexList(dataBlock_TOB[idx]) +
                                        str_to_hexList(dataBlock_POB[idx]) +
                                        [len(extra_data)//2] +
                                        str_to_hexList(extra_data + '30303030'))

            if(retData[1] != True): raise UDSProgrammingError(f"WriteDID('F01C') => Failed => response {retData[2]}")
            # ----------------------------------------------------------------------------

            # Clean the PDX program temporary folders
            if os.path.exists(os.path.dirname(file)):
                shutil.rmtree(os.path.dirname(file))

        wait_ms(50)
        
        retData = self.Uds.StartReset(0x1)
        # print(retData)
        
        print('')
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
