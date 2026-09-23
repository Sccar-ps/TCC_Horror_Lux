# Etapa 2 (UE): IK Rigs (Mixamo proxy e Cowboy), IK Retargeter Mixamo -> Cowboy, retarget em lote e medicoes.
import os, json, math, unreal
EAL = unreal.EditorAssetLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()
ROOT = "/Game/Characters/MixamoFP"
P_SRC = ROOT + "/Source"
P_RIG = ROOT + "/Rig"
P_ANIM = ROOT + "/Anims"
COWBOY = "/Game/Cowboy_character/Mesh/SM_SkeletalMesh_cowboy_character"
PROJ = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
MAN = json.load(open(os.path.join(PROJ, "SourceArt", "MixamoFP_v2", "manifest.json"), encoding="utf-8"))
saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
LOG = os.path.join(saved, "MixamoFP_retarget.txt")
out = []
SRC = unreal.RetargetSourceOrTarget.SOURCE
TGT = unreal.RetargetSourceOrTarget.TARGET


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


def chains(ctrl):
    return [(str(c.get_editor_property("chain_name")), str(c.get_editor_property("start_bone").get_editor_property("bone_name")) if hasattr(c.get_editor_property("start_bone"), "get_editor_property") else "?",
             str(c.get_editor_property("end_bone").get_editor_property("bone_name")) if hasattr(c.get_editor_property("end_bone"), "get_editor_property") else "?") for c in ctrl.get_retarget_chains()]


def bone_names(skm):
    c = unreal.new_object(unreal.SkeletalMeshComponent)
    c.set_skeletal_mesh_asset(skm)
    return [str(c.get_bone_name(i)) for i in range(c.get_num_bones())], c


def rig_for(name, mesh):
    rig, created = create(name, P_RIG, unreal.IKRigDefinition, unreal.IKRigDefinitionFactory())
    ctrl = unreal.IKRigController.get_controller(rig)
    if created or not ctrl.get_retarget_chains():
        ctrl.set_skeletal_mesh(mesh)
        a = ctrl.apply_auto_generated_retarget_definition()
        b = ctrl.apply_auto_fbik()
        w("%s: auto retarget=%s auto fbik=%s" % (name, a, b))
    try:
        w("%s: retarget root=%s | cadeias=%s" % (name, ctrl.get_retarget_root(), chains(ctrl)))
    except Exception as e:
        w("%s: cadeias ? %s" % (name, e))
    EAL.save_loaded_asset(rig, False)
    return rig


def comp_pos(anim, chain, t):
    """posicao em component space do ultimo osso da cadeia (compondo transforms locais)"""
    M = unreal.Transform()
    for b in chain:
        l = unreal.AnimationLibrary.get_bone_pose_for_time(anim, b, t, False)
        M = l.multiply(M)   # filho * pai
    return M.translation


