import functools
import struct
import bisect
from collections import defaultdict, Counter
import re
from dataclasses import dataclass

from wos.utils import endian, log

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

@dataclass
class EncodedPointer():
    bucket: int
    offset: int
    address: int

class APKFBase():
    
    @staticmethod
    def alignAddressToBoundary(address, alignment):
        return address + (-address & alignment - 1)
    
    @staticmethod
    def readNullTerminatedString(data, offset, convertToString=False):
        c = struct.unpack_from(f"{endian.get()}s", data, offset)[0]
        filename = b""
        i = 0
        while c != b'\x00':
            c = struct.unpack_from(f"{endian.get()}s", data, offset + i)[0]
            filename += c
            i += 1
            if i > 256:
                raise Exception("NullTerminatedString too long: %s" % filename)
        if convertToString:
            return filename.split(b'\x00')[0].decode('utf-8')
        return filename


class APKFHeader(APKFBase):
    def __init__(self, archive, offset=0):
        self.FORMAT = f"{endian.get()}4s6I"
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
    FORMAT = f"4s5I"
    
    def __init__(self, archive, offset):
        self.FORMAT = f"{endian.get()}4s5I"
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
        
    @property
    def components(self):
        components = []
        componentOffsets = getattr(self, 'componentOffsets', [])
        for o in componentOffsets:
            components.append(self.archive.data[slice(*o)])
        return components
    
    @property
    def unpatchedComponents(self):
        components = []
        componentOffsets = getattr(self, 'componentOffsets', [])
        for o in componentOffsets:
            components.append(self.archive._unpatchedData[slice(*o)])
        return components
    
    def __repr__(self):
        return "%s:%s-%s-{%s}" % (
        self.fileType, self.filename, self.filenameHash, ', '.join([str(len(c)) for c in self.components]))
    
    def _parseBytes(self, offset):
        fileHeaderAddress = offset
        pFilename, filenameHash = struct.unpack_from(f"{endian.get()}II", self.archive.data, offset)
        self.offset += struct.calcsize(f"{endian.get()}II")
        
        filename = self.readNullTerminatedString(self.archive.data, fileHeaderAddress + pFilename)
        self.filename = str(filename, 'utf-8').replace('\x00', '')
        self.filenameHash = "0x%08X" % filenameHash
        
        componentSizesFmt = f"{endian.get()}" + ("I" * self.fileTableHeader.nActiveComponents)
        componentSizes = list(struct.unpack_from(componentSizesFmt, self.archive.data, self.offset))
        self.offset += struct.calcsize(componentSizesFmt)
        
        self.componentOffsets = []
        for i, componentSize in enumerate(componentSizes):
            
            beforePos = self.archive.componentHeaders[i].dataCursor.address + self.archive.componentHeaders[i].dataCursor.pos
            componentData, componentOffset = self.archive.componentHeaders[i].dataCursor.readChunk(self.archive.data,
                                                                                                   componentSize,
                                                                                                   self.fileTableHeader.componentByteAlignments[
                                                                                                       i] & 0xFFFFFF)
            self.componentOffsets.append(componentOffset)

    @property
    def prettyFilename(self):
        return f"{self.filename}.{self.fileType.lower()}"
    
    def toStandaloneFile(self):
        sortedPatches = sorted(self.archive.fileToPatchesMap.get(self, []), key=lambda p: p.targetAddress)
        out = Wrapper.wrapResourceFile(self.components, self.componentOffsets,
                                       sortedPatches,
                                       self.archive.archiveFilenameHash)
        return out

