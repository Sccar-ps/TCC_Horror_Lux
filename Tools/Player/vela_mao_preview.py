# LUX: bancada de inspecao da pega da vela (SEM PIE). Braco com a pose calculada pelo vela_pega.py + castical no socket
# hand_r_Vela, longe da casa (z = 20000), e a camera do viewport em volta da mao.
#   py "<projeto>/Tools/Player/vela_mao_preview.py" montar            -> cria/atualiza os atores LUX_PREVIEW_* (nao salva o mapa)
#   py "<projeto>/Tools/Player/vela_mao_preview.py" ver olho|palma|costas|cima|baixo|polegar|minimo
#   py "<projeto>/Tools/Player/vela_mao_preview.py" desmontar         -> apaga os atores LUX_PREVIEW_*
#   py "<projeto>/Tools/Player/vela_mao_preview.py" variacao          -> quanto os dedos mudam nas animacoes da lanterna
# Log: Saved/LuxSnapshots/vela_preview_log.txt
import importlib, os, sys, traceback
import unreal

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import vela_pega as vp
importlib.reload(vp)

EAL, MATH = unreal.EditorAssetLibrary, unreal.MathLibrary
PREV = vp.DIR + "/AS_LuxVela_PegaPreview"
SM_VELA = "/Game/OldWest/VOL6/Meshes/SM_Candles_NN_01c"
BASE = unreal.Vector(0.0, 0.0, 20000.0)
LOG = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), "LuxSnapshots", "vela_preview_log.txt")


def w(*a):
    line = " ".join(str(x) for x in a)
    unreal.log("[LUX preview] " + line)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def atores():
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    return [a for a in eas.get_all_level_actors() if a.get_actor_label().startswith("LUX_PREVIEW_")]


def desmontar():
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for a in atores():
        eas.destroy_actor(a)
    if EAL.does_asset_exist(PREV):          # sobra de uma versao anterior da bancada (nunca foi salva)
        EAL.delete_asset(PREV)
    w("preview desmontado")


def montar():
    desmontar()
    P, centro_h, eixo_h, dedos, rel, alvo, giro, r, locais = vp.calcula()
    vp.relatorio(P, centro_h, eixo_h, dedos, rel, alvo, giro, r)
    for l in rel:
        w("  ", l)
    # PoseableMeshComponent: cada osso recebe a transformacao calculada (a animacao nao roda no editor sem tick)
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    mao = eas.spawn_actor_from_class(unreal.StaticMeshActor, BASE, unreal.Rotator(0, 0, 0))
    mao.set_actor_label("LUX_PREVIEW_Mao")
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    raiz = sds.k2_gather_subobject_data_for_instance(mao)[0]
    h, falha = sds.add_new_subobject(unreal.AddNewSubobjectParams(parent_handle=raiz, new_class=unreal.PoseableMeshComponent))
    c = mao.get_component_by_class(unreal.PoseableMeshComponent)
    if not c:
        raise RuntimeError("PoseableMeshComponent nao criado: %s" % falha)
    c.set_skinned_asset_and_update(EAL.load_asset(vp.SKM), True)
    cs = {}
    for b in P.nomes:
        if c.get_bone_index(b) < 0:
            continue
        lp, lq = P.loc[b]
        loc = unreal.Transform()
        loc.translation, loc.rotation, loc.scale3d = unreal.Vector(*lp), unreal.Quat(*locais.get(b, lq)), unreal.Vector(1, 1, 1)
        pai = str(c.get_parent_bone(b))
        cs[b] = MATH.compose_transforms(loc, cs[pai]) if pai in cs else loc
        c.set_bone_transform_by_name(b, cs[b], unreal.BoneSpaces.COMPONENT_SPACE)
    for b in ("hand_r", "index_02_r", "middle_03_r", "thumb_02_r"):
        lido = c.get_bone_transform_by_name(b, unreal.BoneSpaces.COMPONENT_SPACE)
        w("  osso %s: pedido %s | lido %s | pai %s | ordem %d" % (b, cs[b].translation, lido.translation, c.get_parent_bone(b),
                                                                 list(cs).index(b)))
    vela = eas.spawn_actor_from_class(unreal.StaticMeshActor, BASE, unreal.Rotator(0, 0, 0))
    vela.set_actor_label("LUX_PREVIEW_Vela")
    sm = vela.static_mesh_component
    sm.set_mobility(unreal.ComponentMobility.MOVABLE)
    sm.set_static_mesh(EAL.load_asset(SM_VELA))
    vela.attach_to_component(c, vp.SOCKET, unreal.AttachmentRule.SNAP_TO_TARGET, unreal.AttachmentRule.SNAP_TO_TARGET,
                             unreal.AttachmentRule.SNAP_TO_TARGET, False)
    sm.set_relative_location(unreal.Vector(0, 0, -vp.HASTE_MEIO), False, False)
    sm.set_relative_scale3d(unreal.Vector(vp.ESCALA_VELA, vp.ESCALA_VELA, vp.ESCALA_VELA))
    eas.select_nothing()
    w("preview montado em", BASE)


