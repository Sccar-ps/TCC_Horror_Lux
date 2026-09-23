# PIE apenas: verifica se a malha-sombra (Mesh, fora do main pass) projeta sombra na visao 1P.
# Para cada yaw tira 2 fotos: sombra ligada / desligada (set_cast_shadow e funcao de runtime; nada e salvo).
import os, unreal
saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
LOG = os.path.join(saved, "MixamoFP_shadow.txt")
open(LOG, "w", encoding="utf-8").write("inicio\n")
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
pc = unreal.GameplayStatics.get_player_controller(w, 0)
pawn = pc.get_controlled_pawn()
mesh = pawn.get_editor_property("mesh")
S = {"i": 0, "t": 0.0, "shot": False, "h": None}
PH = []
for yaw in (0.0, 90.0, 180.0, 270.0):
    PH.append(("yaw%d_on" % yaw, 1.0, yaw, True))
    PH.append(("yaw%d_off" % yaw, 0.6, yaw, False))
PH.append(("fim", 0.2, 0.0, True))


def log(m):
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(m + "\n")


def tick(dt):
    try:
        if S["i"] >= len(PH):
            unreal.unregister_slate_post_tick_callback(S["h"])
            log("fim")
            return
        name, dur, yaw, shadow = PH[S["i"]]
        if S["t"] == 0.0:
            pc.set_control_rotation(unreal.Rotator(roll=0.0, pitch=-60.0, yaw=yaw))
            mesh.set_cast_shadow(shadow)
            log("fase %s" % name)
        S["t"] += dt
        if name != "fim" and not S["shot"] and S["t"] >= dur * 0.8:
            unreal.SystemLibrary.execute_console_command(w, "HighResShot 1")
            S["shot"] = True
        if S["t"] >= dur:
            S["i"] += 1
            S["t"] = 0.0
            S["shot"] = False
    except Exception:
        import traceback
        log("ERRO " + traceback.format_exc())
        unreal.unregister_slate_post_tick_callback(S["h"])
        mesh.set_cast_shadow(True)


S["h"] = unreal.register_slate_post_tick_callback(tick)
