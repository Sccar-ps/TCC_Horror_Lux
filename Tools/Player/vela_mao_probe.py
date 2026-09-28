# LUX: diagnostico (so leitura) da vela na mao. RODAR COM O PIE ABERTO (usa o jogador vivo + amostra as animacoes).
#   py "<projeto>/Tools/Player/vela_mao_probe.py"  -> Saved/LuxSnapshots/vela_mao_probe.txt
# Mede: hierarquia e sockets do braco direito, onde fica o "buraco" do punho fechado (eixo de pega ajustado pelos dedos),
# eixo/posicao da vela, distancia dos dedos ao cabo da vela, e o mesmo nas animacoes idle/andar/puxar/guardar.
import json, math, os, traceback, unreal

EAL, MATH = unreal.EditorAssetLibrary, unreal.MathLibrary
OUT = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), "LuxSnapshots", "vela_mao_probe.txt")
AQUI = os.path.dirname(os.path.abspath(__file__))
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
    return "(%.1f, %.1f, %.1f)" % a


def ang(a, b):
    return math.degrees(math.acos(max(-1.0, min(1.0, abs(dot(norm(a), norm(b)))))))


def circ(a, b, c):
    """centro e raio do circulo por 3 pontos"""
    u, v = sub(b, a), sub(c, a)
    w = cross(u, v)
    ww = dot(w, w)
    if ww < 1e-9:
        return None, 0.0
    cc = mul(cross(sub(mul(v, dot(u, u)), mul(u, dot(v, v))), w), 1.0 / (2 * ww))
    return add(a, cc), math.sqrt(dot(cc, cc))


def dist_linha(pt, o, d):
    """distancia do ponto a reta (o, d unitario) e parametro ao longo dela"""
    r = sub(pt, o)
    t = dot(r, d)
    q = sub(r, mul(d, t))
    return math.sqrt(dot(q, q)), t


def analisa(nome, pos, vela_base, vela_up, cam, raio_cabo):
    """pos: dict osso -> ponto (qualquer espaco); cam: funcao ponto/direcao -> espaco da camera (x frente, y dir, z cima)"""
    p("--", nome)
    centros = []
    for d in DEDOS:
        j = [pos.get("%s_0%d_r" % (d, i)) for i in (1, 2, 3)]
        if None in j:
            continue
        tip = add(j[2], mul(sub(j[2], j[1]), 0.85))
        c, r = circ(j[1], j[2], tip)
        if c:
            centros.append(c)
            dl, t = dist_linha(c, vela_base, vela_up)
            p("   %-6s centro do arco %s r=%.1f | dist ao eixo da vela %.1f cm (altura %.1f cm)" % (d, f(cam(c, True)), r, dl, t))
    if len(centros) >= 2:
        eixo = norm(sub(centros[-1], centros[0]))           # index -> pinky
        meio = mul(add(centros[0], centros[-1]), 0.5)
        p("   eixo do punho (index->pinky) cam=%s | angulo com a vela %.0f graus | com o 'cima' da camera %.0f graus" % (
            f(cam(eixo, False)), ang(eixo, vela_up), ang(cam(eixo, False), (0, 0, 1))))
        dl, t = dist_linha(meio, vela_base, vela_up)
        p("   centro do punho -> eixo da vela: %.1f cm (altura na vela %.1f cm)" % (dl, t))
    # dedos atravessando o cabo: menor distancia de cada falange ao eixo da vela entre 0 e 12 cm de altura
    ruins = []
    for d in DEDOS + ("thumb",):
        for i in (1, 2):
            a, b = pos.get("%s_0%d_r" % (d, i)), pos.get("%s_0%d_r" % (d, i + 1))
            if not a or not b:
                continue
            m = min(dist_linha(add(a, mul(sub(b, a), k / 4.0)), vela_base, vela_up) for k in range(5))
            ruins.append("%s%d %.1f(h%.1f)" % (d[:2], i, m[0], m[1]))
    p("   falange -> eixo da vela (cm, altura): %s | raio do cabo ~%.1f cm" % (", ".join(ruins), raio_cabo))
    p("   vela: base %s eixo %s (angulo com o 'cima' da camera %.0f graus)" % (f(cam(vela_base, True)), f(cam(vela_up, False)),
                                                                         ang(cam(vela_up, False), (0, 0, 1))))


