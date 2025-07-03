#pragma pattern_limit 10485760
#pragma base_address 0x00

import std.core;
import std.io;
import std.mem;
import type.base;
import type.float16;

fn showHexDec(auto v){
    return std::format("0x{:08X} ({})", v, v);
};

using HexDec<T> = T[[format("showHexDec")]];

enum D3DDECLTYPE : u8 {
    FLOAT1     = 0,
    FLOAT2     = 1,
    FLOAT3     = 2,
    FLOAT4     = 3,
    D3DCOLOR   = 4,
    UBYTE4     = 5,
    SHORT2     = 6,
    SHORT4     = 7,
    UBYTE4N    = 8,
    SHORT2N    = 9,
    SHORT4N    = 10,
    USHORT2N   = 11,
    USHORT4N   = 12,
    UDEC3      = 13,
    DEC3N      = 14,
    FLOAT16_2  = 15,
    FLOAT16_4  = 16,
    UNUSED     = 17
};

enum D3DDECLMETHOD : u8 {
    DEFAULT           = 0,
    PARTIALU          = 1,
    PARTIALV          = 2,
    CROSSUV           = 3,
    UV                = 4,
    LOOKUP            = 5,
    LOOKUPPRESAMPLED  = 6
};

enum D3DDECLUSAGE : u8 {
    POSITION      = 0,
    BLENDWEIGHT   = 1,
    BLENDINDICES  = 2,
    NORMAL        = 3,
    PSIZE         = 4,
    TEXCOORD      = 5,
    TANGENT       = 6,
    BINORMAL      = 7,
    TESSFACTOR    = 8,
    POSITIONT     = 9,
    COLOR         = 10,
    FOG           = 11,
    DEPTH         = 12,
    SAMPLE        = 13
};

struct D3DVERTEXELEMENT9{
    u16 Stream;
    u16 Offset;
    D3DDECLTYPE Type;
    D3DDECLMETHOD Method;
    D3DDECLUSAGE Usage;
    u8 UsageIndex;
};

struct FLOAT16_2Strc<auto usage, auto n1, auto n2>{
    type::float16[[name(std::format("{}_{}", usage, n1))]];
    type::float16[[name(std::format("{}_{}", usage, n2))]];
}[[name(usage)]];

struct FLOAT16_4Strc<auto usage, auto n1, auto n2, auto n3, auto n4>{
    type::float16 [[name(std::format("{}_{}", usage, n1))]];
    type::float16 [[name(std::format("{}_{}", usage, n2))]];
    type::float16 [[name(std::format("{}_{}", usage, n3))]];
    type::float16 [[name(std::format("{}_{}", usage, n4))]];
}[[name(usage)]];

struct SHORT4NStrc<auto usage, auto n1, auto n2, auto n3, auto n4>{
    s16 [[name(std::format("{}_{}", usage, n1))]];
    s16 [[name(std::format("{}_{}", usage, n2))]];
    s16 [[name(std::format("{}_{}", usage, n3))]];
    s16 [[name(std::format("{}_{}", usage, n4))]];
}[[name(usage)]];

struct UBYTE4Strc<auto usage, auto n1, auto n2, auto n3, auto n4>{
    u8 [[name(std::format("{}_{}", usage, n1))]];
    u8 [[name(std::format("{}_{}", usage, n2))]];
    u8 [[name(std::format("{}_{}", usage, n3))]];
    u8 [[name(std::format("{}_{}", usage, n4))]];
}[[name(usage)]];

struct UBYTE4NStrc<auto usage, auto n1, auto n2, auto n3, auto n4>{
    u8 [[name(std::format("{}_{}", usage, n1))]];
    u8 [[name(std::format("{}_{}", usage, n2))]];
    u8 [[name(std::format("{}_{}", usage, n3))]];
    u8 [[name(std::format("{}_{}", usage, n4))]];
}[[name(usage)]];

struct VertexComponent<auto schema>{    
    u32 i = std::core::array_index();
    D3DDECLTYPE type = schema[i].Type;
    D3DDECLUSAGE usage = schema[i].Usage;
    u32 offset = schema[i].Offset;
    
