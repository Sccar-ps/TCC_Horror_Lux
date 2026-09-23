from t3d import *
import json

ABP = "/Game/Characters/MixamoFP/Blueprints/ABP_CowboyFP.ABP_CowboyFP"
ABP_C = "/Game/Characters/MixamoFP/Blueprints/ABP_CowboyFP.ABP_CowboyFP_C"
VIS = "/Game/Characters/MixamoFP/Blueprints/ABP_CowboyFP_Visible.ABP_CowboyFP_Visible"
VIS_C = "/Game/Characters/MixamoFP/Blueprints/ABP_CowboyFP_Visible.ABP_CowboyFP_Visible_C"
BPP_C = "/Game/FPMovement/Player/Blueprints/BP_Player.BP_Player_C"
KML = "/Script/Engine.KismetMathLibrary"
KML_D = "/Script/Engine.Default__KismetMathLibrary"
KAL = "/Script/AnimGraphRuntime.KismetAnimationLibrary"
KAL_D = "/Script/AnimGraphRuntime.Default__KismetAnimationLibrary"
PLAYER = bpc_ref(BPP_C)
CAPSULE = cls_ref("/Script/Engine.CapsuleComponent")
D = ("real", "double", "None")


def dbl(name, default="0.0"):
    return (name, "real", "double", "None", default, False, False)


def math2(g, func, x, y, a="0.0", b="0.0", names=("A", "B")):
    return call(g, KML, func, x, y, lib=KML_D, ret=D, inputs=[dbl(names[0], a), dbl(names[1], b)])


# ====================================================================== ABP_CowboyFP / EventGraph
g = Graph(ABP, "EventGraph", abpc_ref(ABP_C))
e_init = ev(g, "BlueprintInitializeAnimation", -1400, -700)
f_pawn = call(g, "/Script/Engine.AnimInstance", "TryGetPawnOwner", -1380, -540, self_ctx=True,
              ret=("object", "", cls_ref("/Script/Engine.Pawn")), self_ref=abpc_ref(ABP_C))
c_cast = cast(g, BPP_C, "AsBP Player", -1080, -700)
s_player = var_set(g, "Player", "object", "", PLAYER, -760, -700)
g_cap1 = var_get(g, "CapsuleComponent", "object", "", CAPSULE, owner=cls_ref("/Script/Engine.Character"), x=-760, y=-520)
f_hh1 = call(g, "/Script/Engine.CapsuleComponent", "GetScaledCapsuleHalfHeight", -500, -520, ret=("real", "float", "None"))
s_stand = var_set(g, "StandingHalfHeight", "real", "double", "None", -240, -700)
link(e_init["then"], c_cast["execute"])
link(f_pawn["ReturnValue"], c_cast["Object"])
link(c_cast["then"], s_player["execute"])
link(c_cast["AsBP Player"], s_player["Player"])
link(s_player["then"], s_stand["execute"])
link(s_player["Output_Get"], g_cap1["self"])
link(g_cap1["CapsuleComponent"], f_hh1["self"])
link(f_hh1["ReturnValue"], s_stand["StandingHalfHeight"])

X, Y = -1100, 0
g_pl = var_get(g, "Player", "object", "", PLAYER, x=X - 260, y=Y + 240)
m_valid = is_valid(g, X, Y)
link(g_pl["Player"], m_valid["InputObject"])
# Speed / Direction
f_vel = call(g, "/Script/Engine.Actor", "GetVelocity", X + 80, Y + 300, ret=("struct", "", VEC))
f_vsz = call(g, KML, "VSizeXY", X + 360, Y + 300, lib=KML_D, ret=D, inputs=[("A", "struct", "", VEC, "0, 0, 0", False, False)])
s_speed = var_set(g, "Speed", "real", "double", "None", X + 300, Y)
link(g_pl["Player"], f_vel["self"]); link(f_vel["ReturnValue"], f_vsz["A"]); link(f_vsz["ReturnValue"], s_speed["Speed"])
link(m_valid["Is Valid"], s_speed["execute"])
f_rot = call(g, "/Script/Engine.Actor", "K2_GetActorRotation", X + 360, Y + 440, ret=("struct", "", ROT))
f_dir = call(g, KAL, "CalculateDirection", X + 640, Y + 320, lib=KAL_D, ret=("real", "float", "None"),
             inputs=[("Velocity", "struct", "", VEC, "0, 0, 0", True, True), ("BaseRotation", "struct", "", ROT, "0, 0, 0", True, True)])
