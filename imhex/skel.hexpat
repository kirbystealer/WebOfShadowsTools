struct BoneEntry{
    u32 unk[36];
};

struct SkelFileHeader{
    u32 pFilename;
    u32 filenameHash;
    u32 boneCount;
    u32 pBoneTable;
};

struct SkelFile{
    SkelFileHeader header;
    BoneEntry bones[header.boneCount];
};

SkelFile file @ 0x00;