try:
    ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    world = ues.get_game_world()
    if not world:
        raise RuntimeError("abra o PIE antes de rodar")
    pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
    comps = {c.get_name(): c for c in pawn.get_components_by_class(unreal.SceneComponent)}
    mesh, cam_c, vela = comps["FirstPersonMesh"], [c for c in comps.values() if isinstance(c, unreal.CameraComponent)][0], comps["Vela"]
    sk = mesh.get_editor_property("skeletal_mesh_asset") if hasattr(mesh, "skeletal_mesh_asset") else mesh.skeletal_mesh
    p("pawn", pawn.get_class().get_name(), "| FirstPersonMesh", sk.get_path_name(), "| skeleton", sk.skeleton.get_path_name())
    p("FirstPersonMesh pai:", mesh.get_attach_parent().get_name(), "rel", mesh.get_editor_property("relative_location"),
      mesh.get_editor_property("relative_rotation"))
    # 1) esqueleto do braco direito
    nb = mesh.get_num_bones()
    ossos = [str(mesh.get_bone_name(i)) for i in range(nb)]
    braco = [b for b in ossos if b.endswith("_r") and any(k in b for k in ("clavicle", "upperarm", "lowerarm", "hand", "thumb", "index",
                                                                           "middle", "ring", "pinky", "weapon"))]
    p("ossos: %d; braco direito: %d" % (nb, len(braco)))
    for b in braco:
        pai = str(mesh.get_parent_bone(b))
        t = mesh.get_socket_transform(b, unreal.RelativeTransformSpace.RTS_PARENT_BONE_SPACE)
        p("   %-24s pai %-22s local %s %s" % (b, pai, f(v3(t.translation)), t.rotation.rotator()))
    # 2) sockets
    for i in range(sk.num_sockets()):
        s = sk.get_socket_by_index(i)
        p("socket", s.socket_name, "osso", s.bone_name, "loc", f(v3(s.relative_location)), "rot", s.relative_rotation, "esc", s.relative_scale)
    try:
        p("sockets do skeleton:", [str(s.socket_name) for s in sk.skeleton.get_editor_property("sockets")])
    except Exception as ex:
        p("sockets do skeleton: ?", ex)
    # 3) attachment da vela e da lanterna
    p("Vela: pai %s socket %s rel %s %s esc %s" % (vela.get_attach_parent().get_name(), vela.get_attach_socket_name(),
                                                  f(v3(vela.get_editor_property("relative_location"))), vela.get_editor_property("relative_rotation"),
                                                  f(v3(vela.get_editor_property("relative_scale3d")))))
    lan = comps.get("SM_Flashlight")
    orig = json.load(open(os.path.join(AQUI, "vela_lanterna_original.json"), encoding="utf-8")) if os.path.exists(os.path.join(AQUI, "vela_lanterna_original.json")) else {}
    if lan:
        bb = lan.get_editor_property("static_mesh").get_bounding_box()
        p("SM_Flashlight: pai %s socket %s rel(original) %s rot %s | malha %s bounds %s %s" % (
            lan.get_attach_parent().get_name(), lan.get_attach_socket_name(), orig.get("SM_Flashlight", {}).get("relative_location"),
            lan.get_editor_property("relative_rotation"), lan.get_editor_property("static_mesh").get_name(), f(v3(bb.min)), f(v3(bb.max))))
    # 4) perfil da vela (raio x altura, em cm ja com a escala)
    smv = vela.get_editor_property("static_mesh")
    esc = vela.get_editor_property("relative_scale3d").z
    perfil = {}
    try:
        for s in range(smv.get_num_sections(0)):
            vs = unreal.ProceduralMeshLibrary.get_section_from_static_mesh(smv, 0, s)[0]
            for v in vs:
                k = int(v.z * esc)
                perfil[k] = max(perfil.get(k, 0.0), math.hypot(v.x, v.y) * esc)
        p("perfil da vela (altura cm: raio cm):", ", ".join("%d:%.1f" % (k, perfil[k]) for k in sorted(perfil)))
    except Exception as ex:
        p("perfil: ?", ex)
    raio_cabo = min([perfil[k] for k in perfil if 1 <= k <= 6] or [1.0])
    # 5) pose viva
    camT = cam_c.get_world_transform()

    def cam_w(x, ponto):
        vv = unreal.Vector(*x)
        return v3(MATH.inverse_transform_location(camT, vv) if ponto else MATH.inverse_transform_direction(camT, vv))

    vivo = {b: v3(mesh.get_socket_location(b)) for b in braco}
    vt = vela.get_world_transform()
    analisa("PIE agora (espaco da camera; x frente, y direita, z cima)", vivo, v3(vt.translation),
            norm(v3(MATH.transform_direction(vt, unreal.Vector(0, 0, 1)))), cam_w, raio_cabo)
    for b in ("lowerarm_r", "hand_r"):
        t = mesh.get_socket_transform(b, unreal.RelativeTransformSpace.RTS_WORLD)
        p("   %s cam %s | eixo X do osso %s" % (b, f(cam_w(v3(t.translation), True)),
                                              f(cam_w(v3(MATH.get_forward_vector(t.rotation.rotator())), False))))
    p("   antebraco (lowerarm->hand) cam %s" % f(cam_w(norm(sub(vivo["hand_r"], vivo["lowerarm_r"])), False)))
    # 6) animacoes (espaco do componente -> camera pela relacao viva malha/camera)
    meshT = mesh.get_world_transform()
    sock = sk.find_socket(vela.get_attach_socket_name())
    sockT = unreal.Transform(sock.relative_location, sock.relative_rotation, sock.relative_scale)
    velaRel = vela.get_relative_transform()

    def cam_cs(x, ponto):
        vv = unreal.Vector(*x)
        w = MATH.transform_location(meshT, vv) if ponto else MATH.transform_direction(meshT, vv)
        return cam_w(v3(w), ponto)

    base = "/Game/FPMovement/Demo/Character/Animations/Flashlight/"
    opts = unreal.AnimPoseEvaluationOptions()
    for an, tempos in (("AS_Flashlight_Idle", (0.0, 1.25)), ("AS_Flashlight_Walk", (0.0, 0.3, 0.6, 0.9)),
                       ("AS_Flashlight_Eqiup", (0.0, 0.4, 0.8)), ("AS_Flashlight_Unequip", (0.0, 0.4, 0.8))):
        seq = EAL.load_asset(base + an)
        for tt in tempos:
            pose = unreal.AnimPoseExtensions.get_anim_pose_at_time(seq, tt, opts)
            cs = {b: v3(unreal.AnimPoseExtensions.get_bone_pose(pose, b, unreal.AnimPoseSpaces.WORLD).translation) for b in braco}
            hT = unreal.AnimPoseExtensions.get_bone_pose(pose, "hand_r", unreal.AnimPoseSpaces.WORLD)
            vT = MATH.compose_transforms(MATH.compose_transforms(velaRel, sockT), hT)
            analisa("%s t=%.2f" % (an, tt), cs, v3(vT.translation), norm(v3(MATH.transform_direction(vT, unreal.Vector(0, 0, 1)))),
                    cam_cs, raio_cabo)
    # 7) animacoes do mesmo esqueleto (para achar uma pose de segurar em pe)
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    alvo = sk.skeleton.get_path_name()
    nomes = []
    for d in ar.get_assets_by_class(unreal.TopLevelAssetPath("/Script/Engine", "AnimSequence"), True):
        if alvo.split(".")[0] in str(d.get_tag_value("Skeleton")):
            nomes.append(str(d.package_name))
    p("AnimSequences do esqueleto dos bracos (%d):" % len(nomes))
    for n in sorted(nomes):
        p("   ", n)
except Exception:
    p(traceback.format_exc())
os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT, "w", encoding="utf-8").write("\n".join(L))
unreal.log("[LUX vela] mao probe ok: %d linhas" % len(L))
