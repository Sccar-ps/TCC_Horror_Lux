# "Atmosfera densa" no Mapa_B (abordagem 2 de claude/Atmosfera_Mapa_B.md). Editor, NAO salva o mapa.
# Uso:  py "C:/Users/bruno/Documents/Unreal Projects/TCC_Horror_Lux/Tools/Lighting/apply_atmosphere.py"
# Idempotente: ajuste os valores abaixo e rode de novo. Desfazer: Ctrl+Z ("LUX: atmosfera").
# Log com os valores ANTERIORES de tudo que mudou: Saved/AtmosphereApply.txt
# Condicao A (controle) do TCC = desligar o PPV_Atmosfera + Volumetric Fog/densidade da nevoa.
import os, unreal

# ---------- 1. Limpeza: raio da luz ~ tamanho do comodo (antes: 8-53 m, avaliadas na casa inteira) ----------
LIGHTS = {
    "LUX_Luz_Quarto_VelaComoda": {"attenuation_radius": 300.0},
    # sombra off: a luz fica dentro da cupula (a sombra da cupula apagava o abajur); igual ao abajur da sala
    "LUX_Luz_Sala_Abajur2": {"attenuation_radius": 500.0, "source_radius": 10.0, "soft_source_radius": 20.0,
                             "cast_shadows": False},
    "LUX_Luz_Sala_Candelabro": {"attenuation_radius": 300.0, "source_radius": 5.0},
    "LUX_Luz_Sala_Candelabro2": {"attenuation_radius": 300.0, "source_radius": 5.0},
    "LUX_Luz_Sala_Candelabro3": {"attenuation_radius": 300.0, "source_radius": 5.0},
    # arandelas: 11 m atravessavam as paredes e acenderiam a nevoa dos comodos vizinhos (sem volumetric shadow)
    "LUX_Luz_Corredor_Arandela3": {"attenuation_radius": 600.0},
    "LUX_Luz_Corredor_Arandela5": {"attenuation_radius": 600.0},
}
DELETE = ["PointLight"]  # template, fora da casa, raio nao alcanca o interior
LUX_VOL_SCATTER = 3.0    # velas/abajures (LUX_Luz_*): so o brilho na nevoa (halo), nao muda a luz na superficie

# ---------- 2. PPV_Atmosfera (prioridade 1, por cima do PPV_Global) ----------
# Faixa segura do cache (CachedLightingPreExposure=1): EV100 - bias(1) dentro de [-11, 9]  ->  [-8, 3] ok
PPV = {
    "auto_exposure_min_brightness": -7.0,   # era -8: o olho clareia menos o escuro (-6 esmagou tudo em preto)
    "auto_exposure_max_brightness": 4.0,
    "auto_exposure_speed_down": 0.5,        # demora mais para se acostumar ao escuro
    "local_exposure_shadow_contrast_scale": 0.9,  # projeto usa 0.8 (clareia sombras)
    "white_temp": 5800.0,                   # camera um pouco mais fria; velas (2200 K) seguem quentes
    "color_contrast": unreal.Vector4(1.0, 1.0, 1.0, 1.08),
    "color_saturation_shadows": unreal.Vector4(1.0, 1.0, 1.0, 0.7),
    "color_gain_shadows": unreal.Vector4(0.85, 0.95, 1.15, 1.0),  # sombras frias
    "vignette_intensity": 0.7,
    "film_grain_intensity": 0.3,
    "scene_fringe_intensity": 0.25,         # aberracao cromatica leve
}

# ---------- 3. Nevoa (o ExponentialHeightFog existente) ----------
FOG_Z = 0.0  # era -6850: nivel do piso
FOG = {
    "fog_density": 0.15,                    # ~14% em 10 m, ~45% em 40 m
    "fog_height_falloff": 0.2,
    "fog_inscattering_luminance": unreal.LinearColor(0.0005, 0.001, 0.002, 1.0),  # alem dos 40 m (exterior)
    "sky_atmosphere_ambient_contribution_color_scale": unreal.LinearColor(0.0, 0.0, 0.0, 1.0),
    "enable_volumetric_fog": True,
    "volumetric_fog_albedo": unreal.Color(r=200, g=205, b=215, a=255),
    "volumetric_fog_scattering_distribution": 0.3,  # 0.5 = janela contra a lua "acende" demais
    "volumetric_fog_extinction_scale": 1.0,
    "volumetric_fog_distance": 3000.0,      # era 6000; menos ar "aceso" do lado de fora das janelas
    # "ar" frio visivel no escuro. Soma ao longo do raio: e o que clareia as janelas (nevoa externa); nao suba muito
    "volumetric_fog_emissive": unreal.LinearColor(0.0001, 0.0002, 0.0004, 1.0),
}

