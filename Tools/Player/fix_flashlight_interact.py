# LUX: a lanterna na mao (SM_Flashlight) fica sem colisao no BP_Player_Cowboy. Ela vinha do BP_Player (FPMovement)
# com BlockAllDynamic (Query and Physics): um item segurado nao deve bloquear nada. O BP_Player nao e editado:
# o ajuste e feito no template do componente herdado dentro do BP_Player_Cowboy.
# Idempotente. Compila e salva so o BP_Player_Cowboy.
#   py "<projeto>/Tools/Player/fix_flashlight_interact.py"          -> NoCollision
#   py "<projeto>/Tools/Player/fix_flashlight_interact.py" desfazer -> BlockAllDynamic (como no BP_Player)
import sys
import unreal

BP = "/Game/Characters/MixamoFP/Blueprints/BP_Player_Cowboy"
DESFAZER = "desfazer" in [str(a).lower() for a in sys.argv[1:]]
PERFIL = "BlockAllDynamic" if DESFAZER else "NoCollision"

bp = unreal.EditorAssetLibrary.load_asset(BP)
unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
lib = unreal.SubobjectDataBlueprintFunctionLibrary
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)


def lanterna():
    out = []
    for h in sds.k2_gather_subobject_data_for_blueprint(bp):
        o = lib.get_object_for_blueprint(lib.get_data(h), bp)
        if isinstance(o, unreal.PrimitiveComponent) and "Flashlight" in o.get_name():
            out.append(o)
    return out


def estado():
    return ["%s @ %s: %s %s" % (o.get_name(), o.get_outer().get_name(), o.get_collision_profile_name(), o.get_collision_enabled())
            for o in lanterna()]


print("antes: ", estado())
with unreal.ScopedEditorTransaction("LUX: lanterna sem colisao"):
    for o in lanterna():
        o.modify()
        o.set_collision_profile_name(PERFIL)
unreal.BlueprintEditorLibrary.compile_blueprint(bp)
print("depois:", estado())
luzes = [lib.get_object_for_blueprint(lib.get_data(h), bp) for h in sds.k2_gather_subobject_data_for_blueprint(bp)]
print("luzes da lanterna (sem colisao por serem luzes):",
      [o.get_name() for o in luzes if isinstance(o, unreal.LightComponent) and "Flashlight" in o.get_name()])
print("salvo:", unreal.EditorAssetLibrary.save_loaded_asset(bp, False))
