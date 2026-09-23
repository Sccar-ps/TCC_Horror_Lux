# Etapa 5c (UE): garante um no "Event Blueprint Update Animation" real (nao-fantasma) no ABP_CowboyFP_Visible.
import os, unreal
BEL = unreal.BlueprintEditorLibrary
EAL = unreal.EditorAssetLibrary
VIS = "/Game/Characters/MixamoFP/Blueprints/ABP_CowboyFP_Visible"
saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
LOG = os.path.join(saved, "MixamoFP_fixupdate.txt")
out = []


def events():
    prefix = VIS + ".ABP_CowboyFP_Visible:EventGraph."
    return {o.get_name(): o for o in unreal.ObjectIterator(unreal.K2Node_Event) if o.get_path_name().startswith(prefix)}


try:
    vis = EAL.load_asset(VIS)
    out.append("list_events antes: %s" % [str(e) for e in BEL.list_events(vis)])
    out.append("nos antes: %s" % sorted(events()))
    n = BEL.add_event_override(vis, "BlueprintUpdateAnimation")
    out.append("add_event_override -> %s" % (n and n.get_name()))
    out.append("list_events depois: %s" % [str(e) for e in BEL.list_events(vis)])
    for name, e in sorted(events().items()):
        out.append("  %s pos=%s links=%s" % (name, e.get_node_pos(), [(p.get_pin_name(), [c.get_owning_node().get_name() for c in p.list_connected_pins()]) for p in e.list_all_pins()]))
except Exception:
    import traceback
    out.append("ERRO " + traceback.format_exc())
open(LOG, "w", encoding="utf-8").write("\n".join(out))
