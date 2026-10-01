# Cria/atualiza o PostProcessVolume global do mapa aberto (editor, NAO salva o mapa).
# Uso (console do editor):
#   py ".../Tools/Lighting/apply_ppv_global.py"                -> valores recomendados (ver PRESET abaixo)
#   py ".../Tools/Lighting/apply_ppv_global.py" <min> <max> <bias>   -> so troca a faixa de exposicao (teste)
# Idempotente: procura o volume pela tag LUX_PPV_GLOBAL e so atualiza. Desfazer: Ctrl+Z ou apagar o ator PPV_Global.
# DEPOIS deste script rode vela_legibilidade.py instalar (01/10/2026): o mesmo PPV_Global ganha a mascara de metragem da exposicao
# (a mao e a vela deixam de puxar a exposicao) e o motion blur 0. Este script nao conhece essas propriedades e nao as desfaz.
import os, sys, unreal

TAG = "LUX_PPV_GLOBAL"
saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
OUT = os.path.join(saved, "LightingApplyPPV.txt")

# ---- PRESET "horror escuro" para RTX 5060 / 8 GB ----
# Faixa segura do cache com r.EyeAdaptation.CachedLightingPreExposure=1  ->  [1-12, 1+8] = [-11, +9]
# O aviso compara "Exposure" = EV100 - AutoExposureBias (medido no editor). Com min -8 / max 8 / bias 1
# a exposicao efetiva fica em [-9, +7]: 2 EV de folga para cada lado (flashes de fotofobia via bias, lampadas estourando).
PRESET = {
    # Exposicao: histograma mantido (adaptacao do olho e parte do jogo: fotofobia), mas presa dentro da faixa segura
    "auto_exposure_method": unreal.AutoExposureMethod.AEM_HISTOGRAM,
    "auto_exposure_min_brightness": -8.0,   # EV100 mais escuro que a camera "enxerga": escuro continua escuro
    "auto_exposure_max_brightness": 8.0,    # teto: lampada/lanterna na cara nao leva a exposicao para fora da faixa
    "auto_exposure_bias": 1.0,              # = valor efetivo atual do projeto (r.DefaultFeature.AutoExposure.Bias=1)
    "histogram_log_min": -10.0,             # 64 buckets em 20 EV (em vez de 30): medicao mais fina
    "histogram_log_max": 10.0,
    "auto_exposure_speed_up": 3.0,
    "auto_exposure_speed_down": 1.0,
    # Lumen: a casa e um interior pequeno; nao precisa de cena Lumen de 200 m
    "lumen_scene_view_distance": None,      # cm (padrao 20000) -> calculado pela diagonal do mapa, ver abaixo
    "lumen_max_trace_distance": None,       # cm (padrao 20000)
    "lumen_skylight_leaking": 0.0,
}


def log(msg, lines=[]):
    lines.append(str(msg))
    open(OUT, "w", encoding="utf-8").write("\n".join(lines))


ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
if ues.get_game_world():
    raise RuntimeError("Pare o PIE antes (o volume precisa ir para o mundo do editor).")
w = ues.get_editor_world()
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

ppv = None
for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.PostProcessVolume):
    if a.actor_has_tag(TAG):
        ppv = a
created = False
with unreal.ScopedEditorTransaction("LUX: PPV_Global"):
    if ppv is None:
        ppv = eas.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector(0, 0, 0))
        ppv.set_actor_label("PPV_Global")
        ppv.tags = [TAG]
        created = True
    ppv.modify()
    ppv.set_editor_property("unbound", True)
    ppv.set_editor_property("priority", 0.0)
    ppv.set_editor_property("blend_weight", 1.0)
    ppv.set_editor_property("enabled", True)

    # diagonal dos StaticMeshActors do projeto (/Game) -> distancia minima para a cena Lumen cobrir a casa inteira
    lo, hi = None, None
    for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.StaticMeshActor):
        smc = a.get_component_by_class(unreal.StaticMeshComponent)
        sm = smc.get_editor_property("static_mesh") if smc else None
        if not sm or not sm.get_path_name().startswith("/Game/"):
            continue
        o, e = a.get_actor_bounds(False)
        mn, mx = o - e, o + e
        lo = mn if lo is None else unreal.Vector(min(lo.x, mn.x), min(lo.y, mn.y), min(lo.z, mn.z))
        hi = mx if hi is None else unreal.Vector(max(hi.x, mx.x), max(hi.y, mx.y), max(hi.z, mx.z))
    diag = (hi - lo).length() if lo else 20000.0
    dist = float(min(20000, max(4000, int(diag * 1.25 / 500 + 1) * 500)))
    log("bounds /Game: %s .. %s | diagonal %.0f cm -> distancia Lumen %.0f cm" % (lo, hi, diag, dist))

    s = ppv.get_editor_property("settings")
    values = dict(PRESET)
    values["lumen_scene_view_distance"] = dist
    values["lumen_max_trace_distance"] = dist
    args = [float(a) for a in sys.argv[1:]]
    if len(args) == 3:
        values = {"auto_exposure_min_brightness": args[0], "auto_exposure_max_brightness": args[1],
                  "auto_exposure_bias": args[2]}
    for k, v in values.items():
        s.set_editor_property("override_" + k, True)
        s.set_editor_property(k, v)
    ppv.set_editor_property("settings", s)

log("mapa: %s | PPV %s | %s" % (w.get_path_name(), "criado" if created else "atualizado", ppv.get_actor_label()))
for k, v in values.items():
    log("  %s = %s" % (k, v))
log("NAO SALVO: revise e salve o mapa (Ctrl+S).")
unreal.log("LUX PPV_Global aplicado: " + OUT)
