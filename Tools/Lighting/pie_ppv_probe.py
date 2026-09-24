# PIE apenas (nada e salvo): cria/atualiza um PostProcessVolume unbound no mundo do PIE para testar faixas de exposicao.
# Uso: py ".../pie_ppv_probe.py" <ev100_min> <ev100_max> <bias>   |  sem argumentos = remove o volume de teste
import sys, unreal
ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
gw = ues.get_game_world()
TAG = "PIE_PROBE_PPV"
ppv = None
for a in unreal.GameplayStatics.get_all_actors_of_class(gw, unreal.PostProcessVolume):
    if a.actor_has_tag(TAG):
        ppv = a
args = [float(a) for a in sys.argv[1:]]
if len(args) != 3:
    if ppv:
        ppv.destroy_actor()
    unreal.log("probe ppv removido")
else:
    if not ppv:
        xf = unreal.Transform()
        ppv = unreal.GameplayStatics.begin_deferred_actor_spawn_from_class(gw, unreal.PostProcessVolume, xf)
        ppv = unreal.GameplayStatics.finish_spawning_actor(ppv, xf)
        ppv.tags = [TAG]
    ppv.set_editor_property("unbound", True)
    ppv.set_editor_property("priority", 1000.0)
    s = ppv.get_editor_property("settings")
    for f, v in (("auto_exposure_min_brightness", args[0]), ("auto_exposure_max_brightness", args[1]), ("auto_exposure_bias", args[2])):
        s.set_editor_property("override_" + f, True)
        s.set_editor_property(f, v)
    ppv.set_editor_property("settings", s)
    unreal.log("probe ppv: %s em %s" % (args, ppv.get_world().get_name()))
