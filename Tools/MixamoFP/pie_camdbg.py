# PIE: rastreia a camera (relativa/mundo) enquanto anda, corre e agacha, para achar o que desloca a camera.
import os, unreal
saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
LOG = os.path.join(saved, "MixamoFP_camdbg.txt")
open(LOG, "w", encoding="utf-8").write("inicio\n")
IA = "/Game/FPMovement/Player/Input/Actions/"
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
pc = unreal.GameplayStatics.get_player_controller(w, 0)
pawn = pc.get_controlled_pawn()
cam = pawn.get_components_by_class(unreal.CameraComponent)[0]
arm = pawn.get_components_by_class(unreal.SpringArmComponent)[0]
cmc = pawn.get_editor_property("character_movement")
S = {"t": 0.0, "k": 0, "h": None, "phase": ""}


def log(m):
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(m + "\n")


def fmt(v):
    return "(%.0f,%.0f,%.0f)" % (v.x, v.y, v.z)


log("cam=%s parent=%s arm=%s arm_parent=%s absolute_loc=%s" % (cam.get_name(), cam.get_attach_parent().get_name() if cam.get_attach_parent() else None,
    arm.get_name(), arm.get_attach_parent().get_name() if arm.get_attach_parent() else None, cam.get_editor_property("absolute_location")))
log("arm lag=%s rotlag=%s len=%s" % (arm.get_editor_property("enable_camera_lag"), arm.get_editor_property("enable_camera_rotation_lag"), arm.get_editor_property("target_arm_length")))
PH = [("walk", 1.5, (1, 0)), ("sprint", 1.5, (1, 0)), ("crouch", 1.5, None), ("crouch_walk", 1.5, (1, 0)), ("uncrouch", 1.0, None)]


def tick(dt):
    try:
        S["t"] += dt
        ph = int(S["t"] // 1.5)
        if ph >= len(PH):
            unreal.unregister_slate_post_tick_callback(S["h"])
            log("fim")
            return
        name, dur, d = PH[ph]
        if name != S["phase"]:
            S["phase"] = name
            log("fase %s" % name)
            if name == "sprint":
                cmc.set_editor_property("max_walk_speed", 450.0)
            if name in ("crouch", "uncrouch"):
                cmc.set_editor_property("max_walk_speed", 150.0)
                pawn.call_method("InpActEvt_IA_Crouch_K2Node_EnhancedInputActionEvent_4", (unreal.InputActionValue(), 0.0, 0.0, unreal.load_asset(IA + "IA_Crouch")))
        if d:
            pawn.add_movement_input(pawn.get_actor_forward_vector(), 1.0, False)
        if S["t"] >= S["k"] * 0.25:
            S["k"] += 1
            p = pawn.get_actor_location()
            c = cam.get_world_location()
            log("  t=%.2f pawn=%s cam-pawn=%s camRel=%s camRelRot=%s armRel=%s vt=%s" % (S["t"], fmt(p), fmt(c - p), fmt(cam.get_editor_property("relative_location")),
                cam.get_editor_property("relative_rotation"), fmt(arm.get_editor_property("relative_location")), pc.get_view_target().get_name()))
    except Exception:
        import traceback
        log("ERRO " + traceback.format_exc())
        unreal.unregister_slate_post_tick_callback(S["h"])


S["h"] = unreal.register_slate_post_tick_callback(tick)
