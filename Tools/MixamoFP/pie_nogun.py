# PIE apenas (nada e salvo): confere o Cowboy sem coldre/revolver em 3a pessoa (frente, lado, costas, cintura) e em 1P.
import os, unreal
saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
LOG = os.path.join(saved, "MixamoFP_pie_nogun.txt")
open(LOG, "w", encoding="utf-8").write("inicio\n")
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
pc = unreal.GameplayStatics.get_player_controller(w, 0)
pawn = pc.get_controlled_pawn()
mesh = pawn.get_editor_property("mesh")
skc = pawn.get_components_by_class(unreal.SkeletalMeshComponent)
vis = next(c for c in skc if c.get_name().startswith("BodyVisible"))
arms = next(c for c in skc if c.get_name().startswith("FirstPersonMesh"))
cam = pawn.get_components_by_class(unreal.CameraComponent)[0]
S = {"i": 0, "t": 0.0, "shot": False, "h": None}
R = unreal.Rotator


def log(m):
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(m + "\n")


log("pawn=%s mesh=%s vis=%s" % (pawn.get_class().get_name(), mesh.get_skeletal_mesh_asset().get_name(), vis.get_skeletal_mesh_asset().get_name()))
# (nome, dur, modo, pitch, loc relativa da camera, rot relativa)
PH = [("frente", 1.0, "3p", 0.0, unreal.Vector(260.0, 0.0, -60.0), R(roll=0.0, pitch=-4.0, yaw=180.0)),
      ("lado", 0.8, "3p", 0.0, unreal.Vector(0.0, 260.0, -60.0), R(roll=0.0, pitch=-4.0, yaw=-90.0)),
      ("costas", 0.8, "3p", 0.0, unreal.Vector(-260.0, 0.0, -60.0), R(roll=0.0, pitch=-4.0, yaw=0.0)),
      ("cintura_frente", 0.8, "3p", 0.0, unreal.Vector(95.0, 0.0, -75.0), R(roll=0.0, pitch=0.0, yaw=180.0)),
      ("cintura_direita", 0.8, "3p", 0.0, unreal.Vector(0.0, 95.0, -75.0), R(roll=0.0, pitch=0.0, yaw=-90.0)),
      ("cintura_esquerda", 0.8, "3p", 0.0, unreal.Vector(0.0, -95.0, -75.0), R(roll=0.0, pitch=0.0, yaw=90.0)),
      ("fp_baixo_-75", 1.0, "fp", -75.0, None, None),
      ("fp_baixo_-89", 0.8, "fp", -89.0, None, None),
      ("fim", 0.3, "fp", 0.0, None, None)]


def set_mode(mode, p, loc, rot):
    r = pc.get_control_rotation()
    pc.set_control_rotation(R(roll=0.0, pitch=p, yaw=r.yaw))
    third = mode == "3p"
    mesh.set_render_in_main_pass(third)
    vis.set_visibility(not third)
    arms.set_visibility(not third)
    if third:
        cam.set_relative_location_and_rotation(loc, rot, False, True)
    else:
        cam.set_relative_location_and_rotation(unreal.Vector(0.0, 0.0, 0.0), R(roll=0.0, pitch=0.0, yaw=0.0), False, True)


def tick(dt):
    try:
        if S["i"] >= len(PH):
            unreal.unregister_slate_post_tick_callback(S["h"])
            log("fim")
            return
        name, dur, mode, p, loc, rot = PH[S["i"]]
        if S["t"] == 0.0:
            log("fase %s" % name)
        set_mode(mode, p, loc, rot)            # reaplica todo frame (Crouch_TL/headbob mexem na camera)
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


S["h"] = unreal.register_slate_post_tick_callback(tick)
