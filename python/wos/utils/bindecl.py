import struct
import re

from wos.utils import print_hex, log

verbose = False

def get_node_ref_index(node, flat):
    ref = node.ref.split('+')[0]
    for i, info in enumerate(flat):
        offset, node_path, *rest = info
        if node_path.endswith(ref):
            return i
    else:
        raise Exception(f"Couldn't find a node with ref {node.ref}")


class Node:
    def __init__(self, name=None):
        self.name = name
        self.parent = None


class AbstractNode(): pass


class ComputedNode():
    def compute_value(self, node_info, ref_info):
        raise NotImplementedError(f"{type(self).__name__} must define compute_value")


class Alignment(Node, AbstractNode):
    def __init__(self, *, align=4):
        super().__init__(f"Align{align}")
        self.align = align


class LeafNode(Node):
    fmt = None
    default = 0
    
    def __init__(self, *values, name=None):
        super().__init__(name)
        self.value = values
        if values and len(values) == 1:
            self.value = values[0]
        elif not values:
            self.value = self.default
    
    @staticmethod
    def _is_multi_value(val):
        return isinstance(val, (tuple, list))
    
    def pack(self):
        if not self.fmt:
            raise NotImplementedError(f"{type(self).__name__} must define fmt")
        values = self.value if self._is_multi_value(self.value) else (self.value,)
        return struct.pack(self.fmt, *values)


class Container(Node):
    def __init__(self, children=None, name=None):
        super().__init__(name)
        self.children = []
        if children:
            for c in children:
                self.add_child(c, name=c.name)
    
    def add_child(self, node, name=None):
        node.parent = self
        self.children.append(node)
        if name is not None:
            node.name = name
        return node
    
    def layout(self, base_offset=0):
        flat, fixups = [], []
        
        offset = base_offset
        stack = [("root", self)]
        
        while stack:
            current_path, node = stack.pop(0)
            
            node_bytes = b""
            if isinstance(node, (Array, Struct)):
                children = []
                i = 0
                for c in node.children:
                    child_name = c.name
                    if not child_name:
                        child_name = node.child_name_template.format(i=i)
                    node_path = ".".join([current_path, child_name])
                    children.append((node_path, c))
                    if not isinstance(c, AbstractNode):
                        i += 1
                stack = children + stack
            elif isinstance(node, (Alignment)):
                aligned = (offset + node.align - 1) & ~(node.align - 1)
                node_bytes = b"\xA1" * (aligned - offset)
            else:
                node_bytes = node.pack()
            
            if isinstance(node, (Pointer, ComputedCount)):
                fixups.append(len(flat))
            
            size = len(node_bytes)
            verbose and log.debug(f"{current_path} {size}")
            
            flat.append((offset, current_path, node_bytes, node))
            offset += size
        
        fixups_msg = ["\nBefore fixups:"]
        if verbose:
            if base_offset == 0:
                for offset, node_path, node_bytes, node in flat:
                    offset_hex = f"0x{offset:0X}"
                    fixups_msg.append(f"{offset_hex:<10} {node_path:<70} {type(node).__name__:<20} {bytearray(node_bytes).hex('-')[:50]} ")
        
        fixups_msg.append("\nFixups:")
        for i in fixups:
            node_info = (offset, node_path, node_bytes, node) = flat[i]
            ref_index = get_node_ref_index(node, flat)
            ref_info = (ref_offset, ref_path, ref_bytes, ref_node) = flat[ref_index]
            
            node.value = node.compute_value(node_info, ref_info)
            fixups_msg.append(' '.join([hex(offset), node_path, node.ref, "=>", hex(ref_offset), ref_path, "=>", hex(node.value)]))
            flat[i] = offset, node_path, node.pack(), node
            
        fixups_msg.append("\nAfter fixups:")
        
        if verbose:
            if base_offset == 0:
                for offset, node_path, node_bytes, node in flat:
                    offset_hex = f"0x{offset:0X}"
                    fixups_msg.append(
                        f"{offset_hex:<10} {node_path:<70} {type(node).__name__:<20} {bytearray(node_bytes).hex('-')[:50]} ")
        verbose and log.debug('\n'.join(fixups_msg))
        return flat
    
    def serialize(self, base_offset=0):
        flat = self.layout(base_offset=base_offset)
        return b"".join([node_bytes for offset, node_path, node_bytes, node in flat])


