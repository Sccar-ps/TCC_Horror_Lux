"""Ferramentas Blender para preparar animacoes Mixamo para o UE (in-place, stride warp offline, agachamento sintetico)."""
import bpy, math, os
from mathutils import Vector, Matrix, Quaternion

# Pasta com os FBX brutos do Mixamo. Padrao: <Projeto>/Content/AnimationAdobe (este arquivo fica em <Projeto>/Tools/MixamoFP/blender)
SRC = os.environ.get("MIXAMO_SRC", os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "Content", "AnimationAdobe")))
P = "mixamorig:"
LEG = {"Left": ("LeftUpLeg", "LeftLeg", "LeftFoot", "LeftToeBase"), "Right": ("RightUpLeg", "RightLeg", "RightFoot", "RightToeBase")}


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.fps = 30
    sc.render.fps_base = 1.0
    # 1 unidade Blender = 1 cm: o FBX do Mixamo (cm) entra sem escala e sai com UnitScaleFactor 1
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 0.01


def load(fname):
    reset()
    bpy.ops.import_scene.fbx(filepath=os.path.join(SRC, fname + ".fbx"), automatic_bone_orientation=False,
                             ignore_leaf_bones=False, use_anim=True, anim_offset=0.0)
    arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    arm.name = "Armature"
    act = arm.animation_data.action
    f0, f1 = [int(round(x)) for x in act.frame_range]
    set_range(f0, f1)
    return arm, f0, f1


def set_range(f0, f1):
    sc = bpy.context.scene
    sc.frame_start, sc.frame_end = f0, f1


def pb(arm, name):
    return arm.pose.bones[P + name]


def frames(f0, f1):
    return list(range(f0, f1 + 1))


def record(arm, names, f0, f1):
    """matrizes em espaco de armature (Y-up, cm, Z frente, X esquerda) por frame"""
    out = {n: [] for n in names}
    sc = bpy.context.scene
    for f in frames(f0, f1):
        sc.frame_set(f)
        for n in names:
            out[n].append(pb(arm, n).matrix.copy())
    return out


def set_hips(arm, f0, f1, fn):
    """fn(i, f, Matrix) -> Matrix (espaco de armature) para o Hips; grava keys de loc/rot"""
    sc = bpy.context.scene
    h = pb(arm, "Hips")
    mats = []
    for i, f in enumerate(frames(f0, f1)):
        sc.frame_set(f)
        mats.append(fn(i, f, h.matrix.copy()))
    for i, f in enumerate(frames(f0, f1)):
        sc.frame_set(f)
        h.matrix = mats[i]
        h.keyframe_insert("location", frame=f)
        h.keyframe_insert("rotation_quaternion" if h.rotation_mode == "QUATERNION" else "rotation_euler", frame=f)


def in_place(arm, f0, f1, center=None):
    """remove a deriva horizontal (X,Z) linear do Hips entre o primeiro e o ultimo frame; center = (x,z) extra"""
    rec = record(arm, ["Hips"], f0, f1)["Hips"]
    p0, p1 = rec[0].translation.copy(), rec[-1].translation.copy()
    n = max(1, f1 - f0)
    cx, cz = center if center else (0.0, 0.0)

    def fn(i, f, M):
        a = i / n
        d = p0 + (p1 - p0) * a
        M = M.copy()
        t = M.translation.copy()
        t.x -= d.x + cx
        t.z -= d.z + cz
        M.translation = t
        return M
    set_hips(arm, f0, f1, fn)
    return (p1 - p0)


def reverse(arm, f0, f1):
    """inverte o tempo de todas as fcurves"""
    act = arm.animation_data.action
    for fc in fcurves_of(act):
        pts = [(kp.co[0], kp.co[1]) for kp in fc.keyframe_points]
        for kp, (t, v) in zip(fc.keyframe_points, reversed(pts)):
            kp.co[1] = v
            kp.handle_left_type = kp.handle_right_type = "AUTO_CLAMPED"
        fc.update()


def fcurves_of(act):
    """compativel com actions em camadas (Blender 4.4+/5.x) e legadas"""
    try:
        return list(act.fcurves)
    except Exception:
        pass
    out = []
    for layer in act.layers:
        for strip in layer.strips:
            for cb in strip.channelbags:
                out.extend(cb.fcurves)
    return out


def ensure_pose_mode(arm):
    bpy.context.view_layer.objects.active = arm
    for o in bpy.context.view_layer.objects:
        o.select_set(o == arm)
    if arm.mode != "POSE":
        bpy.ops.object.mode_set(mode="POSE")


def object_mode():
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")


