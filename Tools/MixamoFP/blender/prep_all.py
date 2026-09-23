import sys, os, json, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Quaternion, Vector, Matrix
import mxlib as M

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prep")
os.makedirs(OUT, exist_ok=True)
FPS = 30.0
manifest = {}


def dur(f0, f1):
    return (f1 - f0) / FPS


def done(arm, name, f0, f1, **info):
    M.to_ue_space(arm)
    M.set_range(f0, f1)
    M.export_fbx(arm, os.path.join(OUT, name + ".fbx"))
    info.update(frames=f1 - f0 + 1, length_s=round(dur(f0, f1), 4))
    manifest[name] = info
    print("OK", name, info)


# ---------- poses de referencia (em pe e agachado) para o delta de coluna
arm, f0, f1 = M.load("Stop Walking")
bpy.context.scene.frame_set(f1)
stand = {n: M.pb(arm, n).matrix_basis.copy() for n in ("Spine", "Spine1", "Spine2", "Neck", "Head")}
stand_hips = M._rot(M.pb(arm, "Hips").matrix)
arm, f0, f1 = M.load("Crouch Idle")
bpy.context.scene.frame_set(f0)
crouch = {n: M.pb(arm, n).matrix_basis.copy() for n in stand}
crouch_hips = M._rot(M.pb(arm, "Hips").matrix)


def pitch_only(q):
    """mantem so a componente de rotacao em torno de X"""
    e = q.to_euler("XYZ")
    return Quaternion((1, 0, 0), e.x)


spine_extra = {n: pitch_only((stand[n].to_quaternion().inverted() @ crouch[n].to_quaternion())) for n in stand}
dh = crouch_hips @ stand_hips.inverted()
hips_pitch = pitch_only(dh.to_quaternion())
print("delta pelvis pitch %.1f graus | coluna %s" % (math.degrees(hips_pitch.angle) * (1 if hips_pitch.axis.x >= 0 else -1),
      {k: round(math.degrees(v.angle) * (1 if v.axis.x >= 0 else -1), 1) for k, v in spine_extra.items()}))

# ---------- Idle: pose final do Stop Walking, 4 s, respiracao sutil
arm, f0, f1 = M.load("Stop Walking")
g0, g1 = M.static_pose_clip(arm, f1, 121, breathe=True)
M.center_on_feet(arm, g0, g1)
done(arm, "MX_Idle", g0, g1, src="Stop Walking (pose final)", speed_mx=0.0, dir=0)

# ---------- loops em pe
LOOPS = [
    ("MX_Walk_F", "Walk With Briefcase", "z", 1.0, 0, True),
    ("MX_Walk_B", "Walking Backward", "z", 1.25, 180, False),
    ("MX_Walk_L", "Walk Strafe Left", "x", 1.25, -90, False),
    ("MX_Walk_R", "Walk Strafe Right", "x", 1.25, 90, False),
    ("MX_Run_L", "run Left Strafe", "x", 1.0, -90, False),
    ("MX_Run_R", "run Right Strafe", "x", 1.0, 90, False),
]
for name, src, axis, k, d, fix_arm in LOOPS:
    arm, f0, f1 = M.load(src)
    drift = M.in_place(arm, f0, f1)
    rep = {"miss_max": 0.0}
    if k != 1.0 and name == "MX_Walk_B":
        lo, hi, avg = M.hips_height_stats(arm, f0, f1)
        rep = M.crouchify(arm, f0, f1, avg - 3.0, k=k, axis=axis)
    elif k != 1.0:
        rep = M.stride_warp(arm, f0, f1, k, axis)
    if fix_arm:
        M.mirror_arm_from_left(arm, f0, f1, (f1 - f0) // 2)
    spd = abs(getattr(drift, axis)) / dur(f0, f1) * k
    done(arm, name, f0, f1, src=src, speed_mx=round(spd, 2), dir=d, stride_k=k, ik_miss_cm=round(rep["miss_max"], 2), briefcase_fix=fix_arm)

# ---------- agachado
arm, f0, f1 = M.load("Crouch Idle")
M.center_on_feet(arm, f0, f1)
done(arm, "MX_Crouch_Idle", f0, f1, src="Crouch Idle", speed_mx=0.0, dir=0)

CROUCH_TARGET = 62.0
for name, rev in (("MX_Crouch_F", False), ("MX_Crouch_B", True)):
    arm, f0, f1 = M.load("Crouched Walking")
    drift = M.in_place(arm, f0, f1)
    k = 0.6
    rep = M.crouchify(arm, f0, f1, CROUCH_TARGET, k=k, axis="z")
    if rev:
        M.reverse(arm, f0, f1)
    spd = abs(drift.z) / dur(f0, f1) * k
    done(arm, name, f0, f1, src="Crouched Walking" + (" (invertido)" if rev else ""), speed_mx=round(spd, 2), dir=180 if rev else 0,
         stride_k=k, ik_miss_cm=round(rep["miss_max"], 2), hips_drop=round(rep["drop"], 1))

for name, src, d in (("MX_Crouch_L", "Walk Strafe Left", -90), ("MX_Crouch_R", "Walk Strafe Right", 90)):
    arm, f0, f1 = M.load(src)
    drift = M.in_place(arm, f0, f1)
    k = 1.3
    rep = M.crouchify(arm, f0, f1, CROUCH_TARGET, hips_extra_rot=hips_pitch, spine_extra=spine_extra, k=k, axis="x", knee_hint=True)
    spd = abs(drift.x) / dur(f0, f1) * k
    done(arm, name, f0, f1, src=src + " (agachado sintetico)", speed_mx=round(spd, 2), dir=d, stride_k=k,
         ik_miss_cm=round(rep["miss_max"], 2), hips_drop=round(rep["drop"], 1))

# ---------- queda (placeholder): pose com joelhos dobrados do Crouched To Standing
arm, f0, f1 = M.load("Crouched To Standing")
fr = f0 + int(round((f1 - f0) * 0.5))
g0, g1 = M.static_pose_clip(arm, fr, 31, breathe=False)
M.center_on_feet(arm, g0, g1)
done(arm, "MX_Fall", g0, g1, src="Crouched To Standing (50%%)", speed_mx=0.0, dir=0, placeholder=True)

# ---------- proxy com malha (define o esqueleto no UE)
arm, f0, f1 = M.load("Walk With Briefcase")
arm.animation_data.action = None
for p in arm.pose.bones:
    p.matrix_basis = Matrix.Identity(4)
arm.data.pose_position = "REST"
M.to_ue_space(arm)
mesh = M.build_proxy_mesh(arm)
M.export_fbx(arm, os.path.join(OUT, "SKM_Mixamo_Proxy.fbx"), with_mesh=mesh)
print("OK proxy", len(mesh.data.vertices), "verts")

json.dump(manifest, open(os.path.join(OUT, "manifest.json"), "w"), indent=1, ensure_ascii=False)
print("MANIFEST", json.dumps(manifest, ensure_ascii=False))
