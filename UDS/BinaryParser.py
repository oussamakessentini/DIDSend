import os
import mmap
import struct
from dataclasses import dataclass
from typing import BinaryIO, Dict, List, Tuple, Union, Optional

@dataclass
class BinaryField:
    name: str
    format: str  # struct format character
    offset: int
    description: str = ""
    value: Union[int, float, bytes, str] = None

class BinaryParser:
    """Enhanced binary file parser with large file support"""
    
    def __init__(self, file_path: str, byte_order: str = '<', buffer_size: int = 1024*1024):
        """
        Initialize parser with large file support
        :param file_path: Path to binary file
        :param byte_order: '<' for little-endian, '>' for big-endian
        :param buffer_size: Read buffer size in bytes (default: 1MB)
        """
        self.file_path = file_path
        self.byte_order = byte_order
        self.buffer_size = buffer_size
        self.fields: List[BinaryField] = []
        self._file: BinaryIO = None
        self._mmap = None
        self._file_size = 0
    
    def __enter__(self):
        self.open()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def open(self) -> None:
        """Open the binary file with memory mapping for large files"""
        try:
            self._file = open(self.file_path, 'rb')
            self._file_size = os.path.getsize(self.file_path)
            
            # Use memory mapping for files larger than 10MB
            if self._file_size > 10*1024*1024:
                self._mmap = mmap.mmap(self._file.fileno(), 0, access=mmap.ACCESS_READ)
            
            print(f"Opened binary file ({self._file_size:,} bytes)")
        except Exception as e:
            print(f"Failed to open file: {str(e)}")
            raise
    
    def close(self) -> None:
        """Close the file handle and clean up"""
        if self._mmap:
            self._mmap.close()
        if self._file and not self._file.closed:
            self._file.close()
        print("Closed binary file")
    
    def _read_data(self, offset: int, size: int) -> bytes:
        """Read data from either mmap or file with bounds checking"""
        if offset + size > self._file_size:
            raise ValueError(f"Read beyond file bounds (offset: {offset}, size: {size})")
        
        if self._mmap:
            return self._mmap[offset:offset+size]
        else:
            self._file.seek(offset)
            return self._file.read(size)
    
    def add_field(self, name: str, fmt: str, offset: int, description: str = "") -> None:
        """Add a field definition"""
        self.fields.append(BinaryField(
            name=name,
            format=fmt,
            offset=offset,
            description=description
        ))
    
    def parse(self) -> Dict[str, Union[int, float, bytes, str]]:
        """Parse all defined fields"""
        if not (self._file or self._mmap):
            raise RuntimeError("File not opened")
        
        results = {}
        
        for field in sorted(self.fields, key=lambda x: x.offset):
            try:
                format_str = self.byte_order + field.format
                size = struct.calcsize(format_str)
                data = self._read_data(field.offset, size)
                
                if field.format.endswith('s'):  # String type
                    field.value = data.decode('ascii').strip('\x00')
                else:
                    field.value = struct.unpack(format_str, data)[0]
                
                results[field.name] = field.value
                print(f"Parsed {field.name} = {field.value} at offset {field.offset}")
            
            except Exception as e:
                print(f"Failed to parse field {field.name}: {str(e)}")
                raise
        
        return results
    
    def read_all(self, chunk_size: Optional[int] = None) -> bytes:
        """Read entire file content (optionally in chunks)"""
        if not (self._file or self._mmap):
            raise RuntimeError("File not opened")
        
        if self._mmap:
            return self._mmap[:]
        
        self._file.seek(0)
        if chunk_size:
            while True:
                chunk = self._file.read(chunk_size)
                if not chunk:
                    break
                yield chunk
        else:
            return self._file.read()
    
    def find_pattern(self, pattern: bytes, start_offset: int = 0) -> int:
        """Find byte pattern in file, returns offset or -1 if not found"""
        if self._mmap:
            return self._mmap.find(pattern, start_offset)
        else:
            # For non-mmap files, read in chunks
            chunk_size = max(len(pattern), self.buffer_size)
            self._file.seek(start_offset)
            
            while True:
                chunk = self._file.read(chunk_size)
                if not chunk:
                    return -1
                
                pos = chunk.find(pattern)
                if pos >= 0:
                    return self._file.tell() - len(chunk) + pos
                
                # Handle pattern crossing chunk boundaries
                if len(chunk) >= len(pattern):
                    self._file.seek(self._file.tell() - len(pattern) + 1)

# Usage Example
if __name__ == "__main__":
    with BinaryParser("large_file.bin") as parser:
        # Add fields to parse (adjust offsets according to your format)
        parser.add_field("header", "4s", 0, "File header magic")
        parser.add_field("file_size", "I", 4, "Total file size")
        parser.add_field("entry_count", "Q", 8, "Number of entries")
        
        # Parse specific fields
        header_data = parser.parse()
        print("Header data:", header_data)
        
        # Read entire file in chunks
        print("\nReading entire file in chunks:")
        for chunk in parser.read_all(chunk_size=1024*1024):  # 1MB chunks
            print(f"Read chunk of {len(chunk):,} bytes")
        
        # Alternative: read entire file at once
        # full_content = parser.read_all()
        # print(f"\nRead {len(full_content):,} bytes total")