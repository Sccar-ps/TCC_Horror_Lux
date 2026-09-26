# Somente leitura: levantamento de iluminacao/atmosfera do mapa aberto no editor (UE 5.8).
# Rodar no console do editor:
#   py "C:/Users/bruno/Documents/Unreal Projects/TCC_Horror_Lux/Tools/Lighting/audit_atmosphere.py"
# Saida: Saved/AtmosphereAudit.txt  (nada e alterado nem salvo)
import os, collections, unreal

saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
OUT = os.path.join(saved, "AtmosphereAudit.txt")
L = []


def log(s=""):
    L.append(str(s))


def gp(obj, name, default="n/a"):
    try:
        return obj.get_editor_property(name)
    except Exception:
        return default


def fmt(v):
    if isinstance(v, unreal.LinearColor):
        return "(%.3f,%.3f,%.3f,%.2f)" % (v.r, v.g, v.b, v.a)
    if isinstance(v, unreal.Color):
        return "(%d,%d,%d)" % (v.r, v.g, v.b)
    if isinstance(v, unreal.Vector4):
        return "(%.3f,%.3f,%.3f,%.3f)" % (v.x, v.y, v.z, v.w)
    if isinstance(v, unreal.Vector):
        return "(%.0f,%.0f,%.0f)" % (v.x, v.y, v.z)
    if isinstance(v, float):
        return str(round(v, 4))
    if isinstance(v, unreal.Object):
        return v.get_name()
    return str(v)


def props(obj, names):
    out = []
    for n in names:
        v = gp(obj, n)
        if v == "n/a":
            continue
        out.append("%s=%s" % (n, fmt(v)))
    return " ".join(out)


# Comodos (faces internas medidas em Mapa_B_mobilia.md)
ROOMS = {
    "Sala": ((-3000, -2052), (-1940, -350)),
    "Corredor": ((-3402, -3149), (-700, 850)),
    "Quarto": ((-3614, -2510), (900, 1740)),
    "Escritorio": ((-3855, -3107), (-1500, -729)),
}


def room_of(loc):
    for name, ((x0, x1), (y0, y1)) in ROOMS.items():
        if x0 - 60 <= loc.x <= x1 + 60 and y0 - 60 <= loc.y <= y1 + 60:
            return name
    return "fora"


ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
w = ues.get_game_world() or ues.get_editor_world()
log("mapa: %s (%s)" % (w.get_path_name(), "PIE" if ues.get_game_world() else "editor"))
all_actors = unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Actor)

# ---------------- Luzes ----------------
log("\n== LUZES ==")
LOCAL = ["attenuation_radius", "source_radius", "soft_source_radius", "source_length", "source_width",
         "source_height", "barn_door_angle", "inner_cone_angle", "outer_cone_angle", "max_draw_distance"]
COMMON = ["intensity", "intensity_units", "light_color", "use_temperature", "temperature", "cast_shadows",
          "indirect_lighting_intensity", "volumetric_scattering_intensity", "cast_volumetric_shadow",
          "specular_scale", "light_function_material", "ies_texture", "visible", "affects_world"]
per_room = collections.defaultdict(lambda: [0, 0])
n_lights, n_shadow = 0, 0
for a in all_actors:
    for c in a.get_components_by_class(unreal.LightComponentBase):
        n_lights += 1
        loc = c.get_world_location()
        rot = c.get_world_rotation()
        room = room_of(loc)
        sh = gp(c, "cast_shadows") is True
        per_room[room][0] += 1
        per_room[room][1] += int(sh)
        n_shadow += int(sh)
        tags = ",".join(str(t) for t in a.tags)
        extra = props(c, LOCAL) if isinstance(c, unreal.LocalLightComponent) else ""
        if isinstance(c, unreal.DirectionalLightComponent):
            extra = props(c, ["atmosphere_sun_light", "light_source_angle", "cast_cloud_shadows"])
        log("%s | %s | pasta=%s | tags=%s | comodo=%s | loc=%s | rot(p,y,r)=(%.1f,%.1f,%.1f) | mob=%s | %s %s" % (
            a.get_actor_label(), c.get_class().get_name(), a.get_folder_path(), tags, room, fmt(loc),
            rot.pitch, rot.yaw, rot.roll, str(gp(c, "mobility")).split(".")[-1].split(":")[0], props(c, COMMON), extra))