class Struct(Container):
    child_name_template = "field{i}"
    
    def __init__(self, *args, **kwargs):
        self.child_lookup = {}
        super().__init__(*args, **kwargs)
    
    def __getattr__(self, name):
        child = self.child_lookup.get(name)
        if child is None:
            child = super().__getattribute__(name)
        return child
    
    def add_child(self, node, name=None):
        child = super().add_child(node, name=name)
        self.child_lookup[child.name] = child
        return child


class Array(Container):
    child_name_template = "{i}"
    
    def __getitem__(self, i):
        return self.children[i]


class Bytes(LeafNode):
    def pack(self):
        return self.value


class U8(LeafNode):  fmt = "<B"; default = 0x55


class U16(LeafNode): fmt = "<H"; default = 0x1234


class U32(LeafNode): fmt = "<I"; default = 0x03030303


class S16(LeafNode): fmt = "<h"; default = 0x1122


class S32(LeafNode): fmt = "<i"; default = 0x05050505


class F32(LeafNode): fmt = "<f"; default = 1.0


class Pointer(U32, ComputedNode):
    def __init__(self, ref, name=None):
        super().__init__(0, name=name)
        self.ref = ref
    
    def compute_value(self, node_info, ref_info):
        offset, node_path, node_bytes, node = node_info
        ref_offset, ref_path, ref_bytes, ref_node = ref_info
        in_ref_offset = 0
        m = re.search(r'\+(0[xX][a-fA-F0-9]+|\d+)$', node.ref)
        if m:
            s = m.group(0)[1:]
            base = 16 if s.lower().startswith("0x") else 10
            in_ref_offset = int(s, base)
        
        return (ref_offset + in_ref_offset) - offset


class ComputedCount(U32, ComputedNode):
    def __init__(self, ref, name=None):
        super().__init__(0, name=name)
        self.ref = ref
    
    def compute_value(self, node_info, ref_info):
        offset, node_path, node_bytes, node = node_info
        ref_offset, ref_path, ref_bytes, ref_node = ref_info
        return len([c for c in ref_node.children if not isinstance(c, AbstractNode)])


if __name__ == '__main__':
    # fields is a list of nodes
    # walk the list left to right, descend into fields and make them concrete
    # if a field is a pointer, store it and its ref and update it at the end
    # if a field is an array or a struct, descend into it and make it concrete
    # ref is a notation describing how to search the tree relative to the node to find its ref
    # it can be an absolute id, or "goto tree root then find symbol", or "go one up and find symbol in subtree", etc
    
    buf = "This is a long byte string of words".encode('utf-8')
    mesh_root = Struct([
        U32(name="pFilename"),
        U32(name="filenameHash"),
        U32(name="parsedFlag"),
        ComputedCount(ref="meshTable", name="meshCount"),
        Pointer(ref="meshTable", name="pMeshTable"),
        U32(name="pSkeleton"),
        Pointer(ref="str+0x20", name="pStr"),
        Bytes(buf, name="str"),
        U32(),
        U32(),
        Array([F32(5.6), F32(), F32(), F32()], name="bsphere"),
        Array([F32(), F32(), F32(), F32()], name="bbox"),
        Array([F32(), F32(), F32(), F32()], name="unkHeaderVec4"),
    ])
    
    mesh_table = mesh_root.add_child(Array(), name="meshTable")
    mesh_infos = mesh_root.add_child(Array(), name="meshInfos")
    for i in range(4):
        mesh_table.add_child(Array([U32(name="parsedFlag"), Pointer(ref=f"meshInfos.{i}", name="pMesh")]))
        mesh_infos.add_child(Alignment(align=4))
        mesh_infos.add_child(Struct([U32()]))
    

    
    print_hex(mesh_root.serialize())
    print(mesh_root.bsphere[0])
    mesh_root.bsphere[0].value = 6666.0
    print_hex(mesh_root.serialize())
    # print_hex(s.fields[4].serialize())