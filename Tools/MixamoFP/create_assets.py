# Etapa 3 (UE): BlendSpaces com velocidades medidas, dois Anim Blueprints e o BP_Player_Cowboy (duas malhas).
import os, json, unreal
EAL = unreal.EditorAssetLibrary
BEL = unreal.BlueprintEditorLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()
ROOT = "/Game/Characters/MixamoFP"
P_ANIM = ROOT + "/Anims"
P_BS = ROOT + "/BlendSpaces"
P_BP = ROOT + "/Blueprints"
COWBOY = "/Game/Cowboy_character/Mesh/SM_SkeletalMesh_cowboy_character"
BP_PLAYER = "/Game/FPMovement/Player/Blueprints/BP_Player"
BP_GM = "/Game/FPMovement/Player/Blueprints/BP_PlayerMode"
saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
SPD = json.load(open(os.path.join(saved, "MixamoFP_speeds.json"), encoding="utf-8"))
LOG = os.path.join(saved, "MixamoFP_assets.txt")
out = []
WALK, SPRINT, CROUCH = 150.0, 450.0, 80.0


def w(m):
    out.append(str(m))
    unreal.log("[MixamoFP] " + str(m))


def ensure_dir(p):
    if not EAL.does_directory_exist(p):
        EAL.make_directory(p)


def create(name, path, cls, factory):
    full = path + "/" + name
    if EAL.does_asset_exist(full):
        return EAL.load_asset(full), False
    return AT.create_asset(name, path, cls, factory), True


def anim(n):
    return EAL.load_asset(P_ANIM + "/A_CB_" + n)


def nat(n):
    return max(1.0, SPD["A_CB_" + n]["ground_speed"])


def param(display, vmin, vmax, grid, wrap):
    p = unreal.BlendParameter()
    for k, v in (("display_name", display), ("min", vmin), ("max", vmax), ("grid_num", grid), ("snap_to_grid", False), ("wrap_input", wrap)):
        p.set_editor_property(k, v)
    return p


def sample(n, x, y, rate):
    s = unreal.BlendSample()
    s.set_editor_property("animation", anim(n))
    s.set_editor_property("sample_value", unreal.Vector(x, y, 0.0))
    s.set_editor_property("rate_scale", round(rate, 3))
    return s


def make_bs(name, skel, ymax, rows):
    f = unreal.BlendSpaceFactoryNew()
    f.set_editor_property("target_skeleton", skel)
    bs, created = create(name, P_BS, unreal.BlendSpace, f)
    bs.modify()
    bs.set_editor_property("sample_data", [sample(*r) for r in rows])
    params = list(bs.get_editor_property("blend_parameters"))
    params[0] = param("Direction", -180.0, 180.0, 8, True)
    params[1] = param("Speed", 0.0, ymax, 4, False)
    bs.set_editor_property("blend_parameters", params)
    try:
        ip = list(bs.get_editor_property("interpolation_param"))
        ip[0].set_editor_property("interpolation_time", 0.15)
        ip[1].set_editor_property("interpolation_time", 0.10)
        bs.set_editor_property("interpolation_param", ip)
    except Exception as e:
        w("interp %s" % e)
    w("%s: %s" % (name, [(r[0], r[1], r[2], round(r[3], 2)) for r in rows]))
    return bs


def type_of(kind, cls=None):
    if kind == "real":
        return BEL.get_basic_type_by_name("real")
    if kind == "bool":
        return BEL.get_basic_type_by_name("bool")
    if kind == "vector":
        return BEL.get_struct_type(unreal.Vector.static_struct())
    return BEL.get_object_reference_type(cls)


def make_abp(name, skel, mesh, variables, player_cls):
    f = unreal.AnimBlueprintFactory()
    f.set_editor_property("target_skeleton", skel)
    f.set_editor_property("parent_class", unreal.AnimInstance)
    f.set_editor_property("preview_skeletal_mesh", mesh)
    abp, created = create(name, P_BP, unreal.AnimBlueprint, f)
    have = set(str(n) for n in BEL.list_member_variable_names(abp))
    for vname, kind in variables:
        if vname not in have:
            BEL.add_member_variable(abp, vname, type_of(kind, player_cls))
    BEL.compile_blueprint(abp)
    EAL.save_loaded_asset(abp, False)
    w("%s variaveis: %s" % (name, [str(n) for n in BEL.list_member_variable_names(abp)]))
    return abp


PENDING = []