s_dir = var_set(g, "Direction", "real", "double", "None", X + 620, Y)
link(g_pl["Player"], f_rot["self"]); link(f_vel["ReturnValue"], f_dir["Velocity"]); link(f_rot["ReturnValue"], f_dir["BaseRotation"])
link(f_dir["ReturnValue"], s_dir["Direction"]); link(s_speed["then"], s_dir["execute"])
# CrouchAlpha = clamp((Stand - Cur) / (Stand - Crouched), 0, 1)
g_cap2 = var_get(g, "CapsuleComponent", "object", "", CAPSULE, owner=cls_ref("/Script/Engine.Character"), x=X + 700, y=Y + 560)
f_hh2 = call(g, "/Script/Engine.CapsuleComponent", "GetScaledCapsuleHalfHeight", X + 960, Y + 560, ret=("real", "float", "None"))
g_st = var_get(g, "StandingHalfHeight", "real", "double", x=X + 960, y=Y + 440)
g_ch = var_get(g, "CrouchedHalfHeight", "real", "double", x=X + 960, y=Y + 680)
f_dz = math2(g, "Subtract_DoubleDouble", X + 1240, Y + 460)
f_depth = math2(g, "Subtract_DoubleDouble", X + 1240, Y + 640)
f_div = math2(g, "Divide_DoubleDouble", X + 1500, Y + 520, b="1.0")
f_clamp = call(g, KML, "FClamp", X + 1740, Y + 520, lib=KML_D, ret=D, inputs=[dbl("Value"), dbl("Min", "0.0"), dbl("Max", "1.0")])
s_ca = var_set(g, "CrouchAlpha", "real", "double", "None", X + 940, Y)
link(g_pl["Player"], g_cap2["self"]); link(g_cap2["CapsuleComponent"], f_hh2["self"])
link(g_st["StandingHalfHeight"], f_dz["A"]); link(f_hh2["ReturnValue"], f_dz["B"])
link(g_st["StandingHalfHeight"], f_depth["A"]); link(g_ch["CrouchedHalfHeight"], f_depth["B"])
link(f_dz["ReturnValue"], f_div["A"]); link(f_depth["ReturnValue"], f_div["B"])
link(f_div["ReturnValue"], f_clamp["Value"]); link(f_clamp["ReturnValue"], s_ca["CrouchAlpha"])
link(s_dir["then"], s_ca["execute"])
# InAirAlpha = FInterpTo(InAirAlpha, IsFalling ? 1 : 0, DeltaTime, 10)
f_move = call(g, "/Script/Engine.Pawn", "GetMovementComponent", X + 1260, Y + 820, ret=("object", "", cls_ref("/Script/Engine.PawnMovementComponent")))
f_fall = call(g, "/Script/Engine.NavMovementComponent", "IsFalling", X + 1540, Y + 820, ret=("bool", "", "None"))
f_sel = call(g, KML, "SelectFloat", X + 1780, Y + 780, lib=KML_D, ret=D, inputs=[dbl("A", "1.0"), dbl("B", "0.0"), ("bPickA", "bool", "", "None", "false", False, False)])
g_ia = var_get(g, "InAirAlpha", "real", "double", x=X + 1780, y=Y + 660)
f_interp = call(g, KML, "FInterpTo", X + 2040, Y + 700, lib=KML_D, ret=D,
                inputs=[dbl("Current"), dbl("Target"), dbl("DeltaTime", "0.016"), dbl("InterpSpeed", "10.0")])
