# Etapa A2 (UE): causa real das maos 1P. O SKM_Metahuman_Arms (FPMovement) tem o ABP_Player como
# "Post Process Anim Blueprint": com o ABP copiado como Anim Class, o ABP_Player original rodava DEPOIS dele e
# sobrescrevia a pose (e custava uma segunda avaliacao). Aqui, so no BP_Player_Cowboy:
#   - FirstPersonMesh (componente herdado) -> Disable Post Process Blueprint = True (a malha do pack nao muda)
#   - BlendSpaces copiados dos bracos: amostra de corrida em RUN_ARMS (menor velocidade de sprint entre as direcoes)
# Uso: py ".../arms_fix2.py" 280
import os, sys, unreal
EAL = unreal.EditorAssetLibrary
BEL = unreal.BlueprintEditorLibrary
RUN_ARMS = float(sys.argv[1]) if len(sys.argv) > 1 else 280.0
DST = "/Game/Characters/MixamoFP/Arms"
BS_LIST = (DST + "/BS_Arms_Unarmed", DST + "/BS_Arms_Flashlight")
BP = "/Game/Characters/MixamoFP/Blueprints/BP_Player_Cowboy"
saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
LOG = os.path.join(saved, "MixamoFP_arms_fix2.txt")
out = []


def w(m):
    out.append(str(m))


try:
    for p in BS_LIST:
        bs = EAL.load_asset(p)
        bs.modify()
        samples = list(bs.get_editor_property("sample_data"))
        top = max(s.get_editor_property("sample_value").x for s in samples)
        for s in samples:
            v = s.get_editor_property("sample_value")
            if abs(v.x - top) < 0.5:
                s.set_editor_property("sample_value", unreal.Vector(RUN_ARMS, v.y, v.z))
        bs.set_editor_property("sample_data", samples)
        EAL.save_loaded_asset(bs, False)
        w("%s: %s" % (p.rsplit("/", 1)[-1], [(round(s.get_editor_property("sample_value").x), s.get_editor_property("animation").get_name(),
                                              round(s.get_editor_property("rate_scale"), 2)) for s in bs.get_editor_property("sample_data")]))
    bp = EAL.load_asset(BP)
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    done = set()
    for h in sds.k2_gather_subobject_data_for_blueprint(bp):
        d = lib.get_data(h)
        o = lib.get_object(d)
        if not (o and o.get_name().startswith("FirstPersonMesh")):
            continue
        t = lib.get_object_for_blueprint(d, bp)
        if not t or "BP_Player_Cowboy" not in t.get_path_name() or t.get_path_name() in done:
            continue
        done.add(t.get_path_name())
        t.modify()
        t.set_editor_property("disable_post_process_blueprint", True)
        w("FirstPersonMesh (filho): anim_class=%s disable_post_process_blueprint=%s" % (
            t.get_editor_property("anim_class").get_name(), t.get_editor_property("disable_post_process_blueprint")))
    BEL.compile_blueprint(bp)
    EAL.save_loaded_asset(bp, False)
    w("BP_Player_Cowboy compilado e salvo")
except Exception:
    import traceback
    w("ERRO " + traceback.format_exc())
finally:
    open(LOG, "w", encoding="utf-8").write("\n".join(out))

AES = unreal.get_editor_subsystem(unreal.AssetEditorSubsystem)
st = {"t": 0.0, "opened": False, "done": False, "h": None}


def _tick(dt):
    if st["done"]:
        return
    try:
        st["t"] += dt
        if not st["opened"]:
            AES.open_editor_for_assets([EAL.load_asset(p) for p in BS_LIST])
            st["opened"] = True
            st["t"] = 0.0
        elif st["t"] > 0.6:
            st["done"] = True
            res = []
            for p in BS_LIST:
                a = EAL.load_asset(p)
                res.append(EAL.save_loaded_asset(a, False))
                AES.close_all_editors_for_asset(a)
            with open(LOG, "a", encoding="utf-8") as fh:
                fh.write("\nBlendSpaces dos bracos validados e salvos: %s" % res)
            unreal.unregister_slate_post_tick_callback(st["h"])
    except Exception:
        import traceback
        st["done"] = True
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write("\nERRO validacao: " + traceback.format_exc())
        unreal.unregister_slate_post_tick_callback(st["h"])


st["h"] = unreal.register_slate_post_tick_callback(_tick)
