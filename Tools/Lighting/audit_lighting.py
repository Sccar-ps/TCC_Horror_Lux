# Somente leitura: auditoria de iluminacao/exposicao/Lumen do mapa aberto (UE 5.8).
# Rodar no console do editor:  py "C:/Users/bruno/Documents/Unreal Projects/TCC_Horror_Lux/Tools/Lighting/audit_lighting.py"
# Saida: Saved/LightingAudit.txt   (nada e salvo nem alterado)
import os, collections, unreal

saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
OUT = os.path.join(saved, "LightingAudit.txt")
L = []


def log(s=""):
    L.append(str(s))


def gp(obj, name, default="n/a"):
    try:
        return obj.get_editor_property(name)
    except Exception:
        return default


def props(obj, names):
    parts = []
    for n in names:
        v = gp(obj, n)
        if v == "n/a":
            continue
        if isinstance(v, unreal.LinearColor):
            v = "(%.2f,%.2f,%.2f)" % (v.r, v.g, v.b)
        elif isinstance(v, unreal.Color):
            v = "(%d,%d,%d)" % (v.r, v.g, v.b)
        elif isinstance(v, float):
            v = round(v, 4)
        elif isinstance(v, unreal.Object):
            v = v.get_name()
        parts.append("%s=%s" % (n, v))
    return " ".join(parts)


PPS_FIELDS = [
    # exposicao
    "auto_exposure_method", "auto_exposure_bias", "auto_exposure_min_brightness", "auto_exposure_max_brightness",
    "auto_exposure_speed_up", "auto_exposure_speed_down", "auto_exposure_low_percent", "auto_exposure_high_percent",
    "histogram_log_min", "histogram_log_max", "auto_exposure_apply_physical_camera_exposure",
    "auto_exposure_bias_curve", "auto_exposure_meter_mask", "camera_iso", "camera_shutter_speed", "depth_of_field_fstop",
    "local_exposure_method", "local_exposure_highlight_contrast_scale", "local_exposure_shadow_contrast_scale",
    "local_exposure_detail_strength", "local_exposure_blurred_luminance_blend",
    # Lumen / GI / reflexos
    "dynamic_global_illumination_method", "reflection_method", "lumen_scene_lighting_quality", "lumen_scene_detail",
    "lumen_scene_view_distance", "lumen_scene_lighting_update_speed", "lumen_final_gather_quality",
    "lumen_final_gather_lighting_update_speed", "lumen_final_gather_screen_traces", "lumen_max_trace_distance",
    "lumen_surface_cache_resolution", "lumen_reflection_quality", "lumen_ray_lighting_mode",
    "lumen_front_layer_translucency_reflections", "lumen_max_reflection_bounces", "lumen_skylight_leaking",
    "lumen_full_skylight_leaking_distance", "lumen_diffuse_color_boost", "indirect_lighting_intensity",
    # outros caros
    "bloom_method", "bloom_intensity", "motion_blur_amount", "ambient_occlusion_intensity", "screen_percentage",
    "vignette_intensity", "film_grain_intensity",
]


def pps_dump(pps, prefix):
    over, vals = [], []
    for f in PPS_FIELDS:
        ov = gp(pps, "override_" + f, None)
        v = gp(pps, f)
        if v == "n/a":
            continue
        if isinstance(v, float):
            v = round(v, 4)
        elif isinstance(v, unreal.Object):
            v = v.get_name()
        tag = "*" if ov else " "
        vals.append("%s%s=%s" % (tag, f, v))
    log(prefix + "  (* = override ligado)")
    for i in range(0, len(vals), 4):
        log(prefix + "    " + "  ".join(vals[i:i + 4]))


ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
w = ues.get_editor_world() or ues.get_game_world()
log("mapa: %s (%s)" % (w.get_path_name(), "PIE" if ues.get_game_world() else "editor"))
ws = w.get_world_settings()
log("WorldSettings: " + props(ws, ["force_no_precomputed_lighting", "enable_world_composition", "kill_z"]))
try:
    log("WorldPartition: %s" % (w.get_world_partition() is not None))
except Exception:
    pass

