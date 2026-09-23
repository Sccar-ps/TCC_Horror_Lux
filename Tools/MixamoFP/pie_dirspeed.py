# PIE apenas (nada e salvo): velocidades por direcao (BPC_DirectionalSpeed) + maos 1P correndo.
# Configuracoes dos bracos comparadas no mesmo PIE (trocadas so em runtime):
#   old  = ABP_Player original, post process da malha ligado (estado de quando so a mao esquerda aparecia)
#   mid  = ABP_Arms_Cowboy com o post process ABP_Player ainda ligado (depois do arms_fix.py)
#   new  = ABP_Arms_Cowboy e post process desligado (estado salvo agora)
import os, unreal
saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
LOG = os.path.join(saved, "MixamoFP_pie_dirspeed.txt")
open(LOG, "w", encoding="utf-8").write("inicio\n")
IA = "/Game/FPMovement/Player/Input/Actions/"
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
pc = unreal.GameplayStatics.get_player_controller(w, 0)
pawn = pc.get_controlled_pawn()
mesh = pawn.get_editor_property("mesh")
cmc = pawn.get_editor_property("character_movement")
skc = pawn.get_components_by_class(unreal.SkeletalMeshComponent)
vis = next(c for c in skc if c.get_name().startswith("BodyVisible"))
arms = next(c for c in skc if c.get_name().startswith("FirstPersonMesh"))
cam = pawn.get_components_by_class(unreal.CameraComponent)[0]
ds = pawn.get_components_by_class(unreal.load_class(None, "/Game/Characters/MixamoFP/Blueprints/BPC_DirectionalSpeed.BPC_DirectionalSpeed_C"))[0]
ai = mesh.get_anim_instance()
ABP_OLD = unreal.load_class(None, "/Game/FPMovement/Demo/Character/ABP_Player.ABP_Player_C")
ABP_NEW = unreal.load_class(None, "/Game/Characters/MixamoFP/Arms/ABP_Arms_Cowboy.ABP_Arms_Cowboy_C")
FS0 = ds.get_editor_property("ForwardSprintFactor")
R = unreal.Rotator
S = {"i": 0, "t": 0.0, "shots": set(), "h": None, "sprint": False, "crouch": False, "stat": None}
HANDS = []
for side in ("l", "r"):
    HANDS.append(next((b for b in ("middle_02_" + side, "middle_01_" + side, "hand_" + side) if arms.does_socket_exist(b)), "hand_" + side))


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


def arms_state():
    a, pp = arms.get_anim_instance(), arms.get_post_process_instance()
    return "main=%s post_process=%s disable_pp=%s" % (a.get_class().get_name() if a else None, pp.get_class().get_name() if pp else None,
                                                      arms.get_editor_property("disable_post_process_blueprint"))


NEVER = unreal.PropertyAccessChangeNotifyMode.NEVER   # sem PreEditChange/PostEditChange: nao reconstroi o ator no PIE


def arms_cfg(cfg, fs):
    ds.set_editor_property("ForwardSprintFactor", fs, NEVER)
    if cfg is None:
        return
    arms.set_editor_property("disable_post_process_blueprint", cfg == "new", NEVER)
    log("    apos flag: " + arms_state())
    arms.set_anim_instance_class(ABP_OLD if cfg == "old" else ABP_NEW)
    log("    apos set_anim_instance_class: " + arms_state())


def on_screen(loc):
    res = unreal.GameplayStatics.project_world_to_screen(pc, loc, False)
    ok, sp = (res[0], res[1]) if isinstance(res, tuple) else (res is not None, res)
    size = unreal.WidgetLayoutLibrary.get_viewport_size(w)
    return bool(ok) and sp is not None and 0 <= sp.x <= size.x and 0 <= sp.y <= size.y


# (nome, dur, (frente, direita) ou None, sprint, agachar, modo, pitch, fotos, medir_em, bracos(cfg, fator frente), virar, estatistica_maos_desde)
P = [("virar", 0.3, None, False, False, "3p", 0.0, (), None, None, True, None),
     ("andar_frente", 1.2, (1, 0), False, False, "3p", 0.0, (), 1.1, None, False, None),
     ("andar_tras", 1.5, (-1, 0), False, False, "3p", 0.0, (1.2,), 1.4, None, False, None),
     ("correr_frente", 1.3, (1, 0), True, False, "3p", 0.0, (1.0,), 1.2, None, False, None),
     ("correr_tras", 1.7, (-1, 0), True, False, "3p", 0.0, (1.3,), 1.6, None, False, None),
     ("correr_esq", 1.1, (0, -1), True, False, "3p", 0.0, (), 1.0, None, False, None),
     ("correr_dir", 1.1, (0, 1), True, False, "3p", 0.0, (), 1.0, None, False, None),
     ("correr_diag_fe", 1.0, (0.7071, -0.7071), True, False, "3p", 0.0, (), 0.9, None, False, None),
     ("correr_diag_td", 1.0, (-0.7071, 0.7071), True, False, "3p", 0.0, (), 0.9, None, False, None),
     ("andar_esq", 1.0, (0, -1), False, False, "3p", 0.0, (), 0.9, None, False, None),
     ("andar_dir", 1.0, (0, 1), False, False, "3p", 0.0, (), 0.9, None, False, None),
     ("agachar_frente", 1.2, (1, 0), False, True, "3p", 0.0, (), 1.1, None, False, None),
     ("agachar_tras", 1.2, (-1, 0), False, True, "3p", 0.0, (), 1.1, None, False, None),
     ("levantar", 0.8, None, False, False, "3p", 0.0, (), None, None, False, None),
     # ---- maos 1P (pitch 0), vai e volta com meia-volta entre as corridas
     ("fp_old360", 1.5, (1, 0), True, False, "fp", 0.0, (0.9, 1.1, 1.3), 1.4, ("old", 1.0), False, 0.5),
     ("fp_virar1", 0.4, None, False, False, "fp", 0.0, (), None, None, True, None),
     ("fp_mid360", 1.5, (1, 0), True, False, "fp", 0.0, (0.9, 1.1, 1.3), 1.4, ("mid", 1.0), False, 0.5),
     ("fp_virar2", 0.4, None, False, False, "fp", 0.0, (), None, None, True, None),
     ("fp_old450", 1.4, (1, 0), True, False, "fp", 0.0, (0.9, 1.1), 1.3, ("old", 1.25), False, 0.5),
     ("fp_virar3", 0.4, None, False, False, "fp", 0.0, (), None, None, True, None),
     ("fp_new400", 1.5, (1, 0), True, False, "fp", 0.0, (0.9, 1.1, 1.3), 1.4, ("new", FS0), False, 0.5),
     ("fp_new_tras", 1.6, (-1, 0), True, False, "fp", 0.0, (1.0, 1.2), 1.5, None, False, 0.5),
     ("fp_new_andar", 1.2, (1, 0), False, False, "fp", 0.0, (0.9,), 1.1, None, False, 0.4),
     ("parar", 0.6, None, False, False, "fp", 0.0, (), None, None, False, None)]


