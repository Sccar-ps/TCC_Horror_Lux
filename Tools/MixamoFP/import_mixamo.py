# Etapa 1 (UE): importa o proxy do esqueleto Mixamo e as animacoes pre-processadas (SourceArt/MixamoFP).
# Usa o importador FBX classico (desliga o Interchange so durante a importacao e religa no final).
import os, json, unreal
PROJ = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
SRC = os.path.join(PROJ, "SourceArt", "MixamoFP")
DST = "/Game/Characters/MixamoFP/Source"
DST_A = DST + "/Anims"
saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
LOG = os.path.join(saved, "MixamoFP_import.txt")
out = []


def w(m):
    out.append(str(m))
    unreal.log("[MixamoFP] " + str(m))


def cvar(v):
    unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX " + v)


def run(tasks):
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
    res = []
    for t in tasks:
        res.append(list(t.get_editor_property("imported_object_paths")))
    return res


def bone_names(skm):
    c = unreal.new_object(unreal.SkeletalMeshComponent)
    c.set_skeletal_mesh_asset(skm)
    return [str(c.get_bone_name(i)) for i in range(c.get_num_bones())]


try:
    prev = unreal.SystemLibrary.get_console_variable_int_value("Interchange.FeatureFlags.Import.FBX")
    cvar("0")
    w("Interchange FBX: %s -> 0 (temporario)" % prev)
    # ---- proxy
    o = unreal.FbxImportUI()
    o.set_editor_property("import_mesh", True)
    o.set_editor_property("import_as_skeletal", True)
    o.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_SKELETAL_MESH)
    o.set_editor_property("import_animations", False)
    o.set_editor_property("import_materials", False)
    o.set_editor_property("import_textures", False)
    o.set_editor_property("create_physics_asset", False)
    sd = o.get_editor_property("skeletal_mesh_import_data")
    sd.set_editor_property("import_morph_targets", False)
    sd.set_editor_property("convert_scene", True)
    sd.set_editor_property("use_t0_as_ref_pose", False)
    t = unreal.AssetImportTask()
    t.set_editor_property("filename", os.path.join(SRC, "SKM_Mixamo_Proxy.fbx"))
    t.set_editor_property("destination_path", DST)
    t.set_editor_property("automated", True)
    t.set_editor_property("save", True)
    t.set_editor_property("replace_existing", True)
    t.set_editor_property("options", o)
    w("proxy: %s" % run([t]))
    skm = unreal.load_asset(DST + "/SKM_Mixamo_Proxy")
    skel = skm.get_editor_property("skeleton")
    names = bone_names(skm)
    w("skeleton: %s | %d ossos | raiz=%s | %s" % (skel.get_path_name(), len(names), names[0] if names else None, names[:6]))
    # ---- animacoes
    man = json.load(open(os.path.join(SRC, "manifest.json"), encoding="utf-8"))
    tasks = []
    for name in man:
        a = unreal.FbxImportUI()
        a.set_editor_property("import_mesh", False)
        a.set_editor_property("import_animations", True)
        a.set_editor_property("import_materials", False)
        a.set_editor_property("import_textures", False)
        a.set_editor_property("skeleton", skel)
        a.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_ANIMATION)
        ad = a.get_editor_property("anim_sequence_import_data")
        ad.set_editor_property("animation_length", unreal.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
        ad.set_editor_property("import_bone_tracks", True)
        ad.set_editor_property("remove_redundant_keys", False)
        ad.set_editor_property("use_default_sample_rate", False)
        ad.set_editor_property("custom_sample_rate", 30)
        ad.set_editor_property("convert_scene", True)
        ad.set_editor_property("import_meshes_in_bone_hierarchy", False)
        ad.set_editor_property("import_custom_attribute", False)
        tt = unreal.AssetImportTask()
        tt.set_editor_property("filename", os.path.join(SRC, name + ".fbx"))
        tt.set_editor_property("destination_path", DST_A)
        tt.set_editor_property("destination_name", name)
        tt.set_editor_property("automated", True)
        tt.set_editor_property("save", True)
        tt.set_editor_property("replace_existing", True)
        tt.set_editor_property("options", a)
        tasks.append(tt)
    res = run(tasks)
    for name, r in zip(man, res):
        anim = unreal.load_asset(DST_A + "/" + name)
        if anim is None:
            w("  FALHOU %s %s" % (name, r))
            continue
        hips = unreal.AnimationLibrary.get_bone_pose_for_time(anim, "Hips", 0.0, False).translation
        w("  %-16s len=%.3f s frames=%s hips0=(%.1f,%.1f,%.1f)" % (name, anim.get_play_length(), unreal.AnimationLibrary.get_num_frames(anim), hips.x, hips.y, hips.z))
except Exception:
    import traceback
    w("ERRO: " + traceback.format_exc())
finally:
    cvar("1")
    w("Interchange FBX restaurado para 1")
    open(LOG, "w", encoding="utf-8").write("\n".join(out))