log("total luzes: %d | com sombra: %d" % (n_lights, n_shadow))
for r, (n, s) in sorted(per_room.items()):
    log("  %s: %d luzes, %d com sombra" % (r, n, s))

# ---------------- Ceu / nevoa ----------------
log("\n== CEU / NEVOA ==")
FOG = ["fog_density", "fog_height_falloff", "second_fog_data", "fog_inscattering_luminance", "fog_inscattering_color",
       "sky_atmosphere_ambient_contribution_color_scale", "inscattering_color_cubemap", "directional_inscattering_exponent",
       "directional_inscattering_start_distance", "directional_inscattering_luminance", "fog_max_opacity",
       "start_distance", "end_distance", "fog_cutoff_distance", "enable_volumetric_fog", "volumetric_fog",
       "volumetric_fog_scattering_distribution", "volumetric_fog_albedo", "volumetric_fog_emissive",
       "volumetric_fog_extinction_scale", "volumetric_fog_distance", "volumetric_fog_start_distance",
       "volumetric_fog_near_fade_in_distance", "override_light_colors_with_fog_inscattering_colors"]
for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.ExponentialHeightFog):
    fc = a.get_component_by_class(unreal.ExponentialHeightFogComponent)
    log("ExponentialHeightFog '%s' loc=%s" % (a.get_actor_label(), fmt(a.get_actor_location())))
    for n in FOG:
        v = gp(fc, n)
        if v == "n/a":
            continue
        if n == "second_fog_data":
            v = "density=%s falloff=%s offset=%s" % (gp(v, "fog_density"), gp(v, "fog_height_falloff"), gp(v, "fog_height_offset"))
        log("    %s = %s" % (n, fmt(v)))
for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.SkyAtmosphere):
    sc = a.get_component_by_class(unreal.SkyAtmosphereComponent)
    log("SkyAtmosphere '%s': %s" % (a.get_actor_label(), props(sc, [
        "sky_luminance_factor", "height_fog_contribution", "aerial_pespective_view_distance_scale",
        "aerial_perspective_view_distance_scale", "multi_scattering_factor", "rayleigh_scattering_scale",
        "mie_scattering_scale", "transmittance_min_light_elevation_angle"])))
for cls_name in ("SkyLight", "VolumetricCloud", "LocalFogVolume", "SphereReflectionCapture", "BoxReflectionCapture",
                 "LightmassImportanceVolume", "LumenOverrides"):
    cls = getattr(unreal, cls_name, None)
    if cls is None:
        log("%s: classe nao exposta ao Python" % cls_name)
        continue
    found = unreal.GameplayStatics.get_all_actors_of_class(w, cls)
    log("%s: %d" % (cls_name, len(found)))
    for a in found:
        log("    %s loc=%s scale=%s" % (a.get_actor_label(), fmt(a.get_actor_location()), fmt(a.get_actor_scale3d())))

# ---------------- Post process ----------------
PPS = [
    "auto_exposure_method", "auto_exposure_bias", "auto_exposure_min_brightness", "auto_exposure_max_brightness",
    "auto_exposure_speed_up", "auto_exposure_speed_down",
    "local_exposure_highlight_contrast_scale", "local_exposure_shadow_contrast_scale", "local_exposure_detail_strength",
    "white_temp", "white_tint", "color_saturation", "color_contrast", "color_gamma", "color_gain", "color_offset",
    "color_saturation_shadows", "color_contrast_shadows", "color_gain_shadows", "color_offset_shadows",
    "color_saturation_highlights", "color_gain_highlights", "shadows_max", "highlights_min",
    "scene_color_tint", "color_grading_lut", "color_grading_intensity",
    "film_slope", "film_toe", "film_shoulder", "film_black_clip", "film_white_clip",
    "bloom_intensity", "bloom_threshold", "lens_flare_intensity", "vignette_intensity",
    "film_grain_intensity", "film_grain_intensity_shadows", "scene_fringe_intensity", "sharpen",
    "ambient_occlusion_intensity", "motion_blur_amount", "indirect_lighting_intensity", "lumen_diffuse_color_boost",
    "lumen_scene_view_distance", "lumen_max_trace_distance", "lumen_skylight_leaking",
]