# ---------- 3b. Lua = DirectionalLight existente, acima do horizonte ----------
MOON_ROT = unreal.Rotator(roll=0.0, pitch=-25.0, yaw=-22.9)  # era pitch +2.9 (sol abaixo do horizonte)
MOON = {"intensity": 0.06,  # 0.15: o chao/paredes externos iluminados deixavam as janelas brancas "use_temperature": False, "light_color": unreal.Color(r=170, g=195, b=255, a=255),
        "volumetric_scattering_intensity": 0.4}  # nevoa externa iluminada pela lua = janelas; >1 fica branco
SKY = {"sky_luminance_factor": unreal.LinearColor(0.1, 0.1, 0.1, 1.0)}  # ceu noturno (1.0 = ceu de dia)

TAG = "LUX_ATMOS"
saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
OUT = os.path.join(saved, "AtmosphereApply.txt")
L = []
ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
if ues.get_game_world():
    raise RuntimeError("Pare o PIE antes.")
w = ues.get_editor_world()
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actors = {a.get_actor_label(): a for a in eas.get_all_level_actors()}


def setp(obj, values, who):
    obj.modify()
    for k, v in values.items():
        L.append("%s.%s: %s -> %s" % (who, k, obj.get_editor_property(k), v))
        obj.set_editor_property(k, v)


with unreal.ScopedEditorTransaction("LUX: atmosfera"):
    for label, vals in LIGHTS.items():
        a = actors.get(label)
        if a:
            setp(a.get_component_by_class(unreal.LightComponent), vals, label)
        else:
            L.append("AVISO: %s nao encontrada" % label)

    for label in DELETE:
        a = actors.get(label)
        if a:
            c = a.get_component_by_class(unreal.LightComponent)
            L.append("apagada %s em %s (intensity=%s radius=%s)" % (
                label, a.get_actor_location(), c.get_editor_property("intensity"),
                c.get_editor_property("attenuation_radius")))
            eas.destroy_actor(a)

    ppv = next((a for a in actors.values() if a.actor_has_tag(TAG)), None)
    if ppv is None:
        ppv = eas.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector(0, 0, 0))
        ppv.set_actor_label("PPV_Atmosfera")
        ppv.tags = [TAG]
        L.append("criado PPV_Atmosfera")
    ppv.modify()
    ppv.set_editor_property("unbound", True)
    ppv.set_editor_property("priority", 1.0)
    ppv.set_editor_property("blend_weight", 1.0)
    ppv.set_editor_property("enabled", True)
    s = ppv.get_editor_property("settings")
    for k, v in PPV.items():
        s.set_editor_property("override_" + k, True)
        s.set_editor_property(k, v)
    ppv.set_editor_property("settings", s)
    L.append("PPV_Atmosfera: %s" % PPV)

    fog = unreal.GameplayStatics.get_all_actors_of_class(w, unreal.ExponentialHeightFog)[0]
    fog.modify()
    p = fog.get_actor_location()
    L.append("Fog loc: %s -> z=%s" % (p, FOG_Z))
    fog.set_actor_location(unreal.Vector(p.x, p.y, FOG_Z), False, False)
    setp(fog.get_component_by_class(unreal.ExponentialHeightFogComponent), FOG, "Fog")

    sun = unreal.GameplayStatics.get_all_actors_of_class(w, unreal.DirectionalLight)[0]
    sun.modify()
    L.append("Lua rot: %s -> %s" % (sun.get_actor_rotation(), MOON_ROT))
    sun.set_actor_rotation(MOON_ROT, False)
    setp(sun.get_component_by_class(unreal.DirectionalLightComponent), MOON, "Lua")
    sky = unreal.GameplayStatics.get_all_actors_of_class(w, unreal.SkyAtmosphere)[0]
    setp(sky.get_component_by_class(unreal.SkyAtmosphereComponent), SKY, "Ceu")

    for label, a in actors.items():
        if label.startswith("LUX_Luz_"):
            setp(a.get_component_by_class(unreal.LightComponent),
                 {"volumetric_scattering_intensity": LUX_VOL_SCATTER}, label)

L.append("NAO SALVO: revise e salve o mapa (Ctrl+S).")
open(OUT, "w", encoding="utf-8").write("\n".join(str(x) for x in L))
unreal.log("LUX atmosfera aplicada: " + OUT)
