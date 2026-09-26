# Somente leitura: triangulos por secao (secao = slot de material) das malhas _GENERATED, em espaco local.
# Usa apenas chamadas ja testadas (get_section_from_static_mesh). Saida: Saved/Furnish/sections.json
import os, json, unreal

saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
OUT = os.path.join(saved, "Furnish", "sections.json")
ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
w = ues.get_editor_world()
res = []
done = {}
for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.StaticMeshActor):
    for c in a.get_components_by_class(unreal.StaticMeshComponent):
        sm = c.get_editor_property("static_mesh")
        if not sm:
            continue
        p = sm.get_path_name()
        if "/Masion/_GENERATED/" not in p:
            continue
        t = c.get_world_transform()
        entry = {"label": a.get_actor_label(), "comp": c.get_name(), "mesh": p,
                 "mats": [(m.get_path_name() if m else None) for m in c.get_materials()],
                 "loc": [t.translation.x, t.translation.y, t.translation.z],
                 "rot": [t.rotation.rotator().roll, t.rotation.rotator().pitch, t.rotation.rotator().yaw],
                 "scale": [t.scale3d.x, t.scale3d.y, t.scale3d.z], "sections": []}
        n = sm.get_num_sections(0)
        for s in range(n):
            r = unreal.ProceduralMeshLibrary.get_section_from_static_mesh(sm, 0, s)
            verts, idx = r[0], r[1]
            uvs = r[3] if len(r) > 3 else []
            entry["sections"].append({"v": [[round(v.x, 1), round(v.y, 1), round(v.z, 1)] for v in verts],
                                      "i": list(idx),
                                      "uv": [[round(u.x, 4), round(u.y, 4)] for u in uvs]})
        res.append(entry)
json.dump(res, open(OUT, "w"))
unreal.log("sections.json OK (%d)" % len(res))
