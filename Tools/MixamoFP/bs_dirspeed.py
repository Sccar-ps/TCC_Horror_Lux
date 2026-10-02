# Etapa D2 (UE): BS_CB_Stand com as velocidades por direcao (lidas do BP_Player_Cowboy + fatores do BPC_DirectionalSpeed).
# Cada amostra fica na velocidade real daquela direcao e o rate scale = velocidade do jogo / velocidade medida do clipe
# (pes sem patinar). Rode de novo sempre que mudar MaxWalkSpeed/MaxSprintSpeed ou os fatores.
import os, json, unreal
EAL = unreal.EditorAssetLibrary
ANIM = "/Game/Characters/MixamoFP/Anims/"
BS = "/Game/Characters/MixamoFP/BlendSpaces/BS_CB_Stand"
COWBOY = "/Game/Characters/MixamoFP/Blueprints/BP_Player_Cowboy"
BPC = "/Game/Characters/MixamoFP/Blueprints/BPC_DirectionalSpeed"
saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
LOG = os.path.join(saved, "MixamoFP_bs_dirspeed.txt")
SPD = json.load(open(os.path.join(saved, "MixamoFP_speeds.json"), encoding="utf-8"))
NAT = {k: max(1.0, v["ground_speed"]) for k, v in SPD.items()}
NAT["A_CB_Run_F"] = 479.8
out = []


def w(m):
    out.append(str(m))


def sample(name, x, y, rate, ymax=None):
    s = unreal.BlendSample()
    s.set_editor_property("animation", EAL.load_asset(ANIM + name))
    # 02/10: o maximo do eixo Speed e gravado com round(); a posicao tem de ficar dentro dele (Run_F em 400,032 com eixo ate 400 = "amostra fora dos limites",
    # P14: o motor a invalida e a tira da triangulacao). Ver Tools/MixamoFP/corrige_carga_corpo.py.
    s.set_editor_property("sample_value", unreal.Vector(x, min(y, ymax) if ymax is not None else y, 0.0))
    s.set_editor_property("rate_scale", round(rate, 3))
    return s


try:
    cow = unreal.get_default_object(EAL.load_asset(COWBOY).generated_class())
    fac = unreal.get_default_object(EAL.load_asset(BPC).generated_class())
    walk, sprint = cow.get_editor_property("MaxWalkSpeed"), cow.get_editor_property("MaxSprintSpeed")
    fs, fw, sd, bk = (fac.get_editor_property(k) for k in ("ForwardSprintFactor", "ForwardWalkFactor", "SideFactor", "BackwardFactor"))
    WF, WS, WB = walk * fw, walk * sd, walk * bk
    RF, RS, RB = sprint * fs, sprint * sd, sprint * bk
    w("velocidades: andar F/L-R/T = %.0f/%.0f/%.0f | sprint F/L-R/T = %.0f/%.0f/%.0f" % (WF, WS, WB, RF, RS, RB))
    rows = [("A_CB_Idle", x, 0.0, 1.0) for x in (-180.0, -90.0, 0.0, 90.0, 180.0)]
    rows += [("A_CB_Walk_F", 0.0, WF, WF / NAT["A_CB_Walk_F"]),
             ("A_CB_Walk_B", 180.0, WB, WB / NAT["A_CB_Walk_B"]), ("A_CB_Walk_B", -180.0, WB, WB / NAT["A_CB_Walk_B"]),
             ("A_CB_Walk_L", -90.0, WS, WS / NAT["A_CB_Walk_L"]), ("A_CB_Walk_R", 90.0, WS, WS / NAT["A_CB_Walk_R"]),
             ("A_CB_Run_F", 0.0, RF, RF / NAT["A_CB_Run_F"]),
             ("A_CB_Walk_B", 180.0, RB, RB / NAT["A_CB_Walk_B"]), ("A_CB_Walk_B", -180.0, RB, RB / NAT["A_CB_Walk_B"]),
             ("A_CB_Run_L", -90.0, RS, RS / NAT["A_CB_Run_L"]), ("A_CB_Run_R", 90.0, RS, RS / NAT["A_CB_Run_R"])]
    bs = EAL.load_asset(BS)
    bs.modify()
    vmax = float(round(max(RF, RS, RB)))
    bs.set_editor_property("sample_data", [sample(*r, ymax=vmax) for r in rows])
    params = list(bs.get_editor_property("blend_parameters"))
    params[1].set_editor_property("max", vmax)
    bs.set_editor_property("blend_parameters", params)
    EAL.save_loaded_asset(bs, False)
    w("BS_CB_Stand: %s %.0f..%.0f | %s" % (params[1].get_editor_property("display_name"), params[1].get_editor_property("min"),
                                          params[1].get_editor_property("max"),
                                          [(r[0][5:], r[1], round(r[2]), round(r[3], 2)) for r in rows]))
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
            AES.open_editor_for_assets([EAL.load_asset(BS)])
            st["opened"] = True
            st["t"] = 0.0
        elif st["t"] > 0.6:
            st["done"] = True
            a = EAL.load_asset(BS)
            ok = EAL.save_loaded_asset(a, False)
            AES.close_all_editors_for_asset(a)
            with open(LOG, "a", encoding="utf-8") as fh:
                fh.write("\nBS_CB_Stand validado e salvo: %s" % ok)
            unreal.unregister_slate_post_tick_callback(st["h"])
    except Exception:
        import traceback
        st["done"] = True
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write("\nERRO validacao: " + traceback.format_exc())
        unreal.unregister_slate_post_tick_callback(st["h"])


st["h"] = unreal.register_slate_post_tick_callback(_tick)
