# -*- coding: utf-8 -*-

from io import StringIO
import os
from lxml import etree
import xml.etree.ElementTree as ET
import shutil


class Pdx_Odx(object):

    def __init__(self):
        self.odxTree = ''
        self.extract_dir=''
        self.out_path=''
        self.odxFile=''

    def pdx_unzip(self, filename, out_path):
      if os.path.exists(filename):
        if((filename != None) and (out_path != None)):
          shutil.unpack_archive(filename, out_path, 'zip')
        else:
          print('pdx_unzip : issue on the input arguments')
      else:
        print('[Error] pdx_unzip : file not found =>', filename)

    def pdx_zip(self, source_dir, out_file_path):
        if((source_dir != None) and (out_file_path != None)):
          shutil.make_archive(out_file_path, 'zip', source_dir)
        else:
          print('pdx_zip : issue on the input arguments')

    def getFilePath(self, path, pattern=None, extension=None):
        if (path != None) and (os.path.exists(os.path.realpath(path))):
          for file in os.listdir(os.path.realpath(path)):
            if extension != None:
              if file.endswith(extension):
                if pattern != None:
                  if pattern.upper() in file :
                    # print(os.path.realpath(path + file))
                    return os.path.realpath(path + file)
                else:
                  return os.path.realpath(path + file)
            else:
              print("Error [getFilePath] : Extension not defined")
              return None
        else:
            print("Error [getFilePath] : Folder not found")
            return None

    def getFolderPath(self, path):
        # print(os.path.realpath(path + file))
        folder_path = str(os.path.realpath(path)).replace('\\', "/")
        return folder_path

    def odx_get_value(self, odxFile='', xPath='', type='', attrib_idx=None, iteration = 0):
        try:
          odxTree = etree.parse(odxFile)
        except Exception as e:
          print(f"[ODX] Unexpected error while parsing {odxFile}:\n {e}")
          raise

        # Get Value in arboressance
        for child in odxTree.xpath(xPath):
            if(iteration == 0):
              if type == 'TAG':
                  # print(child.tag)
                  return child.tag
              
              elif type == 'ATTRIB':
                  if(attrib_idx != None):
                    # print(child.attrib[attrib_idx])
                    return child.attrib[attrib_idx]
                  else:
                    # print(child.attrib)
                    return child.attrib
              
              elif type == 'VALUE':
                  # print(child.text)
                  return child.text
              else:
                  print('odx_get_value : type => not defined')
            else:
              iteration = iteration - 1

    def odx_get_block_content(self, odxFile='', blockName=''):
        #  reading the file as UTF-8 with BOM support => "utf-8-sig" encoding strips the BOM
        with open(odxFile, "r", encoding="utf-8-sig") as file:
          # odxTree = ET.parse(file)
          odxTree = etree.parse(file)
          root = odxTree.getroot()

          if(blockName == ''):
            # print(etree.tostring(root, pretty_print=True, encoding='unicode')) # For debug
            return root
          
          # XPath to find block where child <name>
          block = root.find(f".//{blockName}")

          if block is None:
            print("No Block found")
          
          # print(etree.tostring(block, pretty_print=True, encoding='unicode')) # For debug
          return block


    def odx_set_value(self, odxFile='', xPath='', type='', attrib_idx=None, value=''):
        odxTree = etree.parse(odxFile)
        odxTreeRoot = odxTree.getroot()

        # Get Value in arboressance
        for child in odxTree.xpath(xPath):
            if type == 'TAG':
                # print(child.tag):
                child.tag = value
            
            elif type == 'ATTRIB':
                if(attrib_idx != None):
                  # print(child.attrib[attrib_idx])
                  child.attrib[attrib_idx] = value
                else:
                  # print(child.attrib)
                  child.attrib = value
            
            elif type == 'VALUE':
                # print(child.text)
                child.text = value
            else:
                print('odx_set_value : type => not defined')

            etree.ElementTree(odxTreeRoot).write(odxFile, encoding="utf-8", xml_declaration=True, pretty_print=True)

    def filesCounter(self, path):
      files_counter = 0
      for data in os.scandir(path):
          if data.is_file():
            files_counter += 1
      return files_counter

    def checkPdxGen(self, filename):
      self.pdxFile = self.getFilePath('resources/gsp/Output/', filename , '.pdx')
      # print(self.pdxFile)
      if (self.pdxFile != '' and self.pdxFile != None):
        return True
      else:
        return False


      # if ((self.pdxBootFile != None) and (self.pdxAppFile != None) and (self.pdxDataFile != None)):

      #   self.pdx_unzip(self.pdxBootFile, self.getFolderPath('resources/gsp/Output/Temp_Boot/'))
      #   self.pdx_unzip(self.pdxAppFile,  self.getFolderPath('resources/gsp/Output/Temp_App/'))
      #   self.pdx_unzip(self.pdxDataFile, self.getFolderPath('resources/gsp/Output/Temp_Data/'))

      #   self.odxBootFile = self.getFilePath('resources/gsp/Output/Temp_Boot/', '_BOOT', '.odx')
      #   # print(self.odxBootFile)
      #   self.odxAppFile  = self.getFilePath('resources/gsp/Output/Temp_App/',  '_APPLICATION_CODE', '.odx')
      #   # print(self.odxAppFile)
      #   self.odxDataFile = self.getFilePath('resources/gsp/Output/Temp_Data/', '_APPLICATION_DATA', '.odx')
      #   # print(self.odxDataFile)

      #   if ((self.odxBootFile != None) and (self.odxAppFile != None) and (self.odxDataFile != None)):
      #     return True
      #   else:
      #     print("[setupWorkSpace] => ODX Files not found")
      #     return False
      # else:
      #    print("[setupWorkSpace] => PDX Files not found")
      #    return False

    def updateOdxData(self, odxFile, ref, index, product_id, tob, pob, csversion):
        if odxFile != None :
          refData = ref + "." + index + "." + product_id
          self.odx_set_value(odxFile, 'FLASH/ECU-MEMS/ECU-MEM/MEM/SESSIONS/SESSION/DATABLOCK-REFS/DATABLOCK-REF', 'ATTRIB', 'ID-REF', refData)
          self.odx_set_value(odxFile, 'FLASH/ECU-MEMS/ECU-MEM/MEM/DATABLOCKS/DATABLOCK', 'ATTRIB', 'ID', refData)

          typeData = tob + ";" + pob + ";" + csversion
          self.odx_set_value(odxFile, 'FLASH/ECU-MEMS/ECU-MEM/MEM/DATABLOCKS/DATABLOCK', 'ATTRIB', 'TYPE', typeData)
        else:
           print("Error [updateOdxData] : ODX File not defined")

    def updatedPdx(self, pdxType, ref, index, product_id, tob, pob, csversion):
      
      if pdxType == 'BOOT':
        self.updateOdxData(self.odxBootFile, ref, index, product_id, tob, pob, csversion)
        
        self.pdx_zip(self.getFolderPath('resources/gsp/Output/Temp_Boot/'), self.pdxBootFile)
        # Rename updated PDX File
        shutil.move(self.pdxBootFile + '.zip', self.pdxBootFile)
        # Delete boot temporary folder
        shutil.rmtree(self.getFolderPath('resources/gsp/Output/Temp_Boot/'))

      elif pdxType == 'APP':
        self.updateOdxData(self.odxAppFile,  ref, index, product_id, tob, pob, csversion)

        self.pdx_zip(self.getFolderPath('resources/gsp/Output/Temp_App/'), self.pdxAppFile)
        # Rename updated PDX File
        shutil.move(self.pdxAppFile + '.zip', self.pdxAppFile)
        # Delete application temporary folder
        shutil.rmtree(self.getFolderPath('resources/gsp/Output/Temp_App/'))

      elif pdxType == 'DATA':
        self.updateOdxData(self.odxDataFile, ref, index, product_id, tob, pob, csversion)

        self.pdx_zip(self.getFolderPath('resources/gsp/Output/Temp_Data/'), self.pdxDataFile)
        # Rename updated PDX File
        shutil.move(self.pdxDataFile + '.zip', self.pdxDataFile)
        # Delete data temporary folder
        shutil.rmtree(self.getFolderPath('resources/gsp/Output/Temp_Data/'))

      else:
         print("Error [updatedPdx] : PDX Type not reconized")

    def getPdxReference(self, odxFile):
        if odxFile != None :
          # self.odx_get_value(odxFile, 'FLASH/ECU-MEMS/ECU-MEM/MEM/SESSIONS/SESSION/DATABLOCK-REFS/DATABLOCK-REF', 'ATTRIB', 'ID-REF')
          return self.odx_get_value(odxFile, 'FLASH/ECU-MEMS/ECU-MEM/MEM/DATABLOCKS/DATABLOCK', 'ATTRIB', 'ID')
        else:
           print("Error [updateOdxData] : ODX File not defined")
           
    def getPdxData(self, odxFile):
        
        dictPdxData = {}

        if odxFile != None :

          ident_content = self.odx_get_block_content(odxFile, 'EXPECTED-IDENTS')

          for ident in ident_content.findall("EXPECTED-IDENT"):
            # print(ident)
            id = ident.findtext("SHORT-NAME")
            if('ODXF_TEMPLATE' in id):
              dictPdxData['ODXF_TEMPLATE'] = ident.find("IDENT-VALUES/IDENT-VALUE").text

            if('HARDWARE_REFERENCE' in id):
              dictPdxData['HARDWARE'] = ident.find("IDENT-VALUES/IDENT-VALUE").text

            if('BOOT_REFERENCE' in id):
              dictPdxData['BOOT_SOFTWARE'] = ident.find("IDENT-VALUES/IDENT-VALUE").text

            if('TYPE' in id):
              tmp = ident.attrib.get("ID").replace('.', '_').split('_')
              dictPdxData['ECU_TYPE'] = tmp[2].lstrip("0")
              dictPdxData['DOWNLOAD_TYPE'] = ident.find("SHORT-NAME").text.split('_')[1]

          dictPdxData['ECU'] = self.odx_get_value(odxFile, 'FLASH/ECU-MEMS/ECU-MEM', 'ATTRIB', 'ID')

          cksBlock_content = self.odx_get_block_content(odxFile, 'CHECKSUMS')

          # Ensure CHECKSUMS key exists
          dictPdxData["CHECKSUMS"] = []

          for checksum in cksBlock_content.findall("CHECKSUM"):
            dictPdxData["CHECKSUMS"].append({
              "ID": checksum.attrib.get("ID"),
              "SHORT-NAME": checksum.findtext("SHORT-NAME"),
              "LONG-NAME": checksum.findtext("LONG-NAME"),
              "SOURCE-START-ADDRESS": checksum.findtext("SOURCE-START-ADDRESS"),
              "UNCOMPRESSED-SIZE": int(checksum.findtext("UNCOMPRESSED-SIZE")),
              "COMPRESSED-SIZE": int(checksum.findtext("COMPRESSED-SIZE")) if checksum.findtext("COMPRESSED-SIZE") is not None else "",
              "CHECKSUM-RESULT": checksum.find("CHECKSUM-RESULT").text
            })
          

          # dictPdxData['DATA_BLOCK'] = self.odx_get_value(odxFile, 'FLASH/ECU-MEMS/ECU-MEM/MEM/DATABLOCKS/DATABLOCK', 'ATTRIB', 'ID')

          dictPdxData["DATA_BLOCKS"] = []
          dataBlocks_content = self.odx_get_block_content(odxFile, 'DATABLOCKS')
          # print(dataBlocks_content)

          for idx, dataBlock in enumerate(dataBlocks_content.findall("DATABLOCK"), start=0):
            blockId = dataBlock.attrib.get('ID')
            blockType = dataBlock.attrib.get('TYPE')

            id_parts = blockId.split('.')

            # Process Software Reference Data
            dictPdxData["DATA_BLOCKS"].append({
              'SW_REFERENCE'  : ".".join(id_parts[:2]).lstrip(),
              'SW_INDEX'      : id_parts[2].lstrip(),
              'SW_PRODUCT_ID' : id_parts[3].lstrip(),
              'TOB'           : blockType.split(';')[0].lstrip(),
              'POB'           : blockType.split(';')[1].lstrip(),
              'CS_VERSION'    : blockType.split(';')[2].lstrip(),
            })

          # Ensure SEGMENTS key exists
          dictPdxData["SEGMENTS"] = []
          datablock_content = self.odx_get_block_content(odxFile, 'DATABLOCK')

          for segment in datablock_content.find("SEGMENTS").findall("SEGMENT"):
            dictPdxData["SEGMENTS"].append({
              "ID": segment.attrib.get("ID"),
              "SHORT-NAME": segment.findtext("SHORT-NAME"),
              "SOURCE-START-ADDRESS": segment.findtext("SOURCE-START-ADDRESS"),
              "UNCOMPRESSED-SIZE": int(segment.findtext("UNCOMPRESSED-SIZE")),
              "COMPRESSED-SIZE": int(segment.findtext("COMPRESSED-SIZE")),
              "ENCRYPT-COMPRESS-METHOD": segment.find("ENCRYPT-COMPRESS-METHOD").text
            })

          # Ensure SECURITYS key exists
          dictPdxData["SECURITYS"] = []

          for security in datablock_content.find("SECURITYS").findall("SECURITY"):
            dictPdxData["SECURITYS"].append({
              "SECURITY-METHOD": security.findtext("SECURITY-METHOD"),
              "FW-SIGNATURE": security.findtext("FW-SIGNATURE")
            })

          # Ensure SECURITYS key exists
          dictPdxData["INFOS"] = []

          dictPdxData["INFOS"].append({
          'ID_COMP_SHORT-NAME' : self.odx_get_value(odxFile, 'FLASH/COMPANY-DATAS/COMPANY-DATA/SHORT-NAME', 'VALUE', ''),
          'ID_COMP_LONG-NAME'  : self.odx_get_value(odxFile, 'FLASH/COMPANY-DATAS/COMPANY-DATA/LONG-NAME', 'VALUE', ''),
          'ID_TEAM_MEMBER_ID'  : self.odx_get_value(odxFile, 'FLASH/COMPANY-DATAS/COMPANY-DATA', 'ATTRIB', 'ID'),
          'ID_TEAM_MEMBER'     : self.odx_get_value(odxFile, 'FLASH/COMPANY-DATAS/COMPANY-DATA/TEAM-MEMBERS/TEAM-MEMBER/SHORT-NAME', 'VALUE', ''),
          'ID_TEAM_MEMBER_LN'  : self.odx_get_value(odxFile, 'FLASH/COMPANY-DATAS/COMPANY-DATA/TEAM-MEMBERS/TEAM-MEMBER/LONG-NAME', 'VALUE', ''),
          'ID_DESCRIPTION'     : self.odx_get_value(odxFile, 'FLASH/COMPANY-DATAS/COMPANY-DATA/TEAM-MEMBERS/TEAM-MEMBER/DESC/p', 'VALUE', ''),
          'ID_ROLE'            : self.odx_get_value(odxFile, 'FLASH/COMPANY-DATAS/COMPANY-DATA/TEAM-MEMBERS/TEAM-MEMBER/ROLES/ROLE', 'VALUE', ''),
          'ID_DEPARTMENT'      : self.odx_get_value(odxFile, 'FLASH/COMPANY-DATAS/COMPANY-DATA/TEAM-MEMBERS/TEAM-MEMBER/DEPARTMENT', 'VALUE', ''),
          'ID_ADDRESS'         : self.odx_get_value(odxFile, 'FLASH/COMPANY-DATAS/COMPANY-DATA/TEAM-MEMBERS/TEAM-MEMBER/ADDRESS', 'VALUE', ''),
          'ID_ZIP'             : self.odx_get_value(odxFile, 'FLASH/COMPANY-DATAS/COMPANY-DATA/TEAM-MEMBERS/TEAM-MEMBER/ZIP', 'VALUE', ''),
          'ID_CITY'            : self.odx_get_value(odxFile, 'FLASH/COMPANY-DATAS/COMPANY-DATA/TEAM-MEMBERS/TEAM-MEMBER/CITY', 'VALUE', ''),
          'ID_PHONE'           : self.odx_get_value(odxFile, 'FLASH/COMPANY-DATAS/COMPANY-DATA/TEAM-MEMBERS/TEAM-MEMBER/PHONE', 'VALUE', ''),
          'ID_FAX'             : self.odx_get_value(odxFile, 'FLASH/COMPANY-DATAS/COMPANY-DATA/TEAM-MEMBERS/TEAM-MEMBER/FAX', 'VALUE', ''),
          'ID_EMAIL'           : self.odx_get_value(odxFile, 'FLASH/COMPANY-DATAS/COMPANY-DATA/TEAM-MEMBERS/TEAM-MEMBER/EMAIL', 'VALUE', '')})
          # print(dictPdxData) # For debug

        else:
          print("Error [updateOdxData] : ODX File not defined")
          
        return dictPdxData

# if __name__ == '__main__':
#     odxC = Pdx_Odx()

#     if(odxC.setupWorkSpace() == True):
#       print("OK -------------------------- ")
#       data = odxC.getPdxReference(odxC.odxBootFile)
#       for i in range(0, 4):
#         print(data.split('.')[i].lstrip())
#       data = odxC.getPdxReference(odxC.odxAppFile)
#       for i in range(0, 4):
#         print(data.split('.')[i].lstrip())
#       data = odxC.getPdxReference(odxC.odxDataFile)
#       for i in range(0, 4):
#         print(data.split('.')[i].lstrip())

#       print("Goooo")
#       data = odxC.getPdxData(odxC.odxDataFile)
#       for i in range(0, 3):
#         print(data.split(';')[i].lstrip())

#       # odxC.updatedPdx('BOOT', 'REF.PBMS_BOOT',  '03', '09')
#       # odxC.updatedPdx('APP',  'REF.PBMS_APPLI', '09', '07')
#       # odxC.updatedPdx('DATA', 'REF.PBMS_DATA',  '05', '03')
#     else:
#        print("Error [setupWorkSpace] : PDX Files not found")
