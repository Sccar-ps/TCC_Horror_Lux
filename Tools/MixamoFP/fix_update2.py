# Etapa 5c (UE): garante um no "Event Blueprint Update Animation" real (nao-fantasma) no ABP_CowboyFP_Visible.
import os, unreal
BEL = unreal.BlueprintEditorLibrary
EAL = unreal.EditorAssetLibrary
VIS = "/Game/Characters/MixamoFP/Blueprints/ABP_CowboyFP_Visible"
saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
LOG = os.path.join(saved, "MixamoFP_fixupdate2.txt")
out = []


def events():
    prefix = VIS + ".ABP_CowboyFP_Visible:EventGraph."
    return {o.get_name(): o for o in unreal.ObjectIterator(unreal.K2Node_Event) if o.get_path_name().startswith(prefix)}


def implemented():
    return [(str(e.get_editor_property("name")), e.get_editor_property("is_implemented")) for e in BEL.list_events(vis)]


try:
    vis = EAL.load_asset(VIS)
    out.append("doc: %s" % BEL.add_event_override.__doc__)
    ghost = events().get("K2Node_Event_0")
    p = ghost.find_then_pin()
    out.append("API pino: %s" % ", ".join(x for x in dir(p) if not x.startswith("_")))
    n = None
    for pos in (lambda: unreal.Vector2D(-900.0, 500.0), lambda: unreal.IntPoint(-900, 500)):
        try:
            n = BEL.add_event_override(vis, "BlueprintUpdateAnimation", pos())
            break
        except Exception as e:
            out.append("  tentativa: %s" % str(e)[:200])
    out.append("add_event_override -> %s" % (n and n.get_name()))
    out.append("implementados: %s" % implemented())
    for name, e in sorted(events().items()):
        out.append("  %s pos=%s links=%s" % (name, e.get_node_pos(), [(q.get_pin_name(), [c.get_owning_node().get_name() for c in q.list_connected_pins()]) for q in e.list_all_pins()]))
except Exception:
    import traceback
    out.append("ERRO " + traceback.format_exc())
open(LOG, "w", encoding="utf-8").write("\n".join(out))