def make_empty(name):
    e = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(e)
    e.rotation_mode = "QUATERNION"
    return e


def key_empty(e, f, Mw):
    loc, rot, _ = Mw.decompose()
    e.location = loc
    e.rotation_quaternion = rot
    e.keyframe_insert("location", frame=f)
    e.keyframe_insert("rotation_quaternion", frame=f)


def solve_legs(arm, f0, f1, foot_targets, knee_poles, pole_angle_deg):
    """IK nas pernas (UpLeg+Leg) levando a cabeca do Foot ao alvo; Copy Rotation mantem a orientacao do pe.
    foot_targets/knee_poles: {'Left': [Matrix/Vector em espaco de armature por frame]}; depois faz bake visual."""
    W = arm.matrix_world
    empties = []
    for side in ("Left", "Right"):
        et = make_empty("IKT_" + side)
        ep = make_empty("IKP_" + side)
        empties += [et, ep]
        for i, f in enumerate(frames(f0, f1)):
            key_empty(et, f, W @ foot_targets[side][i])
            key_empty(ep, f, Matrix.Translation(W @ knee_poles[side][i]))
        foot = pb(arm, LEG[side][2])
        leg = pb(arm, LEG[side][1])
        ik = leg.constraints.new("IK")
        ik.target = et
        ik.pole_target = ep
        ik.pole_angle = math.radians(pole_angle_deg)
        ik.chain_count = 2
        ik.use_tail = True
        ik.use_stretch = False
        cr = foot.constraints.new("COPY_ROTATION")
        cr.target = et
        cr.target_space = "WORLD"
        cr.owner_space = "WORLD"
    ensure_pose_mode(arm)
    bpy.ops.pose.select_all(action="SELECT")
    bpy.ops.nla.bake(frame_start=f0, frame_end=f1, only_selected=False, visual_keying=True, clear_constraints=True,
                     use_current_action=True, bake_types={"POSE"})
    object_mode()
    for e in empties:
        bpy.data.objects.remove(e, do_unlink=True)


def knee_pole(hip, knee, ankle, dist=40.0):
    """ponto a frente do joelho, no plano quadril-joelho-tornozelo"""
    axis = (ankle - hip)
    if axis.length < 1e-6:
        return knee + Vector((0, 0, dist))
    axis.normalize()
    v = knee - hip
    perp = v - axis * v.dot(axis)
    if perp.length < 1e-4:
        perp = Vector((0, 0, 1))
    return knee + perp.normalized() * dist


def leg_state(arm, f0, f1):
    names = ["Hips"] + [b for s in LEG.values() for b in s]
    return record(arm, names, f0, f1)


def export_fbx(arm, path, with_mesh=None):
    object_mode()
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    arm.select_set(True)
    if with_mesh:
        with_mesh.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, object_types={"ARMATURE", "MESH"}, add_leaf_bones=False,
                             primary_bone_axis="Y", secondary_bone_axis="X", armature_nodetype="NULL",
                             bake_anim=with_mesh is None, bake_anim_use_all_bones=True, bake_anim_use_nla_strips=False,
                             bake_anim_use_all_actions=False, bake_anim_force_startend_keying=True, bake_anim_step=1.0,
                             bake_anim_simplify_factor=0.0, axis_forward="-Z", axis_up="Y", apply_unit_scale=True,
                             apply_scale_options="FBX_SCALE_NONE", global_scale=1.0, mesh_smooth_type="FACE",
                             use_armature_deform_only=False)


# ----------------------------------------------------------------- IK analitico (2 ossos) + escrita direta das bases
def _rot(M):
    return M.to_3x3().normalized()


def _mat(R3, t):
    M = R3.to_4x4()
    M.translation = t
    return M


def basis_for(pbone, desired, parent_pose):
    """matrix_basis que produz 'desired' (espaco de armature) dado o pose matrix NOVO do pai"""
    b = pbone.bone
    if b.parent is None:
        return b.matrix_local.inverted() @ desired
    rest_rel = b.parent.matrix_local.inverted() @ b.matrix_local
    return rest_rel.inverted() @ parent_pose.inverted() @ desired


def key_basis(pbone, basis, f):
    loc, rot, sca = basis.decompose()
    pbone.location = loc
    if pbone.rotation_mode == "QUATERNION":
        pbone.rotation_quaternion = rot
        pbone.keyframe_insert("rotation_quaternion", frame=f)
    else:
        pbone.rotation_euler = rot.to_euler(pbone.rotation_mode)
        pbone.keyframe_insert("rotation_euler", frame=f)
    pbone.keyframe_insert("location", frame=f)


