"""Gera os nos novos do ABP_CowboyFP_Visible (camada de apresentacao 1P):
   - EventGraph: cache do Player no Initialize + Update com alinhamento pescoco/camera e inclinacao ao olhar para baixo
   - AnimGraph: CopyPose -> LocalToComponent -> ModifyBone(root, translacao) -> ModifyBone(spine_01, rotacao) -> ComponentToLocal
"""
from t3d import *
import json

VIS = "/Game/Characters/MixamoFP/Blueprints/ABP_CowboyFP_Visible.ABP_CowboyFP_Visible"
VIS_C = "/Game/Characters/MixamoFP/Blueprints/ABP_CowboyFP_Visible.ABP_CowboyFP_Visible_C"
BPP_C = "/Game/FPMovement/Player/Blueprints/BP_Player.BP_Player_C"
KML = "/Script/Engine.KismetMathLibrary"
KML_D = "/Script/Engine.Default__KismetMathLibrary"
PLAYER = bpc_ref(BPP_C)
D = ("real", "double", "None")
F = False


class G(Graph):
    def __init__(self, *a, tag="FV"):
        super().__init__(*a)
        self.tag = tag

    def uname(self, base):
        self._n += 1
        return "%s_%s%02d" % (base, self.tag, self._n)


def dbl(name, default="0.0"):
    return (name, "real", "double", "None", default, F, F)


def vec(name, default="0.000000,0.000000,0.000000"):
    return (name, "struct", "", VEC, default, F, F)


def kml(g, func, x, y, ret=D, inputs=()):
    return call(g, KML, func, x, y, lib=KML_D, ret=ret, inputs=inputs)


def math2(g, func, x, y, a="0.0", b="0.0"):
    return kml(g, func, x, y, inputs=[dbl("A", a), dbl("B", b)])


# ====================================================================== EventGraph
v = G(VIS, "EventGraph", abpc_ref(VIS_C), tag="FV")
# --- Initialize (continua a cadeia dos HideBoneByName): Player = Cast<BP_Player>(TryGetPawnOwner())
f_pawn = call(v, "/Script/Engine.AnimInstance", "TryGetPawnOwner", 560, 60, self_ctx=True,
              ret=("object", "", cls_ref("/Script/Engine.Pawn")), self_ref=abpc_ref(VIS_C))
c_cast = cast(v, BPP_C, "AsBP Player", 820, -100)
s_player = var_set(v, "Player", "object", "", PLAYER, 1120, -100)
link(f_pawn["ReturnValue"], c_cast["Object"])
link(c_cast["then"], s_player["execute"])
link(c_cast["AsBP Player"], s_player["Player"])

# --- Update
X, Y = -600, 500
g_pl = var_get(v, "Player", "object", "", PLAYER, x=X - 260, y=Y + 260)
m_valid = is_valid(v, X, Y)
link(g_pl["Player"], m_valid["InputObject"])
g_cam = var_get(v, "FirstPersonCamera", "object", "", cls_ref("/Script/Engine.CameraComponent"), owner=PLAYER, x=X, y=Y + 420)
link(g_pl["Player"], g_cam["self"])
f_camloc = call(v, "/Script/Engine.SceneComponent", "K2_GetComponentLocation", X + 300, Y + 420, ret=("struct", "", VEC))
link(g_cam["FirstPersonCamera"], f_camloc["self"])
g_mesh = var_get(v, "Mesh", "object", "", cls_ref("/Script/Engine.SkeletalMeshComponent"), owner=cls_ref("/Script/Engine.Character"),
                 x=X, y=Y + 300)
link(g_pl["Player"], g_mesh["self"])
f_neck = call(v, "/Script/Engine.SceneComponent", "GetSocketLocation", X + 300, Y + 280, ret=("struct", "", VEC),
              inputs=[("InSocketName", "name", "", "None", "neck_01", F, F)])
