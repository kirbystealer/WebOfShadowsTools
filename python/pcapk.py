import struct
from collections import defaultdict

try:
    from ._utils import print_hex
except:
    pass

class APKFComponentDataCursor():
    def __init__(self, address, pos=0):
        self.address = address
        self.pos = pos
    
    def readChunk(self, data, numBytes, alignment):
        readPos = (self.pos - 1) + alignment & ~(alignment - 1)
        
        start, end = self.address + readPos, self.address + readPos + numBytes
        chunk = data[start:end]
        
        self.pos = readPos + numBytes
        return chunk, (start, end)


class APKFBase():
    
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


class APKFHeader(APKFBase):
    FORMAT = "<4s6I"
    
    def __init__(self, archive, offset=0):
        self.archive = archive
        self._parseBytes(offset)
    
    def _parseBytes(self, offset):
        magic, version, flagField, boolField, componentTypeCount, componentTablePtr, fileTablePtr = struct.unpack_from(
            self.FORMAT, self.archive.data, offset=offset)
        self.magic = magic
        self.version = version
        self.flagField = flagField
        self.boolField = boolField
        self.componentTypeCount = componentTypeCount
        self.componentTablePtr = componentTablePtr + struct.calcsize("5I")
        self.fileTablePtr = fileTablePtr


class APKFComponentHeader(APKFBase):
    FORMAT = "<4s5I"
    
    def __init__(self, archive, offset):
        self.archive = archive
        self._parseBytes(offset)
    
    def _parseBytes(self, offset):
        typeIdBytes, externalHandlerFlag, field2, field3, dataSize, dataOffset = struct.unpack_from(self.FORMAT,
                                                                                                    self.archive.data,
                                                                                                    offset=offset)
        self.typeIdBytes = typeIdBytes
        self.externalHandlerFlag = externalHandlerFlag
        self.field2 = field2
        self.field3 = field3
        self.dataSize = dataSize
        self.dataOffset = dataOffset
        
        self.baseDataAddress = offset + struct.calcsize("4s4I") + dataOffset
        self.dataCursor = APKFComponentDataCursor(self.baseDataAddress)


class APKFFile(APKFBase):
    def __init__(self, archive, fileTableHeader, offset):
        self.archive = archive
        self.fileTableHeader = fileTableHeader
        self.offset = offset
        self._parseBytes(offset)
        self.fileType = self.fileTableHeader.fileType
    
    def __repr__(self):
        return "%s:%s-%s-{%s}" % (
        self.fileType, self.filename, self.filenameHash, ', '.join([str(len(c)) for c in self.components]))
    
    def _parseBytes(self, offset):
        fileHeaderAddress = offset
        pFilename, filenameHash = struct.unpack_from("<II", self.archive.data, offset)
        self.offset += struct.calcsize("<II")
        
        filename = self.readNullTerminatedString(self.archive.data, fileHeaderAddress + pFilename)
        self.filename = str(filename, 'utf-8').replace('\x00', '')
        self.filenameHash = "0x%08X" % filenameHash
        
        componentSizesFmt = "<" + ("I" * self.fileTableHeader.nActiveComponents)
        componentSizes = list(struct.unpack_from(componentSizesFmt, self.archive.data, self.offset))
        self.offset += struct.calcsize(componentSizesFmt)
        
        self.components = []
        self.componentOffsets = []
        for i, componentSize in enumerate(componentSizes):
            
            beforePos = self.archive.componentHeaders[i].dataCursor.address + self.archive.componentHeaders[i].dataCursor.pos
            componentData, componentOffset = self.archive.componentHeaders[i].dataCursor.readChunk(self.archive.data,
                                                                                                   componentSize,
                                                                                                   self.fileTableHeader.componentByteAlignments[
                                                                                                       i] & 0xFFFFFF)
            self.components.append(componentData)
            self.componentOffsets.append(componentOffset)

class APKFFileTableHeader(APKFBase):
    FORMAT = "<4s4I"
    
    def __init__(self, archive, offset):
        self.archive = archive
        self.offset = offset
        self._parseBytes(self.offset)
        self._parseFileHeaders()
    
    def _parseBytes(self, offset):
        fileHeaderAddress = offset
        typeIdBytes, unk0, nActiveComponents, pFileHeaderTable, nFileHeaders = struct.unpack_from(self.FORMAT,
                                                                                                  self.archive.data,
                                                                                                  offset=offset)
        self.offset += struct.calcsize(self.FORMAT)
        self.typeIdBytes = typeIdBytes
        self.fileType = str(typeIdBytes, 'utf-8').replace('\x00', '')
        self.unk0 = unk0
        self.nActiveComponents = nActiveComponents
        self.pFileHeaderTable = fileHeaderAddress + struct.calcsize("3I") + pFileHeaderTable
        self.nFileHeaders = nFileHeaders
        
        componentAlignmentFmt = "<" + ("I" * len(self.archive.componentHeaders))
        self.componentByteAlignments = list(struct.unpack_from(componentAlignmentFmt, self.archive.data, offset=self.offset))
        self.offset += struct.calcsize(componentAlignmentFmt)
    
    def _parseFileHeaders(self):
        files = []
        offset = self.pFileHeaderTable
        for i in range(self.nFileHeaders):
            file = APKFFile(self.archive, self, offset)
            files.append(file)
            offset = file.offset
        
        self.endAddress = offset
        self.files = files