def two_bone(hip, knee_m, ankle_m, target, L1, L2, hint=None):
    """retorna (joelho novo, tornozelo alcancado, erro). Direcao do joelho: a do pose original ou 'hint' (frente)."""
    u = target - hip
    d = u.length
    miss = 0.0
    dmax = L1 + L2 - 0.05
    if d > dmax:
        miss = d - dmax
        d = dmax
    u.normalize()
    w = (knee_m - hip)
    w = w - u * w.dot(u)
    if hint is not None:
        hv = hint - u * hint.dot(u)
        if hv.length > 1e-6:
            w = hv
    if w.length < 1e-6:
        w = (knee_m - ankle_m).cross(u).cross(u)
    w.normalize()
    a = (L1 * L1 - L2 * L2 + d * d) / (2.0 * d)
    h = math.sqrt(max(0.0, L1 * L1 - a * a))
    knee = hip + u * a + w * h
    ankle = hip + u * d
    return knee, ankle, miss


KNEE_HINT = {"Left": Vector((0.25, 0.0, 1.0)).normalized(), "Right": Vector((-0.25, 0.0, 1.0)).normalized()}


def retarget_legs(arm, f0, f1, hips_new, foot_new, extra_local=None, knee_hint=False):
    """reescreve Hips + pernas por frame.
    hips_new[i]: Matrix (armature) do Hips; foot_new[side][i]: Matrix (armature) desejada do Foot (pos+rot).
    extra_local: {bone: Quaternion} rotacao local extra aplicada a ossos da coluna (antes de gravar)."""
    names = ["Hips"] + [b for s in LEG.values() for b in s]
    orig = record(arm, names, f0, f1)
    sc = bpy.context.scene
    report = {"miss_max": 0.0}
    H = pb(arm, "Hips")
    # comprimentos das pernas
    lens = {}
    for side, (up, lg, ft, toe) in LEG.items():
        lens[side] = ((orig[lg][0].translation - orig[up][0].translation).length,
                      (orig[ft][0].translation - orig[lg][0].translation).length)
    for i, f in enumerate(frames(f0, f1)):
        sc.frame_set(f)
        Hn = hips_new[i]
        Ho = orig["Hips"][i]
        rigid = Hn @ Ho.inverted()          # move o que era filho do quadril junto com ele
        bases = {"Hips": basis_for(H, Hn, None)}
        for side, (up, lg, ft, toe) in LEG.items():
            Up0 = rigid @ orig[up][i]
            Lg0 = rigid @ orig[lg][i]
            Ft0 = rigid @ orig[ft][i]
            hip = Up0.translation.copy()
            target = foot_new[side][i].translation.copy()
            L1, L2 = lens[side]
            hint = (_rot(Hn) @ KNEE_HINT[side]) if knee_hint else None
            knee, ankle, miss = two_bone(hip, Lg0.translation, Ft0.translation, target, L1, L2, hint)
            report["miss_max"] = max(report["miss_max"], miss)
            s1 = (Lg0.translation - hip).rotation_difference(knee - hip)
            Rup = s1.to_matrix() @ _rot(Up0)
            shin_dir = s1.to_matrix() @ (Ft0.translation - Lg0.translation)
            s2 = shin_dir.rotation_difference(ankle - knee)
            Rlg = s2.to_matrix() @ s1.to_matrix() @ _rot(Lg0)
            Mup = _mat(Rup, hip)
            Mlg = _mat(Rlg, knee)
            Mft = _mat(_rot(foot_new[side][i]), ankle)
            bases[up] = basis_for(pb(arm, up), Mup, Hn)
            bases[lg] = basis_for(pb(arm, lg), Mlg, Mup)
            bases[ft] = basis_for(pb(arm, ft), Mft, Mlg)
        for name, B in bases.items():
            key_basis(pb(arm, name), B, f)
        if extra_local:
            for bname, q in extra_local.items():
                p = pb(arm, bname)
                if p.rotation_mode == "QUATERNION":
                    p.rotation_quaternion = p.rotation_quaternion @ q
                    p.keyframe_insert("rotation_quaternion", frame=f)
    return report


def feet_state(arm, f0, f1):
    return record(arm, ["Hips", "LeftFoot", "RightFoot", "LeftLeg", "RightLeg", "LeftToeBase", "RightToeBase"], f0, f1)


