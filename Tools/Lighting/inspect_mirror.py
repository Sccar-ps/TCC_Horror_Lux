# Somente leitura: dados para o espelho (moldura do corredor + componentes do BP_Player_Cowboy).
# Saida: Saved/MirrorInspect.txt
import os, unreal

saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
L = []
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for a in eas.get_all_level_actors():
    lab = a.get_actor_label()
    smc0 = a.get_component_by_class(unreal.StaticMeshComponent)
    sm0 = smc0.get_editor_property("static_mesh") if smc0 else None
    if ("Quadro" in lab or "Aparador" in lab or (sm0 and "PictureFrame" in sm0.get_name())) and "Livro" not in lab:
        o, e = a.get_actor_bounds(False)
        smc = a.get_component_by_class(unreal.StaticMeshComponent)
        sm = smc.get_editor_property("static_mesh") if smc else None
        L.append("%s loc=%s rot=%s scale=%s bounds_o=%s ext=%s mesh=%s" % (
            lab, a.get_actor_location(), a.get_actor_rotation(), a.get_actor_scale3d(), o, e,
            sm.get_path_name() if sm else None))
        if sm:
            L.append("   mesh bounds: %s" % (sm.get_bounds(),))

F = ["render_in_main_pass", "render_in_depth_pass", "hidden_in_scene_capture", "visible_in_scene_capture_only",
     "cast_hidden_shadow", "cast_shadow", "owner_no_see", "only_owner_see", "hidden_in_game", "visible"]
bp = unreal.load_asset("/Game/Characters/MixamoFP/Blueprints/BP_Player_Cowboy")
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
for h in sds.k2_gather_subobject_data_for_blueprint(bp):
    d = unreal.SubobjectDataBlueprintFunctionLibrary.get_data(h)
    o = unreal.SubobjectDataBlueprintFunctionLibrary.get_object(d)
    if isinstance(o, unreal.PrimitiveComponent):
        vals = []
        for f in F:
            try:
                vals.append("%s=%s" % (f, o.get_editor_property(f)))
            except Exception:
                pass
        mesh = ""
        for p in ("skeletal_mesh_asset", "static_mesh"):
            try:
                m = o.get_editor_property(p)
                mesh = m.get_name() if m else "None"
            except Exception:
                pass
        L.append("%s (%s) inherited=%s mesh=%s | %s" % (
            o.get_name(), o.get_class().get_name(),
            unreal.SubobjectDataBlueprintFunctionLibrary.is_inherited_component(d), mesh, " ".join(vals)))
for n in ("r.AllowGlobalClipPlane", "r.ReflectionMethod"):
    L.append("%s = %s" % (n, unreal.SystemLibrary.get_console_variable_float_value(n)))
open(os.path.join(saved, "MirrorInspect.txt"), "w", encoding="utf-8").write("\n".join(str(x) for x in L))
unreal.log("MirrorInspect ok")
