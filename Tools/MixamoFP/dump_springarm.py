# Somente leitura: o que no BP_Player mexe no SpringArm/camera (e a logica de sprint).
import os, unreal
BP = "/Game/FPMovement/Player/Blueprints/BP_Player.BP_Player:"
out = []
nodes = {}
for n in unreal.ObjectIterator(unreal.K2Node):
    p = n.get_path_name()
    if p.startswith(BP):
        nodes[p[len(BP):]] = n


def title(n):
    return str(n.get_node_title()).replace("\n", " ")[:40]


def pins(n):
    r = []
    for p in n.list_all_pins():
        links = p.list_connected_pins()
        dv = ""
        try:
            dv = p.get_default_value()
        except Exception:
            pass
        if links or dv not in ("", None, "0", "0.0", "False", "0.000000"):
            r.append("%s%s%s" % (p.get_pin_name(), ("=" + str(dv)) if dv not in ("", None) else "",
                                 ("->[" + ",".join("%s.%s" % (title(l.get_owning_node())[:26], l.get_pin_name()) for l in links) + "]") if links else ""))
    return " | ".join(r)


starts = [n for k, n in nodes.items() if any(s in title(n) for s in ("SpringArm", "Sprint", "Set Relative Location", "Set World Location", "Headbob"))]
seen, fr = set(), [(s, 0) for s in starts]
while fr:
    n, d = fr.pop(0)
    if n.get_path_name() in seen or d > 2:
        continue
    seen.add(n.get_path_name())
    g = n.get_path_name()[len(BP):].split(".")[0]
    out.append("[%d] %-22s %-40s %s" % (d, g[:22], title(n), pins(n)))
    for p in n.list_all_pins():
        for l in p.list_connected_pins():
            fr.append((l.get_owning_node(), d + 1))
saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
open(os.path.join(saved, "MixamoFP_springarm.txt"), "w", encoding="utf-8").write("\n".join(out))
