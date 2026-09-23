# PIE apenas (nada e salvo): percorre as fases de locomocao do BP_Player_Cowboy, com camera externa (3P)
# e camera normal (1P), medindo pes/pelvis/camera e tirando HighResShot em cada fase.
import os, math, unreal
saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
LOG = os.path.join(saved, "MixamoFP_pie.txt")
open(LOG, "w", encoding="utf-8").write("inicio\n")
BPP = "/Game/FPMovement/Player/Blueprints/BP_Player.BP_Player_C:"
IA = "/Game/FPMovement/Player/Input/Actions/"
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
pc = unreal.GameplayStatics.get_player_controller(w, 0)
pawn = pc.get_controlled_pawn()
S = {"i": 0, "t": 0.0, "shot": False, "h": None, "yaw0": None}


def log(m):
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(m + "\n")


def prop(o, n):
    try:
        return o.get_editor_property(n)
    except Exception as e:
        return "?(%s)" % str(e)[:40]


def comps(cls):
    return pawn.get_components_by_class(cls)


mesh = pawn.get_editor_property("mesh")
cap = pawn.get_editor_property("capsule_component")
cmc = pawn.get_editor_property("character_movement")
vis = next((c for c in comps(unreal.SkeletalMeshComponent) if c.get_name().startswith("BodyVisible")), None)
arms = next((c for c in comps(unreal.SkeletalMeshComponent) if c.get_name().startswith("FirstPersonMesh")), None)
cam = next((c for c in comps(unreal.CameraComponent)), None)
log("pawn=%s classe=%s mesh=%s vis=%s arms=%s cam=%s" % (pawn.get_name(), pawn.get_class().get_name(), mesh.get_name(), vis and vis.get_name(), arms and arms.get_name(), cam and cam.get_name()))


def call_input(ia_name, idx):
    fn = "InpActEvt_%s_K2Node_EnhancedInputActionEvent_%d" % (ia_name, idx)
    try:
        pawn.call_method(fn, (unreal.InputActionValue(), 0.0, 0.0, unreal.load_asset(IA + ia_name)))
        log("  input %s" % fn)
    except Exception as e:
        log("  input %s erro %s" % (fn, e))


def set_view(mode, pitch=0.0):
    r = pc.get_control_rotation()
    pc.set_control_rotation(unreal.Rotator(roll=0.0, pitch=pitch, yaw=r.yaw))
    if mode == "3p":
        mesh.set_render_in_main_pass(True)
        if vis:
            vis.set_visibility(False)
        if arms:
            arms.set_visibility(False)
        cam.set_relative_location_and_rotation(unreal.Vector(0.0, 260.0, -60.0), unreal.Rotator(roll=0.0, pitch=-6.0, yaw=-90.0), False, True)
    else:
        mesh.set_render_in_main_pass(False)
        if vis:
            vis.set_visibility(True)
        if arms:
            arms.set_visibility(True)
        cam.set_relative_location_and_rotation(unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0), False, True)


def diag(tag):
    ai = mesh.get_anim_instance()
    loc = pawn.get_actor_location()
    half = cap.get_scaled_capsule_half_height()
    floor = loc.z - half
    parts = []
    for b in ("foot_l", "foot_r", "ball_l", "pelvis", "spine_03", "head"):
        parts.append("%s=%.1f" % (b, mesh.get_socket_location(b).z - floor))
    cam_w = cam.get_world_location()
    fwd = pawn.get_actor_forward_vector()
    head = mesh.get_socket_location("neck_01")
    chest = mesh.get_socket_location("spine_03")
    dz_head = head.z - cam_w.z
    df_head = (head - cam_w).dot(fwd)
    df_chest = (chest - cam_w).dot(fwd)
    log("[%s] spd=%.0f dir=%.0f crouchA=%.2f airA=%.2f root=%s | %s | cam=%.1f pescoco(dz=%.1f,frente=%.1f) peito_frente=%.1f | vel=%.0f" % (
        tag, prop(ai, "Speed"), prop(ai, "Direction"), prop(ai, "CrouchAlpha"), prop(ai, "InAirAlpha"),
        prop(ai, "RootOffset"), " ".join(parts), cam_w.z - floor, dz_head, df_head, df_chest, pawn.get_velocity().length()))


# (nome, dur, direcao (fwd,right) ou None, acao, vista, pitch)
PH = [("prep", 0.5, None, "prep", "3p", 0.0),
      ("idle", 1.0, None, None, "3p", 0.0),
      ("walk_f", 1.4, (1, 0), None, "3p", 0.0),
      ("walk_l", 1.4, (0, -1), None, "3p", 0.0),
      ("walk_b", 1.4, (-1, 0), None, "3p", 0.0),
      ("sprint_f", 1.4, (1, 0), "sprint", "3p", 0.0),
      ("crouch_idle", 1.2, None, "crouch", "3p", 0.0),
      ("crouch_f", 1.4, (1, 0), None, "3p", 0.0),
      ("crouch_r", 1.4, (0, 1), None, "3p", 0.0),
      ("fp_crouch_down", 1.0, None, None, "fp", -65.0),
      ("fp_crouch_walk", 1.2, (1, 0), None, "fp", -55.0),
      ("uncrouch", 1.2, None, "crouch", "fp", -65.0),
      ("fp_walk_down", 1.2, (1, 0), None, "fp", -60.0),
      ("fp_idle_down", 1.0, None, None, "fp", -75.0),
      ("jump", 0.5, None, "jump", "3p", 0.0),
      ("end", 0.3, None, "end", "fp", 0.0)]
SHOT = {"idle", "walk_f", "walk_l", "walk_b", "sprint_f", "crouch_idle", "crouch_f", "crouch_r", "fp_crouch_down", "fp_crouch_walk", "uncrouch", "fp_walk_down", "fp_idle_down", "jump"}


def tick(dt):
    try:
        if S["i"] >= len(PH):
            unreal.unregister_slate_post_tick_callback(S["h"])
            log("fim")
            return
        name, dur, d, act, view, pitch = PH[S["i"]]
        if S["t"] == 0.0:
            log("fase %s" % name)
            set_view(view, pitch)
            if act == "sprint":
                cmc.set_editor_property("max_walk_speed", 450.0)
            elif S["i"] > 0 and PH[S["i"] - 1][3] == "sprint":
                cmc.set_editor_property("max_walk_speed", 150.0)
            if act == "crouch":
                call_input("IA_Crouch", 4)
            if act == "jump":
                call_input("IA_Jump", 10)
                pawn.jump()
            if act == "end":
                cmc.set_editor_property("max_walk_speed", 150.0)
        if d is not None:
            fwd = pawn.get_actor_forward_vector()
            right = pawn.get_actor_right_vector()
            pawn.add_movement_input(fwd * d[0] + right * d[1], 1.0, False)
        S["t"] += dt
        if name in SHOT and not S["shot"] and S["t"] >= dur * (0.6 if name == "jump" else 0.8):
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