s_ia = var_set(g, "InAirAlpha", "real", "double", "None", X + 1260, Y)
link(g_pl["Player"], f_move["self"]); link(f_move["ReturnValue"], f_fall["self"]); link(f_fall["ReturnValue"], f_sel["bPickA"])
link(g_ia["InAirAlpha"], f_interp["Current"]); link(f_sel["ReturnValue"], f_interp["Target"]); link(f_interp["ReturnValue"], s_ia["InAirAlpha"])
link(s_ca["then"], s_ia["execute"])
# RootOffset = (0, -Lerp(BackStand, BackCrouch, CrouchAlpha), Stand - Cur)   [component space do Cowboy: +Y = frente]
g_bs = var_get(g, "BackOffsetStand", "real", "double", x=X + 2040, y=Y + 300)
g_bc = var_get(g, "BackOffsetCrouch", "real", "double", x=X + 2040, y=Y + 380)
f_lerp = call(g, KML, "Lerp", X + 2300, Y + 320, lib=KML_D, ret=D, inputs=[dbl("A"), dbl("B"), dbl("Alpha")])
f_neg = math2(g, "Multiply_DoubleDouble", X + 2540, Y + 320, b="-1.0")
f_mk = call(g, KML, "MakeVector", X + 2780, Y + 360, lib=KML_D, ret=("struct", "", VEC), inputs=[dbl("X"), dbl("Y"), dbl("Z")])
s_root = var_set(g, "RootOffset", "struct", "", VEC, X + 1580, Y)
link(g_bs["BackOffsetStand"], f_lerp["A"]); link(g_bc["BackOffsetCrouch"], f_lerp["B"]); link(s_ca["Output_Get"], f_lerp["Alpha"])
link(f_lerp["ReturnValue"], f_neg["A"]); link(f_neg["ReturnValue"], f_mk["Y"]); link(f_dz["ReturnValue"], f_mk["Z"])
link(f_mk["ReturnValue"], s_root["RootOffset"]); link(s_ia["then"], s_root["execute"])
open("mx_abp_event.t3d", "w", newline="").write(g.text())
names = {"abp_event_entry": m_valid.name, "abp_finterp": f_interp.name}

# ====================================================================== ABP_CowboyFP / AnimGraph
a = Graph(ABP, "AnimGraph", abpc_ref(ABP_C))
BS1 = "/Game/Characters/MixamoFP/BlendSpaces/BS_CB_Stand.BS_CB_Stand"
BS2 = "/Game/Characters/MixamoFP/BlendSpaces/BS_CB_Crouch.BS_CB_Crouch"
FALL = "/Game/Characters/MixamoFP/Anims/A_CB_Fall.A_CB_Fall"


def pose_out(n, name="Pose", comp=False):
    return n.pin(name, "struct", "", CPOSE if comp else POSE, out=True)


def pose_in(n, name, comp=False):
    return n.pin(name, "struct", "", CPOSE if comp else POSE, default="(LinkID=-1,SourceLinkID=-1)")


def bs_player(path, x, y):
    n = AnimNode(a, "/Script/AnimGraph.AnimGraphNode_BlendSpacePlayer", a.uname("AnimGraphNode_BlendSpacePlayer"), x, y, [
        "Node=(BlendSpace=\"/Script/Engine.BlendSpace'%s'\")" % path,
        'ShowPinForProperties(0)=(PropertyName="X",PropertyFriendlyName="X",CategoryName="Coordinates",bShowPin=True,bCanToggleVisibility=True)',
        'ShowPinForProperties(1)=(PropertyName="Y",PropertyFriendlyName="Y",CategoryName="Coordinates",bShowPin=True,bCanToggleVisibility=True)'])
    n.pin("X", "real", "float", default="0.000000")
    n.pin("Y", "real", "float", default="0.000000")
    pose_out(n)
    return n


def two_way(x, y):
    n = AnimNode(a, "/Script/AnimGraph.AnimGraphNode_TwoWayBlend", a.uname("AnimGraphNode_TwoWayBlend"), x, y, [
        'ShowPinForProperties(0)=(PropertyName="A",PropertyFriendlyName="A",CategoryName="Links",bShowPin=True)',
        'ShowPinForProperties(1)=(PropertyName="B",PropertyFriendlyName="B",CategoryName="Links",bShowPin=True)',
        'ShowPinForProperties(2)=(PropertyName="Alpha",PropertyFriendlyName="Alpha",CategoryName="Settings",bShowPin=True,bCanToggleVisibility=True)'])
    pose_in(n, "A")
    pose_in(n, "B")
    n.pin("Alpha", "real", "float", default="0.000000")
    pose_out(n)
    return n