# ---------- Luzes ----------
log("\n== LUZES ==")
light_count = collections.Counter()
shadow_local_movable = 0
all_actors = unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Actor)
for a in all_actors:
    comps = a.get_components_by_class(unreal.LightComponentBase)
    for c in comps:
        cls = c.get_class().get_name()
        light_count[cls] += 1
        mob = gp(c, "mobility")
        common = props(c, ["intensity", "intensity_units", "light_color", "cast_shadows", "indirect_lighting_intensity",
                           "volumetric_scattering_intensity", "affects_world", "visible", "hidden_in_game"])
        extra = ""
        if isinstance(c, unreal.SkyLightComponent):
            extra = props(c, ["source_type", "real_time_capture", "cubemap_resolution", "lower_hemisphere_is_black",
                              "lower_hemisphere_color", "sky_distance_threshold", "capture_emissive_only",
                              "cubemap", "occlusion_max_distance", "min_occlusion"])
        elif isinstance(c, unreal.DirectionalLightComponent):
            extra = props(c, ["atmosphere_sun_light", "atmosphere_sun_light_index", "dynamic_shadow_distance_movable_light",
                              "cast_cloud_shadows", "cast_volumetric_shadow", "light_source_angle"])
        elif isinstance(c, unreal.LocalLightComponent):
            extra = props(c, ["attenuation_radius", "source_radius", "soft_source_radius", "source_length",
                              "use_inverse_squared_falloff", "cast_volumetric_shadow", "max_draw_distance",
                              "inner_cone_angle", "outer_cone_angle", "ies_texture", "use_ies_brightness",
                              "source_width", "source_height", "barn_door_angle"])
            if gp(c, "cast_shadows") is True and str(mob).endswith("MOVABLE"):
                shadow_local_movable += 1
        log("%s | %s | %s | mob=%s | %s %s" % (a.get_actor_label(), a.get_class().get_name(), cls, mob, common, extra))
log("contagem: %s" % dict(light_count))
log("luzes locais Movable com sombra (custo VSM/Lumen): %d" % shadow_local_movable)

# ---------- Ceu / nevoa ----------
log("\n== CEU / NEVOA / NUVENS ==")
for cls in (unreal.SkyAtmosphere, unreal.ExponentialHeightFog, unreal.VolumetricCloud, unreal.SphereReflectionCapture,
            unreal.BoxReflectionCapture):
    for a in unreal.GameplayStatics.get_all_actors_of_class(w, cls):
        info = ""
        if cls is unreal.ExponentialHeightFog:
            fc = a.get_component_by_class(unreal.ExponentialHeightFogComponent)
            info = props(fc, ["fog_density", "fog_height_falloff", "fog_inscattering_luminance", "fog_inscattering_color",
                              "volumetric_fog", "volumetric_fog_scattering_distribution", "volumetric_fog_extinction_scale",
                              "view_distance", "volumetric_fog_distance", "volumetric_fog_emissive",
                              "sky_atmosphere_ambient_contribution_color_scale", "start_distance"])
        log("%s (%s) %s" % (a.get_actor_label(), cls.__name__, info))
for a in all_actors:
    n = a.get_class().get_name()
    if "Fog" in n and "ExponentialHeightFog" not in n:
        log("%s (%s)" % (a.get_actor_label(), n))

# ---------- Post Process Volumes ----------
log("\n== POST PROCESS VOLUMES ==")
for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.PostProcessVolume):
    log("%s unbound=%s priority=%s blend_weight=%s enabled=%s" % (
        a.get_actor_label(), gp(a, "unbound"), gp(a, "priority"), gp(a, "blend_weight"), gp(a, "enabled")))
    pps_dump(gp(a, "settings"), "  ")

# ---------- Cameras com PP (PIE) ----------
gw = ues.get_game_world()
if gw:
    log("\n== PIE: CAMERA DO JOGADOR ==")
    pc = unreal.GameplayStatics.get_player_controller(gw, 0)
    pawn = pc.get_controlled_pawn() if pc else None
    if pawn:
        log("pawn: %s (%s)" % (pawn.get_name(), pawn.get_class().get_name()))
        for cam in pawn.get_components_by_class(unreal.CameraComponent):
            log("camera %s pp_blend_weight=%s" % (cam.get_name(), gp(cam, "post_process_blend_weight")))
            pps_dump(gp(cam, "post_process_settings"), "  ")
        for lc in pawn.get_components_by_class(unreal.LightComponentBase):
            log("luz do pawn %s (%s): %s" % (lc.get_name(), lc.get_class().get_name(), props(lc, [
                "intensity", "intensity_units", "attenuation_radius", "inner_cone_angle", "outer_cone_angle",
                "cast_shadows", "indirect_lighting_intensity", "volumetric_scattering_intensity", "source_radius",
                "use_inverse_squared_falloff", "ies_texture", "visible"])))
        for att in unreal.GameplayStatics.get_all_actors_of_class(gw, unreal.Actor):
            if att.get_attach_parent_actor() == pawn:
                for lc in att.get_components_by_class(unreal.LightComponentBase):
                    log("luz anexada %s/%s (%s): %s" % (att.get_name(), lc.get_name(), lc.get_class().get_name(), props(lc, [
                        "intensity", "intensity_units", "attenuation_radius", "inner_cone_angle", "outer_cone_angle",
                        "cast_shadows", "indirect_lighting_intensity", "volumetric_scattering_intensity", "visible"])))

