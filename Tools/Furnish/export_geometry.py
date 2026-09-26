# Somente leitura: exporta triangulos (espaco de mundo) das malhas do mapa aberto para gerar a planta baixa.
# Rodar:  py "C:/Users/bruno/Documents/Unreal Projects/TCC_Horror_Lux/Tools/Furnish/export_geometry.py"
# Saida:  Saved/Furnish/geometry.json
import os, json, unreal

saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
OUTDIR = os.path.join(saved, "Furnish")
os.makedirs(OUTDIR, exist_ok=True)
MAX_TRIS = 20000

ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
w = ues.get_editor_world()
out, errs = [], []
cache = {}


def mesh_tris(sm):
    key = sm.get_path_name()
    if key in cache:
        return cache[key]
    tris_all = []
    try:
        nsec = sm.get_num_sections(0)
    except Exception:
        nsec = 1
    for s in range(nsec):
        try:
            r = unreal.ProceduralMeshLibrary.get_section_from_static_mesh(sm, 0, s)
            verts, idx = r[0], r[1]
            for i in range(0, len(idx) - 2, 3):
                tris_all.append((verts[idx[i]], verts[idx[i + 1]], verts[idx[i + 2]]))
                if len(tris_all) > MAX_TRIS:
                    break
        except Exception as e:
            errs.append("%s sec%d: %s" % (key, s, e))
    cache[key] = tris_all
    return tris_all


for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Actor):
    for c in a.get_components_by_class(unreal.StaticMeshComponent):
        sm = c.get_editor_property("static_mesh")
        if not sm:
            continue
        if isinstance(c, unreal.InstancedStaticMeshComponent):
            continue
        org, ext = a.get_actor_bounds(False)
        entry = {"label": a.get_actor_label(), "mesh": sm.get_path_name().split(".")[0],
                 "comp": c.get_name(), "tris": []}
        try:
            ntri = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem).get_number_verts(sm, 0)
        except Exception:
            ntri = 0
        if ntri > MAX_TRIS:
            entry["skipped"] = ntri
        else:
            t = c.get_world_transform()
            for (p0, p1, p2) in mesh_tris(sm):
                q = [unreal.MathLibrary.transform_location(t, p) for p in (p0, p1, p2)]
                entry["tris"].append([[round(v.x, 1), round(v.y, 1), round(v.z, 1)] for v in q])
        out.append(entry)

json.dump({"actors": out, "errors": errs[:50]}, open(os.path.join(OUTDIR, "geometry.json"), "w"))
unreal.log("Furnish geometry OK: %d componentes, %d erros" % (len(out), len(errs)))
