# Somente leitura: mede velocidade no chao das corridas disponiveis no esqueleto do Cowboy e le o
# SetPlayRate dos passos (Footsteps_TL) do sprint no BP_Player, para escolher a nova velocidade de corrida.
import os, unreal
saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
LOG = os.path.join(saved, "MixamoFP_measure_run.txt")
out = []
CH = {"l": ["root", "pelvis", "thigh_l", "calf_l", "foot_l"], "r": ["root", "pelvis", "thigh_r", "calf_r", "foot_r"]}
ANIMS = ["/Game/Cowboy_character/Demo/Animations_Demo/MM_Run_Fwd", "/Game/Cowboy_character/Demo/Animations_Demo/MM_Walk_Fwd",
         "/Game/Cowboy_character/Demo/Animations_Demo/MM_Walk_InPlace", "/Game/Characters/MixamoFP/Anims/A_CB_Walk_F",
         "/Game/Characters/MixamoFP/Anims/A_CB_Run_L"]


def w(m):
    out.append(str(m))


def comp_pos(anim, chain, t):
    M = unreal.Transform()
    for b in chain:
        M = unreal.AnimationLibrary.get_bone_pose_for_time(anim, b, t, False).multiply(M)
    return M.translation


try:
    for p in ANIMS:
        anim = unreal.load_asset(p)
        if anim is None:
            w("%s: nao existe" % p)
            continue
        L = anim.get_play_length()
        N = max(2, int(round(L * 60)))
        ts = [L * i / N for i in range(N + 1)]
        root0 = comp_pos(anim, ["root"], 0.0)
        root1 = comp_pos(anim, ["root"], L)
        feet = {s: [comp_pos(anim, CH[s], t) for t in ts] for s in ("l", "r")}
        minz = {s: min(q.z for q in feet[s]) for s in feet}
        best = {}
        for ax in ("x", "y"):
            sp = []
            for s in ("l", "r"):
                pts = [(ts[i], getattr(feet[s][i], ax)) for i in range(len(ts)) if feet[s][i].z < minz[s] + 2.0]
                for i in range(1, len(pts)):
                    dt = pts[i][0] - pts[i - 1][0]
                    if 0 < dt < 0.03:
                        sp.append(abs(pts[i][1] - pts[i - 1][1]) / dt)
            sp.sort()
            best[ax] = round(sp[len(sp) // 2], 1) if sp else 0.0
        d = root1 - root0
        w("%-16s len=%.3f s  root_motion=%s  desloc_root=(%.1f, %.1f, %.1f) -> %.1f cm/s  contato_pe x=%s y=%s  ankle_min=(%.1f, %.1f)" % (
            p.rsplit("/", 1)[-1], L, anim.get_editor_property("enable_root_motion"), d.x, d.y, d.z,
            (d.x ** 2 + d.y ** 2) ** 0.5 / L, best["x"], best["y"], minz["l"], minz["r"]))
    # SetPlayRate do Footsteps_TL no BP_Player
    prefix = "/Game/FPMovement/Player/Blueprints/BP_Player.BP_Player:"
    unreal.load_asset("/Game/FPMovement/Player/Blueprints/BP_Player")
    for o in unreal.ObjectIterator(unreal.K2Node):
        pth = o.get_path_name()
        if pth.startswith(prefix) and "SetPlayRate" in str(o.get_node_title()).replace(" ", ""):
            vals = []
            for pin in o.list_input_pins():
                try:
                    v = pin.get_pin_value()
                except Exception as e:
                    v = "?%s" % str(e)[:40]
                vals.append("%s=%s%s" % (pin.get_pin_name(), v, "(ligado)" if pin.list_connected_pins() else ""))
            w("SetPlayRate %s: %s" % (o.get_name(), vals))
except Exception:
    import traceback
    w("ERRO " + traceback.format_exc())
open(LOG, "w", encoding="utf-8").write("\n".join(out))
