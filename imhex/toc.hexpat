import std.core;
import std.mem;
import std.io;

fn displayFileHeaderEntry(ref auto fileHeaderEntry){
    return std::format("{}:{}", fileHeaderEntry.fileIndex, fileHeaderEntry.filename);
};

struct TOCFilenameLengthTable{
    u32;
    u32 fileCount;
    u32 nameLengths[fileCount];
    u32;
    u32;
    u32;
    u32;
};

struct TOCHeader{
    char magic[4];
    u32;
    TOCFilenameLengthTable* filenameLengthTable : u32;
    u32;
    u32;
    u32;
    u32;
    u32;
    u32;
    u32;
    u32;
    u32;
    u32;
    u32;
    u32 fileCount;
    u32;
    u32;
    u32;
    u32;
    u32;
    u32;
    u32;
    u32;
    u32;
    u32;
    u32;
};

struct TOCFileHeader{
    u32;
    u32 filenameLength;
    u32;
    u32;
    u32;
    u32;
    u32;
    u32 unk[10];
    u32;
    char filename[filenameLength+1];
    
    u32 fileIndex = std::core::array_index();
    u32 nextBoundary = std::mem::align_to(4, $);
    u32 paddingSize = nextBoundary - $;
    padding[paddingSize];
    std::print("{:08X}", paddingSize);
};

struct TOCFile{
    TOCHeader header;
    u32 emptyFileAddressSpace[header.fileCount];
    TOCFileHeader fileHeaders[header.fileCount][[format_entries("displayFileHeaderEntry")]];
};

TOCFile toc @ 0x00;