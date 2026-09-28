# LUX: camera de inspecao da mao COM O PIE ABERTO (so muda o mundo do PIE; nada e salvo).
# Usa uma CameraActor do nivel, presa ao socket hand_r_Vela: a mao fica parada na tela mesmo andando/puxando/guardando.
#   py "<projeto>/Tools/Player/vela_mao_camera.py" ver frente|tras|esq|dir|cima|baixo  [distancia_cm]
#   py "<projeto>/Tools/Player/vela_mao_camera.py" jogador      -> volta a camera do jogador
# Eixos do socket hand_r_Vela: Z = haste (para cima), X = para onde apontam os dedos, Y = Z x X.
import os, sys, traceback
import unreal

MATH = unreal.MathLibrary
LOG = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), "LuxSnapshots", "vela_camera_log.txt")
SOCKET = "hand_r_Vela"


def w(*a):
    line = " ".join(str(x) for x in a)
    unreal.log("[LUX cam] " + line)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def pie():
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    if not world:
        raise RuntimeError("abra o PIE")
    pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
    pc = unreal.GameplayStatics.get_player_controller(world, 0)
    mesh = [c for c in pawn.get_components_by_class(unreal.SkeletalMeshComponent) if c.get_name() == "FirstPersonMesh"][0]
    cams = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.CameraActor)
    cam = sorted(cams, key=lambda a: (a.get_actor_label() != "LUX_CAM_MAO", a.get_actor_label()))[0]
    return world, pawn, pc, mesh, cam


def ver(nome, d):
    world, pawn, pc, mesh, cam = pie()
    cam.detach_from_actor(unreal.DetachmentRule.KEEP_WORLD, unreal.DetachmentRule.KEEP_WORLD, unreal.DetachmentRule.KEEP_WORLD)
    s = mesh.get_socket_transform(SOCKET, unreal.RelativeTransformSpace.RTS_WORLD)
    O = s.translation
    ax = {"frente": (1, 0, 0), "tras": (-1, 0, 0), "esq": (0, 1, 0), "dir": (0, -1, 0), "cima": (0.35, 0, 1), "baixo": (0.35, 0, -1)}[nome]
    v = MATH.transform_direction(s, unreal.Vector(*ax))
    v = v * (d / max((v.x * v.x + v.y * v.y + v.z * v.z) ** 0.5, 1e-6))
    loc = O + v
    cam.set_actor_location_and_rotation(loc, MATH.find_look_at_rotation(loc, O), False, False)
    cam.attach_to_component(mesh, SOCKET, unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD,
                            unreal.AttachmentRule.KEEP_WORLD, False)
    cc = cam.get_component_by_class(unreal.CameraComponent)
    if isinstance(cc, unreal.CineCameraComponent):
        cc.set_editor_property("current_focal_length", 30.0)
    else:
        cc.set_field_of_view(55.0)
    mesh.set_only_owner_see(False)
    pc.set_view_target_with_blend(cam, 0.0, unreal.ViewTargetBlendFunction.VT_BLEND_LINEAR, 0.0, False)
    w("camera %s (%s) a %.0f cm do socket" % (nome, cam.get_actor_label(), d))


def jogador():
    world, pawn, pc, mesh, cam = pie()
    cam.detach_from_actor(unreal.DetachmentRule.KEEP_WORLD, unreal.DetachmentRule.KEEP_WORLD, unreal.DetachmentRule.KEEP_WORLD)
    pc.set_view_target_with_blend(pawn, 0.0, unreal.ViewTargetBlendFunction.VT_BLEND_LINEAR, 0.0, False)
    w("camera do jogador")


def main():
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    args = [str(a).lower() for a in sys.argv[1:]]
    try:
        if not args or args[0] == "jogador":
            jogador()
        else:
            ver(args[1] if len(args) > 1 else "frente", float(args[2]) if len(args) > 2 else 20.0)
    except Exception:
        w("ERRO " + traceback.format_exc())


if __name__ == "__main__":
    main()