def pps_dump(pps, prefix):
    on, off = [], []
    for f in PPS:
        v = gp(pps, f)
        if v == "n/a":
            continue
        (on if gp(pps, "override_" + f, False) else off).append("%s=%s" % (f, fmt(v)))
    log(prefix + "OVERRIDES LIGADOS: " + ("  ".join(on) if on else "(nenhum)"))
    try:
        wb = gp(pps, "weighted_blendables")
        arr = gp(wb, "array", [])
        log(prefix + "blendables (materiais de PP): %d" % len(arr))
    except Exception:
        pass


log("\n== POST PROCESS VOLUMES ==")
for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.PostProcessVolume):
    log("%s unbound=%s priority=%s blend_weight=%s enabled=%s" % (
        a.get_actor_label(), gp(a, "unbound"), gp(a, "priority"), gp(a, "blend_weight"), gp(a, "enabled")))
    pps_dump(gp(a, "settings"), "    ")

# ---------------- Lanterna / camera do jogador (template do Blueprint) ----------------
log("\n== LANTERNA E CAMERA (BP_Player_Cowboy, template) ==")
try:
    bp = unreal.load_asset("/Game/Characters/MixamoFP/Blueprints/BP_Player_Cowboy")
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    for h in sds.k2_gather_subobject_data_for_blueprint(bp):
        d = unreal.SubobjectDataBlueprintFunctionLibrary.get_data(h)
        o = unreal.SubobjectDataBlueprintFunctionLibrary.get_object(d)
        if isinstance(o, unreal.LightComponentBase):
            log("luz %s (%s): %s %s" % (o.get_name(), o.get_class().get_name(), props(o, COMMON), props(o, LOCAL)))
        elif isinstance(o, unreal.CameraComponent):
            log("camera %s pp_blend_weight=%s" % (o.get_name(), gp(o, "post_process_blend_weight")))
            pps_dump(gp(o, "post_process_settings"), "    ")
except Exception as e:
    log("falhou ao ler o Blueprint: %s" % e)

# ---------------- Decals / outros ----------------
log("\n== OUTROS ==")
cnt = collections.Counter(a.get_class().get_name() for a in all_actors)
for k in ("DecalActor", "AmbientSound", "PostProcessVolume", "StaticMeshActor", "BP_ThirdPersonCharacter_C"):
    log("%s: %d" % (k, cnt.get(k, 0)))

# ---------------- CVars ----------------
log("\n== CVARS ==")
for n in ["r.VolumetricFog", "r.VolumetricFog.GridPixelSize", "r.VolumetricFog.GridSizeZ",
          "r.VolumetricFog.TemporalReprojection", "r.VolumetricFog.InjectShadowedLightsSeparately",
          "r.Lumen.HeightFog", "r.LocalFogVolume.GlobalStartDistance", "r.EyeAdaptation.CachedLightingPreExposure",
          "r.LocalExposure", "r.Tonemapper.GrainQuantization", "r.MegaLights.Enable", "r.Shadow.Virtual.Enable",
          "r.ScreenPercentage", "sg.PostProcessQuality", "sg.EffectsQuality", "sg.ShadowQuality",
          "sg.GlobalIlluminationQuality"]:
    try:
        log("%s = %s" % (n, unreal.SystemLibrary.get_console_variable_float_value(n)))
    except Exception as e:
        log("%s = ERRO %s" % (n, e))

open(OUT, "w", encoding="utf-8").write("\n".join(L))
unreal.log("AtmosphereAudit gravado em " + OUT)