try:
    for p in (ROOT, P_BS, P_BP):
        ensure_dir(p)
    cowboy = EAL.load_asset(COWBOY)
    skel = cowboy.get_editor_property("skeleton")
    # ---------------- BlendSpaces (amostras na velocidade do jogo; rate = alvo / velocidade natural medida)
    stand = [("Idle", x, 0.0, 1.0) for x in (-180.0, -90.0, 0.0, 90.0, 180.0)]
    stand += [("Walk_F", 0.0, WALK, WALK / nat("Walk_F")),
              ("Walk_B", 180.0, WALK, WALK / nat("Walk_B")), ("Walk_B", -180.0, WALK, WALK / nat("Walk_B")),
              ("Walk_L", -90.0, WALK, WALK / nat("Walk_L")), ("Walk_R", 90.0, WALK, WALK / nat("Walk_R")),
              ("Walk_F", 0.0, SPRINT, SPRINT / nat("Walk_F")),                       # placeholder de corrida p/ frente
              ("Walk_B", 180.0, SPRINT, SPRINT / nat("Walk_B")), ("Walk_B", -180.0, SPRINT, SPRINT / nat("Walk_B")),
              ("Run_L", -90.0, SPRINT, SPRINT / nat("Run_L")), ("Run_R", 90.0, SPRINT, SPRINT / nat("Run_R"))]
    crouch = [("Crouch_Idle", x, 0.0, 1.0) for x in (-180.0, -90.0, 0.0, 90.0, 180.0)]
    crouch += [("Crouch_F", 0.0, CROUCH, CROUCH / nat("Crouch_F")),
               ("Crouch_B", 180.0, CROUCH, CROUCH / nat("Crouch_B")), ("Crouch_B", -180.0, CROUCH, CROUCH / nat("Crouch_B")),
               ("Crouch_L", -90.0, CROUCH, CROUCH / nat("Crouch_L")), ("Crouch_R", 90.0, CROUCH, CROUCH / nat("Crouch_R"))]
    bs1 = make_bs("BS_CB_Stand", skel, SPRINT, stand)
    bs2 = make_bs("BS_CB_Crouch", skel, CROUCH, crouch)
    for b in (bs1, bs2):
        EAL.save_loaded_asset(b, False)
        PENDING.append(b.get_path_name())

    # ---------------- Anim Blueprints
    player_bp = EAL.load_asset(BP_PLAYER)
    player_cls = player_bp.generated_class()
    abp = make_abp("ABP_CowboyFP", skel, cowboy, [("Player", "player"), ("Speed", "real"), ("Direction", "real"), ("CrouchAlpha", "real"),
                                                  ("InAirAlpha", "real"), ("StandingHalfHeight", "real"), ("CrouchedHalfHeight", "real"),
                                                  ("BackOffsetStand", "real"), ("BackOffsetCrouch", "real"), ("RootOffset", "vector")], player_cls)
    cdo = unreal.get_default_object(abp.generated_class())
    cdo.set_editor_property("root_motion_mode", unreal.RootMotionMode.IGNORE_ROOT_MOTION)
    for k, v in (("StandingHalfHeight", 96.0), ("CrouchedHalfHeight", 40.0), ("BackOffsetStand", 4.0), ("BackOffsetCrouch", 30.0)):
        try:
            cdo.set_editor_property(k, v)
        except Exception as e:
            w("default %s: %s" % (k, e))
    EAL.save_loaded_asset(abp, False)
    abp_vis = make_abp("ABP_CowboyFP_Visible", skel, cowboy, [], player_cls)

    # ---------------- Character
    full = P_BP + "/BP_Player_Cowboy"
    bp = EAL.load_asset(full) if EAL.does_asset_exist(full) else BEL.create_blueprint_asset_with_parent(full, player_cls)
    BEL.compile_blueprint(bp)
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    handles = sds.k2_gather_subobject_data_for_blueprint(bp)
    mesh_h, vis_h = None, None
    for h in handles:
        o = unreal.SubobjectDataBlueprintFunctionLibrary.get_object(unreal.SubobjectDataBlueprintFunctionLibrary.get_data(h))
        if o and o.get_name().startswith("CharacterMesh0"):
            mesh_h = h
        if o and o.get_name().startswith("BodyVisible"):
            vis_h = h
    if vis_h is None and mesh_h is not None:
        params = unreal.AddNewSubobjectParams(parent_handle=mesh_h, new_class=unreal.SkeletalMeshComponent, blueprint_context=bp)
        vis_h, reason = sds.add_new_subobject(params)
        sds.rename_subobject(vis_h, unreal.Text("BodyVisible"))
        w("BodyVisible criado (%s)" % reason)
    BEL.compile_blueprint(bp)

    def cfg():
        cdo_bp = unreal.get_default_object(bp.generated_class())
        m = cdo_bp.get_editor_property("mesh")
        m.set_skeletal_mesh_asset(cowboy)
        for k, v in (("animation_mode", unreal.AnimationMode.ANIMATION_BLUEPRINT), ("anim_class", abp.generated_class()),
                     ("relative_location", unreal.Vector(0.0, 0.0, -96.0)), ("relative_rotation", unreal.Rotator(roll=0.0, pitch=0.0, yaw=-90.0)),
                     ("cast_shadow", True), ("render_in_main_pass", False), ("render_in_depth_pass", False),
                     ("visibility_based_anim_tick_option", unreal.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE_AND_REFRESH_BONES),
                     ("receives_decals", False)):
            try:
                m.set_editor_property(k, v)
            except Exception as e:
                w("Mesh.%s: %s" % (k, e))
        m.set_collision_profile_name("NoCollision")
        vis = unreal.SubobjectDataBlueprintFunctionLibrary.get_object(unreal.SubobjectDataBlueprintFunctionLibrary.get_data(vis_h))
        vis.set_skeletal_mesh_asset(cowboy)
        for k, v in (("animation_mode", unreal.AnimationMode.ANIMATION_BLUEPRINT), ("anim_class", abp_vis.generated_class()),
                     ("cast_shadow", False), ("visibility_based_anim_tick_option", unreal.VisibilityBasedAnimTickOption.ONLY_TICK_POSE_WHEN_RENDERED),
                     ("receives_decals", False), ("relative_location", unreal.Vector(0, 0, 0)), ("relative_rotation", unreal.Rotator(0, 0, 0))):
            try:
                vis.set_editor_property(k, v)
            except Exception as e:
                w("BodyVisible.%s: %s" % (k, e))
        vis.set_collision_profile_name("NoCollision")
        return m, vis
    m, vis = cfg()
    EAL.save_loaded_asset(bp, False)
    BEL.compile_blueprint(bp)
    m, vis = cfg()          # compile pode resetar valores do template; reaplica
    EAL.save_loaded_asset(bp, False)
    w("BP_Player_Cowboy: Mesh(sombra)=%s anim=%s mainpass=%s | BodyVisible anim=%s shadow=%s" % (
        m.get_skeletal_mesh_asset().get_name(), m.get_editor_property("anim_class").get_name(), m.get_editor_property("render_in_main_pass"),
        vis.get_editor_property("anim_class").get_name(), vis.get_editor_property("cast_shadow")))

    # ---------------- GameMode
    gm = EAL.load_asset(BP_GM)
    gcdo = unreal.get_default_object(gm.generated_class())
    old = gcdo.get_editor_property("default_pawn_class")
    gcdo.set_editor_property("default_pawn_class", bp.generated_class())
    EAL.save_loaded_asset(gm, False)
    w("BP_PlayerMode.DefaultPawnClass: %s -> BP_Player_Cowboy" % (old.get_name() if old else None))