v_dir = var_get(a, "Direction", "real", "double", x=-1700, y=-40)
v_spd = var_get(a, "Speed", "real", "double", x=-1700, y=40)
n_st = bs_player(BS1, -1450, -220)
n_cr = bs_player(BS2, -1450, 140)
for n in (n_st, n_cr):
    link(v_dir["Direction"], n["X"]); link(v_spd["Speed"], n["Y"])
v_ca = var_get(a, "CrouchAlpha", "real", "double", x=-1200, y=300)
n_b1 = two_way(-1100, -40)
link(n_st["Pose"], n_b1["A"]); link(n_cr["Pose"], n_b1["B"]); link(v_ca["CrouchAlpha"], n_b1["Alpha"])
n_fall = AnimNode(a, "/Script/AnimGraph.AnimGraphNode_SequencePlayer", a.uname("AnimGraphNode_SequencePlayer"), -1100, 360, [
    "Node=(Sequence=\"/Script/Engine.AnimSequence'%s'\")" % FALL])
pose_out(n_fall)
v_ia = var_get(a, "InAirAlpha", "real", "double", x=-820, y=420)
n_b2 = two_way(-760, -20)
link(n_b1["Pose"], n_b2["A"]); link(n_fall["Pose"], n_b2["B"]); link(v_ia["InAirAlpha"], n_b2["Alpha"])
n_save = AnimNode(a, "/Script/AnimGraph.AnimGraphNode_SaveCachedPose", a.uname("AnimGraphNode_SaveCachedPose"), -440, -20, [
    'CacheName="CB_Locomotion"',
    'ShowPinForProperties(0)=(PropertyName="Pose",PropertyFriendlyName="Pose",CategoryName="Links",bShowPin=True)'])
pose_in(n_save, "Pose")
link(n_b2["Pose"], n_save["Pose"])


def use_cache(x, y):
    n = AnimNode(a, "/Script/AnimGraph.AnimGraphNode_UseCachedPose", a.uname("AnimGraphNode_UseCachedPose"), x, y, [
        "SaveCachedPoseNode=\"/Script/AnimGraph.AnimGraphNode_SaveCachedPose'%s'\"" % n_save.name, 'NameOfCache="CB_Locomotion"'])
    pose_out(n)
    return n


n_u1 = use_cache(-200, -200)
n_u2 = use_cache(-200, 80)
n_slot = AnimNode(a, "/Script/AnimGraph.AnimGraphNode_Slot", a.uname("AnimGraphNode_Slot"), 40, 80, [
    'Node=(SlotName="DefaultSlot")',
    'ShowPinForProperties(0)=(PropertyName="Source",PropertyFriendlyName="Source",CategoryName="Links",bShowPin=True)'])
pose_in(n_slot, "Source"); pose_out(n_slot)
link(n_u2["Pose"], n_slot["Source"])
n_layer = AnimNode(a, "/Script/AnimGraph.AnimGraphNode_LayeredBoneBlend", a.uname("AnimGraphNode_LayeredBoneBlend"), 300, -100, [
    'Node=(LayerSetup=((BranchFilters=((BoneName="spine_01")))),bMeshSpaceRotationBlend=True)'])
pose_in(n_layer, "BasePose"); pose_in(n_layer, "BlendPoses_0")
n_layer.pin("BlendWeights_0", "real", "float", default="1.000000")
pose_out(n_layer)
link(n_u1["Pose"], n_layer["BasePose"]); link(n_slot["Pose"], n_layer["BlendPoses_0"])
n_l2c = AnimNode(a, "/Script/AnimGraph.AnimGraphNode_LocalToComponentSpace", a.uname("AnimGraphNode_LocalToComponentSpace"), 580, -80, [
    'ShowPinForProperties(0)=(PropertyName="LocalPose",PropertyFriendlyName="Local Pose",CategoryName="Links",bShowPin=True)'])