def stride_warp(arm, f0, f1, k, axis):
    """escala o passo ao longo do eixo ('z' frente/tras, 'x' lateral) em relacao ao quadril in-place"""
    st = feet_state(arm, f0, f1)
    hips_new = [m.copy() for m in st["Hips"]]
    foot_new = {}
    for side in ("Left", "Right"):
        lst = []
        for i, m in enumerate(st[side + "Foot"]):
            m2 = m.copy()
            t = m2.translation.copy()
            c = getattr(st["Hips"][i].translation, axis)
            setattr(t, axis, c + (getattr(t, axis) - c) * k)
            m2.translation = t
            lst.append(m2)
        foot_new[side] = lst
    return retarget_legs(arm, f0, f1, hips_new, foot_new)


def hips_height_stats(arm, f0, f1):
    st = record(arm, ["Hips"], f0, f1)["Hips"]
    ys = [m.translation.y for m in st]
    return min(ys), max(ys), sum(ys) / len(ys)


def crouchify(arm, f0, f1, target_avg_hips, hips_extra_rot=None, spine_extra=None, k=1.0, axis="z", knee_hint=False):
    """abaixa o quadril (media -> target_avg_hips) mantendo as trajetorias dos pes (opcionalmente escaladas por k)"""
    st = feet_state(arm, f0, f1)
    avg = sum(m.translation.y for m in st["Hips"]) / len(st["Hips"])
    drop = avg - target_avg_hips
    hips_new = []
    for m in st["Hips"]:
        R = _rot(m)
        if hips_extra_rot is not None:
            R = hips_extra_rot.to_matrix() @ R
        t = m.translation.copy()
        t.y -= drop
        hips_new.append(_mat(R, t))
    foot_new = {}
    for side in ("Left", "Right"):
        lst = []
        for i, m in enumerate(st[side + "Foot"]):
            m2 = m.copy()
            t = m2.translation.copy()
            if k != 1.0:
                c = getattr(st["Hips"][i].translation, axis)
                setattr(t, axis, c + (getattr(t, axis) - c) * k)
            m2.translation = t
            lst.append(m2)
        foot_new[side] = lst
    rep = retarget_legs(arm, f0, f1, hips_new, foot_new, extra_local=spine_extra, knee_hint=knee_hint)
    rep["drop"] = drop
    return rep


# ----------------------------------------------------------------- utilitarios de pose inteira
def all_names(arm):
    return [b.name[len(P):] for b in arm.pose.bones]


def hierarchy_order(arm):
    out = []

    def rec(b):
        out.append(b.name[len(P):])
        for c in b.children:
            rec(c)
    for b in arm.data.bones:
        if b.parent is None:
            rec(b)
    return out


def write_pose_frames(arm, frame_list, poses, names=None):
    """poses[i][name] = Matrix (armature) desejada; grava bases em ordem hierarquica"""
    order = [n for n in hierarchy_order(arm) if names is None or n in names]
    sc = bpy.context.scene
    for i, f in enumerate(frame_list):
        sc.frame_set(f)
        cur = {n: pb(arm, n).matrix.copy() for n in hierarchy_order(arm)}
        newp = dict(cur)
        for n in order:
            if n in poses[i]:
                newp[n] = poses[i][n]
        for n in order:
            p = pb(arm, n)
            parent = p.parent.name[len(P):] if p.parent else None
            B = basis_for(p, newp[n], newp[parent] if parent else None)
            key_basis(p, B, f)


def center_on_feet(arm, f0, f1, frame_ref=None):
    """desloca o quadril em X/Z para que o ponto medio dos pes (no frame_ref) fique na origem"""
    sc = bpy.context.scene
    sc.frame_set(frame_ref if frame_ref is not None else f0)
    l = pb(arm, "LeftFoot").matrix.translation
    r = pb(arm, "RightFoot").matrix.translation
    mid = (l + r) * 0.5

    def fn(i, f, M):
        M = M.copy()
        t = M.translation.copy()
        t.x -= mid.x
        t.z -= mid.z
        M.translation = t
        return M
    set_hips(arm, f0, f1, fn)
    return mid


def static_pose_clip(arm, f_src, n_frames, breathe=True):
    """congela a pose do frame f_src em uma nova action de n_frames (com respiracao sutil opcional)"""
    sc = bpy.context.scene
    sc.frame_set(f_src)
    bases = {p.name: p.matrix_basis.copy() for p in arm.pose.bones}
    arm.animation_data.action = None
    set_range(0, n_frames - 1)
    for f in range(n_frames):
        for p in arm.pose.bones:
            B = bases[p.name]
            if breathe and p.name in (P + "Spine1", P + "Spine2"):
                ang = math.radians(0.6) * math.sin(2 * math.pi * f / (n_frames - 1))
                B = B @ Quaternion((1, 0, 0), ang).to_matrix().to_4x4()
            key_basis(p, B, f)
    return 0, n_frames - 1


