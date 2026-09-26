# Somente leitura: visibilidade/colisao das folhas das portas 5 e 7 e da porta dupla OldWest. Saida: Saved/Loop/probe3.txt
import os, unreal
saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
out = []
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
by = {a.get_actor_label(): a for a in eas.get_all_level_actors()}
for lab in ("BP_BaseDoor5", "BP_BaseDoor7", "SM_Door_Double_NN_01b", "Box_B1714F7C"):
    a = by.get(lab)
    if not a:
        out.append("%s: ausente" % lab)
        continue
    out.append("%s hidden_in_game(ator)=%s hidden_ed=%s" % (lab, a.get_editor_property("hidden"), a.is_hidden_ed()))
    for c in a.get_components_by_class(unreal.PrimitiveComponent):
        mats = [m.get_path_name() if m else None for m in c.get_materials()] if hasattr(c, "get_materials") else []
        out.append("  %-20s visible=%s hidden_in_game=%s colisao=%s perfil=%s mats=%s" % (
            c.get_name(), c.get_editor_property("visible"), c.get_editor_property("hidden_in_game"),
            c.get_collision_enabled(), c.get_collision_profile_name(), mats))
open(os.path.join(saved, "Loop", "probe3.txt"), "w", encoding="utf-8").write("\n".join(out))
