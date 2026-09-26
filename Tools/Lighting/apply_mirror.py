# Espelho na moldura vazia sobre a comoda do quarto (Quarto_Quadro_Comoda) + corpo inteiro do player so no reflexo.
# Uso:  py "C:/Users/bruno/Documents/Unreal Projects/TCC_Horror_Lux/Tools/Lighting/apply_mirror.py"
# Requer Configuracoes do Projeto > Engine > Rendering > "Support global clip plane for Planar Reflections" (+ reiniciar).
# Mapa: 1 transacao ("LUX: espelho"), NAO salva. Material e BP_Player_Cowboy: compilados e SALVOS (reverter pelo git).
# Idempotente (tag LUX_MIRROR). Log com os valores anteriores do BP: Saved/MirrorApply.txt
import os, unreal

FRAME = "Quarto_Quadro_Comoda"
SIZE = (54.0, 80.0)       # cm: abertura da moldura (externa 64 x 90, filete ~6 cm)
OFFSET = 1.0              # cm a frente da parede, dentro da moldura (profundidade da moldura: ~4 cm)
TINT = unreal.LinearColor(0.55, 0.55, 0.52, 1.0)  # prata envelhecida (1.0 = espelho perfeito)
ROUGHNESS = 0.03
PLANAR = {"screen_percentage": 50.0,                 # resolucao do reflexo: principal alavanca de custo
          "distance_from_plane_fadeout_start": 5.0,  # so o plano do espelho recebe o reflexo
          "distance_from_plane_fadeout_end": 10.0}
MODE = "capture"  # corpo no reflexo via flags de Scene Capture; "owner" = via Owner No See / Only Owner See
MAT = "/Game/Masion/LUX/Materials/M_LUX_Mirror"
BP = "/Game/Characters/MixamoFP/Blueprints/BP_Player_Cowboy"
TAG = "LUX_MIRROR"

# CharacterMesh0 = malha-sombra (corpo inteiro). Passa a aparecer SO no reflexo e continua projetando sombra.
# BodyVisible (sem cabeca/bracos) e bracos FP: fora do reflexo.
BODY = {
    "capture": {
        "CharacterMesh0": {"render_in_main_pass": True, "render_in_depth_pass": True,
                           "visible_in_scene_capture_only": True, "cast_hidden_shadow": True},
        "BodyVisible": {"hidden_in_scene_capture": True},
        "FirstPersonMesh": {"hidden_in_scene_capture": True},
        "SM_Flashlight": {"hidden_in_scene_capture": True},
    },
    "owner": {
        "CharacterMesh0": {"render_in_main_pass": True, "render_in_depth_pass": True, "owner_no_see": True,
                           "cast_hidden_shadow": True, "visible_in_scene_capture_only": False},
        "BodyVisible": {"only_owner_see": True, "hidden_in_scene_capture": False},
        "FirstPersonMesh": {"hidden_in_scene_capture": False},
        "SM_Flashlight": {"only_owner_see": True, "hidden_in_scene_capture": False},
    },
}[MODE]

saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
L = ["MODE=%s  r.AllowGlobalClipPlane=%s" % (MODE, unreal.SystemLibrary.get_console_variable_float_value("r.AllowGlobalClipPlane"))]
mel = unreal.MaterialEditingLibrary
eal = unreal.EditorAssetLibrary

# ---------- material ----------
if eal.does_asset_exist(MAT):
    mat = unreal.load_asset(MAT)
else:
    mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        "M_LUX_Mirror", MAT.rsplit("/", 1)[0], unreal.Material, unreal.MaterialFactoryNew())
mel.delete_all_material_expressions(mat)
for cls, prop, val, y in ((unreal.MaterialExpressionConstant3Vector, unreal.MaterialProperty.MP_BASE_COLOR, TINT, 0),
                          (unreal.MaterialExpressionConstant, unreal.MaterialProperty.MP_METALLIC, 1.0, 150),
                          (unreal.MaterialExpressionConstant, unreal.MaterialProperty.MP_ROUGHNESS, ROUGHNESS, 300)):
    e = mel.create_material_expression(mat, cls, -300, y)
    e.set_editor_property("constant" if cls is unreal.MaterialExpressionConstant3Vector else "r", val)
    mel.connect_material_property(e, "", prop)
