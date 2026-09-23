# Somente leitura: pawns/PlayerStarts no mapa aberto e GameMode efetivo.
import os, unreal
out = []
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
out.append("mapa: %s" % w.get_path_name())
for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Pawn):
    ap = a.get_editor_property("auto_possess_player")
    out.append("pawn: %s (%s) auto_possess=%s loc=%s" % (a.get_name(), a.get_class().get_name(), ap, a.get_actor_location()))
for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.PlayerStart):
    out.append("playerstart: %s loc=%s" % (a.get_name(), a.get_actor_location()))
ws = w.get_world_settings()
gm = ws.get_editor_property("default_game_mode")
out.append("GameMode override do mapa: %s" % (gm.get_name() if gm else "nenhum"))
bp = unreal.load_asset("/Game/Characters/MixamoFP/Blueprints/BP_Player_Cowboy")
cdo = unreal.get_default_object(bp.generated_class())
m = cdo.get_editor_property("mesh")
out.append("BP_Player_Cowboy Mesh: %s anim=%s mainpass=%s depthpass=%s shadow=%s tick=%s loc=%s rot=%s" % (
    m.get_skeletal_mesh_asset().get_name() if m.get_skeletal_mesh_asset() else None, m.get_editor_property("anim_class"),
    m.get_editor_property("render_in_main_pass"), m.get_editor_property("render_in_depth_pass"), m.get_editor_property("cast_shadow"),
    m.get_editor_property("visibility_based_anim_tick_option"), m.get_editor_property("relative_location"), m.get_editor_property("relative_rotation")))
saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
open(os.path.join(saved, "MixamoFP_map.txt"), "w", encoding="utf-8").write("\n".join(str(x) for x in out))
