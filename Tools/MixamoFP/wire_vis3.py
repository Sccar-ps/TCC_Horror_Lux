# Etapa 5f (UE): liga o patch LookDownShift, organiza o layout dos dois grafos, compila, aplica defaults e salva.
import os, re, json, unreal
BEL = unreal.BlueprintEditorLibrary
EAL = unreal.EditorAssetLibrary
VIS = "/Game/Characters/MixamoFP/Blueprints/ABP_CowboyFP_Visible"
PROJ = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
T3D = os.path.join(PROJ, "Tools", "MixamoFP", "t3d")
N3 = json.load(open(os.path.join(T3D, "mx_vis3_names.json"), encoding="utf-8"))
saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
LOG = os.path.join(saved, "MixamoFP_wire_vis3.txt")
DEFAULTS = (("NeckMinBehind", 10.0), ("MaxBodyShift", 25.0), ("LeanStartPitch", -20.0), ("LeanFullPitch", -75.0),
            ("LeanMax", 14.0), ("LookDownShift", 12.0))
out = []


def w(m):
    out.append(str(m))


def nodes(graph):
    prefix = VIS + ".ABP_CowboyFP_Visible:" + graph + "."
    return {o.get_name(): o for o in unreal.ObjectIterator(unreal.EdGraphNode)
            if o.get_path_name().startswith(prefix) and "." not in o.get_path_name()[len(prefix):]}


def connect(ns, a, a_pin, b, b_pin):
    pa, pb = ns[a].find_output_pin(a_pin), ns[b].find_input_pin(b_pin)
    ok = pa.try_create_connection(pb) if (pa and pb) else "pino ausente"
    w("  link %s.%s -> %s.%s : %s" % (a, a_pin, b, b_pin, ok))


def t3d_pos(fname):
    txt = open(os.path.join(T3D, fname), encoding="utf-8").read()
    pos = {}
    for m in re.finditer(r'Begin Object Class=\S+ Name="([^"]+)"(.*?)\nEnd Object', txt, re.S):
        x = re.search(r"NodePosX=(-?\d+)", m.group(2))
        y = re.search(r"NodePosY=(-?\d+)", m.group(2))
        if x and y:
            pos[m.group(1)] = (int(x.group(1)), int(y.group(1)))
    return pos


def place(n, x, y):
    p = unreal.IntPoint(int(x), int(y))
    try:
        n.set_node_pos(p)
    except Exception:
        BEL.set_node_pos(n, p)


try:
    vis = EAL.load_asset(VIS)
    ev = nodes("EventGraph")
    connect(ev, "K2Node_CallFunction_FV29", "Pitch", N3["fx_map"], "Value")
    connect(ev, "K2Node_VariableGet_FV30", "LeanStartPitch", N3["fx_map"], "InRangeA")
    connect(ev, "K2Node_VariableGet_FV31", "LeanFullPitch", N3["fx_map"], "InRangeB")
    connect(ev, "K2Node_VariableSet_FV14", "Output_Get", N3["fx_mulw"], "B")
    connect(ev, "K2Node_CallFunction_FV21", "ReturnValue", N3["fx_sum"], "A")
    connect(ev, N3["fx_sum"], "ReturnValue", "K2Node_CallFunction_FV23", "Target")
    # ---- layout do EventGraph
    fixed = {"K2Node_Event_CB01": (-1200, -300), "K2Node_CallFunction_CB02": (-1180, -140), "K2Node_CallFunction_CB03": (-880, -300),
             "K2Node_CallFunction_CB04": (-600, -300), "K2Node_CallFunction_CB05": (-320, -300), "K2Node_CallFunction_FV01": (-60, -140),
             "K2Node_DynamicCast_FV02": (0, -300), "K2Node_VariableSet_FV03": (320, -300), "K2Node_Event_1": (-1200, 100),
             "K2Node_Event_0": (-1200, 1500), "K2Node_CallFunction_0": (-1200, 1650)}
    pos = t3d_pos("mx_vis2_event.t3d")
    pos.update(t3d_pos("mx_vis3_event.t3d"))
    for name, n in ev.items():
        if name in fixed:
            place(n, *fixed[name])
        elif name in (N3["fx_c1"], N3["fx_c2"]) and name in pos:
            place(n, *pos[name])
        elif name in pos:
            place(n, pos[name][0], pos[name][1] - 400)
    # ---- layout do AnimGraph
    an = nodes("AnimGraph")
    apos = {"AnimGraphNode_CopyPoseFromMesh_CB01": (-900, 0), "AnimGraphNode_LocalToComponentSpace_FA01": (-600, 0),
            "K2Node_VariableGet_FA02": (-580, 160), "AnimGraphNode_ModifyBone_FA03": (-340, 0), "K2Node_VariableGet_FA04": (-300, 200),
            "AnimGraphNode_ModifyBone_FA05": (-60, 0), "AnimGraphNode_ComponentToLocalSpace_FA06": (220, 0),
            "AnimGraphNode_Root_0": (480, 0), N3["fy_c3"]: (-940, -120)}
    for name, n in an.items():
        if name in apos:
            place(n, *apos[name])
    BEL.compile_blueprint(vis)
    cdo = unreal.get_default_object(vis.generated_class())
    for k, v in DEFAULTS:
        cdo.set_editor_property(k, v)
    EAL.save_loaded_asset(vis, False)
    w("defaults: %s" % [(k, cdo.get_editor_property(k)) for k, _ in DEFAULTS])
    for g in ("EventGraph", "AnimGraph"):
        w("--- %s" % g)
        for name, n in sorted(nodes(g).items()):
            links = []
            try:
                for p in n.list_all_pins():
                    c = p.list_connected_pins()
                    if c:
                        links.append("%s->[%s]" % (p.get_pin_name(), ",".join("%s.%s" % (l.get_owning_node().get_name(), l.get_pin_name()) for l in c)))
            except Exception:
                pass
            try:
                pp = n.get_node_pos()
                ptxt = "(%d,%d)" % (pp.x, pp.y)
            except Exception:
                ptxt = "?"
            w("  %-42s %-12s %s" % (name, ptxt, " ".join(links)))
except Exception:
    import traceback
    w("ERRO " + traceback.format_exc())
open(LOG, "w", encoding="utf-8").write("\n".join(out))