link(g_mesh["Mesh"], f_neck["self"])
f_sub = kml(v, "Subtract_VectorVector", X + 600, Y + 320, ret=("struct", "", VEC), inputs=[vec("A"), vec("B")])
link(f_neck["ReturnValue"], f_sub["A"]); link(f_camloc["ReturnValue"], f_sub["B"])
s_rel = var_set(v, "NeckRel", "struct", "", VEC, X + 300, Y)                      # NeckRel = pescoco - camera (mundo)
link(m_valid["Is Valid"], s_rel["execute"]); link(f_sub["ReturnValue"], s_rel["NeckRel"])

# StandW = MapRangeClamped(NeckRel.Z, 0, -10, 0, 1): 1 com a camera >=10 cm acima do pescoco (em pe), 0 agachado
f_dotup = kml(v, "Dot_VectorVector", X + 640, Y + 180, inputs=[vec("A"), vec("B", "0.000000,0.000000,1.000000")])
link(s_rel["Output_Get"], f_dotup["A"])
f_stw = kml(v, "MapRangeClamped", X + 900, Y + 180,
            inputs=[dbl("Value"), dbl("InRangeA", "0.0"), dbl("InRangeB", "-10.0"), dbl("OutRangeA", "0.0"), dbl("OutRangeB", "1.0")])
link(f_dotup["ReturnValue"], f_stw["Value"])
s_stw = var_set(v, "StandW", "real", "double", "None", X + 640, Y)
link(s_rel["then"], s_stw["execute"]); link(f_stw["ReturnValue"], s_stw["StandW"])

# BodyShift = FInterpTo(BodyShift, Clamp(NeckFwd + NeckMinBehind, 0, MaxBodyShift) * StandW, dt, 8)
f_fwd = call(v, "/Script/Engine.Actor", "GetActorForwardVector", X + 1000, Y + 440, ret=("struct", "", VEC))
link(g_pl["Player"], f_fwd["self"])
f_dotf = kml(v, "Dot_VectorVector", X + 1260, Y + 360, inputs=[vec("A"), vec("B")])
link(s_rel["Output_Get"], f_dotf["A"]); link(f_fwd["ReturnValue"], f_dotf["B"])
g_nmb = var_get(v, "NeckMinBehind", "real", "double", x=X + 1260, y=Y + 500)
f_add = math2(v, "Add_DoubleDouble", X + 1500, Y + 380)
link(f_dotf["ReturnValue"], f_add["A"]); link(g_nmb["NeckMinBehind"], f_add["B"])
g_mbs = var_get(v, "MaxBodyShift", "real", "double", x=X + 1500, y=Y + 540)
f_cl = kml(v, "FClamp", X + 1740, Y + 400, inputs=[dbl("Value"), dbl("Min", "0.0"), dbl("Max", "25.0")])
link(f_add["ReturnValue"], f_cl["Value"]); link(g_mbs["MaxBodyShift"], f_cl["Max"])
f_mulw = math2(v, "Multiply_DoubleDouble", X + 1980, Y + 400)
link(f_cl["ReturnValue"], f_mulw["A"]); link(s_stw["Output_Get"], f_mulw["B"])
g_bsh = var_get(v, "BodyShift", "real", "double", x=X + 1980, y=Y + 260)
f_interp = kml(v, "FInterpTo", X + 2220, Y + 300,
               inputs=[dbl("Current"), dbl("Target"), dbl("DeltaTime", "0.016"), dbl("InterpSpeed", "8.0")])
link(g_bsh["BodyShift"], f_interp["Current"]); link(f_mulw["ReturnValue"], f_interp["Target"])
s_bsh = var_set(v, "BodyShift", "real", "double", "None", X + 1000, Y)
link(s_stw["then"], s_bsh["execute"]); link(f_interp["ReturnValue"], s_bsh["BodyShift"])

