# Somente leitura: lista a API Python disponivel nos nos do grafo (para lidar com o no "fantasma" do Update).
import os, unreal
VIS = "/Game/Characters/MixamoFP/Blueprints/ABP_CowboyFP_Visible"
ABP = "/Game/Characters/MixamoFP/Blueprints/ABP_CowboyFP"
saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
LOG = os.path.join(saved, "MixamoFP_probe.txt")
out = []
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if les.is_in_play_in_editor():
    les.editor_request_end_play()
    out.append("PIE encerrado")
unreal.EditorAssetLibrary.load_asset(VIS)
unreal.EditorAssetLibrary.load_asset(ABP)
ev = {}
for asset in (VIS, ABP):
    prefix = asset + "." + asset.rsplit("/", 1)[-1] + ":EventGraph."
    for obj in unreal.ObjectIterator(unreal.K2Node_Event):
        p = obj.get_path_name()
        if p.startswith(prefix):
            ev[p] = obj
for p, n in sorted(ev.items()):
    out.append(p)
    for attr in ("enabled_state", "b_user_set_enabled_state", "node_pos_x", "node_pos_y", "node_comment", "b_comment_bubble_visible"):
        try:
            out.append("   %s = %s" % (attr, n.get_editor_property(attr)))
        except Exception as e:
            out.append("   %s : %s" % (attr, str(e)[:90]))
names = sorted(set(dir(next(iter(ev.values())))))
out.append("API K2Node_Event: " + ", ".join(x for x in names if not x.startswith("_")))
for lib in ("BlueprintEditorLibrary", "EdGraphNodeLibrary", "BlueprintNodeLibrary", "K2NodeLibrary", "EdGraphLibrary"):
    if hasattr(unreal, lib):
        out.append("%s: %s" % (lib, ", ".join(x for x in dir(getattr(unreal, lib)) if not x.startswith("_"))))
open(LOG, "w", encoding="utf-8").write("\n".join(out))
