# LUX: diagnostico 2 (so leitura, COM O PIE ABERTO): o "buraco" do punho no espaco do socket hand_r_Flashlight.
#   py "<projeto>/Tools/Player/vela_mao_probe2.py"  -> Saved/LuxSnapshots/vela_mao_probe2.txt
import math, os, traceback, unreal

EAL, MATH = unreal.EditorAssetLibrary, unreal.MathLibrary
OUT = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), "LuxSnapshots", "vela_mao_probe2.txt")
L = []
DEDOS = ("index", "middle", "ring", "pinky")


def p(*a):
    L.append(" ".join(str(x) for x in a))


def v3(v):
    return (v.x, v.y, v.z)


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def mul(a, k):
    return (a[0] * k, a[1] * k, a[2] * k)


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def norm(a):
    n = math.sqrt(dot(a, a)) or 1.0
    return mul(a, 1.0 / n)


def f(a):
    return "(%.2f, %.2f, %.2f)" % a


def circ(a, b, c):
    u, v = sub(b, a), sub(c, a)
    w = cross(u, v)
    ww = dot(w, w)
    if ww < 1e-9:
        return None, 0.0
    cc = mul(cross(sub(mul(v, dot(u, u)), mul(u, dot(v, v))), w), 1.0 / (2 * ww))
    return add(a, cc), math.sqrt(dot(cc, cc))


def mede(nome, pos_s, extra=""):
    """pos_s: osso -> ponto no espaco do socket"""
    cs, rs = [], []
    for d in DEDOS:
        j = [pos_s.get("%s_0%d_r" % (d, i)) for i in (1, 2, 3)]
        c, r = circ(*j)
        if c:
            cs.append(c)
            rs.append(r)
            p("   %-6s MCP %s PIP %s DIP %s -> centro %s r %.2f" % (d, f(j[0]), f(j[1]), f(j[2]), f(c), r))
    if len(cs) == 4:
        eixo = norm(sub(cs[3], cs[0]))
        meio = mul(add(add(cs[0], cs[1]), add(cs[2], cs[3])), 0.25)
        p("  [%s] centro do punho %s | eixo index->pinky %s | raio medio %.2f %s" % (nome, f(meio), f(eixo), sum(rs) / 4, extra))
        return meio, eixo
    return None, None


