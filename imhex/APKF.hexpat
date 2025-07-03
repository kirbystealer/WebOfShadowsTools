import std.core;
import std.mem;
import std.ptr;
import std.io;
import type.base;

struct RelativePointer {
    u32 address[[no_unique_address]];
    u32 *ptr : u32[[pointer_base("std::ptr::relative_to_pointer")]];
};

fn displayIdBytes(u32 i){
    str s = str(i);
    return std::format("{}", s);
};

fn displayFileTypeEntry(auto p){
    return p.typeIdBytes;
};

fn displayFileHeaderEntry(ref auto fileHeaderEntry){
    return std::format("{}:{}", fileHeaderEntry.fileIndex, fileHeaderEntry.pFilename);
};


u32 alignedAddresses[63];
struct FileResourceData<auto fileIndex, auto subResourceAlignments, auto subResourceHeaders> {
    u32 size;
    
    u32 subResourceIndex = std::core::array_index();
    u32 alignment = subResourceAlignments[subResourceIndex] & 0xFFFFFF;    
    u32 baseDataAddress = addressof(subResourceHeaders[subResourceIndex].baseDataAddress);
    
    alignedAddresses[subResourceIndex] = std::mem::align_to(alignment, alignedAddresses[subResourceIndex]);
    u32 dataAddress = baseDataAddress + alignedAddresses[subResourceIndex];
    alignedAddresses[subResourceIndex] = alignedAddresses[subResourceIndex] + size;
     
    std::print ("{} - {} - F{}=>R{}: {:08X}, {:08X}, {:08X}, {:08X} ({} bytes at 0x{:X}-0x{:X})", parent.parent.typeIdBytes, parent.pFilename, fileIndex, subResourceIndex, alignment, alignedAddresses[subResourceIndex], dataAddress, dataAddress - baseDataAddress,
    size, dataAddress, dataAddress + size);
    
    u8 bytes[size] @ dataAddress;
};

struct FileHeaderEntry{    
    char* pFilename[while(std::mem::read_unsigned($, 1) != 0x00)]: u32[[pointer_base("std::ptr::relative_to_pointer")]];
    type::Hex<u32> filenameHash;
    
    u32 fileIndex = std::core::array_index();
    FileResourceData<fileIndex, parent.subResourceAlignments, parent.parent.subResourceTable.headers> resourceData[parent.headerExtraFieldCount];        
};

struct FileTypeEntry{
    char typeIdBytes[4];
    u32 field1;
    u32 headerExtraFieldCount;
    u32 pFileHeaderTable;   
    u32 nFileHeaders;   
    u32 subResourceAlignments[parent.subResourceCount];
 
    FileHeaderEntry fileHeaders[nFileHeaders] @ addressof(pFileHeaderTable) + pFileHeaderTable[[format_entries("displayFileHeaderEntry")]];      
};

struct SubResourceHeader{
    char resourceIdBytes[4];
    u32 externalHandlerFlag; // if odd
    u32 field2;
    u32 field3;
    u32 dataSize;
    
    u32 dataOffset;
    u32 baseDataAddress @ addressof(dataOffset) + dataOffset;
};

struct SubResourceTable{
    SubResourceHeader headers[parent.subResourceCount];
};

struct ExternalHeader{
    u32 field0;
    char typeIdBytes[4];
    type::Hex<u32> filenameOffset; // Offset of filename start in in the file type filename table
    type::Hex<u32> filenameHash;
    
    u32 pFilenameTableStart = addressof(parent.parent.fileTypes[0].fileHeaders[0].pFilename);  
    char filename[while(std::mem::read_unsigned($, 1) != 0x00)] @ (pFilenameTableStart + filenameOffset - 1);
    std::print("ExternalHeader {} - {} - {:0X}", typeIdBytes, filename, field0);
};

struct EncodedPointer{
    u32 pointer;
    
    u32 i = std::core::array_index();
    u32 sourcePtrIndex = pointer >> 26; // upper 6 bits
    u32 sourcePtrOffset = pointer & 0x3FFFFFF; // lower 26 bits
    
    sourcePtrIndex = sourcePtrIndex * 3;
    sourcePtrOffset = sourcePtrOffset * 4;
    
    u32 pSubResourceTable = addressof(parent.parent.subResourceTable);
    
    u32 dataOffset @ (pSubResourceTable + sourcePtrIndex * 8 + 20);
    u32 pTargetPtr = addressof(dataOffset) + dataOffset + sourcePtrOffset;
    u32 targetPtr @ pTargetPtr;
    
    u32 targetPtrIndex = targetPtr >> 26; // upper 6 bits
    u32 targetPtrOffset = targetPtr & 0x3FFFFFF; // lower 26 bits
    
    targetPtrOffset = targetPtrOffset * 4;
            
    std::print("{} src: 0x{:08X}@0x{:0X} - {:04},{:04}. target: 0x{:08X}@0x{:0X} - {:08},{:08}", i,
    pointer, addressof(pointer), pointer >> 26, pointer & 0x3FFFFFF,
    targetPtr, pTargetPtr, targetPtr >> 26, targetPtr & 0x3FFFFFF);
    if (targetPtrIndex == 63){
        u32 filenameTableAddress = 0xEC;
        u32 pTargetPtr2 = filenameTableAddress + targetPtrOffset;
        char filename[while(std::mem::read_unsigned($, 1) != 0x00)] @ pTargetPtr2;
        std::print("{} Filename: Would change at {:0X} from {:0X} => {:0X} ({})", i, pTargetPtr, targetPtr, pTargetPtr2, filename);
    } else {
        targetPtrIndex = targetPtrIndex * 3;
        u32 pTargetPtr2 = (pSubResourceTable + targetPtrIndex * 8 + 20);
        u32 targetPtrValue = std::mem::read_unsigned(pTargetPtr2, 4);
        u32 finalValue = pTargetPtr2 + targetPtrValue + targetPtrOffset;        
        std::print("{} Relative: Would change at 0x{:0X} from 0x{:0X} => 0x{:0X}", i, pTargetPtr, targetPtr, finalValue);
    }
    
    



};

struct APKFEnd{
   EncodedPointer encodedPointers[while(std::mem::read_unsigned($, 4) != 0xFFFFFFFF)];
   s32;
   ExternalHeader externals[while(std::mem::read_unsigned($, 4) != 0xFFFFFFFF)];
   s32;
};

struct APKFHeader{
    char magic[4];
    u32 version;
    u32 flagField;
    u32 boolField;
    u32 subResourceCount;
    
    SubResourceTable *subResourceTable: u32[[pointer_base("std::ptr::relative_to_pointer")]];
    
    u32 fileTypesPtr[[comment("Filled in during parse.")]];
    FileTypeEntry fileTypes[while(std::mem::read_unsigned($, 4) != 0x00)][[format_entries("displayFileTypeEntry")]];
       
    u32 pointerTableAddress = std::mem::align_to(4, addressof(subResourceTable.headers[subResourceCount - 1].baseDataAddress) + subResourceTable.headers[subResourceCount - 1].dataSize);
    APKFEnd @ pointerTableAddress;
};


APKFHeader header @ 0x00;