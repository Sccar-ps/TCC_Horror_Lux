"""Parser minimo de FBX binario (7.x) -> arvore de nos com propriedades."""
import struct, zlib
import numpy as np


class Node:
    __slots__ = ("name", "props", "children")

    def __init__(self, name, props, children):
        self.name, self.props, self.children = name, props, children

    def find(self, name):
        for c in self.children:
            if c.name == name:
                return c
        return None

    def findall(self, name):
        return [c for c in self.children if c.name == name]


def _read_array(data, off, typecode, dtype):
    length, encoding, comp_len = struct.unpack_from("<III", data, off)
    off += 12
    raw = data[off:off + comp_len]
    off += comp_len
    if encoding == 1:
        raw = zlib.decompress(raw)
    arr = np.frombuffer(raw, dtype=dtype, count=length)
    return arr, off


def _read_prop(data, off):
    t = chr(data[off]); off += 1
    if t == "Y": v = struct.unpack_from("<h", data, off)[0]; off += 2
    elif t == "C": v = bool(data[off]); off += 1
    elif t == "I": v = struct.unpack_from("<i", data, off)[0]; off += 4
    elif t == "F": v = struct.unpack_from("<f", data, off)[0]; off += 4
    elif t == "D": v = struct.unpack_from("<d", data, off)[0]; off += 8
    elif t == "L": v = struct.unpack_from("<q", data, off)[0]; off += 8
    elif t == "f": v, off = _read_array(data, off, t, "<f4")
    elif t == "d": v, off = _read_array(data, off, t, "<f8")
    elif t == "l": v, off = _read_array(data, off, t, "<i8")
    elif t == "i": v, off = _read_array(data, off, t, "<i4")
    elif t == "b": v, off = _read_array(data, off, t, "<u1")
    elif t in "SR":
        n = struct.unpack_from("<I", data, off)[0]; off += 4
        v = data[off:off + n]; off += n
        if t == "S":
            v = v.decode("utf-8", "replace")
    else:
        raise ValueError("tipo desconhecido %r em %d" % (t, off))
    return v, off


def _read_node(data, off, v75):
    if v75:
        end, nprops, plen = struct.unpack_from("<QQQ", data, off); off += 24
    else:
        end, nprops, plen = struct.unpack_from("<III", data, off); off += 12
    nlen = data[off]; off += 1
    if end == 0:
        return None, off
    name = data[off:off + nlen].decode("ascii", "replace"); off += nlen
    props = []
    for _ in range(nprops):
        v, off = _read_prop(data, off)
        props.append(v)
    children = []
    sentinel = 25 if v75 else 13
    while off < end:
        if end - off == sentinel and data[off:end] == b"\0" * sentinel:
            off = end
            break
        ch, off = _read_node(data, off, v75)
        if ch is None:
            break
        children.append(ch)
    return Node(name, props, children), end


def parse(path):
    data = open(path, "rb").read()
    assert data[:20] == b"Kaydara FBX Binary  ", "nao e FBX binario"
    version = struct.unpack_from("<I", data, 23)[0]
    v75 = version >= 7500
    off = 27
    top = []
    while off < len(data):
        node, off = _read_node(data, off, v75)
        if node is None:
            break
        top.append(node)
    return version, Node("root", [], top)


def props70(node):
    """Properties70 -> dict nome -> valores"""
    out = {}
    p = node.find("Properties70") if node else None
    if p:
        for c in p.children:
            out[c.props[0]] = c.props[4:]
    return out
