import struct
import lzo
from wos.utils import hash_to_filename, endianness, endian
from wos._resource_info import RESOURCE_INFO, RESOURCE_INFO_PLATFORM


NCH_BLOCK_SIZE = 0x80000
class PACKBase():
    
    @staticmethod
    def alignAddressToBoundary(address, alignment):
        return address + (-address & alignment - 1)
    
    
class PACKBlockHeader(PACKBase):
    def __init__(self, archive, data):
        self.archive = archive
        self.data = data
        self._parseBytes()
    
    def __repr__(self):
        import pprint
        return pprint.pformat(self.__dict__.items())
    
    def _parseBytes(self):
        # 32 byte header, block is padded to 0x80000 with \xA1
        magic, compressedDataSize, a2, decompressedDataSize, a4, a5, compressedDataEnd, a6 = struct.unpack_from(
            f"{endian.get()}4s7I", self.data)
        
        self.magic = magic
        self.compressedDataSize = compressedDataSize
        self.a2 = a2
        self.decompressedDataSize = decompressedDataSize
        self.a4 = a5
        self.a5 = a5
        self.compressedDataEnd = compressedDataEnd
        self.a6 = a6


class PACKBlock(PACKBase):
    BLOCK_SIGNATURE = b'NCH\x00'
    
    def __init__(self, archive, blockData):
        self.archive = archive
        self.blockData = blockData
        self._parseBytes()
    
    def _parseBytes(self):
        self.header = PACKBlockHeader(self.archive, self.blockData[:32])
        if self.header.magic != self.BLOCK_SIGNATURE:
            raise Exception(f"Block signature {self.BLOCK_SIGNATURE} missing in compressed block data.")
    
    def decompressBlock(self):
        compressedData = self.blockData[
                         self.header.compressedDataEnd - self.header.compressedDataSize:self.header.compressedDataEnd]
        return lzo.decompress(compressedData, False, self.header.decompressedDataSize, algorithm="LZO1X")


class PACKFileHeader(PACKBase):
    
    def __init__(self, archive, offset, index):
        self.archive = archive
        self.offset = offset
        self.index = index
        self._parseBytes()
        self.fileExt = RESOURCE_INFO_PLATFORM.get(self.archive.platform, RESOURCE_INFO).get(self.fileTypeId, '.bin').lower()[1:]
    
    @property
    def actualFilename(self):
        actualFilename = ""
        try:
            actualFilename = hash_to_filename(self.filenameHash)
        except Exception as ex:
            raise
        return actualFilename
    
    @property
    def filename(self):
        actualFilename = self.actualFilename
        bits = [f"F{self.index + 1:03}", f"0x{self.filenameHash:08X}", f"{actualFilename}", f"T{self.fileTypeId}", f"{self.fileExt}"]
        bits = [b for b in bits if b]
        return ".".join(bits)
        
    
    def _parseBytes(self):
        fileHeader = struct.unpack_from(f"{endian.get()}11I", self.archive.data, self.offset)
        self.offset += struct.calcsize(f"{endian.get()}11I")
        rest = []
        if fileHeader[8] != 0:
            rest = struct.unpack_from(f"{endian.get()}8I", self.archive.data, self.offset)
            self.offset += struct.calcsize(f"{endian.get()}8I")
        
        fileHeader = list(fileHeader) + list(rest)
        filenameHash, fileTypeId, dataOffset, dataSize, *_ = fileHeader
        self.filenameHash = filenameHash
        self.fileTypeId = fileTypeId
        self.dataOffset = dataOffset
        self.dataSize = dataSize
        self.data = self.archive.data[self.dataOffset:self.dataOffset + self.dataSize]


class PACKFileHeaderTable(PACKBase):
    def __init__(self, archive, offset):
        self.archive = archive
        self._parseBytes(offset)
    
    def _parseBytes(self, offset):
        offset += struct.calcsize(f"{endian.get()}I") * self.archive.header.fileCount
        self.fileHeaders = []
        for i in range(self.archive.header.fileCount):
            fileHeader = PACKFileHeader(self.archive, offset, i)
            self.fileHeaders.append(fileHeader)
            offset = fileHeader.offset


class PACKHeader(PACKBase):
    def __init__(self, archive):
        self.archive = archive
        self._parseBytes()
    
    def _parseBytes(self):
        header = struct.unpack_from(f"{endian.get()}16I", self.archive.data)
        self.fileCount = header[14]


class PACKArchive(PACKBase):
    FILE_HEADER_TABLE_OFFSET = 0x408
    
    def __init__(self, compressedData):
        self.compressedData = compressedData
        self._parseBytes()
    
    @property
    def files(self):
        return self.fileHeaderTable.fileHeaders
    
    def getFile(self, filename):
        for f in self.files:
            if f.filename == filename:
                return f
    
    
    def _parseBytes(self):
        NCH_BLOCK_SIZE = 0x80000
        
        self.compressedBlocks = []
        for i in range(0, len(self.compressedData), NCH_BLOCK_SIZE):
            raw = self.compressedData[i:i + NCH_BLOCK_SIZE]
            block = PACKBlock(self, raw)
            self.compressedBlocks.append(block)
            
        self.data = b''.join([b.decompressBlock() for b in self.compressedBlocks])
        self.header = PACKHeader(self)
        self.fileHeaderTable = PACKFileHeaderTable(self, self.FILE_HEADER_TABLE_OFFSET)
        

class PCPACKArchive(PACKArchive):
    endianness = "<"
    platform = "pc"
    
    def __init__(self, *args, **kwargs):
        with endianness(self.endianness):
            super().__init__(*args, **kwargs)

class PS3PACKArchive(PACKArchive):
    endianness = ">"
    platform = "ps3"
    
    def __init__(self, *args, **kwargs):
        with endianness(self.endianness):
            super().__init__(*args, **kwargs)
    
    def _parseBytes(self):
        offset = 0
        i = 0
        BLOCK_SIGNATURE = b'NCH\x00'
        self.data = b''
        
        while offset < len(self.compressedData):
            magic, dataSize, a1, decompressedDataSize, a2, a3, compressedDataEnd, a4 = struct.unpack_from(
                f"{endian.get()}4s7I",
                self.compressedData,
                offset=offset)
            
            compressedDataStart = offset + (compressedDataEnd - dataSize)
            compressedData = self.compressedData[compressedDataStart:compressedDataStart + dataSize]
            
            if magic != BLOCK_SIGNATURE:
                break
            
            shouldDecompress = decompressedDataSize != dataSize
            if shouldDecompress:
                decompressed = lzo.decompress(compressedData, False, decompressedDataSize, algorithm="LZO1X")
            else:
                decompressed = compressedData
            
            self.data += decompressed
            offset += compressedDataEnd
            
            while offset < len(self.compressedData) and self.compressedData[offset] == 0xA1:
                offset += 1
            
            i += 1
        
        print(f"Unpacked {i} blocks from PS3Archive")
        
        self.header = PACKHeader(self)
        self.fileHeaderTable = PACKFileHeaderTable(self, self.FILE_HEADER_TABLE_OFFSET)

class XEPACKArchive(PACKArchive):
    endianness = ">"
    platform = "xe"
    def __init__(self, *args, **kwargs):
        with endianness(self.endianness):
            super().__init__(*args, **kwargs)