def ver(nome):
    mao = [a for a in atores() if a.get_actor_label() == "LUX_PREVIEW_Mao"]
    if not mao:
        raise RuntimeError("rode 'montar' antes")
    c = mao[0].get_component_by_class(unreal.PoseableMeshComponent)
    s = c.get_socket_transform(vp.SOCKET, unreal.RelativeTransformSpace.RTS_WORLD)
    O = vp.uv(s.translation)
    Z = vp.unit(vp.uv(MATH.transform_direction(s, unreal.Vector(0, 0, 1))))
    h = c.get_socket_transform("hand_r", unreal.RelativeTransformSpace.RTS_WORLD)
    P = vp.Pose()
    _, _, palma = vp.haste_na_mao(P)
    p = vp.unit(vp.uv(MATH.transform_direction(h, unreal.Vector(*palma))))
    lado = vp.unit(vp.cross(Z, p))
    d = 24.0
    if nome == "olho":
        (x, y, z), yaw = vp.MESH_NA_CAMERA
        cam = MATH.compose_transforms(MATH.invert_transform(unreal.Transform(unreal.Vector(x, y, z), unreal.Rotator(0, 0, yaw))),
                                      c.get_world_transform())
        loc, rot = cam.translation, cam.rotation.rotator()
    else:
        dirs = {"palma": p, "costas": vp.mul(p, -1), "cima": vp.add(Z, vp.mul(p, 0.25)), "baixo": vp.add(vp.mul(Z, -1), vp.mul(p, 0.25)),
                "polegar": lado, "minimo": vp.mul(lado, -1)}
        loc = unreal.Vector(*vp.add(O, vp.mul(vp.unit(dirs[nome]), d)))
        rot = MATH.find_look_at_rotation(loc, unreal.Vector(*O))
    unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(loc, rot)
    w("camera %s em %s" % (nome, loc))


def variacao():
    """maior diferenca (graus) da rotacao local de cada dedo nas animacoes da lanterna em relacao ao idle quadro 0
    (a aditiva soma a pega em cima disso: se o dedo abre na animacao, abre tambem com a vela)"""
    P = vp.Pose()
    base = "/Game/FPMovement/Demo/Character/Animations/Flashlight/"
    dedos = [b for b in P.nomes if b.endswith("_r") and any(k in b for k in vp.DEDOS + ("thumb",)) and "metacarpal" not in b]
    for an in ("AS_Flashlight_Idle", "AS_Flashlight_Walk", "AS_Flashlight_Eqiup", "AS_Flashlight_Unequip", "AS_Flashlight_Jump",
               "AS_Flashlight_InAir", "AS_Flashlight_Land", "AS_Flashlight_Inspection", "AS_Flashlight_FlickerReaction"):
        seq = EAL.load_asset(base + an)
        n = unreal.AnimationLibrary.get_num_frames(seq)
        pior = {}
        for f in range(0, n + 1, max(1, n // 12)):
            pose = unreal.AnimPoseExtensions.get_anim_pose_at_frame(seq, f, unreal.AnimPoseEvaluationOptions())
            for b in dedos:
                q = vp.uq(unreal.AnimPoseExtensions.get_bone_pose(pose, b, unreal.AnimPoseSpaces.LOCAL).rotation)
                a = vp.qang(q, P.loc[b][1])
                if a > pior.get(b, (0, 0))[0]:
                    pior[b] = (a, f)
        top = sorted(pior.items(), key=lambda kv: -kv[1][0])[:5]
        w("%-28s %3d quadros | maiores: %s" % (an, n, ", ".join("%s %.0f (q%d)" % (b, a, f) for b, (a, f) in top)))


def main():
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    args = [str(a).lower() for a in sys.argv[1:]]
    modo = args[0] if args else "montar"
    if modo != "ver":
        open(LOG, "w", encoding="utf-8").close()
    try:
        with unreal.ScopedEditorTransaction("LUX preview da pega"):
            if modo == "montar":
                montar()
            elif modo == "desmontar":
                desmontar()
            elif modo == "variacao":
                variacao()
            elif modo == "ver":
                ver(args[1] if len(args) > 1 else "olho")
    except Exception:
        w("ERRO " + traceback.format_exc())


if __name__ == "__main__":
    main()
