# PIE apenas (nada e salvo): valida a camada 1P do ABP_CowboyFP_Visible (alinhamento pescoco/camera + inclinacao).
import os, unreal
saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
LOG = os.path.join(saved, "MixamoFP_fpvis.txt")
open(LOG, "w", encoding="utf-8").write("inicio\n")
IA = "/Game/FPMovement/Player/Input/Actions/"
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
pc = unreal.GameplayStatics.get_player_controller(w, 0)
pawn = pc.get_controlled_pawn()
mesh = pawn.get_editor_property("mesh")
skc = pawn.get_components_by_class(unreal.SkeletalMeshComponent)
vis = next(c for c in skc if c.get_name().startswith("BodyVisible"))
cam = pawn.get_components_by_class(unreal.CameraComponent)[0]
ai = mesh.get_anim_instance()
vai = vis.get_anim_instance()
S = {"i": 0, "t": 0.0, "shot": False, "h": None}


def log(m):
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(m + "\n")


def pitch(p):
    r = pc.get_control_rotation()
    pc.set_control_rotation(unreal.Rotator(roll=0.0, pitch=p, yaw=r.yaw))


def inp(name, idx):
    pawn.call_method("InpActEvt_%s_K2Node_EnhancedInputActionEvent_%d" % (name, idx),
                     (unreal.InputActionValue(), 0.0, 0.0, unreal.load_asset(IA + name)))


def rel(p):
    c = cam.get_world_location()
    f = pawn.get_actor_forward_vector()
    d = p - c
    return "(%.1f,%.1f)" % (d.x * f.x + d.y * f.y, d.z)


def diag(tag):
    lr = vai.get_editor_property("LeanRot")
    log("  [%s] spd=%.0f crouchA=%.2f | vis: StandW=%.2f BodyShift=%.1f Lean=%.1f | fonte pescoco%s | vis pescoco%s peito%s ball_l%s | pitch=%.1f" % (
        tag, ai.get_editor_property("Speed"), ai.get_editor_property("CrouchAlpha"),
        vai.get_editor_property("StandW"), vai.get_editor_property("BodyShift"), lr.roll,
        rel(mesh.get_socket_location("neck_01")), rel(vis.get_socket_location("neck_01")),
        rel(vis.get_socket_location("spine_03")), rel(vis.get_socket_location("ball_l")), cam.get_world_rotation().pitch))


# (nome, dur, direcao(frente,dir) ou None, acao, pitch)
PH = [("idle_0", 1.0, None, None, 0.0),
      ("idle_-45", 1.0, None, None, -45.0),
      ("idle_-75", 1.0, None, None, -75.0),
      ("idle_-89", 1.0, None, None, -89.0),
      ("walk_-60", 1.6, (1, 0), None, -60.0),
      ("walk_0", 1.0, (1, 0), None, 0.0),
      ("sprint_-35", 1.6, (1, 0), "sprint", -35.0),
      ("stop_-75", 1.4, None, "unsprint", -75.0),
      ("crouch_-65", 1.6, None, "crouch", -65.0),
      ("crouch_walk_-50", 1.4, (1, 0), None, -50.0),
      ("uncrouch_-75", 1.6, None, "crouch", -75.0),
      ("end", 0.3, None, None, 0.0)]


def tick(dt):
    try:
        if S["i"] >= len(PH):
            unreal.unregister_slate_post_tick_callback(S["h"])
            log("fim")
            return
        name, dur, d, act, p = PH[S["i"]]
        if S["t"] == 0.0:
            log("fase %s" % name)
            pitch(p)
            if act == "sprint":
                inp("IA_Sprint", 8)
            elif act == "unsprint":
                inp("IA_Sprint", 9)
            elif act == "crouch":
                inp("IA_Crouch", 4)
        if d is not None:
            pawn.add_movement_input(pawn.get_actor_forward_vector() * d[0] + pawn.get_actor_right_vector() * d[1], 1.0, False)
        S["t"] += dt
        if name != "end" and not S["shot"] and S["t"] >= dur * 0.85:
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


S["h"] = unreal.register_slate_post_tick_callback(tick)
