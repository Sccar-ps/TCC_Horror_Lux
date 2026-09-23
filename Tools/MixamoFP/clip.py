# Copia um arquivo .t3d (texto de nos do Blueprint) para a area de transferencia do Windows.
# Uso: py clip.py mx_abp_event   -> depois clique no grafo e Ctrl+V
import os, sys, ctypes
from ctypes import wintypes
name = sys.argv[1]
path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "t3d", name + ".t3d")
text = open(path, encoding="utf-8").read()
u32, k32 = ctypes.windll.user32, ctypes.windll.kernel32
k32.GlobalAlloc.restype = ctypes.c_void_p
k32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
k32.GlobalLock.restype = ctypes.c_void_p
k32.GlobalLock.argtypes = [ctypes.c_void_p]
k32.GlobalUnlock.argtypes = [ctypes.c_void_p]
u32.SetClipboardData.restype = ctypes.c_void_p
u32.SetClipboardData.argtypes = [wintypes.UINT, ctypes.c_void_p]
data = text.encode("utf-16-le") + b"\x00\x00"
h = k32.GlobalAlloc(0x0002, len(data))
p = k32.GlobalLock(h)
ctypes.memmove(p, data, len(data))
k32.GlobalUnlock(h)
u32.OpenClipboard(0)
u32.EmptyClipboard()
u32.SetClipboardData(13, h)
u32.CloseClipboard()
import unreal
unreal.log("[MixamoFP] clipboard <- %s (%d chars)" % (name, len(text)))