pose_in(n_l2c, "LocalPose"); pose_out(n_l2c, "ComponentPose", comp=True)
link(n_layer["Pose"], n_l2c["LocalPose"])
v_root = var_get(a, "RootOffset", "struct", "", VEC, x=600, y=100)
n_mod = AnimNode(a, "/Script/AnimGraph.AnimGraphNode_ModifyBone", a.uname("AnimGraphNode_ModifyBone"), 840, -80, [
    'Node=(BoneToModify=(BoneName="root"),TranslationMode=BMM_Additive,TranslationSpace=BCS_ComponentSpace,AlphaBoolBlend=(BlendOption=Linear))',
    'ShowPinForProperties(0)=(PropertyName="ComponentPose",PropertyFriendlyName="Component Pose",CategoryName="Links",bShowPin=True)',
    'ShowPinForProperties(1)=(PropertyName="Alpha",PropertyFriendlyName="Alpha",CategoryName="Alpha",bShowPin=True,bCanToggleVisibility=True)',
    'ShowPinForProperties(2)=(PropertyName="Translation",PropertyFriendlyName="Translation",CategoryName="Translation",bShowPin=True,bCanToggleVisibility=True)',
    'ShowPinForProperties(3)=(PropertyName="Rotation",PropertyFriendlyName="Rotation",CategoryName="Rotation",bCanToggleVisibility=True)',
    'ShowPinForProperties(4)=(PropertyName="Scale",PropertyFriendlyName="Scale",CategoryName="Scale",bCanToggleVisibility=True)'])
pose_in(n_mod, "ComponentPose", comp=True)
n_mod.pin("Alpha", "real", "float", default="1.000000")
n_mod.pin("Translation", "struct", "", VEC, default="0.000000,0.000000,0.000000")
pose_out(n_mod, comp=True)
link(n_l2c["ComponentPose"], n_mod["ComponentPose"]); link(v_root["RootOffset"], n_mod["Translation"])
n_c2l = AnimNode(a, "/Script/AnimGraph.AnimGraphNode_ComponentToLocalSpace", a.uname("AnimGraphNode_ComponentToLocalSpace"), 1120, -80, [
    'ShowPinForProperties(0)=(PropertyName="ComponentPose",PropertyFriendlyName="Component Pose",CategoryName="Links",bShowPin=True)'])
pose_in(n_c2l, "ComponentPose", comp=True); pose_out(n_c2l)
link(n_mod["Pose"], n_c2l["ComponentPose"])
open("mx_abp_anim.t3d", "w", newline="").write(a.text())
names["abp_anim_exit"] = n_c2l.name

# ====================================================================== ABP_CowboyFP_Visible / EventGraph (esconde cabeca e bracos)
v = Graph(VIS, "EventGraph", abpc_ref(VIS_C))
ve = ev(v, "BlueprintInitializeAnimation", -600, -100)
vc = call(v, "/Script/Engine.AnimInstance", "GetOwningComponent", -580, 60, self_ctx=True,
          ret=("object", "", cls_ref("/Script/Engine.SkeletalMeshComponent")), self_ref=abpc_ref(VIS_C))
prev = ve["then"]
hides = []
for i, bone in enumerate(("neck_01", "upperarm_l", "upperarm_r")):
    h = call(v, "/Script/Engine.SkinnedMeshComponent", "HideBoneByName", -300 + 280 * i, -100, pure=False,
             inputs=[("BoneName", "name", "", "None", bone, False, False),
                     ("PhysBodyOption", "byte", "", "\"/Script/CoreUObject.Enum'/Script/Engine.EPhysBodyOp'\"", "PBO_None", False, False)])
    link(prev, h["execute"])
    link(vc["ReturnValue"], h["self"])
    prev = h["then"]
    hides.append(h.name)
open("mx_vis_event.t3d", "w", newline="").write(v.text())

# ====================================================================== ABP_CowboyFP_Visible / AnimGraph (copia a pose da malha pai)
va = Graph(VIS, "AnimGraph", abpc_ref(VIS_C))
n_copy = AnimNode(va, "/Script/AnimGraph.AnimGraphNode_CopyPoseFromMesh", va.uname("AnimGraphNode_CopyPoseFromMesh"), -300, 0, [
    "Node=(bUseAttachedParent=True,bCopyCurves=False)"])
n_copy.pin("Pose", "struct", "", POSE, out=True)
open("mx_vis_anim.t3d", "w", newline="").write(va.text())
names["vis_anim_exit"] = n_copy.name
json.dump(names, open("mx_names.json", "w"), indent=1)
print(names, len(g.nodes), len(a.nodes), len(v.nodes), len(va.nodes))
