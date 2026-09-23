# PIE apenas (nada e salvo): pose das maos 1P em relacao a camera, por configuracao dos bracos.
# Cada corrida comeca do mesmo ponto e na mesma direcao (sem paredes na frente: o ABP dos bracos tem um aditivo
# "perto da parede" que mexe nas maos e contaminava o teste anterior).
#   old = ABP_Player original | new = ABP_Arms_Cowboy + post process desligado (estado salvo)
import os, math, unreal
saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
LOG = os.path.join(saved, "MixamoFP_pie_arms2.txt")
open(LOG, "w", encoding="utf-8").write("inicio\n")
IA = "/Game/FPMovement/Player/Input/Actions/"
NEVER = unreal.PropertyAccessChangeNotifyMode.NEVER
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
pc = unreal.GameplayStatics.get_player_controller(w, 0)
pawn = pc.get_controlled_pawn()
skc = pawn.get_components_by_class(unreal.SkeletalMeshComponent)
arms = next(c for c in skc if c.get_name().startswith("FirstPersonMesh"))
cams = pawn.get_components_by_class(unreal.CameraComponent)
cam = cams[0]
ds = pawn.get_components_by_class(unreal.load_class(None, "/Game/Characters/MixamoFP/Blueprints/BPC_DirectionalSpeed.BPC_DirectionalSpeed_C"))[0]
ABP_OLD = unreal.load_class(None, "/Game/FPMovement/Demo/Character/ABP_Player.ABP_Player_C")
ABP_NEW = unreal.load_class(None, "/Game/Characters/MixamoFP/Arms/ABP_Arms_Cowboy.ABP_Arms_Cowboy_C")
FS0 = ds.get_editor_property("ForwardSprintFactor")
Z0 = pawn.get_actor_location().z
R = unreal.Rotator
BONES = ("middle_02_l", "middle_02_r")
S = {"i": 0, "t": 0.0, "h": None, "sprint": False, "acc": None, "shots": set()}


def log(m):
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(m + "\n")


def inp(name, idx):
    pawn.call_method("InpActEvt_%s_K2Node_EnhancedInputActionEvent_%d" % (name, idx),
                     (unreal.InputActionValue(), 0.0, 0.0, unreal.load_asset(IA + name)))


def cfg(which, fs):
    ds.set_editor_property("ForwardSprintFactor", fs, NEVER)
    arms.set_editor_property("disable_post_process_blueprint", which == "new", NEVER)
    arms.set_anim_instance_class(ABP_OLD if which == "old" else ABP_NEW)


def cam_space(p):
    """(frente, direita, cima) em cm e (azimute, elevacao) em graus, relativos a camera."""
    t = cam.get_world_transform()
    l = t.inverse_transform_location(p)
    return l.x, l.y, l.z, math.degrees(math.atan2(l.y, l.x)), math.degrees(math.atan2(l.z, l.x))


try:
    fov = cam.get_editor_property("field_of_view")
    extra = []
    for k in ("enable_first_person_field_of_view", "first_person_field_of_view", "enable_first_person_scale", "first_person_scale"):
        try:
            extra.append("%s=%s" % (k, cam.get_editor_property(k)))
        except Exception:
            pass
    try:
        extra.append("arms.first_person_primitive_type=%s" % arms.get_editor_property("first_person_primitive_type"))
    except Exception:
        pass
    vp = unreal.WidgetLayoutLibrary.get_viewport_size(w)
    vfov = math.degrees(2 * math.atan(math.tan(math.radians(fov / 2)) * vp.y / vp.x))
    log("camera %s fov=%.1f (vertical %.1f) viewport=%dx%d | cameras=%s | %s" % (cam.get_name(), fov, vfov, vp.x, vp.y,
        [c.get_name() for c in cams], " ".join(extra)))
except Exception as e:
    fov, vfov = 90.0, 58.7
    log("camera info: %s" % e)

