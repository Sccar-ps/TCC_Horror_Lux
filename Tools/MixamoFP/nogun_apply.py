# Etapa G2 (UE): remove a geometria do coldre (slot 7) e do revolver (slot 8) em todos os LODs do DUPLICADO
# SKM_Cowboy_NoGun usando Geometry Script, limpa os dois slots de material e salva. O asset original do pacote nao muda.
import os, unreal
EAL = unreal.EditorAssetLibrary
GS = unreal.GeometryScript_AssetUtils
SRC = "/Game/Cowboy_character/Mesh/SM_SkeletalMesh_cowboy_character"
DST = "/Game/Characters/MixamoFP/Mesh/SKM_Cowboy_NoGun"
REMOVE = (7, 8)                     # mat_cowboy_holster, mat_cowboy_colt
saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
LOG = os.path.join(saved, "MixamoFP_nogun_apply.txt")
out = []


def w(m):
    out.append(str(m))


def stats(asset):
    sms = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
    rows = []
    for lod in range(sms.get_lod_count(asset)):
        n = sms.get_num_sections(asset, lod)
        rows.append("LOD%d verts=%d secoes=%d slots=%s" % (lod, sms.get_num_verts(asset, lod), n,
                                                          [sms.get_lod_material_slot(asset, lod, s) for s in range(n)]))
    return rows


try:
    src = EAL.load_asset(SRC)
    dst = EAL.load_asset(DST)
    sms = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
    w("antes: %s" % stats(dst))
    for lod in range(sms.get_lod_count(src)):
        dm = unreal.DynamicMesh()
        ropt = unreal.GeometryScriptCopyMeshFromAssetOptions()
        ropt.set_editor_property("apply_build_settings", False)
        ropt.set_editor_property("request_tangents", True)
        rl = unreal.GeometryScriptMeshReadLOD()
        rl.set_editor_property("lod_index", lod)
        rl.set_editor_property("lod_type", unreal.GeometryScriptLODType.SOURCE_MODEL)
        _, res = GS.copy_mesh_from_skeletal_mesh(src, dm, ropt, rl)
        t0 = dm.get_triangle_count()
        deleted = {}
        for mid in REMOVE:
            _, sel = dm.select_mesh_elements_by_material_id(mid)
            _, n = dm.delete_selected_triangles_from_mesh(sel)
            deleted[mid] = n
        dm.compact_mesh()
        wopt = unreal.GeometryScriptCopyMeshToAssetOptions()
        for k, v in (("replace_materials", False), ("remap_bone_indices_to_match_asset", True), ("enable_recompute_normals", True),
                     ("enable_recompute_tangents", True), ("enable_remove_degenerates", True), ("use_original_vertex_order", False),
                     ("emit_transaction", False), ("defer_mesh_post_edit_change", False)):
            try:
                wopt.set_editor_property(k, v)
            except Exception as e:
                w("  opt %s: %s" % (k, e))
        wl = unreal.GeometryScriptMeshWriteLOD()
        wl.set_editor_property("lod_index", lod)
        _, wres = GS.copy_mesh_to_skeletal_mesh(dm, dst, wopt, wl)
        w("LOD%d: leitura=%s tris %d -> %d  removidos=%s  escrita=%s" % (lod, res, t0, dm.get_triangle_count(), deleted, wres))
    # slots 7 e 8 ficam sem material: nada usa mais, e o duplicado deixa de referenciar as texturas do coldre/revolver
    used = set()
    for lod in range(sms.get_lod_count(dst)):
        for s in range(sms.get_num_sections(dst, lod)):
            m = sms.get_lod_material_slot(dst, lod, s)
            used.add(s if m < 0 else m)
    w("slots usados depois: %s" % sorted(used))
    if not any(r in used for r in REMOVE):
        mats = list(dst.get_editor_property("materials"))      # copias dos structs: preserva os demais campos
        for i in REMOVE:
            mats[i].set_editor_property("material_interface", None)
        dst.set_editor_property("materials", mats)
        w("slots 7/8 limpos")
    else:
        w("AVISO: slot removido ainda em uso; materiais mantidos")
    EAL.save_loaded_asset(dst, False)
    w("depois: %s" % stats(dst))
    w("materiais: %s" % [(i, str(m.get_editor_property("material_slot_name")), m.get_editor_property("material_interface") and m.get_editor_property("material_interface").get_name())
                          for i, m in enumerate(dst.get_editor_property("materials"))])
except Exception:
    import traceback
    w("ERRO " + traceback.format_exc())
open(LOG, "w", encoding="utf-8").write("\n".join(out))
