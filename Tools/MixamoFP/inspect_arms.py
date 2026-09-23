# Somente leitura: como o ABP dos bracos 1P (FirstPersonMesh do FPMovement) decide a animacao de corrida.
import os, unreal
EAL = unreal.EditorAssetLibrary
saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
LOG = os.path.join(saved, "MixamoFP_inspect_arms.txt")
out = []


def w(m):
    out.append(str(m))


def safe(f):
    try:
        return f()
    except Exception as e:
        return "?(%s)" % str(e)[:80]


try:
    bp = unreal.load_asset("/Game/FPMovement/Player/Blueprints/BP_Player")     # unreal.load_asset funciona com o PIE rodando
    arms_cls = None
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    for h in sds.k2_gather_subobject_data_for_blueprint(bp):
        o = lib.get_object(lib.get_data(h))
        if o and o.get_name().startswith("FirstPersonMesh"):
            arms_cls = o.get_editor_property("anim_class")
            w("FirstPersonMesh: mesh=%s anim=%s cast_shadow=%s" % (safe(lambda: o.get_skeletal_mesh_asset().get_path_name()),
                                                                  arms_cls and arms_cls.get_path_name(), o.get_editor_property("cast_shadow")))
    abp_path = arms_cls.get_path_name().split(".")[0]
    abp = unreal.load_asset(abp_path)
    w("ABP: %s vars=%s" % (abp_path, [str(v) for v in unreal.BlueprintEditorLibrary.list_member_variable_names(abp)]))
    prefix = abp.get_path_name() + ":"
    for o in unreal.ObjectIterator(unreal.EdGraphNode):
        p = o.get_path_name()
        if not p.startswith(prefix):
            continue
        graph = p[len(prefix):].rsplit(".", 1)[0]
        title = str(safe(lambda: o.get_node_title())).replace("\n", " ")[:60]
        extra = []
        try:
            node = o.get_editor_property("node")
            for k in ("blend_space", "sequence", "slot_name"):
                try:
                    extra.append("%s=%s" % (k, node.get_editor_property(k)))
                except Exception:
                    pass
        except Exception:
            pass
        pins = []
        try:
            for pin in o.list_all_pins():
                c = pin.list_connected_pins()
                v = safe(lambda: pin.get_pin_value())
                if c:
                    pins.append("%s->%s" % (pin.get_pin_name(), ",".join("%s.%s" % (x.get_owning_node().get_name(), x.get_pin_name()) for x in c)))
                elif v not in ("", "?", None) and not str(v).startswith("?("):
                    pins.append("%s=%s" % (pin.get_pin_name(), v))
        except Exception:
            pass
        w("[%s] %s | %s | %s | %s" % (graph, o.get_name(), title, " ".join(extra), " ".join(pins)[:600]))
except Exception:
    import traceback
    w("ERRO " + traceback.format_exc())
open(LOG, "w", encoding="utf-8").write("\n".join(out))