# ---------- Geometria ----------
log("\n== GEOMETRIA ==")
smc_total, nanite_on, unique = 0, 0, {}
isms = 0
for a in all_actors:
    for c in a.get_components_by_class(unreal.StaticMeshComponent):
        sm = gp(c, "static_mesh", None)
        if not sm:
            continue
        smc_total += 1
        if isinstance(c, unreal.InstancedStaticMeshComponent):
            isms += 1
        key = sm.get_path_name()
        if key not in unique:
            ns = gp(sm, "nanite_settings", None)
            nan = bool(ns and gp(ns, "enabled", False))
            tris = -1
            try:
                tris = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem).get_number_verts(sm, 0)
            except Exception:
                pass
            unique[key] = [nan, tris, 0]
        unique[key][2] += 1
nan_meshes = sum(1 for v in unique.values() if v[0])
log("StaticMeshComponents: %d (ISM/HISM: %d) | meshes unicos: %d | Nanite: %d | nao-Nanite: %d" % (
    smc_total, isms, len(unique), nan_meshes, len(unique) - nan_meshes))
heavy = sorted(unique.items(), key=lambda kv: -kv[1][1])[:15]
log("top 15 por vertices (LOD0): [nanite, verts, instancias]")
for k, v in heavy:
    log("  %s %s" % (v, k))
nn_heavy = [(k, v) for k, v in unique.items() if not v[0] and v[1] > 20000]
log("nao-Nanite com >20k verts (candidatos a Nanite ou LOD): %d" % len(nn_heavy))
for k, v in sorted(nn_heavy, key=lambda kv: -kv[1][1])[:20]:
    log("  %s %s" % (v, k))

# ---------- CVars ----------
log("\n== CVARS ==")
CV = ["r.EyeAdaptation.CachedLightingPreExposure", "r.DefaultFeature.AutoExposure", "r.DefaultFeature.AutoExposure.Method",
      "r.DefaultFeature.AutoExposure.ExtendDefaultLuminanceRange", "r.DefaultFeature.AutoExposure.Bias",
      "r.DynamicGlobalIlluminationMethod", "r.ReflectionMethod", "r.Lumen.HardwareRayTracing",
      "r.Lumen.TraceMeshSDFs", "r.Lumen.ScreenProbeGather.DownsampleFactor", "r.Lumen.ScreenProbeGather.RadianceCache.ProbeResolution",
      "r.Lumen.SurfaceCache.CardCaptureRefreshFraction", "r.LumenScene.SurfaceCache.AtlasSize", "r.LumenScene.Radiosity",
      "r.Lumen.Reflections.DownsampleFactor", "r.Lumen.Reflections.MaxRoughnessToTrace",
      "r.SkyLight.RealTimeReflectionCapture", "r.SkyLight.RealTimeReflectionCapture.TimeSlice",
      "r.Shadow.Virtual.Enable", "r.Shadow.Virtual.ResolutionLodBiasLocal", "r.Shadow.Virtual.ResolutionLodBiasDirectional",
      "r.Shadow.Virtual.MaxPhysicalPages", "r.Shadow.Virtual.SMRT.RayCountLocal", "r.Shadow.Virtual.Cache",
      "r.MegaLights.Enable", "r.VolumetricFog", "r.VolumetricFog.GridPixelSize", "r.VolumetricFog.GridSizeZ",
      "r.Nanite", "r.Nanite.MaxPixelsPerEdge", "r.AntiAliasingMethod", "r.ScreenPercentage",
      "r.DynamicRes.OperationMode", "r.Streaming.PoolSize", "r.Streaming.PoolSizeForMeshes", "r.VirtualTextures",
      "r.GenerateMeshDistanceFields", "r.DistanceFields.DefaultVoxelDensity", "r.AOGlobalDistanceField",
      "r.LocalExposure", "r.Tonemapper.Quality", "r.BloomQuality", "r.MotionBlurQuality", "r.SSR.Quality",
      "t.MaxFPS", "r.VSync",
      "sg.ResolutionQuality", "sg.ViewDistanceQuality", "sg.AntiAliasingQuality", "sg.ShadowQuality",
      "sg.GlobalIlluminationQuality", "sg.ReflectionQuality", "sg.PostProcessQuality", "sg.TextureQuality",
      "sg.EffectsQuality", "sg.FoliageQuality", "sg.ShadingQuality", "sg.LandscapeQuality"]
for n in CV:
    try:
        f = unreal.SystemLibrary.get_console_variable_float_value(n)
        log("%s = %s" % (n, f))
    except Exception as e:
        log("%s = ERRO %s" % (n, e))

open(OUT, "w", encoding="utf-8").write("\n".join(L))
unreal.log("LightingAudit gravado em " + OUT)
