# Converte as luzes Stationary do mapa aberto para Movable (editor, NAO salva o mapa; Ctrl+Z desfaz).
# Motivo: projeto 100% dinamico (Lumen + Virtual Shadow Maps, sem lightmaps). Stationary sem build fica em
# "preview", gera "LIGHTING NEEDS TO BE REBUILT" e ainda carrega o limite de 4 stationary sobrepostas.
# Directional: desliga "Distance Field Shadows" (com VSM ligado os clipmaps ja cobrem a distancia; o pass
# "DistanceField Shadows" custava ~0,24 ms no stat gpu e o SDF global vaza em parede fina de CubeGrid).
# Tambem registra no log as propriedades que a auditoria nao pegou (DF shadows, volumetric fog, ray tracing).
import os, unreal

saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
OUT = os.path.join(saved, "LightingApplyMovable.txt")
L = []
ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
if ues.get_game_world():
    raise RuntimeError("Pare o PIE antes.")
w = ues.get_editor_world()


def gp(o, n):
    try:
        return o.get_editor_property(n)
    except Exception:
        return "n/a"


changed = 0
with unreal.ScopedEditorTransaction("LUX: luzes Stationary -> Movable"):
    for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Light):
        for c in a.get_components_by_class(unreal.LightComponent):
            before = gp(c, "mobility")
            L.append("%s: mob=%s dfshadow=%s cast_vol_shadow=%s shadow_res_scale=%s" % (
                a.get_actor_label(), before, gp(c, "use_ray_traced_distance_field_shadows"),
                gp(c, "cast_volumetric_shadow"), gp(c, "shadow_resolution_scale")))
            if before == unreal.ComponentMobility.STATIONARY:
                a.modify()
                c.modify()
                c.set_mobility(unreal.ComponentMobility.MOVABLE)
                changed += 1
            if isinstance(c, unreal.DirectionalLightComponent) and gp(c, "use_ray_traced_distance_field_shadows") is True:
                c.modify()
                c.set_editor_property("use_ray_traced_distance_field_shadows", False)
                L.append("  -> %s: Distance Field Shadows desligado" % a.get_actor_label())
L.append("convertidas para Movable: %d" % changed)

for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.ExponentialHeightFog):
    fc = a.get_component_by_class(unreal.ExponentialHeightFogComponent)
    L.append("HeightFog: enable_volumetric_fog=%s volumetric_fog_distance=%s" % (
        gp(fc, "enable_volumetric_fog"), gp(fc, "volumetric_fog_distance")))

for n in ("r.RayTracing", "r.RayTracing.Enable", "r.Lumen.HardwareRayTracing.LightingMode", "r.AllowStaticLighting",
          "r.Lumen.HeightFog", "r.Lumen.Reflections.Allow", "r.Lumen.DiffuseIndirect.Allow"):
    L.append("%s = %s" % (n, unreal.SystemLibrary.get_console_variable_float_value(n)))

open(OUT, "w", encoding="utf-8").write("\n".join(L))
unreal.log("LUX luzes Movable: " + OUT)