def mirror_arm_from_left(arm, f0, f1, phase_frames):
    """substitui o braco direito pelo esquerdo espelhado e defasado (corrige o 'braco da maleta')"""
    S = Matrix.Diagonal((-1.0, 1.0, 1.0, 1.0))
    lefts = [n for n in hierarchy_order(arm) if n.startswith("LeftShoulder") or n.startswith("LeftArm") or n.startswith("LeftForeArm") or n.startswith("LeftHand")]
    pairs = [(l, "Right" + l[4:]) for l in lefts]
    # correcao entre o frame de repouso espelhado e o real
    corr = {}
    for l, r in pairs:
        Rl = arm.data.bones[P + l].matrix_local
        Rr = arm.data.bones[P + r].matrix_local
        corr[r] = (S @ Rl @ S).inverted() @ Rr
        corr[r].translation = Vector((0, 0, 0))
    rec = record(arm, [l for l, _ in pairs], f0, f1)
    n = f1 - f0
    poses = []
    for i in range(n + 1):
        j = (i + phase_frames) % n
        d = {}
        for l, r in pairs:
            M = S @ rec[l][j] @ S @ corr[r]
            d[r] = M
        poses.append(d)
    # mantem a translacao do ombro presa ao tronco atual (so troca rotacoes)
    sc = bpy.context.scene
    for i, f in enumerate(frames(f0, f1)):
        sc.frame_set(f)
        cur = pb(arm, "RightShoulder").matrix.translation.copy()
        delta = cur - poses[i]["RightShoulder"].translation
        for r in poses[i]:
            poses[i][r].translation = poses[i][r].translation + delta
    write_pose_frames(arm, frames(f0, f1), poses, names=set(r for _, r in pairs))


def pitch_deltas(src_arm_frame, dst_arm_frame, bones):
    """(nao usado diretamente) placeholder"""
    return {}


def build_proxy_mesh(arm):
    """caixas rigidas por osso (preview do esqueleto Mixamo no UE); skin 100% por osso"""
    import bmesh
    me = bpy.data.meshes.new("SKM_Mixamo_Proxy")
    ob = bpy.data.objects.new("SKM_Mixamo_Proxy", me)
    bpy.context.scene.collection.objects.link(ob)
    ob.parent = arm
    ob.matrix_parent_inverse = Matrix.Identity(4)
    bm = bmesh.new()
    groups = {}
    skip = ("Thumb4", "Index4", "Middle4", "Ring4", "Pinky4", "Toe_End", "HeadTop_End")
    vidx = []
    for b in arm.data.bones:
        short = b.name[len(P):]
        if short.endswith(skip):
            continue
        head, tail = b.head_local, b.tail_local
        L = (tail - head).length
        if L < 0.5:
            continue
        w = max(1.2, min(9.0, L * (0.45 if short in ("Hips", "Spine", "Spine1", "Spine2", "Head") else 0.22)))
        R = b.matrix_local.to_3x3()
        x, y, z = R.col[0].normalized() * w * 0.5, R.col[1].normalized(), R.col[2].normalized() * w * 0.5
        base = []
        for sy in (0.05 * L, 0.95 * L):
            c = head + y * sy
            for sx, sz in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                base.append(bm.verts.new(c + x * sx + z * sz))
        faces = [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
        for fidx in faces:
            bm.faces.new([base[k] for k in fidx])
        vidx.append((b.name, base))
    bm.verts.index_update()
    names_idx = [(bn, [v.index for v in vs]) for bn, vs in vidx]
    bm.to_mesh(me)
    bm.free()
    for bn, ids in names_idx:
        g = ob.vertex_groups.get(bn) or ob.vertex_groups.new(name=bn)
        g.add(ids, 1.0, "REPLACE")
    mod = ob.modifiers.new("Armature", "ARMATURE")
    mod.object = arm
    return ob


def to_ue_space(arm):
    """aplica rotacao/escala do objeto Armature (Y-up/cm do Mixamo -> Z-up/metros do Blender) para o
    exportador colocar a conversao de eixo no no 'Armature', que o UE cancela e descarta.
    Blender nao escala keys de location ao aplicar escala: corrigimos manualmente (x escala)."""
    object_mode()
    s = arm.scale.x
    for o in bpy.context.view_layer.objects:
        o.select_set(o == arm)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    if arm.animation_data and arm.animation_data.action:
        for fc in fcurves_of(arm.animation_data.action):
            if fc.data_path.endswith(".location"):
                for kp in fc.keyframe_points:
                    kp.co[1] *= s
                    kp.handle_left[1] *= s
                    kp.handle_right[1] *= s
                fc.update()
    return s