class APKFFileTableHeader(APKFBase):
    
    def __init__(self, archive, offset):
        self.FORMAT = f"{endian.get()}5I"
        
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
        self.typeIdBytes = typeIdBytes.to_bytes(4, "little")
        self.fileType = self.typeIdBytes.decode('utf-8').replace('\x00', '')
        self.unk0 = unk0
        self.nActiveComponents = nActiveComponents
        self.pFileHeaderTable = fileHeaderAddress + struct.calcsize("3I") + pFileHeaderTable
        self.nFileHeaders = nFileHeaders
        
        componentAlignmentFmt = f"{endian.get()}" + ("I" * len(self.archive.componentHeaders))
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
    
    def __init__(self, archive, offset):
        self.archive = archive
        self._parseBytes(offset)
    
    def _parseBytes(self, offset):
        sentry = struct.unpack_from(f"{endian.get()}I", self.archive.data, offset)[0]
        
        headers = []
        while sentry != 0:
            header = APKFFileTableHeader(self.archive, offset)
            headers.append(header)
            offset = header.offset
            sentry = struct.unpack_from(f"{endian.get()}I", self.archive.data, offset)[0]
        
        self.headers = headers
        self.filenameTableAddress = headers[-1].endAddress if headers else None



class APKFPatch(APKFBase):
    def __init__(self, archive, patchIndex, patch, targetComponentTableIndex, targetComponentTableEntryIndex, targetAddress,
                 targetPtrRef, refIndex, refEntryIndex, refAddress):
        self.archive = archive
        self.patchIndex = patchIndex
        self.patch = patch
        self.targetComponentTableIndex = targetComponentTableIndex
        self.targetComponentTableEntryIndex = targetComponentTableEntryIndex
        self.targetAddress = targetAddress
        
        self.targetPtrRef = targetPtrRef
        self.refIndex = refIndex
        self.refEntryIndex = refEntryIndex
        self.refAddress = refAddress  # This is what target actually becomes
        self.patchType = "filename" if refIndex == 63 else 'pointer'
        
    def __str__(p):
        return f"[APKFPatch] componentTable{p.targetComponentTableIndex} @ 0x{p.targetAddress:0X} : 0x{p.targetPtrRef:0X}=>0x{p.refAddress:0X} = {p.refValue}"
    
    @property
    def refValue(self):
        refValue = None
        if self.refIndex == 63:
            refValue = self.readNullTerminatedString(self.archive._unpatchedData, self.refAddress)
        else:
            refFile = self.refFile
            if refFile:
                refValue = refFile.prettyFilename
        return refValue
    
    @property
    def refFile(self):
        refFile = None
        if self.refIndex != 63:
            refFile = self.archive.findFileFromAddress(self.refAddress)
        return refFile
    
    @classmethod
    def fromEncodedPatch(cls, archive, patchIndex, patch, componentTableAddress, filenameTableAddress):
        targetComponentTableIndex = patch >> 26  # upper 6 [0-63]
        targetComponentTableEntryIndex = patch & 0x3FFFFFF  # lower 26
        
        baseDataPtrAddress = componentTableAddress + targetComponentTableIndex * 24 + 20
        baseDataAddress = struct.unpack_from(f"{endian.get()}I", archive.data, baseDataPtrAddress)[0]
        targetPtr = baseDataPtrAddress + baseDataAddress + (targetComponentTableEntryIndex * 4)
        targetPtrRef = struct.unpack_from(f"{endian.get()}I", archive.data, targetPtr)[0]
        
        refIndex = targetPtrRef >> 26
        refEntryIndex = targetPtrRef & 0x3FFFFFF
        
        refBaseAddress = componentTableAddress + refIndex * 24 + 20 if refIndex != 63 else filenameTableAddress
        
        if refIndex == 63: # string pointer
            finalValue = refBaseAddress + refEntryIndex * 4
        else:
            baseDataOffset = struct.unpack_from(f"{endian.get()}I", archive.data, offset=refBaseAddress)[0]
            finalValue = refBaseAddress + baseDataOffset + refEntryIndex * 4
            
        return cls(archive, patchIndex, patch, targetComponentTableIndex, targetComponentTableEntryIndex, targetPtr,
            targetPtrRef, refIndex, refEntryIndex, finalValue)


