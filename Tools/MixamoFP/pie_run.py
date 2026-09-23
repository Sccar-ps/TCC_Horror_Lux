# PIE apenas (nada e salvo): confere a corrida nova (360 cm/s) em 3a pessoa (lado) e em 1a pessoa.
import os, unreal
saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
LOG = os.path.join(saved, "MixamoFP_pie_run.txt")
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
R = unreal.Rotator
S = {"i": 0, "t": 0.0, "shots": set(), "h": None, "sprint": False}


def log(m):
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(m + "\n")


def inp(name, idx):
    pawn.call_method("InpActEvt_%s_K2Node_EnhancedInputActionEvent_%d" % (name, idx),
                     (unreal.InputActionValue(), 0.0, 0.0, unreal.load_asset(IA + name)))


def view(mode, pitch):
    r = pc.get_control_rotation()
    if abs(r.pitch - pitch) > 0.5:
        pc.set_control_rotation(R(roll=0.0, pitch=pitch, yaw=r.yaw))
    third = mode == "3p"
    mesh.set_render_in_main_pass(third)
    vis.set_visibility(not third)
    arms.set_visibility(not third)
    if third:
        cam.set_relative_location_and_rotation(unreal.Vector(0.0, 300.0, -60.0), R(roll=0.0, pitch=-4.0, yaw=-90.0), False, True)
    else:
        cam.set_relative_location_and_rotation(unreal.Vector(0.0, 0.0, 0.0), R(roll=0.0, pitch=0.0, yaw=0.0), False, True)


# (nome, dur, (frente, direita), sprint, modo, pitch, instantes das fotos)
# vai e volta para nao cair da borda do mapa (o 1o teste correu para fora da plataforma)
PH = [("virar", 0.3, None, False, "3p", 0.0, ()),
      ("andar", 1.0, (1, 0), False, "3p", 0.0, (0.85,)),
      ("correr_inicio", 0.4, (1, 0), True, "3p", 0.0, (0.06, 0.14)),
      ("correr_frente", 0.8, (1, 0), True, "3p", 0.0, (0.55, 0.75)),
      ("correr_tras", 1.4, (-1, 0), True, "3p", 0.0, (1.15,)),
      ("correr_esq", 1.2, (0, -1), True, "3p", 0.0, (0.95,)),
      ("correr_dir", 1.2, (0, 1), True, "3p", 0.0, (0.95,)),
      ("correr_1p", 0.9, (1, 0), True, "fp", -30.0, (0.7,)),
      ("parar", 0.8, None, False, "fp", 0.0, ())]


def tick(dt):
    try:
        if S["i"] >= len(PH):
            unreal.unregister_slate_post_tick_callback(S["h"])
            if S["sprint"]:
                inp("IA_Sprint", 9)
            log("fim")
            return
        name, dur, d, sprint, mode, pitch, shots = PH[S["i"]]
        if S["t"] == 0.0:
            log("fase %s  pos=%s" % (name, pawn.get_actor_location()))
            if name == "virar":                  # meia-volta: o espaco livre da plataforma fica para tras
                r = pc.get_control_rotation()
                pc.set_control_rotation(R(roll=0.0, pitch=0.0, yaw=r.yaw + 180.0))
            if sprint and not S["sprint"]:
                inp("IA_Sprint", 8)          # Started: logica do proprio FPMovement (MaxWalkSpeed = MaxSprintSpeed)
                S["sprint"] = True
            elif not sprint and S["sprint"]:
                inp("IA_Sprint", 9)          # Completed
                S["sprint"] = False
        view(mode, pitch)
        if d is not None:
            pawn.add_movement_input(pawn.get_actor_forward_vector() * d[0] + pawn.get_actor_right_vector() * d[1], 1.0, False)
        S["t"] += dt
        for k, ts in enumerate(shots):
            key = (S["i"], k)
            if key not in S["shots"] and S["t"] >= ts:
                S["shots"].add(key)
                unreal.SystemLibrary.execute_console_command(w, "HighResShot 1")
                v = pawn.get_velocity()
                log("  foto %s@%.2f  vel=%.0f  Speed=%.0f Direction=%.0f  MaxWalkSpeed=%.0f" % (
                    name, S["t"], (v.x ** 2 + v.y ** 2) ** 0.5, ai.get_editor_property("Speed"), ai.get_editor_property("Direction"),
                    pawn.get_editor_property("character_movement").get_editor_property("max_walk_speed")))
        if S["t"] >= dur:
            S["i"] += 1
            S["t"] = 0.0
    except Exception:
        import traceback
        log("ERRO " + traceback.format_exc())
        unreal.unregister_slate_post_tick_callback(S["h"])


S["h"] = unreal.register_slate_post_tick_callback(tick)
