# LUX: o que o Python do editor deixa fazer para a pega nova (so leitura; SEM PIE).
#   py "<projeto>/Tools/Player/vela_api_probe.py"  -> Saved/LuxSnapshots/vela_api_probe.txt
import os, traceback, unreal

EAL, BGE = unreal.EditorAssetLibrary, unreal.BlueprintGraphEditor
OUT = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), "LuxSnapshots", "vela_api_probe.txt")
L = []


def p(*a):
    L.append(" ".join(str(x) for x in a))


def tenta(nome, fn):
    try:
        p(nome, "->", fn())
    except Exception as ex:
        p(nome, "! ", ex)


try:
    seq = EAL.load_asset("/Game/FPMovement/Demo/Character/Animations/Flashlight/AS_Flashlight_Idle")
    p("seq", seq.get_class().get_name(), "tem controller:", hasattr(seq, "controller"))
    tenta("controller", lambda: [x for x in dir(seq.controller) if not x.startswith("_")])
    tenta("data_model", lambda: [x for x in dir(seq.get_editor_property("data_model")) if not x.startswith("_")] if seq.get_editor_property("data_model") else None)
    tenta("aditivo", lambda: {k: str(seq.get_editor_property(k)) for k in ("additive_anim_type", "ref_pose_type", "ref_pose_seq", "ref_frame_index")})
    tenta("AnimationLibrary", lambda: [x for x in dir(unreal.AnimationLibrary) if any(k in x for k in ("pose", "bone", "frame", "key", "additive"))])
    tenta("num frames/keys", lambda: (unreal.AnimationLibrary.get_num_frames(seq), unreal.AnimationLibrary.get_num_keys(seq)))
    tenta("pose frame 0 hand_r local", lambda: str(unreal.AnimationLibrary.get_bone_pose_for_frame(seq, "hand_r", 0, False)))
    opts = unreal.AnimPoseEvaluationOptions()
    pose = unreal.AnimPoseExtensions.get_anim_pose_at_frame(seq, 0, opts)
    p("AnimPose ossos:", len(unreal.AnimPoseExtensions.get_bone_names(pose)))
    p("AnimPoseExtensions:", [x for x in dir(unreal.AnimPoseExtensions) if not x.startswith("_")])
    sk = EAL.load_asset("/Game/FPMovement/Demo/Character/Arms/MetaHuman/SKM_Metahuman_Arms")
    p("SkeletalMesh socket api:", [x for x in dir(sk) if "socket" in x.lower()], "| classe SkeletalMeshSocket:", hasattr(unreal, "SkeletalMeshSocket"))
    abp = EAL.load_asset("/Game/Characters/MixamoFP/Arms/ABP_Arms_Cowboy")
    ge = BGE.get_graph_editor_by_name(abp, "AnimGraph")
    p("graph editor api:", [x for x in dir(ge) if not x.startswith("_")])
    nos = list(ge.list_all_nodes())
    n0 = [n for n in nos if "NearToWall" in str(n.get_node_title())][0]
    p("no NearToWall tipo", type(n0), "| api:", [x for x in dir(n0) if not x.startswith("_")])
    tenta("NearToWall pinos", lambda: [(str(q.get_pin_name()), q.get_pin_type_display_string(), q.get_pin_value()) for q in n0.list_all_pins()])
    for k in ("node", "Node"):
        tenta("NearToWall get_editor_property(%s)" % k, lambda: str(n0.get_editor_property(k))[:300])
    mb = [n for n in nos if "Modify" in str(n.get_node_title())][0]
    tenta("ModifyBone pinos", lambda: [(str(q.get_pin_name()), q.get_pin_type_display_string(), q.get_pin_value()) for q in mb.list_all_pins()])
    ad = [n for n in nos if "Apply Additive" in str(n.get_node_title())][0]
    tenta("ApplyAdditive pinos", lambda: [(str(q.get_pin_name()), q.get_pin_type_display_string(), q.get_pin_value()) for q in ad.list_all_pins()])
    acoes = [str(a) for a in ge.list_available_nodes([])]
    p("acoes no AnimGraph: %d" % len(acoes))
    for a in acoes:
        if any(k in a for k in ("Additive", "AS_Flashlight_Idle", "Sequence Player", "Modify", "Two Bone", "Cached", "Local To Component", "Component To Local", "Layered")):
            p("   ", a)
except Exception:
    p(traceback.format_exc())
open(OUT, "w", encoding="utf-8").write("\n".join(L))
unreal.log("[LUX vela] api probe ok")