except Exception:
    import traceback
    w("ERRO: " + traceback.format_exc())
finally:
    open(LOG, "w", encoding="utf-8").write("\n".join(out))

# validacao dos BlendSpaces (abre o editor alguns frames depois, salva e fecha)
if PENDING:
    AES = unreal.get_editor_subsystem(unreal.AssetEditorSubsystem)
    st = {"t": 0.0, "opened": False, "h": None}

    def _tick(dt):
        try:
            st["t"] += dt
            if not st["opened"]:
                AES.open_editor_for_assets([EAL.load_asset(p) for p in PENDING])
                st["opened"] = True
                st["t"] = 0.0
            elif st["t"] > 0.6:
                res = []
                for p in PENDING:
                    a = EAL.load_asset(p)
                    res.append(EAL.save_loaded_asset(a, False))
                    AES.close_all_editors_for_asset(a)
                with open(LOG, "a", encoding="utf-8") as fh:
                    fh.write("\nBlendSpaces validados e salvos: %s" % res)
                unreal.unregister_slate_post_tick_callback(st["h"])
        except Exception:
            import traceback
            with open(LOG, "a", encoding="utf-8") as fh:
                fh.write("\nERRO validacao: " + traceback.format_exc())
            unreal.unregister_slate_post_tick_callback(st["h"])
    st["h"] = unreal.register_slate_post_tick_callback(_tick)
