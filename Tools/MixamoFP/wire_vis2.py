# Etapa 5b (UE): liga os nos colados no ABP_CowboyFP_Visible aos nos existentes, compila, aplica defaults e salva.
import os, json, unreal
BEL = unreal.BlueprintEditorLibrary
EAL = unreal.EditorAssetLibrary
VIS = "/Game/Characters/MixamoFP/Blueprints/ABP_CowboyFP_Visible"
PROJ = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
NAMES = json.load(open(os.path.join(PROJ, "Tools", "MixamoFP", "t3d", "mx_vis2_names.json"), encoding="utf-8"))
saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
LOG = os.path.join(saved, "MixamoFP_wire_vis2.txt")
DEFAULTS = (("NeckMinBehind", 10.0), ("MaxBodyShift", 25.0), ("LeanStartPitch", -20.0), ("LeanFullPitch", -75.0), ("LeanMax", 16.0))
out = []


def w(m):
    out.append(str(m))


def nodes_of(graph):
    prefix = VIS + ".ABP_CowboyFP_Visible:" + graph + "."
    found = {}
    for obj in unreal.ObjectIterator(unreal.K2Node):
        p = obj.get_path_name()
        if p.startswith(prefix) and "." not in p[len(prefix):]:
            found[p[len(prefix):]] = obj
    return found


def connect(a, a_pin, b, b_pin):
    if a is None or b is None:
        w("  no ausente para %s -> %s" % (a_pin, b_pin))
        return False
    pa, pb = a.find_output_pin(a_pin), b.find_input_pin(b_pin)
    if pa is None or pb is None:
        w("  pino nao encontrado: %s.%s -> %s.%s" % (a.get_name(), a_pin, b.get_name(), b_pin))
        return False
    for c in pb.list_connected_pins():
        if c.get_owning_node() == a:
            return True
    ok = pa.try_create_connection(pb)
    w("  link %s.%s -> %s.%s : %s" % (a.get_name(), a_pin, b.get_name(), b_pin, ok))
    return ok


def dump(nodes):
    for name, n in sorted(nodes.items()):
        pins = []
        for p in n.list_all_pins():
            links = p.list_connected_pins()
            if links:
                pins.append("%s->[%s]" % (p.get_pin_name(), ",".join("%s.%s" % (l.get_owning_node().get_name(), l.get_pin_name()) for l in links)))
        w("  %-44s %-30s %s" % (name, str(n.get_node_title()).replace("\n", " ")[:30], " ".join(pins)))


try:
    vis = EAL.load_asset(VIS)
    ev = nodes_of("EventGraph")
    upd = next((n for k, n in ev.items() if "BlueprintUpdateAnimation" in str(n.get_node_title()).replace(" ", "") and "_FV" not in k), None)
    w("EventGraph %d nos; update=%s" % (len(ev), upd and upd.get_name()))
    connect(ev.get("K2Node_CallFunction_CB05"), "then", ev.get(NAMES["vis_cast"]), "execute")
    connect(upd, "then", ev.get(NAMES["vis_valid"]), "exec")
    connect(upd, "DeltaTimeX", ev.get(NAMES["vis_interp"]), "DeltaTime")
    an = nodes_of("AnimGraph")
    root = next((n for k, n in an.items() if k.startswith("AnimGraphNode_Root")), None)
    copy = next((n for k, n in an.items() if k.startswith("AnimGraphNode_CopyPoseFromMesh")), None)
    w("AnimGraph %d nos; root=%s copy=%s" % (len(an), root and root.get_name(), copy and copy.get_name()))
    connect(an.get(NAMES["vis_c2l"]), "Pose", root, "Result")
    connect(copy, "Pose", an.get(NAMES["vis_l2c"]), "LocalPose")
    BEL.compile_blueprint(vis)
    cdo = unreal.get_default_object(vis.generated_class())
    for k, v in DEFAULTS:
        cdo.set_editor_property(k, v)
    EAL.save_loaded_asset(vis, False)
    w("defaults: %s" % [(k, cdo.get_editor_property(k)) for k, _ in DEFAULTS])
    w("--- EventGraph")
    dump(nodes_of("EventGraph"))
    w("--- AnimGraph")
    dump(nodes_of("AnimGraph"))
except Exception:
    import traceback
    w("ERRO " + traceback.format_exc())
open(LOG, "w", encoding="utf-8").write("\n".join(out))
