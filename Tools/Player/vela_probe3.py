# LUX: levantamento 3 (so leitura): valores dos pinos do fluxo da lanterna no BP_Player e tempos dos notifies.
#   py "<projeto>/Tools/Player/vela_probe3.py"  -> Saved/LuxSnapshots/vela_probe3.txt
import os, unreal

EAL, BGE = unreal.EditorAssetLibrary, unreal.BlueprintGraphEditor
OUT = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), "LuxSnapshots", "vela_probe3.txt")
L = []


def t(n):
    return str(n.get_node_title()).replace("\n", " | ")


def val(p):
    for f in ("get_default_value", "get_pin_value", "get_default_as_string", "get_value"):
        if hasattr(p, f):
            try:
                return "%s" % getattr(p, f)()
            except Exception as e:
                return "!%s" % e
    return "?"


bp = EAL.load_asset("/Game/FPMovement/Player/Blueprints/BP_Player")
ge = BGE.get_graph_editor_by_name(bp, "EventGraph")
nos = list(ge.list_all_nodes())
p0 = next(iter(nos[0].list_all_pins()))
L.append("pin api: %s" % [x for x in dir(p0) if not x.startswith("_")])
CHAVES = ("Flashlight", "Montage", "Delay", "SetVisibility", "SpawnSound", "CanDoFlashlight", "HasFlashlight", "PrintString", "SetIntensity", "Lerp")
for n in nos:
    tt = t(n)
    if not any(k.replace(" ", "") in tt.replace(" ", "") for k in CHAVES):
        continue
    ps = []
    for p in n.list_all_pins():
        lig = ["%s.%s" % (t(q.get_owning_node())[:40], q.get_pin_name()) for q in p.list_connected_pins()]
        ps.append("%s=%r%s" % (p.get_pin_name(), val(p)[:80], (" ->%s" % lig) if lig else ""))
    L.append("[%s] %s @%s :: %s" % (n.get_name(), tt[:80], n.get_node_pos() if hasattr(n, "get_node_pos") else "", "; ".join(ps)))

base = "/Game/FPMovement/Demo/Character/Animations/Flashlight/"
AL = unreal.AnimationLibrary
for n in ("AS_Flashlight_Eqiup", "AS_Flashlight_Unequip", "Montages/AS_Flashlight_Eqiup_Montage", "Montages/AS_Flashlight_Unequip_Montage"):
    a = EAL.load_asset(base + n)
    L.append("ANIM %s len=%s" % (n, AL.get_sequence_length(a)))
    for e in AL.get_animation_notify_events(a):
        tm = "?"
        for f in ("get_anim_notify_event_trigger_time", "get_animation_notify_event_trigger_time"):
            if hasattr(AL, f):
                try:
                    tm = getattr(AL, f)(e)
                except Exception as ex:
                    tm = "!%s" % ex
                break
        L.append("   %s t=%s" % (e.get_editor_property("notify_name"), tm))
    L.append("   AL funcs notify: %s" % [x for x in dir(AL) if "notify" in x.lower() and "time" in x.lower()])

cow = EAL.load_asset("/Game/Characters/MixamoFP/Blueprints/BP_Player_Cowboy")
cdo = unreal.get_default_object(cow.generated_class())
L.append("Cowboy CDO HasFlashlight?=%s FlashlightOn?=%s CanDoFlashlight=%s FlashlightIntensity=%s" % tuple(
    cdo.get_editor_property(k) for k in ("HasFlashlight?", "FlashlightOn?", "CanDoFlashlight", "FlashlightIntensity")))
L.append("Cowboy grafos: %s" % [str(x) for x in unreal.BlueprintEditorLibrary.list_graph_names(cow)])
open(OUT, "w", encoding="utf-8").write("\n".join(L))
unreal.log("[LUX vela] probe3 ok")
