import struct
import io

import lzo

try:
    from ._utils import print_hex, hash_to_filename
except:
    hash_to_filename = None

from ._resource_info import RESOURCE_INFO

NCH_BLOCK_SIZE = 0x80000
class PCPACKBase():
    
    @staticmethod
    def alignAddressToBoundary(address, alignment):
        return address + (-address & alignment - 1)
    
    @staticmethod
    def readNullTerminatedString(data, offset):
        c = struct.unpack_from("<s", data, offset)[0]
        filename = b""
        i = 0
        while c != b'\x00':
            c = struct.unpack_from("<s", data, offset + i)[0]
            filename += c
            i += 1
            if i > 256:
                raise Exception("NullTerminatedString too long: %s" % filename)
        return filename


class PCPACKBlockHeader(PCPACKBase):
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
            "<4s7I", self.data)
        self.magic = magic
        self.compressedDataSize = compressedDataSize
        self.a2 = a2
        self.decompressedDataSize = decompressedDataSize
        self.a4 = a5
        self.a5 = a5
        self.compressedDataEnd = compressedDataEnd
        self.a6 = a6


class PCPACKBlock(PCPACKBase):
    BLOCK_SIGNATURE = b'NCH\x00'
    
    def __init__(self, archive, blockData):
        self.archive = archive
        self.blockData = blockData
        self._parseBytes()
    
    def _parseBytes(self):
        self.header = PCPACKBlockHeader(self.archive, self.blockData[:32])
        if self.header.magic != self.BLOCK_SIGNATURE:
            raise Exception(f"Block signature {self.BLOCK_SIGNATURE} missing in compressed block data.")
    
    def decompressBlock(self):
        compressedData = self.blockData[
                         self.header.compressedDataEnd - self.header.compressedDataSize:self.header.compressedDataEnd]
        return lzo.decompress(compressedData, False, self.header.decompressedDataSize, algorithm="LZO1X")


class PCPACKFileHeader(PCPACKBase):
    
    def __init__(self, archive, offset, index):
        self.archive = archive
        self.offset = offset
        self.index = index
        self._parseBytes()
        self.fileExt = RESOURCE_INFO.get(self.fileTypeId, '.bin').lower()[1:]
    
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
        fileHeader = struct.unpack_from("<11I", self.archive.data, self.offset)
        self.offset += struct.calcsize("<11I")
        rest = []
        if fileHeader[8] != 0:
            rest = struct.unpack_from("<8I", self.archive.data, self.offset)
            self.offset += struct.calcsize("<8I")
        
        fileHeader = list(fileHeader) + list(rest)
        filenameHash, fileTypeId, dataOffset, dataSize, *_ = fileHeader
        self.filenameHash = filenameHash
        self.fileTypeId = fileTypeId
        self.dataOffset = dataOffset
        self.dataSize = dataSize
        self.data = self.archive.data[self.dataOffset:self.dataOffset + self.dataSize]


class PCPACKFileHeaderTable(PCPACKBase):
    def __init__(self, archive, offset):
        self.archive = archive
        self._parseBytes(offset)
    
    def _parseBytes(self, offset):
        offset += struct.calcsize("<I") * self.archive.header.fileCount
        self.fileHeaders = []
        for i in range(self.archive.header.fileCount):
            fileHeader = PCPACKFileHeader(self.archive, offset, i)
            self.fileHeaders.append(fileHeader)
            offset = fileHeader.offset


class PCPACKHeader(PCPACKBase):
    def __init__(self, archive):
        self.archive = archive
        self._parseBytes()
    
    def _parseBytes(self):
        header = struct.unpack_from("<16I", self.archive.data)
        self.fileCount = header[14]


class PCPACKArchive(PCPACKBase):
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
        
        self.compressedBlocks = [PCPACKBlock(self, b) for b in [self.compressedData[i:i + NCH_BLOCK_SIZE] for i in
                                                                range(0, len(self.compressedData), NCH_BLOCK_SIZE)]]
        self.data = b''.join([b.decompressBlock() for b in self.compressedBlocks])
        self.header = PCPACKHeader(self)
        self.fileHeaderTable = PCPACKFileHeaderTable(self, self.FILE_HEADER_TABLE_OFFSET)
        
        
def editExistingFileAndRepack(archive, filename, newFileData):
    existingFile = archive.getFile(filename)
    if not existingFile:
        raise Exception(f"Could not find existing filename {filename} in archive.")
    
    if len(newFileData) != existingFile.dataSize:
        raise Exception("New data size must match existing data size!")
    
    start, end = existingFile.dataOffset, existingFile.dataOffset+existingFile.dataSize
    
    newData = b''.join([archive.data[:start], newFileData, archive.data[end:]])
    
    newData = lzo.compress(newData, 9, False, algorithm="LZO1X")
    newBlocks = [newData[i:i+NCH_BLOCK_SIZE] for i in range(0, len(newData), NCH_BLOCK_SIZE)]
    # print([len(b) for b in newBlocks])
    # compressedBlocks = [lzo.compress(b, 9, False, algorithm="LZO1X") for b in newBlocks]
    # print([len(b) for b in compressedBlocks])
    compressedBlocks = newBlocks
    
    outBlocks = []
    for i, blockData in enumerate(compressedBlocks):
        decompressedBufferSize = len(newBlocks[i])
        compressedFlag = 1
        blockHeader = struct.pack("<4s7I", b"NCH\x00", len(blockData), 0, decompressedBufferSize, 0, 0,
                                  32 + len(blockData),
                                  compressedFlag)
        outBlock = blockHeader + blockData
        paddingLength = NCH_BLOCK_SIZE - len(outBlock)
        outBlock += b'\xA1' * paddingLength
        outBlocks.append(outBlock)
   
    print([len(b) for b in outBlocks])
    return b''.join(outBlocks)