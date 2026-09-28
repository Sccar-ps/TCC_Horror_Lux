# LUX: sonda (so le) - como criar o evento IA_Flashlight no EventGraph do Cowboy.
import os, traceback
import unreal

EAL, BGE = unreal.EditorAssetLibrary, unreal.BlueprintGraphEditor
OUT = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), "LuxSnapshots", "vela_f_probe.txt")
L = []


def main():
    bp = EAL.load_asset("/Game/Characters/MixamoFP/Blueprints/BP_Player_Cowboy")
    ge = BGE.get_graph_editor_by_name(bp, "EventGraph")
    L.append("metodos: %s" % [m for m in dir(ge) if not m.startswith("_")])
    try:
        r = ge.list_available_nodes([])
        L.append("list_available_nodes: %d" % len(r))
        L.extend(["  " + str(x) for x in r if "IA_" in str(x) or "EnhancedAction" in str(x)][:80])
    except Exception as ex:
        import inspect
        L.append("list_available_nodes ! %s | doc %s" % (ex, ge.list_available_nodes.__doc__))
    for fn in []:
        L.append("  tentando %s" % fn)
        for args in (("IA_Flashlight",), ("Flashlight",), ()):
            try:
                r = getattr(ge, fn)(*args)
                txt = [str(x) for x in r] if isinstance(r, (list, tuple)) else str(r)
                L.append("    %s%s -> %s" % (fn, args, [t for t in txt if "IA_" in t][:40] if isinstance(txt, list) else txt[:400]))
                break
            except Exception as ex:
                L.append("    %s%s ! %s" % (fn, args, str(ex)[:200]))
    for nome in ("Entrada|EnhancedActionEvents|IA_Flashlight", "Input|EnhancedActionEvents|IA_Flashlight",
                 "Entrada|Enhanced Action Events|IA_Flashlight", "EnhancedActionEvents|IA_Flashlight", "IA_Flashlight"):
        L.append("  create_node_from_name('%s') -> sem criar (so teste de existencia nao existe); pulado" % nome)


try:
    main()
except Exception:
    L.append("ERRO " + traceback.format_exc())
with open(OUT, "w", encoding="utf-8") as fh:
    fh.write("\n".join(L))
