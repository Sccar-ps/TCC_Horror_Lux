# LUX: levantamento 2 (so leitura): nomes de nos disponiveis no NotifyGraph do ABP_Arms_Cowboy e tempos dos notifies.
import os, unreal

EAL, BGE = unreal.EditorAssetLibrary, unreal.BlueprintGraphEditor
OUT = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), "LuxSnapshots", "vela_probe2.txt")
L = []
abp = EAL.load_asset("/Game/Characters/MixamoFP/Arms/ABP_Arms_Cowboy")
ge = BGE.get_graph_editor_by_name(abp, "NotifyGraph")
for a in ge.list_available_nodes([]):
    s = str(a)
    if any(k in s for k in ("ShowFlashlight", "HideFlashlight", "Flashlight_On", "Flashlight_Off", "BP_Player_Cowboy", "Vela")):
        L.append("no: " + s)
base = "/Game/FPMovement/Demo/Character/Animations/Flashlight/"
for n in ("AS_Flashlight_Eqiup", "AS_Flashlight_Unequip"):
    a = EAL.load_asset(base + n)
    for e in unreal.AnimationLibrary.get_animation_notify_events(a):
        L.append("%s %s attrs=%s" % (n, e.get_editor_property("notify_name"), [x for x in dir(e) if not x.startswith("_")]))
        for k in dir(e):
            if k.startswith("_") or k in ("cast", "copy", "static_struct", "export_text", "import_text", "to_tuple", "assign", "get_editor_property", "set_editor_property", "compare"):
                continue
            try:
                v = getattr(e, k)
                L.append("    %s = %s" % (k, v() if callable(v) else v))
            except Exception as ex:
                L.append("    %s ! %s" % (k, ex))
    try:
        L.append("  track names: %s" % unreal.AnimationLibrary.get_animation_notify_track_names(a))
        for tn in unreal.AnimationLibrary.get_animation_notify_track_names(a):
            for e in unreal.AnimationLibrary.get_animation_notify_events_for_track(a, tn):
                L.append("  track %s: %s" % (tn, e.get_editor_property("notify_name")))
    except Exception as ex:
        L.append("  tracks ! %s" % ex)
    try:
        fr = unreal.AnimationLibrary.get_frame_rate(a)
        L.append("  framerate %s frames %s" % (fr, unreal.AnimationLibrary.get_num_frames(a)))
    except Exception as ex:
        L.append("  fr ! %s" % ex)
bp = EAL.load_asset("/Game/Characters/MixamoFP/Blueprints/BP_Player_Cowboy")
lib = unreal.SubobjectDataBlueprintFunctionLibrary
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
for h in sds.k2_gather_subobject_data_for_blueprint(bp):
    o = lib.get_object_for_blueprint(lib.get_data(h), bp)
    if isinstance(o, unreal.SceneComponent) and "Flashlight" in o.get_name():
        L.append("comp %s %s visible=%s hidden_in_game=%s" % (o.get_name(), o.get_class().get_name(), o.get_editor_property("visible"), o.get_editor_property("hidden_in_game")))
open(OUT, "w", encoding="utf-8").write("\n".join(L))
unreal.log("[LUX vela] probe2 ok")
