# Etapa G1 (UE): duplica o Cowboy (o original do pacote NAO e tocado) e analisa, por LOD, os IDs de material
# da malha dinamica (Geometry Script) para localizar coldre (slot 7) e revolver (slot 8). Nada e gravado alem do duplicado.
import os, unreal
EAL = unreal.EditorAssetLibrary
GS = unreal.GeometryScript_AssetUtils
SEL = unreal.GeometryScript_MeshSelection
SRC = "/Game/Cowboy_character/Mesh/SM_SkeletalMesh_cowboy_character"
DST = "/Game/Characters/MixamoFP/Mesh/SKM_Cowboy_NoGun"
saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
LOG = os.path.join(saved, "MixamoFP_nogun_analyze.txt")
out = []


def w(m):
    out.append(str(m))


def read_lod(asset, lod, lod_type):
    dm = unreal.DynamicMesh()
    opts = unreal.GeometryScriptCopyMeshFromAssetOptions()
    opts.set_editor_property("apply_build_settings", False)
    opts.set_editor_property("request_tangents", True)
    rl = unreal.GeometryScriptMeshReadLOD()
    rl.set_editor_property("lod_index", lod)
    rl.set_editor_property("lod_type", lod_type)
    res = GS.copy_mesh_from_skeletal_mesh(asset, dm, opts, rl)
    return dm, res


def mat_histogram(dm):
    mx, has = dm.get_max_material_id()
    hist = {}
    for mid in range(mx + 1):
        _, sel = dm.select_mesh_elements_by_material_id(mid)
        try:
            info = SEL.get_mesh_selection_info(dm, sel)
            n = info[1] if isinstance(info, tuple) else info
        except Exception as e:
            n = "?(%s)" % str(e)[:60]
        hist[mid] = n
    return hist


try:
    if not EAL.does_directory_exist("/Game/Characters/MixamoFP/Mesh"):
        EAL.make_directory("/Game/Characters/MixamoFP/Mesh")
    if not EAL.does_asset_exist(DST):
        EAL.duplicate_asset(SRC, DST)
        w("duplicado criado: %s" % DST)
    dst = EAL.load_asset(DST)
    sms = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
    w("GeometryScriptLODType: %s" % [x for x in dir(unreal.GeometryScriptLODType) if x.isupper()])
    for lod in range(sms.get_lod_count(dst)):
        n = sms.get_num_sections(dst, lod)
        w("LOD%d verts=%d secoes=%d slots=%s" % (lod, sms.get_num_verts(dst, lod), n, [sms.get_lod_material_slot(dst, lod, s) for s in range(n)]))
        for lt in ("SOURCE_MODEL", "RENDER_DATA"):
            try:
                dm, res = read_lod(dst, lod, getattr(unreal.GeometryScriptLODType, lt))
                w("   %s: outcome=%s tris=%d verts=%d mats=%s" % (lt, res[1] if isinstance(res, tuple) else res,
                                                               dm.get_triangle_count(), dm.get_vertex_count(), mat_histogram(dm)))
            except Exception as e:
                w("   %s: ERRO %s" % (lt, str(e)[:200]))
except Exception:
    import traceback
    w("ERRO " + traceback.format_exc())
open(LOG, "w", encoding="utf-8").write("\n".join(out))
