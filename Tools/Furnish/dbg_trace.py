# Somente leitura: line trace vertical em (x, y) e lista o que foi atingido.  py dbg_trace.py x y
import sys, unreal
x, y = float(sys.argv[1]), float(sys.argv[2])
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
ch = unreal.TraceTypeQuery.TRACE_TYPE_QUERY1
ignore = []
z = 380.0
for _ in range(6):
    hit = unreal.SystemLibrary.line_trace_single(w, unreal.Vector(x, y, z), unreal.Vector(x, y, -20), ch, True, ignore,
                                                 unreal.DrawDebugTrace.NONE, True)
    if hit is None:
        break
    t = hit.to_tuple()
    if not t[0]:
        break
    a = t[9]
    unreal.log("LUXTRACE z=%.1f ator=%s comp=%s" % (t[5].z, a.get_actor_label() if a else None, t[10].get_name() if t[10] else None))
    if a:
        ignore.append(a)
    z = t[5].z
