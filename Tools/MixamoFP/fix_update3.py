# Etapa 5d (UE): passa as ligacoes do no fantasma (K2Node_Event_0) para o Update real (K2Node_Event_1), compila e salva.
import os, json, unreal
BEL = unreal.BlueprintEditorLibrary
EAL = unreal.EditorAssetLibrary
VIS = "/Game/Characters/MixamoFP/Blueprints/ABP_CowboyFP_Visible"
PROJ = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
NAMES = json.load(open(os.path.join(PROJ, "Tools", "MixamoFP", "t3d", "mx_vis2_names.json"), encoding="utf-8"))
saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
LOG = os.path.join(saved, "MixamoFP_fixupdate3.txt")
DEFAULTS = (("NeckMinBehind", 10.0), ("MaxBodyShift", 25.0), ("LeanStartPitch", -20.0), ("LeanFullPitch", -75.0), ("LeanMax", 16.0))
out = []


def nodes():
    prefix = VIS + ".ABP_CowboyFP_Visible:EventGraph."
    return {o.get_name(): o for o in unreal.ObjectIterator(unreal.K2Node) if o.get_path_name().startswith(prefix)
            and "." not in o.get_path_name()[len(prefix):]}


try:
    vis = EAL.load_asset(VIS)
    ns = nodes()
    ghost, real = ns.get("K2Node_Event_0"), ns.get("K2Node_Event_1")
    for p in ghost.list_all_pins():
        if p.list_connected_pins():
            p.break_pin_links()
    out.append("fantasma sem ligacoes: %s" % all(not p.list_connected_pins() for p in ghost.list_all_pins()))
    for a_pin, b, b_pin in (("then", NAMES["vis_valid"], "exec"), ("DeltaTimeX", NAMES["vis_interp"], "DeltaTime")):
        ok = real.find_output_pin(a_pin).try_create_connection(ns[b].find_input_pin(b_pin))
        out.append("link %s.%s -> %s.%s : %s" % (real.get_name(), a_pin, b, b_pin, ok))
    real.set_node_pos(unreal.IntPoint(-900, 500))
    BEL.remove_unused_nodes(vis)
    BEL.compile_blueprint(vis)
    cdo = unreal.get_default_object(vis.generated_class())
    for k, v in DEFAULTS:
        cdo.set_editor_property(k, v)
    EAL.save_loaded_asset(vis, False)
    out.append("implementados: %s" % [(str(e.get_editor_property("name")), e.get_editor_property("is_implemented")) for e in BEL.list_events(vis)])
    ns = nodes()
    out.append("nos restantes (%d): %s" % (len(ns), sorted(ns)))
    for k in ("K2Node_Event_0", "K2Node_Event_1"):
        if k in ns:
            out.append("  %s links=%s" % (k, [(q.get_pin_name(), [c.get_owning_node().get_name() for c in q.list_connected_pins()]) for q in ns[k].list_all_pins()]))
except Exception:
    import traceback
    out.append("ERRO " + traceback.format_exc())
open(LOG, "w", encoding="utf-8").write("\n".join(out))
