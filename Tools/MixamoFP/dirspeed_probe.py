# Etapa D0 (UE): cria o componente BPC_DirectionalSpeed (vazio) e lista os nomes de nos disponiveis para montar o grafo.
import os, unreal
EAL = unreal.EditorAssetLibrary
BEL = unreal.BlueprintEditorLibrary
BGE = unreal.BlueprintGraphEditor
PATH = "/Game/Characters/MixamoFP/Blueprints/BPC_DirectionalSpeed"
saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
LOG = os.path.join(saved, "MixamoFP_dirspeed_probe.txt")
out = []


def w(m):
    out.append(str(m))


try:
    w("doc create: %s" % BEL.create_blueprint_asset_with_parent.__doc__)
    w("doc create_node_from_name: %s" % BGE.create_node_from_name.__doc__)
    w("doc add_call_function_node: %s" % BGE.add_call_function_node.__doc__)
    w("doc add_macro_node: %s" % BGE.add_macro_node.__doc__)
    if EAL.does_asset_exist(PATH):
        bp = EAL.load_asset(PATH)
    else:
        bp = BEL.create_blueprint_asset_with_parent(PATH, unreal.ActorComponent)
    w("bp: %s parent=%s" % (bp and bp.get_path_name(), bp and BEL.get_blueprint_parent_class(bp)))
    BEL.compile_blueprint(bp)
    ge = BGE.get_graph_editor_by_name(bp, "EventGraph")
    w("graphs: %s" % [str(g) for g in BEL.list_graph_names(bp)])
    for n in ge.list_all_nodes():
        w("  no: %s | %s | pos=%s" % (n.get_name(), str(n.get_node_title()).replace("\n", " "), n.get_node_pos()))
    names = list(ge.list_available_nodes([]))
    w("total nos disponiveis: %d" % len(names))
    keys = ("cast to bp_player", "is valid", "isvalid", "normal", "dot product", "nearly equal", "select float", "lerp", "absolute",
            "abs", "current acceleration", "forward vector", "tick prerequisite", "get owner", "max walk speed", "self",
            "vector length xy", "vsizexy", "character movement", "branch", "iscrouching", "is crouching", "greater", "and boolean",
            "not boolean", "multiply", "add")
    for k in keys:
        hits = [s for s in names if k in s.lower()]
        w("[%s] %d: %s" % (k, len(hits), hits[:14]))
    # teste do formato de caminho de funcao (no removido em seguida, nada salvo)
    for fp in ("/Script/Engine.KismetMathLibrary:Dot_VectorVector", "/Script/Engine.KismetMathLibrary.Dot_VectorVector"):
        try:
            n = ge.add_call_function_node(fp)
            w("add_call_function_node(%s) -> %s pins=%s" % (fp, n and n.get_name(),
                                                         n and [str(p.get_pin_name()) for p in n.list_all_pins()]))
            if n:
                ge.remove_nodes([n])
        except Exception as e:
            w("add_call_function_node(%s) erro: %s" % (fp, e))
except Exception:
    import traceback
    w("ERRO " + traceback.format_exc())
open(LOG, "w", encoding="utf-8").write("\n".join(out))
