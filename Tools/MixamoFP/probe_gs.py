# Somente leitura: localiza as funcoes do Geometry Script para editar o Skeletal Mesh e mapeia secoes/LODs do Cowboy.
import os, unreal
saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
LOG = os.path.join(saved, "MixamoFP_probe_gs.txt")
out = []
WANT = ("copy_mesh_from_skeletal_mesh", "copy_mesh_to_skeletal_mesh", "select_mesh_elements_by_material_id",
        "delete_selected_triangles_from_mesh", "delete_triangles_from_mesh", "get_material_i_ds_of_triangles",
        "get_triangle_material_id", "get_max_material_id", "compact_mesh", "remap_material_i_ds", "get_num_triangle_i_ds",
        "get_vertex_count", "get_triangle_count", "has_triangle_material_i_ds", "copy_mesh_from_component")
try:
    for name in dir(unreal):
        obj = getattr(unreal, name, None)
        if not isinstance(obj, type):
            continue
        hits = [f for f in WANT if hasattr(obj, f)]
        if hits:
            out.append("%s: %s" % (name, hits))
            for f in hits:
                out.append("   %s" % (getattr(obj, f).__doc__ or "").split("\n")[0][:300])
    for cls in ("GeometryScriptCopyMeshFromAssetOptions", "GeometryScriptCopyMeshToAssetOptions", "GeometryScriptMeshReadLOD", "GeometryScriptMeshWriteLOD"):
        c = getattr(unreal, cls, None)
        if c:
            out.append("%s props: %s" % (cls, [p for p in dir(c()) if not p.startswith("_") and p not in dir(unreal.StructBase)]))
    skm = unreal.load_asset("/Game/Cowboy_character/Mesh/SM_SkeletalMesh_cowboy_character")
    sms = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
    for lod in range(sms.get_lod_count(skm)):
        n = sms.get_num_sections(skm, lod)
        out.append("LOD%d verts=%d secoes=%d slots=%s cloth=%s build=%s" % (
            lod, sms.get_num_verts(skm, lod), n, [sms.get_lod_material_slot(skm, lod, s) for s in range(n)],
            [skm.is_section_using_cloth(s, True) if lod == 0 else "-" for s in range(n)] if lod == 0 else "-",
            str(sms.get_lod_build_settings(skm, lod))[:300]))
    out.append("lod_settings asset: %s" % skm.get_editor_property("lod_settings"))
except Exception:
    import traceback
    out.append("ERRO " + traceback.format_exc())
open(LOG, "w", encoding="utf-8").write("\n".join(out))