class APKFGlobalPatch(APKFBase):
    def __init__(self, patch, typeIdBytes, filenameOffset, refFilenameHash, refFilename, targetAddress, targetIndex, targetEntryIndex, targetValue):
        self.patch = patch
        self.filenameOffset = filenameOffset
        self.refFilenameHash = f"0x{refFilenameHash:08X}"
        self.refFileType = str(typeIdBytes, 'utf-8').replace('\x00', '')
        self.refFilename = str(refFilename, 'utf-8').replace('\x00', '')
        
        self.targetAddress = targetAddress
        self.targetIndex = targetIndex
        self.targetEntryIndex = targetEntryIndex
        self.targetValue = targetValue
        self.targetFile = None
    
    

    @classmethod
    def fromEncodedPatch(cls, patch, typeIdBytes, filenameOffset, filenameHash, filename, archive, componentTableAddress, filenameTableAddress):
        targetIndex = patch >> 26
        targetEntryIndex = patch & 0x3FFFFFF
        
        componentTableAddress = archive.header.componentTablePtr
        
        baseDataPtrAddress = componentTableAddress + targetIndex * 24 + 20
        baseDataAddress = struct.unpack_from(f"{endian.get()}I", archive.data, baseDataPtrAddress)[0]
        
        targetAddress = baseDataPtrAddress + baseDataAddress + (targetEntryIndex * 4)
        targetValue = struct.unpack_from(f"{endian.get()}I", archive.data, targetAddress)[0]
        
        return cls(patch, typeIdBytes, filenameOffset, filenameHash, filename, targetAddress, targetIndex, targetEntryIndex, targetValue)
        

class APKFArchive(APKFBase):
    def __init__(self, data, archiveFilename=None):
        self.archiveFilename = archiveFilename
        self.data = data
        self._parseBytes()
    
    @property
    def archiveFilenameHash(self):
        hash = 0
        if self.archiveFilename is not None:
            match = re.search(r'0x[A-Fa-f0-9]+', self.archiveFilename)
            if match:
                hash = int(match.group(), 16)
        return hash
    
    def files(self, fileType=None):
        filteredFiles = [f for f in self._files if f.fileType == fileType] if fileType is not None else self._files
        return filteredFiles
    
    def _createFileOffsetMap(self):
        self.fileOffsetMap = []
        for f in self.files():
            for cStart, cEnd in f.componentOffsets:
                self.fileOffsetMap.append((cStart, cEnd, f))
        self.fileOffsetMap.sort(key=lambda t: t[0])
        self.fileOffsets = [e[0] for e in self.fileOffsetMap]
        
    
    @functools.cache
    def findFileFromAddress(self, address):
        i = bisect.bisect_right(self.fileOffsets, address) - 1
        if i >= 0:
            cStart, cEnd, f = self.fileOffsetMap[i]
            if cStart <= address < cEnd:
                return f
        return None
                
            
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
        
        self._createFileOffsetMap()
        
        if self.componentHeaders:
            self._parsePatchTable()
            self._unpatchedData = self.data
            self._applyPatches()
            self._parseGlobalPatchTable()

    
    def _applyPatches(self):
        buf = bytearray(self.data)
        for p in self.patchesToFileMap:
            struct.pack_into('<I', buf, p.targetAddress, p.refAddress)
        self.data = bytes(buf)
        
    
    def _parsePatchTable(self):
        patchTableOffset = self.componentHeaders[-1].baseDataAddress + self.componentHeaders[-1].dataSize
        patchTableOffset = self.alignAddressToBoundary(patchTableOffset, 4)
        
        patches = []
        self.patchesToFileMap = {}
        self.fileToPatchesMap = defaultdict(list)
        
        self.offset = patchTableOffset
        patch = struct.unpack_from(f"{endian.get()}I", self.data, offset=self.offset)[0]
        patchIndex = 0
        while patch != 0xFFFFFFFF:
            apkfPatch = APKFPatch.fromEncodedPatch(self, patchIndex, patch, self.header.componentTablePtr,
                                                   self.fileTable.filenameTableAddress)
            
            
            patches.append(apkfPatch)
            patchedFile = self.findFileFromAddress(apkfPatch.targetAddress)
            self.patchesToFileMap[apkfPatch] = patchedFile
            self.fileToPatchesMap[patchedFile].append(apkfPatch)
            
            if patchedFile is None:
                raise Exception(f"Couldn't find {apkfPatch.targetAddress:0X} in any file component")
            
            self.offset += 4
            patch = struct.unpack_from(f"{endian.get()}I", self.data, offset=self.offset)[0]
            patchIndex += 1
    
    def _parseGlobalPatchTable(self):
        globalPatchFmt = f"{endian.get()}I4sII"
        globalPatchTableOffset = self.offset + 4
        self.globalPatches = []
        self.offset = globalPatchTableOffset
        sentry = struct.unpack_from(f"{endian.get()}I", self.data, offset=self.offset)[0]
        while sentry != 0xFFFFFFFF:
            patch, typeIdBytes, filenameOffset, filenameHash = struct.unpack_from(globalPatchFmt, self.data,
                                                                                   self.offset)
            filename = None
            if filenameOffset & 1 != 0:
                filename = self.readNullTerminatedString(self.data,
                                                         self.fileTable.filenameTableAddress + filenameOffset & 0xFFFFFFFE)
            
            globalPatch = APKFGlobalPatch.fromEncodedPatch(patch, typeIdBytes, filenameOffset, filenameHash, filename, self, self.header.componentTablePtr,
                                                   self.fileTable.filenameTableAddress)
            
            targetFile = self.findFileFromAddress(globalPatch.targetAddress)
            globalPatch.targetFile = targetFile
            self.patchesToFileMap[globalPatch] = targetFile
            self.fileToPatchesMap[targetFile].append(globalPatch)
            
            self.globalPatches.append(globalPatch)
            self.offset += struct.calcsize(globalPatchFmt)
            sentry = struct.unpack_from(f"{endian.get()}I", self.data, offset=self.offset)[0]
    
