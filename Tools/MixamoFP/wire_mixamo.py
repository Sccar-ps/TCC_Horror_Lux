# Etapa 4 (UE): liga os nos colados aos nos padrao (Update / Output Pose), compila e salva os dois ABPs.
import os, json, unreal
BEL = unreal.BlueprintEditorLibrary
EAL = unreal.EditorAssetLibrary
ABP = "/Game/Characters/MixamoFP/Blueprints/ABP_CowboyFP"
VIS = "/Game/Characters/MixamoFP/Blueprints/ABP_CowboyFP_Visible"
PROJ = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
NAMES = json.load(open(os.path.join(PROJ, "Tools", "MixamoFP", "t3d", "mx_names.json"), encoding="utf-8"))
saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
LOG = os.path.join(saved, "MixamoFP_wire.txt")
out = []


def w(m):
    out.append(str(m))
    unreal.log("[MixamoFP] " + str(m))


def nodes_of(asset_path, graph):
    prefix = asset_path + "." + asset_path.rsplit("/", 1)[-1] + ":" + graph + "."
    found = {}
    for obj in unreal.ObjectIterator(unreal.K2Node):
        p = obj.get_path_name()
        if p.startswith(prefix) and "." not in p[len(prefix):]:
            found[p[len(prefix):]] = obj
    return found


def connect(a, a_pin, b, b_pin):
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
        w("  %-44s %-34s %s" % (name, str(n.get_node_title()).replace("\n", " ")[:34], " ".join(pins)))


try:
    # ---------------- principal
    abp = EAL.load_asset(ABP)
    ev = nodes_of(ABP, "EventGraph")
    an = nodes_of(ABP, "AnimGraph")
    upd = next((n for k, n in ev.items() if "BlueprintUpdateAnimation" in str(n.get_node_title()).replace(" ", "") and "_CB" not in k), None)
    entry = ev.get(NAMES["abp_event_entry"])
    interp = ev.get(NAMES["abp_finterp"])
    w("EventGraph: %d nos, update=%s entry=%s interp=%s" % (len(ev), upd and upd.get_name(), entry and entry.get_name(), interp and interp.get_name()))
    if upd and entry:
        connect(upd, "then", entry, "exec")
    if upd and interp:
        connect(upd, "DeltaTimeX", interp, "DeltaTime")
    root = next((n for k, n in an.items() if k.startswith("AnimGraphNode_Root")), None)
    exitn = an.get(NAMES["abp_anim_exit"])
    w("AnimGraph: %d nos, root=%s exit=%s" % (len(an), root and root.get_name(), exitn and exitn.get_name()))
    if root and exitn:
        connect(exitn, "Pose", root, "Result")
    BEL.remove_unused_nodes(abp)
    BEL.compile_blueprint(abp)
    cdo = unreal.get_default_object(abp.generated_class())
    for k, v in (("StandingHalfHeight", 96.0), ("CrouchedHalfHeight", 40.0), ("BackOffsetStand", 4.0), ("BackOffsetCrouch", 30.0)):
        cdo.set_editor_property(k, v)
    cdo.set_editor_property("root_motion_mode", unreal.RootMotionMode.IGNORE_ROOT_MOTION)
    EAL.save_loaded_asset(abp, False)
    w("--- ABP_CowboyFP EventGraph")
    dump(nodes_of(ABP, "EventGraph"))
    w("--- ABP_CowboyFP AnimGraph")
    dump(nodes_of(ABP, "AnimGraph"))

    # ---------------- visivel
    vis = EAL.load_asset(VIS)
    van = nodes_of(VIS, "AnimGraph")
    vroot = next((n for k, n in van.items() if k.startswith("AnimGraphNode_Root")), None)
    vexit = van.get(NAMES["vis_anim_exit"])
    w("Visible AnimGraph: root=%s exit=%s" % (vroot and vroot.get_name(), vexit and vexit.get_name()))
    if vroot and vexit:
        connect(vexit, "Pose", vroot, "Result")
    BEL.remove_unused_nodes(vis)
    BEL.compile_blueprint(vis)
    EAL.save_loaded_asset(vis, False)
    w("--- Visible EventGraph")
    dump(nodes_of(VIS, "EventGraph"))
    w("--- Visible AnimGraph")
    dump(van)
except Exception:
    import traceback
    w("ERRO: " + traceback.format_exc())
finally:
    open(LOG, "w", encoding="utf-8").write("\n".join(out))