    match (type, usage) {
        (D3DDECLTYPE::FLOAT16_2, D3DDECLUSAGE::TEXCOORD): FLOAT16_2Strc<"tex", "u", "v"> @ addressof(this.parent) + offset;
        (D3DDECLTYPE::FLOAT16_4, D3DDECLUSAGE::TANGENT): FLOAT16_4Strc<"tangent", "x", "y", "z", "w"> @ addressof(this.parent) + offset;
        (D3DDECLTYPE::SHORT4N, D3DDECLUSAGE::POSITION): SHORT4NStrc<"position", "x", "y", "z", "w"> @ addressof(this.parent) + offset;
        (D3DDECLTYPE::FLOAT16_4, D3DDECLUSAGE::NORMAL): FLOAT16_4Strc<"normal", "x", "y", "z", "w"> @ addressof(this.parent) + offset;
        (D3DDECLTYPE::UBYTE4N, D3DDECLUSAGE::BLENDWEIGHT): UBYTE4NStrc<"blendweight", "x", "y", "z", "w"> @ addressof(this.parent) + offset;
        (D3DDECLTYPE::UBYTE4, D3DDECLUSAGE::BLENDINDICES): UBYTE4Strc<"blendindices", "x", "y", "z", "w"> @ addressof(this.parent) + offset;
        (D3DDECLTYPE::FLOAT16_4, D3DDECLUSAGE::BINORMAL): FLOAT16_4Strc<"binormal", "x", "y", "z", "w"> @ addressof(this.parent) + offset;
        (_, _): continue;
    }
    
}[[inline]];  

struct Vertex<auto schema, auto schemaMemberCount, auto vertexStride>{
    VertexComponent<schema> members[schemaMemberCount][[inline, fixed_size(vertexStride)]];
};

struct IndexBuffer<auto count>{
    u16 indices[count];
};

struct MeshData{
    std::print("Placing MeshData at {}", $);
    u32 idx = std::core::array_index();
    u32 indexCount = parent.header.meshTable.entries[idx].meshInfo.bufferInfo.indexCount;  
    u32 vertexCount = parent.header.meshTable.entries[idx].meshInfo.bufferInfo.vertexCount;    
    u32 vertexStride = parent.header.meshTable.entries[idx].meshInfo.bufferInfo.schemaTable.vertexStride;  
    u32 schemaMemberCount = parent.header.meshTable.entries[idx].meshInfo.bufferInfo.schemaTable.vertexSchema.count;
  
    $ = std::mem::align_to(4, $);    
    Vertex<
    parent.header.meshTable.entries[idx].meshInfo.bufferInfo.schemaTable.vertexSchema.entries, 
    schemaMemberCount, vertexStride
    > vBuffer[vertexCount];
    
    IndexBuffer<indexCount> iBuffer;
};

struct VertexSchema{
    D3DVERTEXELEMENT9 entries[while(std::mem::read_unsigned($, 8, std::mem::Endian::Little) != 0x11000000FF)];        
    D3DVERTEXELEMENT9 d3dEndSentinel;
    u32 count = std::core::member_count(entries);
};

struct SchemaTable{
    u32 vertexStride;
    VertexSchema* vertexSchema: u32;
};

struct MeshHeaderIndexTable<auto count>{
    u16 indexes[count];
};

struct SubMeshBufferInfo{
    u32 pHeaderIndexTable;
    u32 headerIndexCount;
    u32 vBufferPtr;
    u32;
    u32 vertexCount;
    u32;
    u32 iBufferPtr;
    u32;
    u32 indexCount;
    u32 indexSize;
    SchemaTable* schemaTable : u32;

    MeshHeaderIndexTable<headerIndexCount>* indexTable : u32 @ addressof(pHeaderIndexTable);            
};

struct MeshInfo{
    u32 unk0;
    u32;
    u32;
    u32;
    u32;
    u32 inlineShaderFlag; // if the shader is in the mesh header or not      
    u32;
    u32;
    u32;
    SubMeshBufferInfo bufferInfo;
};

struct MeshTableHeader{
    u32 parsdFlag;
    MeshInfo* meshInfo: u32;
};

struct MeshTable<auto meshCount>{
    MeshTableHeader entries[meshCount];
};

struct MeshHeader<auto size>{
    u32 pFilename;
    u32 filenameHash;
    u32 parsedFlag;
    u32 meshCount;
    MeshTable<meshCount>* meshTable : u32;
};

struct MeshFile{
    u32 headerSize = std::mem::find_string(0, "PHYS");    
    
    MeshHeader<headerSize> header;       
    MeshData meshData[header.meshCount] @ headerSize + 4;        
};

MeshFile mesh @ 0x00;

std::print("This file has {} mesh(es)", mesh.header.meshCount);
for (u32 i = 0, i < mesh.header.meshCount, i+= 1){
    
    std::print("Mesh {} has {} vertices of size {} bytes, beginning at 0x{:0X}", i,
        std::core::member_count(mesh.meshData[i].vBuffer), 
        sizeof(mesh.meshData[i].vBuffer[0]),
        addressof(mesh.meshData[i].vBuffer)
    );
    std::print("Mesh {} has {} indices beginning at 0x{:0X}", i,
        std::core::member_count(mesh.meshData[i].iBuffer.indices), 
        addressof(mesh.meshData[i].iBuffer)
    );    
    
}