# RootShift = (0, -BodyShift, 0)   [espaco do componente do Cowboy: +Y = frente]
f_neg = math2(v, "Multiply_DoubleDouble", X + 1400, Y + 160, b="-1.0")
link(s_bsh["Output_Get"], f_neg["A"])
f_mk = kml(v, "MakeVector", X + 1640, Y + 160, ret=("struct", "", VEC), inputs=[dbl("X"), dbl("Y"), dbl("Z")])
link(f_neg["ReturnValue"], f_mk["Y"])
s_rs = var_set(v, "RootShift", "struct", "", VEC, X + 1400, Y)
link(s_bsh["then"], s_rs["execute"]); link(f_mk["ReturnValue"], s_rs["RootShift"])

# LeanRot.Roll = -MapRangeClamped(CameraPitch, LeanStartPitch, LeanFullPitch, 0, LeanMax) * StandW   (roll negativo = tronco para tras)
f_camrot = call(v, "/Script/Engine.SceneComponent", "K2_GetComponentRotation", X + 300, Y + 620, ret=("struct", "", ROT))
link(g_cam["FirstPersonCamera"], f_camrot["self"])
f_brk = kml(v, "BreakRotator", X + 600, Y + 640, ret=None, inputs=[("InRot", "struct", "", ROT, "0.000000,0.000000,0.000000", F, F)])
f_brk.pin("Pitch", "real", "float", out=True)
link(f_camrot["ReturnValue"], f_brk["InRot"])
g_ls = var_get(v, "LeanStartPitch", "real", "double", x=X + 860, y=Y + 700)
g_lf = var_get(v, "LeanFullPitch", "real", "double", x=X + 860, y=Y + 780)
g_lm = var_get(v, "LeanMax", "real", "double", x=X + 860, y=Y + 860)
f_map = kml(v, "MapRangeClamped", X + 1120, Y + 660,
            inputs=[dbl("Value"), dbl("InRangeA", "-20.0"), dbl("InRangeB", "-75.0"), dbl("OutRangeA", "0.0"), dbl("OutRangeB", "16.0")])
link(f_brk["Pitch"], f_map["Value"]); link(g_ls["LeanStartPitch"], f_map["InRangeA"])
link(g_lf["LeanFullPitch"], f_map["InRangeB"]); link(g_lm["LeanMax"], f_map["OutRangeB"])
f_mw2 = math2(v, "Multiply_DoubleDouble", X + 1380, Y + 660)
link(f_map["ReturnValue"], f_mw2["A"]); link(s_stw["Output_Get"], f_mw2["B"])
f_neg2 = math2(v, "Multiply_DoubleDouble", X + 1620, Y + 660, b="-1.0")
link(f_mw2["ReturnValue"], f_neg2["A"])
f_mr = kml(v, "MakeRotator", X + 1860, Y + 640, ret=("struct", "", ROT),
           inputs=[("Roll", "real", "float", "None", "0.0", F, F), ("Pitch", "real", "float", "None", "0.0", F, F),
                   ("Yaw", "real", "float", "None", "0.0", F, F)])
link(f_neg2["ReturnValue"], f_mr["Roll"])
s_lr = var_set(v, "LeanRot", "struct", "", ROT, X + 1800, Y)
link(s_rs["then"], s_lr["execute"]); link(f_mr["ReturnValue"], s_lr["LeanRot"])
open("mx_vis2_event.t3d", "w", newline="").write(v.text())
names = {"vis_cast": c_cast.name, "vis_valid": m_valid.name, "vis_interp": f_interp.name}

# ====================================================================== AnimGraph
a = G(VIS, "AnimGraph", abpc_ref(VIS_C), tag="FA")


def pose_out(n, name="Pose", comp=False):
    return n.pin(name, "struct", "", CPOSE if comp else POSE, out=True)


def pose_in(n, name, comp=False):
    return n.pin(name, "struct", "", CPOSE if comp else POSE, default="(LinkID=-1,SourceLinkID=-1)")


