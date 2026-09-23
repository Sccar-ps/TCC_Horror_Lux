# Etapa 5a (UE): variaveis da camada de apresentacao 1P no ABP_CowboyFP_Visible + abre o editor para colar os nos.
import os, unreal
EAL = unreal.EditorAssetLibrary
BEL = unreal.BlueprintEditorLibrary
VIS = "/Game/Characters/MixamoFP/Blueprints/ABP_CowboyFP_Visible"
BP_PLAYER = "/Game/FPMovement/Player/Blueprints/BP_Player"
saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
LOG = os.path.join(saved, "MixamoFP_visvars.txt")
out = []
DEFAULTS = (("NeckMinBehind", 10.0), ("MaxBodyShift", 25.0), ("LeanStartPitch", -20.0), ("LeanFullPitch", -75.0), ("LeanMax", 16.0))
try:
    vis = EAL.load_asset(VIS)
    player_cls = EAL.load_asset(BP_PLAYER).generated_class()
    real = BEL.get_basic_type_by_name("real")
    types = {"Player": BEL.get_object_reference_type(player_cls),
             "NeckRel": BEL.get_struct_type(unreal.Vector.static_struct()),
             "RootShift": BEL.get_struct_type(unreal.Vector.static_struct()),
             "LeanRot": BEL.get_struct_type(unreal.Rotator.static_struct()),
             "StandW": real, "BodyShift": real}
    for k, _ in DEFAULTS:
        types[k] = real
    have = set(str(n) for n in BEL.list_member_variable_names(vis))
    for name, t in types.items():
        if name not in have:
            BEL.add_member_variable(vis, name, t)
    BEL.compile_blueprint(vis)
    cdo = unreal.get_default_object(vis.generated_class())
    for k, v in DEFAULTS:
        cdo.set_editor_property(k, v)
    EAL.save_loaded_asset(vis, False)
    out.append("vars: %s" % [str(n) for n in BEL.list_member_variable_names(vis)])
    out.append("defaults: %s" % [(k, cdo.get_editor_property(k)) for k, _ in DEFAULTS])
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).open_editor_for_assets([vis])
    out.append("editor aberto")
except Exception:
    import traceback
    out.append("ERRO " + traceback.format_exc())
open(LOG, "w", encoding="utf-8").write("\n".join(out))
