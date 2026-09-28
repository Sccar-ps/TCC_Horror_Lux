# LUX: levantamento (so leitura) das velas: malhas SM_Candles, atores do Mapa_B que as usam, luzes proximas e a vela da mao.
#   py "<projeto>/Tools/Player/vela_probe.py"   -> Saved/LuxSnapshots/vela_probe.txt
import os, unreal

EAL = unreal.EditorAssetLibrary
OUT = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), "LuxSnapshots")
os.makedirs(OUT, exist_ok=True)
L = []


def p(*a):
    L.append(" ".join(str(x) for x in a))


for nome in ("SM_Candles_NN_01a", "SM_Candles_NN_01b", "SM_Candles_NN_01c"):
    sm = EAL.load_asset("/Game/OldWest/VOL6/Meshes/" + nome)
    b = sm.get_bounding_box()
    p(nome, "bounds", b.min, b.max, "nanite", sm.get_editor_property("nanite_settings").enabled)
    for i, s in enumerate(sm.static_materials):
        m = s.material_interface
        p("  slot", i, s.material_slot_name, m.get_path_name() if m else None)
        if m:
            base = m.get_base_material()
            p("     base", base.get_path_name(), "blend", base.get_editor_property("blend_mode"), "shading", base.get_editor_property("shading_model"))
            if isinstance(m, unreal.MaterialInstance):
                for sp in m.get_editor_property("scalar_parameter_values"):
                    p("     scalar", sp.parameter_info.name, sp.parameter_value)
                for vp in m.get_editor_property("vector_parameter_values"):
                    p("     vector", vp.parameter_info.name, vp.parameter_value)

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
atores = eas.get_all_level_actors()
luzes = [(a, c) for a in atores for c in a.get_components_by_class(unreal.PointLightComponent)]
for a in atores:
    for c in a.get_components_by_class(unreal.StaticMeshComponent):
        sm = c.get_editor_property("static_mesh")
        if sm and "Candle" in sm.get_name():
            loc = c.get_world_location()
            perto = sorted((( (lc.get_world_location() - loc).length(), la.get_actor_label(), lc.get_editor_property("intensity"),
                             lc.get_editor_property("attenuation_radius"), lc.get_editor_property("light_function_material")) for la, lc in luzes),
                           key=lambda x: x[0])[:1]
            p("ator", a.get_actor_label(), sm.get_name(), "loc", loc, "escala", c.get_world_scale(), "tags", [str(t) for t in a.tags],
              "luz mais proxima", perto)

bp = EAL.load_asset("/Game/Characters/MixamoFP/Blueprints/BP_Player_Cowboy")
lib = unreal.SubobjectDataBlueprintFunctionLibrary
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
for h in sds.k2_gather_subobject_data_for_blueprint(bp):
    o = lib.get_object_for_blueprint(lib.get_data(h), bp)
    if isinstance(o, unreal.SceneComponent) and any(k in o.get_name() for k in ("Vela", "Lampiao", "Chama", "FirstPersonMesh")):
        p("bp", o.get_name(), o.get_class().get_name(), "rel", o.get_editor_property("relative_location"), o.get_editor_property("relative_rotation"),
          o.get_editor_property("relative_scale3d"), "absrot", o.get_editor_property("absolute_rotation"))
open(os.path.join(OUT, "vela_probe.txt"), "w", encoding="utf-8").write("\n".join(L))
unreal.log("[LUX vela] probe ok: %d linhas" % len(L))
