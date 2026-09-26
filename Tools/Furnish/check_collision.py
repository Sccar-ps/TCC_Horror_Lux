# Somente leitura: verifica se as malhas usadas pela mobilia LUX tem colisao simples (necessaria para o jogador nao atravessar).
# Saida: Saved/Furnish/collision.txt
import os, unreal

saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
OUT = os.path.join(saved, "Furnish", "collision.txt")
ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
w = ues.get_editor_world()
seen = {}
for a in unreal.GameplayStatics.get_all_actors_with_tag(w, "LUX_FURNISH"):
    if not isinstance(a, unreal.StaticMeshActor):
        continue
    sm = a.static_mesh_component.get_editor_property("static_mesh")
    if not sm or sm.get_path_name() in seen:
        continue
    bs = sm.get_editor_property("body_setup")
    info = "sem BodySetup"
    if bs:
        g = bs.get_editor_property("agg_geom")
        n = {k: len(g.get_editor_property(k)) for k in ("box_elems", "sphere_elems", "sphyl_elems", "convex_elems")}
        info = "%s trace=%s" % (n, bs.get_editor_property("collision_trace_flag"))
    seen[sm.get_path_name()] = info
open(OUT, "w", encoding="utf-8").write("\n".join("%s | %s" % (k.split(".")[-1], v) for k, v in sorted(seen.items())))
unreal.log("collision check OK")
