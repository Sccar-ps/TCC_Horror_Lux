# Somente leitura: posicoes (component space; +Y frente, +Z cima) de ossos-chave nas poses do Cowboy retargetadas.
import os, unreal
AL = unreal.AnimationLibrary
P = "/Game/Characters/MixamoFP/Anims/"
PARENT = {"pelvis": "root", "spine_01": "pelvis", "spine_02": "spine_01", "spine_03": "spine_02", "neck_01": "spine_03", "head": "neck_01",
          "clavicle_l": "spine_03", "upperarm_l": "clavicle_l", "thigh_l": "pelvis", "calf_l": "thigh_l", "foot_l": "calf_l", "ball_l": "foot_l",
          "thigh_r": "pelvis", "calf_r": "thigh_r", "foot_r": "calf_r"}
out = []


def chain(b):
    c = [b]
    while c[-1] in PARENT:
        c.append(PARENT[c[-1]])
    return list(reversed(c))


def pos(anim, b, t):
    M = unreal.Transform()
    for x in chain(b):
        M = AL.get_bone_pose_for_time(anim, x, t, False).multiply(M)
    return M.translation


for name, ts in (("A_CB_Idle", (0.0, 2.0)), ("A_CB_Walk_F", (0.0, 0.5)), ("A_CB_Crouch_Idle", (0.0, 0.8)), ("A_CB_Crouch_F", (0.0, 0.5)), ("A_CB_Crouch_L", (0.0, 0.7)), ("A_CB_Fall", (0.0,))):
    a = unreal.load_asset(P + name)
    for t in ts:
        row = []
        for b in ("pelvis", "spine_02", "spine_03", "neck_01", "head", "upperarm_l", "calf_l", "calf_r", "foot_l", "foot_r"):
            v = pos(a, b, t)
            row.append("%s=(%.0f,%.0f,%.0f)" % (b, v.x, v.y, v.z))
        out.append("%-17s t=%.1f  %s" % (name, t, " ".join(row)))
saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
open(os.path.join(saved, "MixamoFP_body.txt"), "w", encoding="utf-8").write("\n".join(out))
