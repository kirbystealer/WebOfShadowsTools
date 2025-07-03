#pragma base_address 0x00
//#pragma debug

import std.array;
import std.core;
import std.hash;
import std.mem;
import type.base;

struct PcPackSubHeader{
    u32 magicBytes;
    u32 headerSize;
    u32 nByteSize;
    u32 field4;
    u32 field5;
    u32 field6;
    u32 entryCount;
    u32 field8;
    u32 field9;
    u32 field10;    
};

struct PcPackHeader{
    u32 field1;
    u32 field2;
    u32 field3;
    u32 field4;
    u32 field5;
    u32 field6;
    u32 nByteSize;
    u32 field8;
    PcPackSubHeader subHeader;
};



struct SubEntryHeader{
    u32 fields[8];
};

struct File{
    type::Hex<u32> filenameHash;
    u32 fileTypeId;
    type::Hex<u32> fileOffset;
    u32 fileSizeBytes1;
    u32 fileSizeBytes2;
    u32 field4;
    type::Hex<u32> field5;
    u32 field6;
    u32 hasSubEntries;
    u32 field8;
    u32 field9;
    
    if (hasSubEntries != 0){
        SubEntryHeader subEntryHeader;
    }
    char data[fileSizeBytes1] @ fileOffset;
};


struct FileEntryTable<auto Size>{
    u32 addressPlaceholders[Size][[comment("Filled in during parse")]];    
    File files[Size];          
};

PcPackHeader header @ 0x00;
FileEntryTable<header.subHeader.entryCount> fileEntryTable @ 0x408;