# PIE apenas (nada e salvo): compara variantes da visao 1P olhando para baixo.
# Mexe so no componente BodyVisible (offset/rotacao relativos) via funcoes de runtime.
import os, unreal
saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
LOG = os.path.join(saved, "MixamoFP_fpvar2.txt")
open(LOG, "w", encoding="utf-8").write("inicio\n")
IA = "/Game/FPMovement/Player/Input/Actions/"
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
pc = unreal.GameplayStatics.get_player_controller(w, 0)
pawn = pc.get_controlled_pawn()
mesh = pawn.get_editor_property("mesh")
skc = pawn.get_components_by_class(unreal.SkeletalMeshComponent)
vis = next(c for c in skc if c.get_name().startswith("BodyVisible"))
arms = next(c for c in skc if c.get_name().startswith("FirstPersonMesh"))
cam = pawn.get_components_by_class(unreal.CameraComponent)[0]
ai = mesh.get_anim_instance()
S = {"i": 0, "t": 0.0, "shot": False, "h": None}
V0 = vis.get_editor_property("relative_location")
R0 = vis.get_editor_property("relative_rotation")


def log(m):
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(m + "\n")


def safe(f):
    try:
        return f()
    except Exception as e:
        return "?(%s)" % str(e)[:60]


log("vis rel=%s rot=%s parent=%s" % (V0, R0, vis.get_attach_parent().get_name()))
log("arms mesh=%s parent=%s rel=%s visible=%s anim=%s fov=%s" % (
    safe(lambda: arms.get_skeletal_mesh_asset().get_name()), safe(lambda: arms.get_attach_parent().get_name()),
    safe(lambda: arms.get_editor_property("relative_location")), arms.is_visible(),
    safe(lambda: arms.get_anim_instance().get_class().get_name()), safe(lambda: cam.get_editor_property("field_of_view"))))


def pitch(p):
    r = pc.get_control_rotation()
    pc.set_control_rotation(unreal.Rotator(roll=0.0, pitch=p, yaw=r.yaw))


def off(back=0.0, roll=0.0):
    # BodyVisible e filho do Mesh (yaw -90): no espaco do Mesh, -Y = para tras.
    vis.set_relative_location_and_rotation(unreal.Vector(V0.x, V0.y - back, V0.z),
                                           unreal.Rotator(roll=R0.roll + roll, pitch=R0.pitch, yaw=R0.yaw), False, True)


def crouch():
    pawn.call_method("InpActEvt_IA_Crouch_K2Node_EnhancedInputActionEvent_4",
                     (unreal.InputActionValue(), 0.0, 0.0, unreal.load_asset(IA + "IA_Crouch")))


def rel(p):
    c = cam.get_world_location()
    f = pawn.get_actor_forward_vector()
    d = p - c
    return "(frente=%.1f, dz=%.1f)" % (d.x * f.x + d.y * f.y, d.z)


def diag(tag):
    log("  shot %s crouchA=%.2f root=(%.0f,%.0f,%.0f) | vis spine_03%s pelvis%s knee_l%s ball_l%s | cam_pitch=%.1f" % (
        tag, ai.get_editor_property("CrouchAlpha"), *[getattr(ai.get_editor_property("RootOffset"), k) for k in "xyz"],
        rel(vis.get_socket_location("spine_03")), rel(vis.get_socket_location("pelvis")),
        rel(vis.get_socket_location("calf_l")), rel(vis.get_socket_location("ball_l")),
        cam.get_world_rotation().pitch))


# (nome, dur, acao)
PH = [("P0_frente", 1.0, lambda: (pitch(0.0), off())),
      ("A_-75", 1.0, lambda: pitch(-75.0)),
      ("B_-75_tras10", 0.8, lambda: off(10.0)),
      ("C_-75_tras20", 0.8, lambda: off(20.0)),
      ("D_-55_tras20", 0.9, lambda: pitch(-55.0)),
      ("E_-75_roll+8", 0.9, lambda: (pitch(-75.0), off(0.0, 8.0))),
      ("F_-75_roll-8", 0.8, lambda: off(0.0, -8.0)),
      ("G_agach_-65", 1.6, lambda: (off(), pitch(-65.0), crouch())),
      ("H_agach_-65_tras10", 0.8, lambda: off(10.0)),
      ("I_agach_-40_tras10", 0.9, lambda: pitch(-40.0)),
      ("J_agach_-65_roll+8", 0.9, lambda: (pitch(-65.0), off(0.0, 8.0))),
      ("K_agach_-65_roll-8", 0.8, lambda: off(0.0, -8.0)),
      ("fim", 1.6, lambda: (off(), pitch(0.0), crouch()))]


def tick(dt):
    try:
        if S["i"] >= len(PH):
            unreal.unregister_slate_post_tick_callback(S["h"])
            log("fim crouchA=%.2f" % ai.get_editor_property("CrouchAlpha"))
            return
        name, dur, act = PH[S["i"]]
        if S["t"] == 0.0:
            act()
            log("fase %s" % name)
        S["t"] += dt
        if name != "fim" and not S["shot"] and S["t"] >= dur * 0.8:
            unreal.SystemLibrary.execute_console_command(w, "HighResShot 1")
            S["shot"] = True
            diag(name)
        if S["t"] >= dur:
            S["i"] += 1
            S["t"] = 0.0
            S["shot"] = False
    except Exception:
        import traceback
        log("ERRO " + traceback.format_exc())
        unreal.unregister_slate_post_tick_callback(S["h"])
        off()


S["h"] = unreal.register_slate_post_tick_callback(tick)