try:
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
    comps = {c.get_name(): c for c in pawn.get_components_by_class(unreal.SceneComponent)}
    mesh, cam = comps["FirstPersonMesh"], [c for c in comps.values() if isinstance(c, unreal.CameraComponent)][0]
    sk = mesh.get_editor_property("skeletal_mesh_asset")
    ossos = [str(mesh.get_bone_name(i)) for i in range(mesh.get_num_bones())]
    mao = [b for b in ossos if b.endswith("_r") and any(k in b for k in DEDOS + ("thumb", "hand", "lowerarm"))]
    sockW = mesh.get_socket_transform("hand_r_Flashlight", unreal.RelativeTransformSpace.RTS_WORLD)
    viv = {b: v3(MATH.inverse_transform_location(sockW, mesh.get_socket_location(b))) for b in mao}
    camT = cam.get_world_transform()
    up_s = norm(v3(MATH.inverse_transform_direction(sockW, MATH.transform_direction(camT, unreal.Vector(0, 0, 1)))))
    fw_s = norm(v3(MATH.inverse_transform_direction(sockW, MATH.transform_direction(camT, unreal.Vector(1, 0, 0)))))
    y_cam = norm(v3(MATH.inverse_transform_direction(camT, MATH.transform_direction(sockW, unreal.Vector(0, 1, 0)))))
    p("PIE: 'cima' da camera no socket %s | 'frente' da camera no socket %s | eixo Y do socket (lanterna) na camera %s" % (f(up_s), f(fw_s), f(y_cam)))
    p("   socket na camera:", f(v3(MATH.inverse_transform_location(camT, sockW.translation))))
    for b in ("hand_r", "lowerarm_r", "thumb_01_r", "thumb_02_r", "thumb_03_r", "index_metacarpal_r", "pinky_metacarpal_r"):
        p("   %-20s no socket %s" % (b, f(viv[b])))
    mede("PIE", viv)
    # animacoes: pose no espaco do componente -> espaco do socket (socket = hand_r * socket local)
    sock = sk.find_socket("hand_r_Flashlight")
    sockL = unreal.Transform(sock.relative_location, sock.relative_rotation, sock.relative_scale)
    meshT = mesh.get_world_transform()
    opts = unreal.AnimPoseEvaluationOptions()
    for k, v in (("optional_skeletal_mesh", sk), ("evaluation_type", unreal.AnimDataEvalType.RAW)):
        try:
            opts.set_editor_property(k, v)
        except Exception as ex:
            p("opts", k, ex)
    base = "/Game/FPMovement/Demo/Character/Animations/Flashlight/"
    for an, tempos in (("AS_Flashlight_Idle", (0.0, 0.8, 1.6)), ("AS_Flashlight_Walk", (0.0, 0.3, 0.6, 0.9)),
                       ("AS_Flashlight_Eqiup", (0.0, 0.2, 0.4, 0.6, 0.8)), ("AS_Flashlight_Unequip", (0.0, 0.2, 0.4, 0.6, 0.8))):
        seq = EAL.load_asset(base + an)
        for tt in tempos:
            pose = unreal.AnimPoseExtensions.get_anim_pose_at_time(seq, tt, opts)
            nb = len(unreal.AnimPoseExtensions.get_bone_names(pose))
            hT = unreal.AnimPoseExtensions.get_bone_pose(pose, "hand_r", unreal.AnimPoseSpaces.WORLD)
            sT = MATH.compose_transforms(sockL, hT)
            pos = {b: v3(MATH.inverse_transform_location(sT, unreal.AnimPoseExtensions.get_bone_pose(pose, b, unreal.AnimPoseSpaces.WORLD).translation))
                   for b in mao}
            # cima/frente da camera no socket nesta pose (malha presa a camera: relacao fixa)
            sW = MATH.compose_transforms(sT, meshT)
            up = norm(v3(MATH.inverse_transform_direction(sW, MATH.transform_direction(camT, unreal.Vector(0, 0, 1)))))
            ycam = norm(v3(MATH.inverse_transform_direction(camT, MATH.transform_direction(sW, unreal.Vector(0, 1, 0)))))
            loc = v3(MATH.inverse_transform_location(camT, sW.translation))
            p("-- %s t=%.2f (ossos %d) socket na camera %s | 'cima' no socket %s | eixo Y na camera %s" % (an, tt, nb, f(loc), f(up), f(ycam)))
            if an == "AS_Flashlight_Idle" and tt == 0.0 or an != "AS_Flashlight_Idle":
                mede("%s %.2f" % (an, tt), pos)
    # malhas candidatas
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    achou = []
    for d in ar.get_assets_by_class(unreal.TopLevelAssetPath("/Script/Engine", "StaticMesh"), True):
        n = str(d.asset_name).lower()
        if any(k in n for k in ("candle", "lantern", "lamp", "holder", "castical", "chamber", "torch", "handle")):
            achou.append(str(d.package_name))
    p("malhas candidatas (%d):" % len(achou))
    for a in sorted(achou):
        p("   ", a)
    smv = EAL.load_asset("/Game/OldWest/VOL6/Meshes/SM_Candles_NN_01c")
    p("SM_Candles_NN_01c materiais:", [(str(s.material_slot_name), s.material_interface.get_path_name() if s.material_interface else None) for s in smv.static_materials])
except Exception:
    p(traceback.format_exc())
open(OUT, "w", encoding="utf-8").write("\n".join(L))
unreal.log("[LUX vela] mao probe2 ok: %d linhas" % len(L))
