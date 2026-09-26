# Somente leitura: colisao da malha de um ator.  py check_mesh.py <label>
import sys, unreal
lab = sys.argv[1]
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.StaticMeshActor):
    if a.get_actor_label() != lab:
        continue
    c = a.static_mesh_component
    sm = c.get_editor_property("static_mesh")
    bs = sm.get_editor_property("body_setup")
    g = bs.get_editor_property("agg_geom")
    unreal.log("LUXMESH %s trace=%s profile=%s enabled=%s" % (sm.get_name(), bs.get_editor_property("collision_trace_flag"),
                                                            c.get_collision_profile_name(), c.get_collision_enabled()))
    for b in g.get_editor_property("box_elems"):
        unreal.log("LUXMESH box center=%s x=%s y=%s z=%s" % (b.get_editor_property("center"), b.get_editor_property("x"),
                                                            b.get_editor_property("y"), b.get_editor_property("z")))
    for cv in g.get_editor_property("convex_elems"):
        unreal.log("LUXMESH convex box=%s" % cv.get_editor_property("elem_box"))
    unreal.log("LUXMESH scale=%s bounds=%s" % (a.get_actor_scale3d(), a.get_actor_bounds(False)))
