# Somente leitura: API de edicao de grafos (UE 5.8) + propriedade de post-process do FirstPersonMesh no BP_Player_Cowboy.
import os, inspect, unreal
saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
LOG = os.path.join(saved, "MixamoFP_probe_api2.txt")
out = []
for cname in ("BlueprintGraphEditor", "BlueprintGraphPin", "BlueprintGraphPinLibrary"):
    c = getattr(unreal, cname, None)
    if not c:
        out.append("%s ausente" % cname)
        continue
    out.append("== %s (%s)" % (cname, c.__mro__[1].__name__ if hasattr(c, "__mro__") else "?"))
    for n in sorted(dir(c)):
        if n.startswith("_") or n in dir(unreal.Object):
            continue
        doc = (getattr(c, n).__doc__ or "").strip().split("\n")
        out.append("  %s :: %s" % (n, " | ".join(x.strip() for x in doc[:6])[:420]))
# post-process no componente herdado (template do filho)
try:
    bp = unreal.load_asset("/Game/Characters/MixamoFP/Blueprints/BP_Player_Cowboy")
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    seen = set()
    for h in sds.k2_gather_subobject_data_for_blueprint(bp):
        d = lib.get_data(h)
        o = lib.get_object(d)
        if o and o.get_name().startswith("FirstPersonMesh"):
            t = lib.get_object_for_blueprint(d, bp)
            if t.get_path_name() in seen:
                continue
            seen.add(t.get_path_name())
            props = [p for p in dir(t) if "post" in p.lower()]
            out.append("template %s: anim_class=%s props_post=%s" % (t.get_path_name(), t.get_editor_property("anim_class").get_name(), props))
            for p in ("disable_post_process_blueprint",):
                try:
                    out.append("  %s = %s" % (p, t.get_editor_property(p)))
                except Exception as e:
                    out.append("  %s: %s" % (p, e))
except Exception:
    import traceback
    out.append("ERRO " + traceback.format_exc())
open(LOG, "w", encoding="utf-8").write("\n".join(str(x) for x in out))