class Wrapper():

    @staticmethod
    def wrapResourceFile(components, componentOffsets, patches, archiveFilenameHash):
        from .utils.bindecl import Struct, Array, Pointer, ComputedCount, Bytes, U32, S32, Alignment
        
        sortedPatches = sorted(patches, key=lambda p: p.targetAddress)
        
        standalone = Struct([
            Bytes(components[0], name="component0")
        ], name="file")
        if len(components) == 2:
            standalone.add_child(Bytes(b"PHYS"))
            standalone.add_child(Bytes(components[1], name="component1"))
        
        externalPatches = Array([], name="externalPatches")
        internalPatches = Array([], name="internalPatches")
        globalPatches = Array([], name="globalPatches")
        
        directionCounter = Counter()
        componentBaseAddresses = [0, len(components[0]) + 4]
        for i, p in enumerate(sortedPatches):
            
            isGlobalPatch = isinstance(p, APKFGlobalPatch)
            isInternalPatch = not isGlobalPatch
            isExternalPatch = not isGlobalPatch
            
            targetBase = componentOffsets[0][0]
            targetOffset = p.targetAddress - targetBase
            targetPath = f"file.component0+0x{targetOffset:0X}"
            
            if not isGlobalPatch:
                isHeaderPatch = componentOffsets[0][0] < p.refAddress < componentOffsets[0][1]
                isDataPatch = len(componentOffsets) > 1 and (componentOffsets[1][0] <= p.refAddress < componentOffsets[1][1])
    
                isInternalPatch = isHeaderPatch or isDataPatch
                isExternalPatch = not isInternalPatch
            
                # Offset of the pointer this patch is for (always in component 0)
                
            
                if isInternalPatch:
                    direction = "IN"
                    internalPatches.add_child(Pointer(ref=targetPath))
                    
                    # Offset from the targetPointer to the ref location (header/data)
                    # The original values are relative offsets from the component start.
                    # We make them relative to the pointer.
                    refOffset = p.refAddress - componentOffsets[p.refIndex][0]
                    refValue = (componentBaseAddresses[p.refIndex] + refOffset) - targetOffset
                elif isExternalPatch:
                    direction = "EX"
                    refValue = (p.refIndex << 26) | p.refEntryIndex
                    refExpectedIndex = -1
                    
                    fourCCFileType = b'NAME'
                    filenameHash = 0
                    if p.patchType == 'pointer':
                        fourCCFileType = p.refFile.fileType.encode('utf-8')
                        fourCCFileType += b'\x00' * (4 - len(fourCCFileType))
                        filenameHash = int(p.refFile.filenameHash, 16)
                    
                    externalPatches.add_child(Struct([
                        Bytes(fourCCFileType, name="fourCC"),
                        U32(filenameHash, name="filenameHash"),
                        S32(refExpectedIndex, name="refExpectedIndex"),
                        Pointer(ref=targetPath, name="pTarget")
                    ]))
            else:
                direction = "GL"
                refPath = f"{p.refFilename}.{p.refFilenameHash}.{p.refFileType}"
                refValue = p.targetValue
                filenameHash = int(p.refFilenameHash, 16)
                fourCCFileType = p.refFileType.encode('utf-8')
                fourCCFileType += b'\x00' * (4 - len(fourCCFileType))
                
                globalPatches.add_child(Struct([
                    Bytes(fourCCFileType, name="fourCC"),
                    U32(filenameHash, name="filenameHash"),
                    Bytes(b"GLBL", name="future"),
                    Pointer(ref=targetPath, name="pTarget")
                ]))
                
            directionCounter[direction] += 1
            if not isGlobalPatch:
                log.debug(f"{direction}.{directionCounter[direction]}: {i} Patch to {targetPath} => using ({p.refIndex}, 0x{p.refEntryIndex:0X}), packed value is 0x{refValue:0X}.")
            else:
                log.debug(f"{direction}.{directionCounter[direction]}: {i} Patch to location (0x{p.targetAddress:08X}) in {p.targetFile} {targetPath} => going to external file {refPath}")
            
            # Update the pointer values in data
            buf = bytearray(standalone.component0.value)
            packFmt = f"{endian.get()}i" if isInternalPatch else f"{endian.get()}I" # internal pointers can point behind themselves
            struct.pack_into(packFmt, buf , targetOffset, refValue)
            standalone.component0.value = buf
            
        componentTable = Array([
            Struct([
                U32(len(c), name="size"),
                Pointer(ref=f"file.component{i}", name=f"pComponent{i}")
            ]) for i, c in enumerate(components)
        ], name="componentTable")
        
        patchTable = Struct([
                ComputedCount(ref="externalPatches", name="externalPatchCount"),
                Pointer(ref="externalPatches", name="pExternalPatches"),
                ComputedCount(ref="internalPatches", name="internalPatchCount"),
                Pointer(ref="internalPatches", name="pInternalPatches"),
                ComputedCount(ref="globalPatches", name="globalPatchCount"),
                Pointer(ref="globalPatches", name="pGlobalPatches"),
                Alignment(align=16),
                externalPatches,
                Alignment(align=16),
                internalPatches,
                Alignment(align=16),
                globalPatches,
            ], name="patchTable")
        
        wrapper = Struct([
            Bytes(b"WRAP"),
            U32(archiveFilenameHash),
            Pointer(ref="patchTable", name="pPatchTable"),
            ComputedCount(ref="componentTable", name="componentCount"),
            Pointer(ref="componentTable", name="pComponentTable"),
            componentTable,
            Alignment(align=16),
            patchTable
        ], name="wrapper")
        
        wrapped = Struct([
            wrapper,
            Alignment(align=16),
            standalone
        ])
        
        return wrapped.serialize()
    
    
def createStandaloneFile(f):
    return f.toStandaloneFile()
        
    



