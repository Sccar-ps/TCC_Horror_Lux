# Etapa A1 (UE): bracos 1P com a corrida nova. O ABP dos bracos do FPMovement (ABP_Player) toca a animacao
# de corrida dos bracos so a 450 cm/s (BlendSpace 1D por Speed). Com o sprint mais lento os bracos ficavam
# numa mistura andar/correr e so a mao esquerda entrava na tela. Solucao sem mexer no FPMovement:
#   copias do ABP e dos dois BlendSpaces dos bracos em /Game/Characters/MixamoFP/Arms, com a amostra de corrida
#   em RUN_ARMS, e o FirstPersonMesh do BP_Player_Cowboy (componente herdado) passa a usar a copia.
import os, sys, unreal
EAL = unreal.EditorAssetLibrary
BEL = unreal.BlueprintEditorLibrary
RUN_ARMS = float(sys.argv[1]) if len(sys.argv) > 1 else 360.0
DST = "/Game/Characters/MixamoFP/Arms"
SRC_ABP = "/Game/FPMovement/Demo/Character/ABP_Player"
BS_MAP = {"/Game/FPMovement/Demo/Character/Animations/Unarmed/Blendspaces/BS_UnarmedMovement_V2": DST + "/BS_Arms_Unarmed",
          "/Game/FPMovement/Demo/Character/Animations/Flashlight/Blendspaces/BS_FlashlightMovement": DST + "/BS_Arms_Flashlight"}
ABP = DST + "/ABP_Arms_Cowboy"
BP = "/Game/Characters/MixamoFP/Blueprints/BP_Player_Cowboy"
saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
LOG = os.path.join(saved, "MixamoFP_arms_fix.txt")
out = []


def w(m):
    out.append(str(m))


try:
    if not EAL.does_directory_exist(DST):
        EAL.make_directory(DST)
    # ---- BlendSpaces 1D dos bracos: amostra de corrida 450 -> RUN_ARMS
    for src, dst in BS_MAP.items():
        if not EAL.does_asset_exist(dst):
            EAL.duplicate_asset(src, dst)
        bs = EAL.load_asset(dst)
        bs.modify()
        samples = list(bs.get_editor_property("sample_data"))
        top = max(s.get_editor_property("sample_value").x for s in samples)
        for s in samples:
            v = s.get_editor_property("sample_value")
            if abs(v.x - top) < 0.5:
                s.set_editor_property("sample_value", unreal.Vector(RUN_ARMS, v.y, v.z))
        bs.set_editor_property("sample_data", samples)
        EAL.save_loaded_asset(bs, False)
        w("%s: amostras %s" % (dst.rsplit("/", 1)[-1], [(round(s.get_editor_property("sample_value").x), s.get_editor_property("animation").get_name())
                                                         for s in bs.get_editor_property("sample_data")]))
    # ---- ABP dos bracos: copia apontando para os BlendSpaces copiados
    if not EAL.does_asset_exist(ABP):
        EAL.duplicate_asset(SRC_ABP, ABP)
    abp = EAL.load_asset(ABP)
    new_bs = {src.rsplit("/", 1)[-1]: EAL.load_asset(dst) for src, dst in BS_MAP.items()}
    prefix = abp.get_path_name() + ":"
    for o in unreal.ObjectIterator(unreal.AnimGraphNode_BlendSpacePlayer):
        if not o.get_path_name().startswith(prefix):
            continue
        node = o.get_editor_property("node")
        cur = node.get_editor_property("blend_space")
        if cur and cur.get_name() in new_bs:
            node.set_editor_property("blend_space", new_bs[cur.get_name()])
            o.set_editor_property("node", node)
            w("ABP: %s %s -> %s" % (o.get_name(), cur.get_name(), o.get_editor_property("node").get_editor_property("blend_space").get_name()))
    BEL.compile_blueprint(abp)
    EAL.save_loaded_asset(abp, False)
    # ---- FirstPersonMesh herdado no BP_Player_Cowboy -> ABP copiado (so no filho)
    bp = EAL.load_asset(BP)
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    w("get_object_for_blueprint existe: %s" % hasattr(lib, "get_object_for_blueprint"))
    for h in sds.k2_gather_subobject_data_for_blueprint(bp):
        d = lib.get_data(h)
        o = lib.get_object(d)
        if o and o.get_name().startswith("FirstPersonMesh"):
            t = lib.get_object_for_blueprint(d, bp) if hasattr(lib, "get_object_for_blueprint") else None
            w("FirstPersonMesh: template=%s | editavel no filho=%s" % (o.get_path_name(), t and t.get_path_name()))
            if t and "BP_Player_Cowboy" in t.get_path_name():
                t.set_editor_property("anim_class", abp.generated_class())
                w("  anim_class -> %s" % t.get_editor_property("anim_class").get_name())
            else:
                w("  NAO alterado por script (seria o template do BP_Player): trocar pela UI")
    BEL.compile_blueprint(bp)
    EAL.save_loaded_asset(bp, False)
except Exception:
    import traceback
    w("ERRO " + traceback.format_exc())
finally:
    open(LOG, "w", encoding="utf-8").write("\n".join(out))

# BlendSpaces editados por script: abrir o editor valida as amostras; depois salva e fecha
AES = unreal.get_editor_subsystem(unreal.AssetEditorSubsystem)
st = {"t": 0.0, "opened": False, "h": None}


def _tick(dt):
    try:
        st["t"] += dt
        if not st["opened"]:
            AES.open_editor_for_assets([EAL.load_asset(p) for p in BS_MAP.values()])
            st["opened"] = True
            st["t"] = 0.0
        elif st["t"] > 0.6:
            res = []
            for p in BS_MAP.values():
                a = EAL.load_asset(p)
                res.append(EAL.save_loaded_asset(a, False))
                AES.close_all_editors_for_asset(a)
            with open(LOG, "a", encoding="utf-8") as fh:
                fh.write("\nBlendSpaces dos bracos validados e salvos: %s" % res)
            unreal.unregister_slate_post_tick_callback(st["h"])
    except Exception:
        import traceback
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write("\nERRO validacao: " + traceback.format_exc())
        unreal.unregister_slate_post_tick_callback(st["h"])


st["h"] = unreal.register_slate_post_tick_callback(_tick)