class APKFFileTable(APKFBase):
    FORMAT = "<4s4I"
    
    def __init__(self, archive, offset):
        self.archive = archive
        self._parseBytes(offset)
    
    def _parseBytes(self, offset):
        sentry = struct.unpack_from("<I", self.archive.data, offset)[0]
        
        headers = []
        filenameTableAddress = 0
        while sentry != 0:
            header = APKFFileTableHeader(self.archive, offset)
            headers.append(header)
            offset = header.offset
            sentry = struct.unpack_from("<I", self.archive.data, offset)[0]
        
        self.headers = headers
        self.filenameTableAddress = headers[-1].endAddress if headers else None


class APKFPatch(APKFBase):
    def __init__(self, patchIndex, patch, targetComponentTableIndex, targetComponentTableEntryIndex, targetAddress,
                 targetPtrRef, refIndex, refEntryIndex, refAddress, refValue):
        self.patchIndex = patchIndex
        self.patch = patch
        self.targetComponentTableIndex = targetComponentTableIndex
        self.targetComponentTableEntryIndex = targetComponentTableEntryIndex
        self.targetAddress = targetAddress
        
        self.targetPtrRef = targetPtrRef
        self.refIndex = refIndex
        self.refEntryIndex = refEntryIndex
        self.refAddress = refAddress  # This is what target actually becomes
        self.refValue = refValue
        self.patchType = "filename" if refIndex == 63 else 'pointer'
        
    def __str__(p):
        return f"[APKFPatch] componentTable{p.targetComponentTableIndex} @ 0x{p.targetAddress:0X} : 0x{p.targetPtrRef:0X}=>0x{p.refAddress:0X} = {p.refValue}"
    
    @classmethod
    def fromEncodedPatch(cls, data, patchIndex, patch, componentTableAddress, filenameTableAddress):
        targetComponentTableIndex = patch >> 26  # upper 6 [0-63]
        targetComponentTableEntryIndex = patch & 0x3FFFFFF  # lower 26
        
        baseDataPtrAddress = componentTableAddress + targetComponentTableIndex * 24 + 20
        baseDataAddress = struct.unpack_from("<I", data, baseDataPtrAddress)[0]
        targetPtr = baseDataPtrAddress + baseDataAddress + (targetComponentTableEntryIndex * 4)
        targetPtrRef = struct.unpack_from("<I", data, targetPtr)[0]
        
        refIndex = targetPtrRef >> 26
        refEntryIndex = targetPtrRef & 0x3FFFFFF
        
        refBaseAddress = componentTableAddress + refIndex * 24 + 20 if refIndex != 63 else filenameTableAddress
        
        if refIndex == 63:
            finalValue = refBaseAddress + refEntryIndex * 4
            refValue = cls.readNullTerminatedString(data, finalValue)
        else:
            baseDataOffset = struct.unpack_from("<I", data, offset=refBaseAddress)[0]
            finalValue = refBaseAddress + baseDataOffset + refEntryIndex * 4
            refValue = None
            
        return cls(patchIndex, patch, targetComponentTableIndex, targetComponentTableEntryIndex, targetPtr,
            targetPtrRef, refIndex, refEntryIndex, finalValue,
            refValue)


class APKFExternalRef(APKFBase):
    def __init__(self, field0, typeIdBytes, filenameOffset, filenameHash, filename):
        self.field0 = field0
        self.filenameOffset = filenameOffset
        self.filenameHash = filenameHash
        self.fileType = str(typeIdBytes, 'utf-8').replace('\x00', '')
        self.filename = str(filename, 'utf-8').replace('\x00', '')