def modify(x, y, bone, what):
    if what == "t":
        node = 'Node=(BoneToModify=(BoneName="%s"),TranslationMode=BMM_Additive,TranslationSpace=BCS_ComponentSpace,AlphaBoolBlend=(BlendOption=Linear))' % bone
    else:
        node = 'Node=(BoneToModify=(BoneName="%s"),RotationMode=BMM_Additive,RotationSpace=BCS_ComponentSpace,AlphaBoolBlend=(BlendOption=Linear))' % bone
    n = AnimNode(a, "/Script/AnimGraph.AnimGraphNode_ModifyBone", a.uname("AnimGraphNode_ModifyBone"), x, y, [
        node,
        'ShowPinForProperties(0)=(PropertyName="ComponentPose",PropertyFriendlyName="Component Pose",CategoryName="Links",bShowPin=True)',
        'ShowPinForProperties(1)=(PropertyName="Alpha",PropertyFriendlyName="Alpha",CategoryName="Alpha",bShowPin=True,bCanToggleVisibility=True)',
        'ShowPinForProperties(2)=(PropertyName="Translation",PropertyFriendlyName="Translation",CategoryName="Translation",bShowPin=%s,bCanToggleVisibility=True)' % ("True" if what == "t" else "False"),
        'ShowPinForProperties(3)=(PropertyName="Rotation",PropertyFriendlyName="Rotation",CategoryName="Rotation",bShowPin=%s,bCanToggleVisibility=True)' % ("True" if what == "r" else "False"),
        'ShowPinForProperties(4)=(PropertyName="Scale",PropertyFriendlyName="Scale",CategoryName="Scale",bCanToggleVisibility=True)'])
    pose_in(n, "ComponentPose", comp=True)
    n.pin("Alpha", "real", "float", default="1.000000")
    if what == "t":
        n.pin("Translation", "struct", "", VEC, default="0.000000,0.000000,0.000000")
    else:
        n.pin("Rotation", "struct", "", ROT, default="0.000000,0.000000,0.000000")
    pose_out(n, comp=True)
    return n


n_l2c = AnimNode(a, "/Script/AnimGraph.AnimGraphNode_LocalToComponentSpace", a.uname("AnimGraphNode_LocalToComponentSpace"), 0, 0, [
    'ShowPinForProperties(0)=(PropertyName="LocalPose",PropertyFriendlyName="Local Pose",CategoryName="Links",bShowPin=True)'])
pose_in(n_l2c, "LocalPose"); pose_out(n_l2c, "ComponentPose", comp=True)
v_rs = var_get(a, "RootShift", "struct", "", VEC, x=20, y=180)
n_m1 = modify(260, 0, "root", "t")
link(n_l2c["ComponentPose"], n_m1["ComponentPose"]); link(v_rs["RootShift"], n_m1["Translation"])
v_lr = var_get(a, "LeanRot", "struct", "", ROT, x=300, y=200)
n_m2 = modify(540, 0, "spine_01", "r")
link(n_m1["Pose"], n_m2["ComponentPose"]); link(v_lr["LeanRot"], n_m2["Rotation"])
n_c2l = AnimNode(a, "/Script/AnimGraph.AnimGraphNode_ComponentToLocalSpace", a.uname("AnimGraphNode_ComponentToLocalSpace"), 820, 0, [
    'ShowPinForProperties(0)=(PropertyName="ComponentPose",PropertyFriendlyName="Component Pose",CategoryName="Links",bShowPin=True)'])
pose_in(n_c2l, "ComponentPose", comp=True); pose_out(n_c2l)
link(n_m2["Pose"], n_c2l["ComponentPose"])
open("mx_vis2_anim.t3d", "w", newline="").write(a.text())
names.update({"vis_l2c": n_l2c.name, "vis_c2l": n_c2l.name})
json.dump(names, open("mx_vis2_names.json", "w"), indent=1)
print(names, len(v.nodes), len(a.nodes))
