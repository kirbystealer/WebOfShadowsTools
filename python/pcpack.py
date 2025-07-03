#!/usr/bin/env -S uv run --script
# /// script
# dependencies = [
#     "python-lzo",
# ]
# ///
import struct
import io

import lzo

try:
    from ._utils import print_hex
    import hash_to_path
except:
    hash_to_path = None

RESOURCE_LOOKUP = [
    (0, 0x0, "error", "error", ".NONE", "", "empty_resource_handler"),
    (1, 0x1, "descriptor", "descriptors", ".DESC", "DESC\\", "mashable_resource_handler"),
    (2, 0x2, "sin", "sins", ".SIN", "SIN\\", "mashable_resource_handler"),
    (3, 0x3, "textfile", "textfiles", ".TXT", "TXT\\", "mashable_resource_handler"),
    (4, 0x4, "terrain_types", "terrain_typeses", ".CSV", "CSV\\", "mashable_resource_handler"),
    (5, 0x5, "language", "languages", ".LANG", "LANG\\", "mashable_resource_handler"),
    (6, 0x6, "district_graph", "district_graphs", ".DSG", "DSG\\", "mashable_resource_handler"),
    (7, 0x7, "speedtree_coll", "speedtree_colls", ".STC", "STC\\", "mashable_resource_handler"),
    (8, 0x8, "speedtree_coll_refs", "speedtree_coll_refss", ".PCSTCR", "PCSTCR\\", "mashable_resource_handler"),
    (9, 0x9, "script", "scripts", ".PCSX", "PCSX\\", "mashable_resource_handler"),
    (10, 0xa, "script_gv", "script_gvs", ".PCGV", "PCGV\\", "mashable_resource_handler"),
    (11, 0xb, "script_sv", "script_svs", ".PCSV", "PCSV\\", "mashable_resource_handler"),
    (12, 0xc, "GenBlockMap", "GenBlockMaps", ".GBMAP", "GBMAP\\", "mashable_resource_handler"),
    (13, 0xd, "traffic_light_info", "traffic_light_infos", ".TRAF_LT_INFPC", "TRAF_LT_INFPC\\",
     "mashable_resource_handler"),
    (14, 0xe, "texture", "textures", ".PCTEXTURE", "PCTEXTURE\\", "merged_singular_apk_resource_handler"),
    (15, 0xf, "fxbinary", "fxbinaries", ".PCFX", "PCFX\\", "merged_singular_apk_resource_handler"),
    (16, 0x10, "material", "materials", ".PCMATERIAL", "PCMATERIAL\\", "merged_singular_apk_resource_handler"),
    (17, 0x11, "mesh", "meshes", ".PCMESH", "PCMESH\\", "merged_singular_apk_resource_handler"),
    (18, 0x12, "ngl_skeleton", "ngl_skeletons", ".PCNGLSKELETON", "PCNGLSKELETON\\",
     "merged_singular_apk_resource_handler"),
    (19, 0x13, "nal_skeleton", "nal_skeletons", ".PCSKEL", "PCSKEL\\", "merged_singular_apk_resource_handler"),
    (20, 0x14, "ngl_font", "ngl_fonts", ".PCFONT", "PCFONT\\", "merged_singular_apk_resource_handler"),
    (21, 0x15, "animation", "animations", ".PCANIM", "PCANIM\\", "merged_singular_apk_resource_handler"),
    (22, 0x16, "scene_animation", "scene_animations", ".PCSANIM", "PCSANIM\\", "merged_singular_apk_resource_handler"),
    (23, 0x17, "morph", "morphs", ".PCMORPH", "PCMORPH\\", "merged_singular_apk_resource_handler"),
    (24, 0x18, "efx", "efxs", ".PCEFXB", "PCEFXB\\", "merged_singular_apk_resource_handler"),
    (25, 0x19, "merged_apk", "merged_apks", ".PCAPK", "PCAPK\\", "merged_apk_resource_handler"),
    (26, 0x1a, "nal_skeleton_map", "nal_skeleton_maps", ".SKELMAP", "SKELMAP\\", "singular_apk_resource_handler"),
    (27, 0x1b, "convex_hull_mesh", "convex_hull_meshes", ".PCCVX", "PCCVX\\", "singular_apk_resource_handler"),
    (28, 0x1c, "vehicle_model_depot", "vehicle_model_depots", ".VDEPOT", "VDEPOT\\", "mashable_resource_handler"),
    (29, 0x1d, "TILEMAP", "TILEMAPs", ".TILEMAP", "TILEMAP\\", "mashable_resource_handler"),
    (30, 0x1e, "ENVIRONMENT", "ENVIRONMENTs", ".ENVIRONMENT", "ENVIRONMENT\\", "mashable_resource_handler"),
    (31, 0x1f, "LIGHTBEHAVIOR", "LIGHTBEHAVIORs", ".LIGHTBEHAVIOR", "LIGHTBEHAVIOR\\", "mashable_resource_handler"),
    (32, 0x20, "GRAPHICSOPTIONS", "GRAPHICSOPTIONSs", ".GRAPHICSOPTIONS", "GRAPHICSOPTIONS\\",
     "mashable_resource_handler"),
    (33, 0x21, "EFFECTCONTAINER", "EFFECTCONTAINERs", ".EFFECTCONTAINER", "EFFECTCONTAINER\\",
     "mashable_resource_handler"),
    (34, 0x22, "SMDECALMATERIAL", "SMDECALMATERIALs", ".SMDECALMATERIAL", "SMDECALMATERIAL\\",
     "mashable_resource_handler"),
    (35, 0x23, "PHATPALETTE", "PHATPALETTEs", ".PHATPALETTE", "PHATPALETTE\\", "mashable_resource_handler"),
    (36, 0x24, "COWBELL", "COWBELLs", ".COWBELL", "COWBELL\\", "mashable_resource_handler"),
    (37, 0x25, "MESHMAP", "MESHMAPs", ".MESHMAP", "MESHMAP\\", "mashable_resource_handler"),
    (38, 0x26, "CLOUDTWEAK", "CLOUDTWEAKs", ".CLOUDTWEAK", "CLOUDTWEAK\\", "mashable_resource_handler"),
    (39, 0x27, "CITYLODS", "CITYLODSs", ".CITYLODS", "CITYLODS\\", "mashable_resource_handler"),
    (40, 0x28, "SMROADPARAM", "SMROADPARAMs", ".SMROADPARAM", "SMROADPARAM\\", "mashable_resource_handler"),
    (41, 0x29, "ALLBUILDINGS", "ALLBUILDINGSs", ".ALLBUILDINGS", "ALLBUILDINGS\\", "mashable_resource_handler"),
    (42, 0x2a, "UIP3DW", "UIP3DWs", ".UIP3DW", "UIP3DW\\", "mashable_resource_handler"),
    (43, 0x2b, "UIP3DT", "UIP3DTs", ".UIP3DT", "UIP3DT\\", "mashable_resource_handler"),
    (44, 0x2c, "SMDECALPARAM", "SMDECALPARAMs", ".SMDECALPARAM", "SMDECALPARAM\\", "mashable_resource_handler"),
    (45, 0x2d, "ADJUSTMENTLAYERSLIBRARY", "ADJUSTMENTLAYERSLIBRARYs", ".ADJUSTMENTLAYERSLIBRARY",
     "ADJUSTMENTLAYERSLIBRARY\\", "mashable_resource_handler"),
    (46, 0x2e, "OUTDOORS", "OUTDOORSs", ".OUTDOORS", "OUTDOORS\\", "mashable_resource_handler"),
    (47, 0x2f, "DAYSKYCOLOR", "DAYSKYCOLORs", ".DAYSKYCOLOR", "DAYSKYCOLOR\\", "mashable_resource_handler"),
    (48, 0x30, "NIGHTSKYCOLOR", "NIGHTSKYCOLORs", ".NIGHTSKYCOLOR", "NIGHTSKYCOLOR\\", "mashable_resource_handler"),
    (49, 0x31, "PRELIGHT", "PRELIGHTs", ".PRELIGHT", "PRELIGHT\\", "mashable_resource_handler"),
    (50, 0x32, "SMBUILDINGLODPARAM", "SMBUILDINGLODPARAMs", ".SMBUILDINGLODPARAM", "SMBUILDINGLODPARAM\\",
     "mashable_resource_handler"),
    (51, 0x33, "SMROADLODPARAM", "SMROADLODPARAMs", ".SMROADLODPARAM", "SMROADLODPARAM\\", "mashable_resource_handler"),
    (52, 0x34, "SMRETROFITPARAM", "SMRETROFITPARAMs", ".SMRETROFITPARAM", "SMRETROFITPARAM\\",
     "mashable_resource_handler"),
    (53, 0x35, "JSON_REGIONINFO", "JSON_REGIONINFOs", ".JSON_REGIONINFO", "JSON_REGIONINFO\\",
     "mashable_resource_handler"),
    (54, 0x36, "JSON_METERDATA", "JSON_METERDATAs", ".JSON_METERDATA", "JSON_METERDATA\\", "mashable_resource_handler"),
    (55, 0x37, "JSON_METERBEHAVIOR", "JSON_METERBEHAVIORs", ".JSON_METERBEHAVIOR", "JSON_METERBEHAVIOR\\",
     "mashable_resource_handler"),
    (56, 0x38, "JSON_COMBOMOVEINFO", "JSON_COMBOMOVEINFOs", ".JSON_COMBOMOVEINFO", "JSON_COMBOMOVEINFO\\",
     "mashable_resource_handler"),
    (57, 0x39, "JSON_QUESTDESC", "JSON_QUESTDESCs", ".JSON_QUESTDESC", "JSON_QUESTDESC\\", "mashable_resource_handler"),
    (58, 0x3a, "JSON_QUESTLIST", "JSON_QUESTLISTs", ".JSON_QUESTLIST", "JSON_QUESTLIST\\", "mashable_resource_handler"),
    (59, 0x3b, "JSON_CONVERSATION", "JSON_CONVERSATIONs", ".JSON_CONVERSATION", "JSON_CONVERSATION\\",
     "mashable_resource_handler"),
    (60, 0x3c, "JSON_SPAWNTABLE", "JSON_SPAWNTABLEs", ".JSON_SPAWNTABLE", "JSON_SPAWNTABLE\\",
     "mashable_resource_handler"),
    (61, 0x3d, "JSON_SPAWNPROGRESSION", "JSON_SPAWNPROGRESSIONs", ".JSON_SPAWNPROGRESSION", "JSON_SPAWNPROGRESSION\\",
     "mashable_resource_handler"),
    (62, 0x3e, "JSON_SPAWNPOINTS", "JSON_SPAWNPOINTSs", ".JSON_SPAWNPOINTS", "JSON_SPAWNPOINTS\\",
     "mashable_resource_handler"),
    (63, 0x3f, "JSON_NEIGHBORHOODINFO", "JSON_NEIGHBORHOODINFOs", ".JSON_NEIGHBORHOODINFO", "JSON_NEIGHBORHOODINFO\\",
     "mashable_resource_handler"),
    (64, 0x40, "JSON_DEF_VALUES", "JSON_DEF_VALUESs", ".JSON_DEF_VALUES", "JSON_DEF_VALUES\\",
     "mashable_resource_handler"),
    (65, 0x41, "JSON_PROGRESSMESSAGES", "JSON_PROGRESSMESSAGESs", ".JSON_PROGRESSMESSAGES", "JSON_PROGRESSMESSAGES\\",
     "mashable_resource_handler"),
    (66, 0x42, "JSON_SPAWNITEMS", "JSON_SPAWNITEMSs", ".JSON_SPAWNITEMS", "JSON_SPAWNITEMS\\",
     "mashable_resource_handler"),
    (67, 0x43, "JSON_UPGRADES", "JSON_UPGRADESs", ".JSON_UPGRADES", "JSON_UPGRADES\\", "mashable_resource_handler"),
    (68, 0x44, "JSON_SOUNDMAP", "JSON_SOUNDMAPs", ".JSON_SOUNDMAP", "JSON_SOUNDMAP\\", "mashable_resource_handler"),
    (69, 0x45, "JSON_UICHARINFO", "JSON_UICHARINFOs", ".JSON_UICHARINFO", "JSON_UICHARINFO\\",
     "mashable_resource_handler"),
    (70, 0x46, "JSON_SUMMONPROGRESSION", "JSON_SUMMONPROGRESSIONs", ".JSON_SUMMONPROGRESSION",
     "JSON_SUMMONPROGRESSION\\", "mashable_resource_handler"),
    (71, 0x47, "JSON_ENVIRONMENTPROGRESSION", "JSON_ENVIRONMENTPROGRESSIONs", ".JSON_ENVIRONMENTPROGRESSION",
     "JSON_ENVIRONMENTPROGRESSION\\", "mashable_resource_handler"),
    (72, 0x48, "JSON_RENDERLOD", "JSON_RENDERLODs", ".JSON_RENDERLOD", "JSON_RENDERLOD\\", "mashable_resource_handler"),
    (73, 0x49, "viseme_stream", "viseme_streams", ".LIP", "LIP\\", "mashable_resource_handler"),
    (74, 0x4a, "static_colgeom", "static_colgeoms", ".SCGPC", "SCGPC\\", "mashable_resource_handler"),
    (75, 0x4b, "lego_map", "lego_maps", ".LEGO_MAPPC", "LEGO_MAPPC\\", "mashable_resource_handler"),
    (76, 0x4c, "scn_quad_path", "scn_quad_paths", ".QP", "QP\\", "mashable_resource_handler"),
    (77, 0x4d, "path", "path", ".PATH", "PATH\\", "mashable_resource_handler"),
    (78, 0x4e, "scn_env_box", "scn_env_boxes", ".EB", "EB\\", "mashable_resource_handler"),
    (79, 0x4f, "cosmetic_environ", "cosmetic_environs", ".CE", "CE\\", "mashable_resource_handler"),
    (80, 0x50, "sm3_light", "sm3_lights", ".SM3_LIGHTPC", "SM3_LIGHTPC\\", "mashable_resource_handler"),
    (81, 0x51, "stall", "stalls", ".STALL", "STALL\\", "stall_resource_handler"),
    (82, 0x52, "slim", "slims", ".SLIM", "SLIM\\", "empty_resource_handler"),
    (83, 0x53, "slim_list", "slim_lists", ".SLIMLIST", "SLIMLIST\\", "slim_list_handler"),
    (84, 0x54, "als_file", "als_files", ".ALS", "ALS\\", "mashable_resource_handler"),
    (85, 0x55, "ai_state_graph", "ai_state_graphs", ".ASG", "ASG\\", "mashable_resource_handler"),
    (86, 0x56, "base_ai", "base_ais", ".BAI", "BAI\\", "mashable_resource_handler"),
    (87, 0x57, "scn_audio_box", "scn_audio_boxes", ".AB", "AB\\", "mashable_resource_handler"),
    (88, 0x58, "box_trigger_info", "box_trigger_infos", ".BOX_TRIG_INFPC", "BOX_TRIG_INFPC\\",
     "box_trigger_resource_handler"),
    (89, 0x59, "scn_entity", "scn_entities", ".ENS", "ENS\\", "scene_entity_container_resource_handler"),
    (90, 0x5a, "anchor_coll", "anchor_colls", ".PCAC", "PCAC\\", "anchor_collection_resource_handler"),
    (91, 0x5b, "fx_cache", "fx_caches", ".FX_CACHE", "FX_CACHE\\", "mashable_resource_handler"),
    (92, 0x5c, "entity", "entities", ".ENT", "ENT\\", "empty_resource_handler"),
    (93, 0x5d, "cut_scene", "cut_scenes", ".CUT", "CUT\\", "mashable_resource_handler"),
    (94, 0x5e, "collision_mesh", "collision_meshes", ".COLL", "COLL\\", "empty_resource_handler"),
    (95, 0x5f, "packfile", "packfiles", ".PCPACK", "PCPACK\\", "empty_resource_handler"),
    (96, 0x60, "speedtree_spt", "speedtree_spts", ".SPT", "SPT\\", "empty_resource_handler"),
    (97, 0x61, "speedtree_seed", "speedtree_seeds", ".SEED", "SEED\\", "empty_resource_handler"),
    (98, 0x62, "speedtree_wind", "speedtree_winds", ".WIND", "WIND\\", "empty_resource_handler"),
    (99, 0x63, "sound_toc", "sound_tocs", ".pcstoc", "pcstoc\\", "mashable_resource_handler"),
    (100, 0x64, "sound_index", "sound_indexs", ".sndids", "sndids\\", "mashable_resource_handler"),
    (101, 0x65, "ise_library", "ise_libraries", ".json_ise", "json_ise\\", "ise_library_handler"),
    (102, 0x66, "vertex_shader", "vertex_shaders", ".PCVS", "PCVS\\", "vertex_shader_handler"),
    (103, 0x67, "pixel_shader", "pixel_shaders", ".PCPS", "PCPS\\", "pixel_shader_handler")
]
RESOURCE_LOOKUP = {id: ext for id, id_hex, desc, descp, ext, path, resource_handler_class in RESOURCE_LOOKUP}

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
        self.fileExt = RESOURCE_LOOKUP.get(self.fileTypeId, '.bin').lower()
    
    @property
    def filename(self):
        actualFilename = ""
        try:
            actualFilename = hash_to_path.hash_to_path(self.filenameHash)
            if actualFilename is not None:
                actualFilename += '.'
            else:
                actualFilename = ""
        except:
            pass
        
        return f"F{self.index + 1:03}.0x{self.filenameHash:08X}.{actualFilename}T{self.fileTypeId}{self.fileExt}"
    
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