def finish_stats(name):
    st = S["stat"]
    if st and st["n"]:
        log("  maos %s: %s=%.0f%%  %s=%.0f%%  (quadros=%d)" % (name, HANDS[0], 100.0 * st["l"] / st["n"], HANDS[1], 100.0 * st["r"] / st["n"], st["n"]))
    S["stat"] = None


def tick(dt):
    try:
        if S["i"] >= len(P):
            unreal.unregister_slate_post_tick_callback(S["h"])
            if S["sprint"]:
                inp("IA_Sprint", 9)
            arms_cfg("new", FS0)
            log("fim (config restaurada: new, fator frente %.4f)" % FS0)
            return
        name, dur, d, sprint, crouch, mode, pitch, shots, meas, acfg, turn, stat_from = P[S["i"]]
        if S["t"] == 0.0:
            log("fase %s  pos=(%.0f, %.0f)" % (name, pawn.get_actor_location().x, pawn.get_actor_location().y))
            if turn:
                r = pc.get_control_rotation()
                pc.set_control_rotation(R(roll=0.0, pitch=r.pitch, yaw=r.yaw + 180.0))
            if acfg:
                arms_cfg(*acfg)
            if sprint != S["sprint"]:
                inp("IA_Sprint", 8 if sprint else 9)
                S["sprint"] = sprint
            if crouch != S["crouch"]:
                inp("IA_Crouch", 4)
                S["crouch"] = crouch
        view(mode, pitch)
        if d is not None:
            pawn.add_movement_input(pawn.get_actor_forward_vector() * d[0] + pawn.get_actor_right_vector() * d[1], 1.0, False)
        S["t"] += dt
        if acfg and S["t"] > dt and S["t"] <= 2.5 * dt:
            log("  bracos: " + arms_state())
        if stat_from is not None and S["t"] >= stat_from:
            if S["stat"] is None:
                S["stat"] = {"n": 0, "l": 0, "r": 0}
            st = S["stat"]
            st["n"] += 1
            st["l"] += on_screen(arms.get_socket_location(HANDS[0]))
            st["r"] += on_screen(arms.get_socket_location(HANDS[1]))
        for k, ts in enumerate(shots):
            key = (S["i"], k)
            if key not in S["shots"] and S["t"] >= ts:
                S["shots"].add(key)
                unreal.SystemLibrary.execute_console_command(w, "HighResShot 1")
                log("  foto %s@%.2f" % (name, S["t"]))
        if meas is not None and S["t"] >= meas and ("m", S["i"]) not in S["shots"]:
            S["shots"].add(("m", S["i"]))
            v = pawn.get_velocity()
            log("  medida %s: vel=%.0f  MaxWalkSpeed=%.1f  Base=%.0f Fator=%.3f  ABP Speed=%.0f Dir=%.0f" % (
                name, (v.x ** 2 + v.y ** 2) ** 0.5, cmc.get_editor_property("max_walk_speed"), ds.get_editor_property("BaseSpeed"),
                ds.get_editor_property("Factor"), ai.get_editor_property("Speed"), ai.get_editor_property("Direction")))
        if S["t"] >= dur:
            finish_stats(name)
            S["i"] += 1
            S["t"] = 0.0
    except Exception:
        import traceback
        log("ERRO " + traceback.format_exc())
        unreal.unregister_slate_post_tick_callback(S["h"])


import sys
if len(sys.argv) > 1 and sys.argv[1] == "fp":
    P = [("virar", 0.3, None, False, False, "fp", 0.0, (), None, None, True, None)] + [p for p in P if p[0].startswith("fp_") or p[0] == "parar"]
log("maos medidas: %s | fator frente salvo=%.4f | %s" % (HANDS, FS0, arms_state()))
S["h"] = unreal.register_slate_post_tick_callback(tick)
