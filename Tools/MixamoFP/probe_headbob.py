# Somente leitura: o que no BP_Player depende da velocidade e mexe na camera (headbob, shakes, FOV)?
import os, unreal
saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
LOG = os.path.join(saved, "MixamoFP_probe_headbob.txt")
out = []
bp = unreal.load_asset("/Game/FPMovement/Player/Blueprints/BP_Player")
BGE = unreal.BlueprintGraphEditor
BEL = unreal.BlueprintEditorLibrary
out.append("graficos: %s" % [str(g) for g in BEL.list_graph_names(bp)])
KEYS = ("shake", "fov", "fieldofview", "headbob", "velocity", "length", "sprint", "speed", "camera", "offset", "bob", "lerp", "timeline")


def dump_graph(gname, everything=False):
    try:
        ge = BGE.get_graph_editor_by_name(bp, gname)
    except Exception as e:
        out.append("  %s: %s" % (gname, e))
        return
    if ge is None:
        return
    nodes = list(ge.list_all_nodes())
    out.append("== %s (%d nos)" % (gname, len(nodes)))
    for n in nodes:
        title = str(n.get_node_title()).replace("\n", " ")
        if not everything and not any(k in title.lower() for k in KEYS):
            continue
        pins = []
        for p in n.list_all_pins():
            c = p.list_connected_pins()
            v = p.get_pin_value()
            if c:
                pins.append("%s->[%s]" % (p.get_pin_name(), ",".join("%s.%s" % (str(l.get_owning_node().get_node_title()).replace("\n", " ")[:28], l.get_pin_name()) for l in c)))
            elif v:
                pins.append("%s=%s" % (p.get_pin_name(), v[:80]))
        out.append("  %-30s %-44s %s" % (n.get_name(), title[:44], " | ".join(pins)))


for g in BEL.list_graph_names(bp):
    g = str(g)
    dump_graph(g, everything=("headbob" in g.lower()))
# classes de camera shake usadas
for p in ("/Game/FPMovement/Player/Effects/Headbob/BP_Sprint", "/Game/FPMovement/Player/Effects/Headbob/BP_Walk",
          "/Game/FPMovement/Player/Effects/Headbob/BP_Idle"):
    try:
        a = unreal.load_asset(p)
        cdo = unreal.get_default_object(a.generated_class())
        info = []
        for k in ("oscillation_duration", "rot_oscillation", "loc_oscillation", "fov_oscillation", "root_shake_pattern"):
            try:
                info.append("%s=%s" % (k, cdo.get_editor_property(k)))
            except Exception:
                pass
        out.append("%s: %s" % (p.rsplit("/", 1)[-1], " ".join(info)[:900]))
    except Exception as e:
        out.append("%s: %s" % (p, e))
open(LOG, "w", encoding="utf-8").write("\n".join(out))
