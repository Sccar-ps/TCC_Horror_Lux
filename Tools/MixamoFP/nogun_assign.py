# Etapa G3 (UE): troca a malha das duas camadas do BP_Player_Cowboy (Mesh = sombra, BodyVisible = visivel)
# para o SKM_Cowboy_NoGun e usa o mesmo mesh como preview dos dois ABPs. BP_Player e o Cowboy original nao mudam.
import os, unreal
EAL = unreal.EditorAssetLibrary
BEL = unreal.BlueprintEditorLibrary
NEW = "/Game/Characters/MixamoFP/Mesh/SKM_Cowboy_NoGun"
BP = "/Game/Characters/MixamoFP/Blueprints/BP_Player_Cowboy"
ABPS = ("/Game/Characters/MixamoFP/Blueprints/ABP_CowboyFP", "/Game/Characters/MixamoFP/Blueprints/ABP_CowboyFP_Visible")
saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
LOG = os.path.join(saved, "MixamoFP_nogun_assign.txt")
out = []


def w(m):
    out.append(str(m))


try:
    new = EAL.load_asset(NEW)
    bp = EAL.load_asset(BP)
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary

    def apply():
        mesh = unreal.get_default_object(bp.generated_class()).get_editor_property("mesh")
        mesh.set_skeletal_mesh_asset(new)
        vis = None
        for h in sds.k2_gather_subobject_data_for_blueprint(bp):
            o = lib.get_object(lib.get_data(h))
            if o and o.get_name().startswith("BodyVisible"):
                vis = o
        vis.set_skeletal_mesh_asset(new)
        return mesh, vis

    apply()
    EAL.save_loaded_asset(bp, False)
    BEL.compile_blueprint(bp)
    mesh, vis = apply()                      # o compile pode restaurar o template; reaplica
    EAL.save_loaded_asset(bp, False)
    w("Mesh=%s | BodyVisible=%s" % (mesh.get_skeletal_mesh_asset().get_name(), vis.get_skeletal_mesh_asset().get_name()))
    for p in ABPS:
        abp = EAL.load_asset(p)
        try:
            abp.set_editor_property("preview_skeletal_mesh", new)
            EAL.save_loaded_asset(abp, False)
            w("%s preview=%s" % (p.rsplit("/", 1)[-1], abp.get_editor_property("preview_skeletal_mesh")))
        except Exception as e:
            w("%s preview: %s" % (p.rsplit("/", 1)[-1], str(e)[:120]))
except Exception:
    import traceback
    w("ERRO " + traceback.format_exc())
open(LOG, "w", encoding="utf-8").write("\n".join(out))
