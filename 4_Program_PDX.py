from collections import defaultdict
from UDS.UDSInterface import *
from UDS.UDSProgram import *
from UDS.Utils import *
import time

project = None
PDX_Folder = None
ULP_Folder = None

if __name__ == "__main__":

    dir_name = os.path.dirname(os.path.abspath(__file__))
    FileConfig = loadConfigFilePath(dir_name)
    load_config(globals(), globals(), FileConfig)

    if(project == 'PR105'):
        Uds = UDSInterface(FileConfig=FileConfig)

        # Programmation Configuration
        programmer = ECUProgrammer(Uds, UDSPdxProgConfig())

        files_list = get_all_files_path(dir_name + PDX_Folder, ['.pdx'])

        # Program PDX files
        programmer.program_pdx_files(files_list)

    elif(project == 'PR128'):
        Uds = UDSInterface(FileConfig=FileConfig)

        # Programmation Configuration
        programmer = ECUProgrammer(Uds, UDSPdxProgConfig())

        files_list = get_all_files_path(dir_name + PDX_Folder, ['.pdx'])

        # Program PDX files
        programmer.program_pdx_files(files_list)
    else:
        print('Please add your project configuration')
