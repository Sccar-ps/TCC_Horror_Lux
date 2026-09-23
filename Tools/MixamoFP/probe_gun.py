# Somente leitura: slots de material do Cowboy, secoes por LOD e APIs disponiveis para remover coldre/revolver.
import os, unreal
EAL = unreal.EditorAssetLibrary
saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
LOG = os.path.join(saved, "MixamoFP_probe_gun.txt")
out = []


def w(m):
    out.append(str(m))


def safe(f):
    try:
        return f()
    except Exception as e:
        return "?(%s)" % str(e)[:120]


try:
    skm = EAL.load_asset("/Game/Cowboy_character/Mesh/SM_SkeletalMesh_cowboy_character")
    for i, m in enumerate(skm.get_editor_property("materials")):
        mi = m.get_editor_property("material_interface")
        w("slot %d name=%s mat=%s" % (i, m.get_editor_property("material_slot_name"), mi and mi.get_path_name()))
    w("lod_info: %s" % safe(lambda: [list(i.get_editor_property("lod_material_map")) for i in skm.get_editor_property("lod_info")]))
    for l in range(3):
        w("LOD%d info: %s" % (l, safe(lambda: skm.get_lod_info(l))))
    sms = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
    w("SkeletalMeshEditorSubsystem: %s" % ", ".join(x for x in dir(sms) if not x.startswith("_")))
    w("SkeletalMesh: %s" % ", ".join(x for x in dir(skm) if not x.startswith("_") and ("section" in x.lower() or "lod" in x.lower() or "mesh_desc" in x.lower() or "material" in x.lower())))
    w("SkinnedMeshComponent.show_material_section: %s" % hasattr(unreal.SkinnedMeshComponent, "show_material_section"))
    w("GeometryScript*: %s" % [n for n in dir(unreal) if "GeometryScript" in n][:80])
    w("plugins: %s" % safe(lambda: [p for p in unreal.PluginBlueprintLibrary.get_enabled_plugin_names() if any(k in p for k in ("Geometry", "Modeling", "SkeletalMesh", "Mesh"))]))
    w("sockets: %s" % safe(lambda: [s.get_editor_property("socket_name") for s in skm.get_editor_property("sockets")]))
    w("morphs: %s" % safe(lambda: len(skm.get_editor_property("morph_targets"))))
    w("physics_asset: %s" % safe(lambda: skm.get_editor_property("physics_asset")))
    w("referenciado por: %s" % safe(lambda: unreal.EditorAssetLibrary.find_package_referencers_for_asset("/Game/Cowboy_character/Mesh/SM_SkeletalMesh_cowboy_character", False)))
except Exception:
    import traceback
    w("ERRO " + traceback.format_exc())
open(LOG, "w", encoding="utf-8").write("\n".join(out))
