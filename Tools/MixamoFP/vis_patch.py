# Etapa 5e (UE): variavel LookDownShift no ABP_CowboyFP_Visible + abre o editor para colar o patch.
import os, unreal
EAL = unreal.EditorAssetLibrary
BEL = unreal.BlueprintEditorLibrary
VIS = "/Game/Characters/MixamoFP/Blueprints/ABP_CowboyFP_Visible"
saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
LOG = os.path.join(saved, "MixamoFP_vispatch.txt")
out = []
try:
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if les.is_in_play_in_editor():
        les.editor_request_end_play()
        out.append("PIE encerrado")
    vis = EAL.load_asset(VIS)
    if "LookDownShift" not in [str(n) for n in BEL.list_member_variable_names(vis)]:
        BEL.add_member_variable(vis, "LookDownShift", BEL.get_basic_type_by_name("real"))
    BEL.compile_blueprint(vis)
    cdo = unreal.get_default_object(vis.generated_class())
    cdo.set_editor_property("LookDownShift", 12.0)
    cdo.set_editor_property("LeanMax", 14.0)
    EAL.save_loaded_asset(vis, False)
    out.append("vars: %s" % [str(n) for n in BEL.list_member_variable_names(vis)])
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).open_editor_for_assets([vis])
except Exception:
    import traceback
    out.append("ERRO " + traceback.format_exc())
open(LOG, "w", encoding="utf-8").write("\n".join(out))
