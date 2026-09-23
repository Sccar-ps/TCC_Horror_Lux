# Etapa R2 (UE): nova velocidade de corrida. Uso no console:  py ".../run_apply.py" 360
#  - BP_Player_Cowboy: sobrescreve o MaxSprintSpeed herdado do BP_Player (o BP_Player nao muda)
#  - BS_CB_Stand: linha de corrida na nova velocidade, com A_CB_Run_F (corrida real) para frente
#    e rate scale = velocidade do jogo / velocidade medida de cada clipe (pes sem patinar)
import os, sys, json, unreal
EAL = unreal.EditorAssetLibrary
BEL = unreal.BlueprintEditorLibrary
SPRINT = float(sys.argv[1]) if len(sys.argv) > 1 else 360.0
WALK = 150.0
ANIM = "/Game/Characters/MixamoFP/Anims/"
BS = "/Game/Characters/MixamoFP/BlendSpaces/BS_CB_Stand"
BP = "/Game/Characters/MixamoFP/Blueprints/BP_Player_Cowboy"
saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
LOG = os.path.join(saved, "MixamoFP_run_apply.txt")
SPD = json.load(open(os.path.join(saved, "MixamoFP_speeds.json"), encoding="utf-8"))
NAT = {k: max(1.0, v["ground_speed"]) for k, v in SPD.items()}
NAT["A_CB_Run_F"] = 479.8          # medido por measure_run.py (contato do pe, clipe in place)
out = []


def w(m):
    out.append(str(m))


def sample(name, x, y, rate):
    s = unreal.BlendSample()
    s.set_editor_property("animation", EAL.load_asset(ANIM + name))
    s.set_editor_property("sample_value", unreal.Vector(x, y, 0.0))
    s.set_editor_property("rate_scale", round(rate, 3))
    return s


try:
    rows = [("A_CB_Idle", x, 0.0, 1.0) for x in (-180.0, -90.0, 0.0, 90.0, 180.0)]
    rows += [("A_CB_Walk_F", 0.0, WALK, WALK / NAT["A_CB_Walk_F"]),
             ("A_CB_Walk_B", 180.0, WALK, WALK / NAT["A_CB_Walk_B"]), ("A_CB_Walk_B", -180.0, WALK, WALK / NAT["A_CB_Walk_B"]),
             ("A_CB_Walk_L", -90.0, WALK, WALK / NAT["A_CB_Walk_L"]), ("A_CB_Walk_R", 90.0, WALK, WALK / NAT["A_CB_Walk_R"]),
             ("A_CB_Run_F", 0.0, SPRINT, SPRINT / NAT["A_CB_Run_F"]),
             ("A_CB_Walk_B", 180.0, SPRINT, SPRINT / NAT["A_CB_Walk_B"]), ("A_CB_Walk_B", -180.0, SPRINT, SPRINT / NAT["A_CB_Walk_B"]),
             ("A_CB_Run_L", -90.0, SPRINT, SPRINT / NAT["A_CB_Run_L"]), ("A_CB_Run_R", 90.0, SPRINT, SPRINT / NAT["A_CB_Run_R"])]
    bs = EAL.load_asset(BS)
    bs.modify()
    bs.set_editor_property("sample_data", [sample(*r) for r in rows])
    params = list(bs.get_editor_property("blend_parameters"))
    params[1].set_editor_property("max", SPRINT)
    bs.set_editor_property("blend_parameters", params)
    EAL.save_loaded_asset(bs, False)
    w("BS_CB_Stand: Speed 0..%.0f | %s" % (SPRINT, [(r[0][5:], r[1], r[2], round(r[3], 2)) for r in rows]))

    bp = EAL.load_asset(BP)
    cdo = unreal.get_default_object(bp.generated_class())
    old = cdo.get_editor_property("MaxSprintSpeed")
    cdo.set_editor_property("MaxSprintSpeed", SPRINT)
    BEL.compile_blueprint(bp)
    cdo = unreal.get_default_object(bp.generated_class())
    if abs(cdo.get_editor_property("MaxSprintSpeed") - SPRINT) > 0.01:        # o compile pode restaurar o template
        cdo.set_editor_property("MaxSprintSpeed", SPRINT)
    EAL.save_loaded_asset(bp, False)
    w("BP_Player_Cowboy.MaxSprintSpeed: %s -> %s (BP_Player continua com o valor original)" % (old, cdo.get_editor_property("MaxSprintSpeed")))
except Exception:
    import traceback
    w("ERRO " + traceback.format_exc())
finally:
    open(LOG, "w", encoding="utf-8").write("\n".join(out))

# amostras de BlendSpace criadas por script so ficam validas depois que o editor do asset abre: abre, salva e fecha
AES = unreal.get_editor_subsystem(unreal.AssetEditorSubsystem)
st = {"t": 0.0, "opened": False, "h": None}


def _tick(dt):
    try:
        st["t"] += dt
        if not st["opened"]:
            AES.open_editor_for_assets([EAL.load_asset(BS)])
            st["opened"] = True
            st["t"] = 0.0
        elif st["t"] > 0.6:
            a = EAL.load_asset(BS)
            ok = EAL.save_loaded_asset(a, False)
            AES.close_all_editors_for_asset(a)
            with open(LOG, "a", encoding="utf-8") as fh:
                fh.write("\nBS_CB_Stand validado e salvo: %s" % ok)
            unreal.unregister_slate_post_tick_callback(st["h"])
    except Exception:
        import traceback
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write("\nERRO validacao: " + traceback.format_exc())
        unreal.unregister_slate_post_tick_callback(st["h"])


st["h"] = unreal.register_slate_post_tick_callback(_tick)