mel.recompile_material(mat)
eal.save_loaded_asset(mat)

# ---------- mapa: plano + Planar Reflection presos a moldura ----------
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actors = eas.get_all_level_actors()
frame = next(a for a in actors if a.get_actor_label() == FRAME)
with unreal.ScopedEditorTransaction("LUX: espelho"):
    for a in actors:
        if a.actor_has_tag(TAG):
            eas.destroy_actor(a)

    def place(actor, label, scale):
        actor.set_actor_label(label)
        actor.tags = [TAG]
        actor.set_folder_path("LUX/Espelho")
        actor.attach_to_actor(frame, "", unreal.AttachmentRule.KEEP_RELATIVE, unreal.AttachmentRule.KEEP_RELATIVE,
                              unreal.AttachmentRule.KEEP_RELATIVE, False)
        for roll in (-90.0, 90.0):  # Z local do ator -> frente da moldura (sinal conferido abaixo)
            actor.set_actor_relative_transform(unreal.Transform(unreal.Vector(0, OFFSET, 0),
                                                                unreal.Rotator(roll=roll, pitch=0.0, yaw=0.0), scale),
                                               False, False)
            if actor.get_actor_up_vector().dot(frame.get_actor_right_vector()) > 0.99:
                break

    plane = eas.spawn_actor_from_class(unreal.StaticMeshActor, frame.get_actor_location())
    smc = plane.static_mesh_component
    smc.set_editor_property("static_mesh", unreal.load_asset("/Engine/BasicShapes/Plane"))
    smc.set_material(0, mat)
    smc.set_collision_profile_name("NoCollision")
    smc.set_editor_property("cast_shadow", False)
    place(plane, "LUX_Espelho", unreal.Vector(SIZE[0] / 100.0, SIZE[1] / 100.0, 1.0))

    pr = eas.spawn_actor_from_class(unreal.PlanarReflection, frame.get_actor_location())
    o, ext = pr.get_actor_bounds(False)  # tamanho base do plano de preview (ator ainda sem rotacao)
    place(pr, "LUX_Espelho_Reflexo", unreal.Vector(SIZE[0] / (2 * max(ext.x, 1)), SIZE[1] / (2 * max(ext.y, 1)), 1.0))
    prc = pr.get_component_by_class(unreal.PlanarReflectionComponent)
    for k, v in PLANAR.items():
        prc.set_editor_property(k, v)
    L.append("frame %s | espelho up=%s | planar base ext=%s" % (frame.get_actor_location(), plane.get_actor_up_vector(), ext))

# ---------- BP_Player_Cowboy ----------
bp = unreal.load_asset(BP)
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
lib = unreal.SubobjectDataBlueprintFunctionLibrary
done = set()
for h in sds.k2_gather_subobject_data_for_blueprint(bp):
    d = lib.get_data(h)
    o = lib.get_object_for_blueprint(d, bp)
    if o is None:  # no raiz (ator) nao ha componente
        continue
    name = str(lib.get_variable_name(d)) if lib.get_variable_name(d) else ""
    key = next((k for k in BODY if k == name or o.get_name().startswith(k)), None)
    if not key or key in done:
        continue
    done.add(key)
    o.modify()
    for p, v in BODY[key].items():
        L.append("%s.%s: %s -> %s" % (key, p, o.get_editor_property(p), v))
        o.set_editor_property(p, v)
L.append("componentes ajustados: %s (faltando: %s)" % (sorted(done), sorted(set(BODY) - done)))
unreal.BlueprintEditorLibrary.compile_blueprint(bp)
eal.save_loaded_asset(bp)

L.append("Mapa NAO salvo (Ctrl+S). Material e BP salvos.")
open(os.path.join(saved, "MirrorApply.txt"), "w", encoding="utf-8").write("\n".join(str(x) for x in L))
unreal.log("LUX espelho aplicado")