try:
    for p in (ROOT, P_RIG, P_ANIM):
        ensure_dir(p)
    proxy = EAL.load_asset(P_SRC + "/SKM_Mixamo_Proxy")
    cowboy = EAL.load_asset(COWBOY)
    names_cb, comp_cb = bone_names(cowboy)
    w("Cowboy ossos (%d): %s" % (len(names_cb), names_cb))
    rig_src = rig_for("IK_Mixamo", proxy)
    rig_tgt = rig_for("IK_Cowboy", cowboy)

    rtg, created = create("RTG_Mixamo_to_Cowboy", P_RIG, unreal.IKRetargeter, unreal.IKRetargetFactory())
    c = unreal.IKRetargeterController.get_controller(rtg)
    c.set_ik_rig(SRC, rig_src)
    c.set_ik_rig(TGT, rig_tgt)
    if c.get_num_retarget_ops() == 0:
        c.add_default_ops()
    c.assign_ik_rig_to_all_ops(SRC, rig_src)
    c.assign_ik_rig_to_all_ops(TGT, rig_tgt)
    c.set_preview_mesh(SRC, proxy)
    c.set_preview_mesh(TGT, cowboy)
    c.auto_map_chains(unreal.AutoMapChainType.FUZZY, True)
    c.auto_align_all_bones(TGT)
    for bone in ("foot_l",):
        try:
            c.snap_bone_to_ground(bone, TGT)
            w("snap_bone_to_ground(%s, TARGET) ok" % bone)
        except Exception as e:
            w("snap_bone_to_ground erro %s" % e)
    ops = []
    for i in range(c.get_num_retarget_ops()):
        n = str(c.get_op_name(i))
        ops.append(n)
        if "Root Motion" in n or "RootMotion" in n:
            c.set_retarget_op_enabled(i, False)      # anims sao in-place: root fica parado
    w("ops: %s" % [(str(c.get_op_name(i)), c.get_retarget_op_enabled(i)) for i in range(c.get_num_retarget_ops())])
    try:
        tgt_names = [x[0] for x in chains(unreal.IKRigController.get_controller(rig_tgt))]
        w("mapeamento: %s" % ["%s<-%s" % (t, c.get_source_chain(t)) for t in tgt_names])
    except Exception as e:
        w("mapeamento ? %s" % e)
    EAL.save_loaded_asset(rtg, False)

    # ---- retarget em lote
    todo = [EAL.find_asset_data(P_SRC + "/Anims/" + n) for n in MAN]
    inputs = unreal.IKRetargetBatchOperationInputs()
    for k, v in (("assets_to_retarget", todo), ("source_mesh", proxy), ("target_mesh", cowboy), ("ik_retarget_asset", rtg),
                 ("search", "MX_"), ("replace", "A_CB_"), ("target_path", P_ANIM), ("use_source_path", False),
                 ("include_referenced_assets", False), ("overwrite_existing_files", True)):
        try:
            inputs.set_editor_property(k, v)
        except Exception as e:
            w("inputs.%s erro %s" % (k, e))
    res = unreal.IKRetargetBatchOperation.run_batch_retarget(inputs)
    w("retarget gerou %d assets" % len(res or []))

    # ---- medicoes no Cowboy
    CH = {"l": ["root", "pelvis", "thigh_l", "calf_l", "foot_l"], "r": ["root", "pelvis", "thigh_r", "calf_r", "foot_r"]}
    BALL = {"l": CH["l"] + ["ball_l"], "r": CH["r"] + ["ball_r"]}
    rest_l = comp_cb.get_socket_transform("foot_l", unreal.RelativeTransformSpace.RTS_COMPONENT).translation if False else None
    report = {}
    for n in MAN:
        name = "A_CB_" + n[3:]
        path = P_ANIM + "/" + name
        anim = EAL.load_asset(path)
        if anim is None:
            w("  sem resultado: %s" % name)
            continue
        anim.set_editor_property("enable_root_motion", False)
        EAL.save_loaded_asset(anim, False)
        L = anim.get_play_length()
        N = max(2, int(round(L * 30)))
        ts = [L * i / N for i in range(N + 1)]
        feet = {s: [comp_pos(anim, CH[s], t) for t in ts] for s in ("l", "r")}
        balls = {s: [comp_pos(anim, BALL[s], t) for t in ts] for s in ("l", "r")}
        pel = [comp_pos(anim, ["root", "pelvis"], t).z for t in ts]
        minz = {s: min(p.z for p in feet[s]) for s in feet}
        minball = {s: min(p.z for p in balls[s]) for s in balls}
        # velocidade no chao: pe em contato (z < min+2) -> inclinacao da posicao horizontal
        d = MAN[n].get("dir", 0)
        ax = "y" if d in (0, 180, -180) else "x"
        speeds = []
        for s in ("l", "r"):
            pts = [(ts[i], getattr(feet[s][i], ax)) for i in range(len(ts)) if feet[s][i].z < minz[s] + 2.0]
            for i in range(1, len(pts)):
                dt = pts[i][0] - pts[i - 1][0]
                if 0 < dt < 0.05:
                    speeds.append(abs(pts[i][1] - pts[i - 1][1]) / dt)
        speeds.sort()
        v = speeds[len(speeds) // 2] if speeds else 0.0
        report[name] = dict(len=round(L, 3), pelvis_avg=round(sum(pel) / len(pel), 1), ankle_min=(round(minz["l"], 1), round(minz["r"], 1)),
                            ball_min=(round(minball["l"], 1), round(minball["r"], 1)), ground_speed=round(v, 1), mx_speed=MAN[n].get("speed_mx", 0), dir=d)
        w("  %-18s %s" % (name, report[name]))
    json.dump(report, open(os.path.join(saved, "MixamoFP_speeds.json"), "w"), indent=1)
    # altura de referencia dos pes do Cowboy (ref pose)
    for b in ("foot_l", "ball_l", "pelvis", "head"):
        w("  ref %s z=%.1f" % (b, comp_cb.get_socket_transform(b, unreal.RelativeTransformSpace.RTS_COMPONENT).translation.z))
except Exception:
    import traceback
    w("ERRO: " + traceback.format_exc())
finally:
    open(LOG, "w", encoding="utf-8").write("\n".join(out))
