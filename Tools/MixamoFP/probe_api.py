# Somente leitura: API disponivel para montar um componente Blueprint por script + checagens dos bracos 1P.
import os, unreal
saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
LOG = os.path.join(saved, "MixamoFP_probe_api.txt")
out = []


def names(obj, filt=None):
    return sorted(n for n in dir(obj) if not n.startswith("_") and (filt is None or any(f in n for f in filt)))


out.append("BlueprintEditorLibrary: %s" % names(unreal.BlueprintEditorLibrary))
out.append("EdGraphNode: %s" % names(unreal.EdGraphNode, ("pin", "pos", "node", "comment", "title")))
out.append("EdGraphPin: %s" % (names(unreal.EdGraphPin) if hasattr(unreal, "EdGraphPin") else "?"))
out.append("EdGraph: %s" % names(unreal.EdGraph))
out.append("SubobjectDataSubsystem: %s" % names(unreal.SubobjectDataSubsystem))
out.append("AddNewSubobjectParams: %s" % names(unreal.AddNewSubobjectParams))
for c in ("K2Node_CallFunction", "K2Node_VariableGet", "K2Node_Event", "K2Node_IfThenElse"):
    k = getattr(unreal, c, None)
    out.append("%s: %s" % (c, names(k) if k else "ausente"))
extra = [n for n in dir(unreal) if any(s in n.lower() for s in ("graphlibrary", "nodelibrary", "blueprintgraph", "k2library", "graphutil"))]
out.append("unreal.* graph libs: %s" % extra)
# bracos 1P
try:
    arms = unreal.load_asset("/Game/FPMovement/Demo/Character/Arms/MetaHuman/SKM_Metahuman_Arms")
    pp = arms.get_editor_property("post_process_anim_blueprint")
    out.append("SKM_Metahuman_Arms.post_process_anim_blueprint = %s" % (pp.get_path_name() if pp else None))
except Exception as e:
    out.append("post_process: %s" % e)
try:
    abp = unreal.load_asset("/Game/Characters/MixamoFP/Arms/ABP_Arms_Cowboy")
    prefix = abp.get_path_name() + ":"
    for o in unreal.ObjectIterator(unreal.AnimGraphNode_BlendSpacePlayer):
        if o.get_path_name().startswith(prefix):
            out.append("ABP_Arms_Cowboy %s -> %s" % (o.get_path_name()[len(prefix):], o.get_editor_property("node").get_editor_property("blend_space").get_path_name()))
    out.append("ABP_Arms_Cowboy status=%s" % abp.get_editor_property("status") if hasattr(abp, "get_editor_property") else "")
except Exception as e:
    out.append("abp: %s" % e)
open(LOG, "w", encoding="utf-8").write("\n".join(str(x) for x in out))