# (nome, config, fator frente, sentido (+1 frente / -1 tras), sprint, x inicial)
RUNS = [("old360", "old", 1.0, 1, True, -760.0), ("old450", "old", 1.25, 1, True, -760.0),
        ("new400", "new", FS0, 1, True, -760.0), ("new_tras288", "new", FS0, -1, True, -60.0),
        ("new_andar150", "new", FS0, 1, False, -500.0)]
PREP, RUN = 0.5, 1.4


def tick(dt):
    try:
        if S["i"] >= len(RUNS):
            unreal.unregister_slate_post_tick_callback(S["h"])
            if S["sprint"]:
                inp("IA_Sprint", 9)
            cfg("new", FS0)
            log("fim (config restaurada)")
            return
        name, which, fs, sense, sprint, x0 = RUNS[S["i"]]
        if S["t"] == 0.0:
            if S["sprint"]:
                inp("IA_Sprint", 9)
                S["sprint"] = False
            pawn.set_actor_location(unreal.Vector(x0, 0.0, Z0), False, True)
            pc.set_control_rotation(R(roll=0.0, pitch=0.0, yaw=0.0))
            cfg(which, fs)
            S["acc"] = {"n": 0, "wall": 0.0, "spd": 0.0, "vis": [0, 0], "fz": [[], []]}
        S["t"] += dt
        t = S["t"]
        r = pc.get_control_rotation()
        if abs(r.pitch) > 0.2 or abs(r.yaw) > 0.2:
            pc.set_control_rotation(R(roll=0.0, pitch=0.0, yaw=0.0))
        if t > PREP:
            if sprint and not S["sprint"]:
                inp("IA_Sprint", 8)
                S["sprint"] = True
            pawn.add_movement_input(pawn.get_actor_forward_vector() * float(sense), 1.0, False)
        if t > PREP + 0.6:
            a = S["acc"]
            a["n"] += 1
            ai = arms.get_anim_instance()
            try:
                a["wall"] = max(a["wall"], ai.get_editor_property("CloseToWall"))
                a["spd"] += ai.get_editor_property("Speed")
            except Exception:
                pass
            for k, b in enumerate(BONES):
                fx, ry, up, az, el = cam_space(arms.get_socket_location(b))
                a["fz"][k].append((round(fx), round(ry), round(up), round(az, 1), round(el, 1)))
                if fx > 0 and abs(az) < fov / 2 and abs(el) < vfov / 2:
                    a["vis"][k] += 1
            for k, ts in enumerate((PREP + 0.8, PREP + 1.0, PREP + 1.2)):
                key = (S["i"], k)
                if key not in S["shots"] and t >= ts:
                    S["shots"].add(key)
                    unreal.SystemLibrary.execute_console_command(w, "HighResShot 1")
                    log("  foto %s@%.2f" % (name, t))
        if t >= PREP + RUN:
            a = S["acc"]
            v = pawn.get_velocity()
            n = max(1, a["n"])
            log("%s: vel=%.0f  Speed(bracos)=%.0f  CloseToWall max=%.2f  quadros=%d  main=%s" % (
                name, (v.x ** 2 + v.y ** 2) ** 0.5, a["spd"] / n, a["wall"], a["n"], arms.get_anim_instance().get_class().get_name()))
            for k, b in enumerate(BONES):
                pts = a["fz"][k]
                if pts:
                    els = [p[4] for p in pts]
                    azs = [p[3] for p in pts]
                    log("   %s: no quadro %.0f%% | elevacao min/med/max = %.1f/%.1f/%.1f | azimute min/max = %.1f/%.1f" % (
                        b, 100.0 * a["vis"][k] / n, min(els), sum(els) / len(els), max(els), min(azs), max(azs)))
                    log("      amostras (frente,dir,cima,az,el): %s" % pts[::6])
            S["i"] += 1
            S["t"] = 0.0
    except Exception:
        import traceback
        log("ERRO " + traceback.format_exc())
        unreal.unregister_slate_post_tick_callback(S["h"])


S["h"] = unreal.register_slate_post_tick_callback(tick)
