# Recria so as cameras LOOP_CamSala e LOOP_CamQuarto (mesma logica do place() do setup_loop.py)
# e aponta o LOOP_Manager para elas. Nao mexe nos outros atores do loop. Nao salva.
#   py "<projeto>/Tools/Loop/add_cams.py"
import unreal

TAG = "LUX_LOOP"
FOLDER = "LUX/Loop"
QUARTO = "BP_BaseDoor7"
APROX = (0.0, 35.0, 4.0)   # igual ao setup_loop.py
FOV_CLOSE = 45.0

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
by = {a.get_actor_label(): a for a in eas.get_all_level_actors()}
mgr, ldoor, quarto = by["LOOP_Manager"], by["LOOP_PortaSala"], by[QUARTO]

with unreal.ScopedEditorTransaction("LUX: cameras do loop"):
    for label in ("LOOP_CamSala", "LOOP_CamQuarto"):
        if label in by:
            eas.destroy_actor(by[label])
    for label, door, prop in (("LOOP_CamSala", ldoor, "CamSala"), ("LOOP_CamQuarto", quarto, "CamQuarto")):
        h = [c for c in door.get_components_by_class(unreal.StaticMeshComponent) if c.get_name() == "DoorHandle"][0]
        o = unreal.SystemLibrary.get_component_bounds(h)[0]
        loc = unreal.Vector(o.x + APROX[0], o.y + APROX[1], o.z + APROX[2])
        c = eas.spawn_actor_from_class(unreal.CameraActor, loc, unreal.Rotator())
        c.set_actor_label(label)
        c.set_folder_path(FOLDER)
        c.set_editor_property("tags", [unreal.Name(TAG)])
        c.set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(loc, o), False)
        cc = c.get_editor_property("camera_component")
        cc.set_editor_property("field_of_view", FOV_CLOSE)
        cc.set_editor_property("constrain_aspect_ratio", False)
        mgr.set_editor_property(prop, c)
        print("%s em %s rot %s -> LOOP_Manager.%s" % (label, loc, c.get_actor_rotation(), prop))
