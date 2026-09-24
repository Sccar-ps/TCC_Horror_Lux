# PIE apenas (nada e salvo): forca a exposicao da camera do jogador para medir como o aviso reporta "Exposure".
# Uso: py ".../pie_exposure_probe.py" <ev100_min> <ev100_max> <bias>    |  sem argumentos = remove os overrides
import sys, unreal
ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
gw = ues.get_game_world()
pawn = unreal.GameplayStatics.get_player_controller(gw, 0).get_controlled_pawn()
cam = pawn.get_components_by_class(unreal.CameraComponent)[0]
pps = cam.get_editor_property("post_process_settings")
args = [float(a) for a in sys.argv[1:]]
on = len(args) == 3
for f in ("auto_exposure_min_brightness", "auto_exposure_max_brightness", "auto_exposure_bias"):
    pps.set_editor_property("override_" + f, on)
if on:
    pps.set_editor_property("auto_exposure_min_brightness", args[0])
    pps.set_editor_property("auto_exposure_max_brightness", args[1])
    pps.set_editor_property("auto_exposure_bias", args[2])
cam.set_editor_property("post_process_settings", pps)
unreal.log("probe exposure: %s" % (args if on else "overrides removidos"))
