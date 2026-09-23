# Etapa R1 (UE): prepara uma corrida para frente de verdade e sync markers de passo.
#  - duplica MM_Run_Fwd (demo do pacote do Cowboy, mesmo esqueleto) para A_CB_Run_F (o original nao muda)
#  - em TODOS os clipes do BS_CB_Stand cria markers "L"/"R" no meio do apoio de cada pe
#    (o BlendSpace so usa sync por markers se todos os clipes tiverem os mesmos markers)
import os, json, unreal
EAL = unreal.EditorAssetLibrary
AL = unreal.AnimationLibrary
ANIM = "/Game/Characters/MixamoFP/Anims/"
RUN_SRC = "/Game/Cowboy_character/Demo/Animations_Demo/MM_Run_Fwd"
TRACK = "Passos"
# clipe -> eixo de deslocamento no espaco do componente do Cowboy (+Y = frente, X = lateral)
CLIPS = {"A_CB_Walk_F": "y", "A_CB_Walk_B": "y", "A_CB_Walk_L": "x", "A_CB_Walk_R": "x",
         "A_CB_Run_L": "x", "A_CB_Run_R": "x", "A_CB_Run_F": "y"}
CH = {"L": ["root", "pelvis", "thigh_l", "calf_l", "foot_l"], "R": ["root", "pelvis", "thigh_r", "calf_r", "foot_r"]}
saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
LOG = os.path.join(saved, "MixamoFP_run_prepare.txt")
out = []


def w(m):
    out.append(str(m))


def comp(anim, chain, t):
    M = unreal.Transform()
    for b in chain:
        M = AL.get_bone_pose_for_time(anim, b, t, False).multiply(M)
    return M.translation


def clear_markers(anim):
    for fn, args in (("remove_all_animation_sync_markers", (anim,)), ("remove_animation_sync_markers_by_track", (anim, TRACK))):
        if hasattr(AL, fn):
            try:
                getattr(AL, fn)(*args)
            except Exception as e:
                w("  %s: %s" % (fn, str(e)[:80]))
    for name in ("L", "R"):
        try:
            AL.remove_animation_sync_markers_by_name(anim, name)
        except Exception:
            pass


def add_markers(anim, events):
    try:
        AL.add_animation_notify_track(anim, TRACK, unreal.LinearColor(0.2, 0.8, 0.3, 1.0))
    except Exception:
        pass
    for name, t in events:
        AL.add_animation_sync_marker(anim, name, t, TRACK)


def stance_events(anim, ax):
    """meio do apoio de cada pe: centro (no tempo) de cada intervalo em que o tornozelo fica perto do chao.
    Funciona igual para andar, correr, de costas e lateral; trata o apoio que atravessa o fim/inicio do loop."""
    L = anim.get_play_length()
    N = max(16, int(round(L * 120)))
    dt = L / N
    res = {}
    for side in ("L", "R"):
        z = [comp(anim, CH[side], i * dt).z for i in range(N)]      # [0, L): o ultimo frame repete o primeiro
        thr = min(z) + 3.0
        low = [v < thr for v in z]
        if all(low) or not any(low):
            res[side] = []
            continue
        start = low.index(False)
        ev, i = [], 0
        while i < N:
            if low[(start + i) % N]:
                j = i
                while j < N and low[(start + j) % N]:
                    j += 1
                if (j - i) * dt >= 0.05:                                # ignora cruzamentos de 1 frame (ruido)
                    mid = (start + i + (j - i - 1) / 2.0) % N
                    ev.append(round(mid * dt, 4))
                i = j
            else:
                i += 1
        res[side] = sorted(ev)
    return res


try:
    if not EAL.does_asset_exist(ANIM + "A_CB_Run_F"):
        EAL.duplicate_asset(RUN_SRC, ANIM + "A_CB_Run_F")
        w("A_CB_Run_F criado a partir de MM_Run_Fwd")
    w("funcoes de marker: %s" % [f for f in dir(AL) if "sync_marker" in f])
    report = {}
    for name, ax in CLIPS.items():
        anim = EAL.load_asset(ANIM + name)
        anim.set_editor_property("enable_root_motion", False)
        ev = stance_events(anim, ax)
        clear_markers(anim)
        pairs = sorted([("L", t) for t in ev["L"]] + [("R", t) for t in ev["R"]], key=lambda p: p[1])
        add_markers(anim, pairs)
        EAL.save_loaded_asset(anim, False)
        report[name] = dict(len=round(anim.get_play_length(), 3), markers=pairs)
        w("%-12s len=%.3f  %s" % (name, anim.get_play_length(), pairs))
    # Idle: pose parada, markers artificiais em 1/4 e 3/4 (so para o BlendSpace aceitar o sync por markers)
    idle = EAL.load_asset(ANIM + "A_CB_Idle")
    L = idle.get_play_length()
    clear_markers(idle)
    add_markers(idle, [("L", round(L * 0.25, 4)), ("R", round(L * 0.75, 4))])
    EAL.save_loaded_asset(idle, False)
    w("A_CB_Idle    len=%.3f  markers L=%.3f R=%.3f" % (L, L * 0.25, L * 0.75))
    json.dump(report, open(os.path.join(saved, "MixamoFP_run_markers.json"), "w"), indent=1)
except Exception:
    import traceback
    w("ERRO " + traceback.format_exc())
open(LOG, "w", encoding="utf-8").write("\n".join(out))