class APKFArchive(APKFBase):
    def __init__(self, data):
        self.data = data
        self._parseBytes()
    
    def files(self, fileType=None):
        filteredFiles = [f for f in self._files if f.fileType == fileType] if fileType is not None else self._files
        return filteredFiles
    
    def findFileFromAddress(self, address):
        for f in self.files():
            for cStart, cEnd in f.componentOffsets:
                if cStart <= address < cEnd:
                    return f
            
    def _parseBytes(self):
        self.header = APKFHeader(self)
        
        self.offset = self.header.componentTablePtr
        self.componentHeaders = []
        for i in range(self.header.componentTypeCount):
            self.componentHeaders.append(APKFComponentHeader(self, self.offset))
            self.offset += struct.calcsize(APKFComponentHeader.FORMAT)
        
        self.offset = struct.calcsize(self.header.FORMAT)
        self.fileTable = APKFFileTable(self, self.offset)
        self._files = []
        self.fileTypes = set()
        for h in self.fileTable.headers:
            for f in h.files:
                self._files.append(f)
                self.fileTypes.add(f.fileType)
        self.fileTypes = list(self.fileTypes)
        
        if self.componentHeaders:
            self._parsePatchTable()
            self._parseExternalRefs()
    
    def _parsePatchTable(self):
        patchTableOffset = self.componentHeaders[-1].baseDataAddress + self.componentHeaders[-1].dataSize
        patchTableOffset = self.alignAddressToBoundary(patchTableOffset, 4)
        
        patches = []
        self.patchesToFileMap = {}
        self.fileToPatchesMap = defaultdict(list)
        
        self.offset = patchTableOffset
        patch = struct.unpack_from("<I", self.data, offset=self.offset)[0]
        patchIndex = 0
        while patch != 0xFFFFFFFF:
            apkfPatch = APKFPatch.fromEncodedPatch(self.data, patchIndex, patch, self.header.componentTablePtr,
                                                   self.fileTable.filenameTableAddress)
            
            
            patches.append(apkfPatch)
            patchedFile = self.findFileFromAddress(apkfPatch.targetAddress)
            self.patchesToFileMap[apkfPatch] = patchedFile
            self.fileToPatchesMap[patchedFile].append(apkfPatch)
            
            if patchedFile is None:
                raise Exception(f"Couldn't find {apkfPatch.targetAddress:0X} in any file component")
            
            self.offset += 4
            patch = struct.unpack_from("<I", self.data, offset=self.offset)[0]
            patchIndex += 1
    
    def _parseExternalRefs(self):
        externalRefFmt = "<I4sII"
        externalRefTableOffset = self.offset + 4
        externalRefs = []
        self.offset = externalRefTableOffset
        sentry = struct.unpack_from("<I", self.data, offset=self.offset)[0]
        while sentry != 0xFFFFFFFF:
            field0, typeIdBytes, filenameOffset, filenameHash = struct.unpack_from(externalRefFmt, self.data,
                                                                                   self.offset)
            filename = None
            if filenameOffset & 1 != 0:
                filename = self.readNullTerminatedString(self.data,
                                                         self.fileTable.filenameTableAddress + filenameOffset & 0xFFFFFFFE)
            externalRefs.append(APKFExternalRef(field0, typeIdBytes, filenameOffset, filenameHash, filename))
            self.offset += struct.calcsize(externalRefFmt)
            sentry = struct.unpack_from("<I", self.data, offset=self.offset)[0]


def createStandaloneFile(f, withPatches=True):
    headerStart, headerEnd = f.componentOffsets[0]
    patchedHeader = f.components[0]
    
    patchedData = None
    dataStart = dataEnd = -1
    if len(f.components) == 2:
        dataStart, dataEnd = f.componentOffsets[1]
        patchedData = f.components[1]
    
    if withPatches:
        # Perform any internal patches. External ones are ignored.
        sortedPatches = sorted(f.archive.fileToPatchesMap.get(f, []), key=lambda p: p.targetAddress)
        for p in sortedPatches:
            relativePatchFrom = None
            pointerDirection = "[BADPOINTER]"
            if headerStart <= p.targetAddress < headerEnd:
                if headerStart <= p.refAddress < headerEnd:
                    pointerDirection = f"[HEADER=>HEADER]"
                    relativePatchFrom = p.targetAddress - headerStart
                    relativePatchTo = p.refAddress - headerStart
                    patchedHeader = patchedHeader[:relativePatchFrom] + struct.pack("<I", relativePatchTo) + patchedHeader[relativePatchFrom+4:]
                elif dataStart <= p.refAddress < dataEnd:
                    pointerDirection = f"[HEADER=>DATA]"
                else:
                    pointerDirection = f"[HEADER=>External]"
            elif dataStart <= p.targetAddress < dataEnd:
                if dataStart <= p.refAddress < dataEnd:
                    pointerDirection = f"[DATA=>DATA]"
                    relativePatchFrom = p.targetAddress - headerStart
                    relativePatchTo = p.refAddress - headerStart
                    patchedData = patchedData[:relativePatchFrom] + struct.pack("<I", relativePatchTo) + patchedData[
                                                                                                             relativePatchFrom + 4:]
                elif headerStart <= p.refAddress < headerEnd:
                    pointerDirection = f"[DATA=>HEADER]"
                else:
                    pointerDirection = f"[DATA=>External]"
                    
                    
            print(f"{pointerDirection: <20}{p} ({relativePatchFrom})")
                    
    if patchedData:
        return b"PHYS".join([patchedHeader, patchedData])
    return patchedHeader
        
    



