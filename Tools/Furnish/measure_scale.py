# Somente leitura: medidas para calibrar a escala (personagem, moveis existentes, portas).
# Saida: Saved/Furnish/scale.txt
import os, unreal

saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
OUT = os.path.join(saved, "Furnish", "scale.txt")
L = []
ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
w = ues.get_editor_world()


def v(x):
    return "(%.3f, %.3f, %.3f)" % (x.x, x.y, x.z)


# personagem (CDO)
for p in ("/Game/Characters/MixamoFP/Blueprints/BP_Player_Cowboy", "/Game/FPMovement/Player/Blueprints/BP_Player"):
    bp = unreal.load_asset(p)
    if not bp:
        L.append("sem " + p)
        continue
    cdo = unreal.get_default_object(bp.generated_class())
    cap = cdo.get_editor_property("capsule_component")
    L.append("%s capsule half=%.1f radius=%.1f" % (p.split("/")[-1], cap.get_editor_property("capsule_half_height"),
                                                   cap.get_editor_property("capsule_radius")))
    mv = cdo.get_editor_property("character_movement")
    for n in ("max_walk_speed", "max_step_height", "walkable_floor_angle"):
        try:
            L.append("   %s = %s" % (n, mv.get_editor_property(n)))
        except Exception:
            pass
    try:
        L.append("   base_eye_height = %s" % cdo.get_editor_property("base_eye_height"))
    except Exception:
        pass

by = {a.get_actor_label(): a for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Actor)}
for lab in ("Bed", "vintage_sofa_23mb", "meubletv1", "SM_Doormat", "BP_BaseDoor5", "BP_BaseDoor7", "BP_BaseDoor3",
            "SM_Door_Double_NN_01b", "Box_B1714F7C", "SM_His_Sal_Curtain_01", "SM_Shutter_Set_NN_03d3"):
    a = by.get(lab)
    if not a:
        L.append("sem ator " + lab)
        continue
    org, ext = a.get_actor_bounds(False)
    L.append("%s loc=%s rot=%s scale=%s | bounds size=%s zmin=%.1f" % (
        lab, v(a.get_actor_location()), a.get_actor_rotation(), v(a.get_actor_scale3d()),
        v(ext * 2.0), org.z - ext.z))
    for c in a.get_components_by_class(unreal.StaticMeshComponent):
        sm = c.get_editor_property("static_mesh")
        if sm:
            bb = sm.get_bounding_box()
            L.append("    comp %s mesh=%s local min%s max%s rel_scale=%s rel_loc=%s" % (
                c.get_name(), sm.get_name(), v(bb.min), v(bb.max), v(c.get_editor_property("relative_scale3d")),
                v(c.get_editor_property("relative_location"))))
open(OUT, "w", encoding="utf-8").write("\n".join(L))
unreal.log("scale OK")
