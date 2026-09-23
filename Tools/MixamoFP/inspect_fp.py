# Somente leitura: crouch/camera do BP_Player, esqueleto do Cowboy, plugins e APIs disponiveis na 5.8.
import os, unreal
out = []


def w(x):
    out.append(str(x))


def g(o, n):
    try:
        return o.get_editor_property(n)
    except Exception as e:
        return "?(%s)" % str(e)[:50]


BP = "/Game/FPMovement/Player/Blueprints/BP_Player"
bp = unreal.load_asset(BP)
cdo = unreal.get_default_object(bp.generated_class())
w("== variaveis do BP_Player (CDO)")
for v in ("CameraOffset", "CrouchedHalfHeight", "MaxCrouchSpeed", "MaxWalkSpeed", "MaxSprintSpeed", "WalkSpeed", "SprintSpeed",
          "ToggleCrouching?", "CanCrouch?", "IsCrouching?", "IsSprinting?", "StandingHalfHeight", "CrouchSpeed", "HeadbobEnabled?"):
    r = g(cdo, v)
    if not str(r).startswith("?("):
        w("  %s = %s" % (v, r))
w("  todas as variaveis: %s" % [str(x.get_editor_property("var_name")) for x in bp.get_editor_property("new_variables")])

w("== componentes (SCS)")
try:
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    for h in sds.k2_gather_subobject_data_for_blueprint(bp):
        d = unreal.SubobjectDataBlueprintFunctionLibrary.get_data(h)
        o = unreal.SubobjectDataBlueprintFunctionLibrary.get_object(d)
        if isinstance(o, unreal.SceneComponent):
            w("  %-28s %-28s loc=%s rot=%s parent_socket=%s" % (o.get_name(), o.get_class().get_name(), g(o, "relative_location"), g(o, "relative_rotation"), g(o, "attach_socket_name") if False else ""))
        if isinstance(o, unreal.SpringArmComponent):
            w("     springarm len=%s use_pawn_rot=%s collision=%s" % (g(o, "target_arm_length"), g(o, "use_pawn_control_rotation"), g(o, "do_collision_test")))
        if isinstance(o, unreal.CameraComponent):
            w("     camera fov=%s use_pawn_rot=%s" % (g(o, "field_of_view"), g(o, "use_pawn_control_rotation")))
except Exception as e:
    w("  erro SCS: %s" % e)

w("== timelines")
try:
    for tl in bp.get_editor_property("timelines"):
        w("  %s len=%s" % (tl.get_name(), g(tl, "timeline_length")))
        for tr in g(tl, "float_tracks"):
            c = g(tr, "curve_float")
            keys = []
            try:
                rc = c.get_editor_property("float_curve")
                keys = [(round(k.get_editor_property("time"), 3), round(k.get_editor_property("value"), 3)) for k in rc.get_editor_property("keys")]
            except Exception as e:
                keys = "?(%s)" % str(e)[:40]
            w("     float track %s keys=%s" % (g(tr, "track_name"), keys))
except Exception as e:
    w("  erro timelines: %s" % e)

w("== nos ligados ao Crouch_TL (BFS, profundidade 4)")
prefix = BP + ".BP_Player:EventGraph."
nodes = {}
for n in unreal.ObjectIterator(unreal.K2Node):
    p = n.get_path_name()
    if p.startswith(prefix) and "." not in p[len(prefix):]:
        nodes[p[len(prefix):]] = n
start = [n for k, n in nodes.items() if "Crouch_TL" in str(n.get_node_title())]
seen, frontier = set(), [(s, 0) for s in start]
while frontier:
    n, d = frontier.pop(0)
    if n.get_name() in seen or d > 4:
        continue
    seen.add(n.get_name())
    pins = []
    for p in n.list_all_pins():
        links = p.list_connected_pins()
        dv = ""
        try:
            dv = p.get_default_value()
        except Exception:
            dv = ""
        if links or dv not in ("", None, "0", "0.0", "False"):
            pins.append("%s%s%s" % (p.get_pin_name(), ("=" + str(dv)) if dv not in ("", None) else "", ("->[" + ",".join("%s.%s" % (str(l.get_owning_node().get_node_title()).replace("\n", " ")[:28], l.get_pin_name()) for l in links) + "]") if links else ""))
        for l in links:
            frontier.append((l.get_owning_node(), d + 1))
    w("  [%d] %-40s %s" % (d, str(n.get_node_title()).replace("\n", " ")[:40], " | ".join(pins)))

w("== Cowboy")
sk = unreal.load_asset("/Game/Cowboy_character/Mesh/SM_SkeletalMesh_cowboy_character")
skel = sk.get_editor_property("skeleton")
try:
    names = [str(n) for n in unreal.SkeletalMeshEditorSubsystem.get_bone_names(sk)] if hasattr(unreal.SkeletalMeshEditorSubsystem, "get_bone_names") else []
except Exception:
    names = []
if not names:
    try:
        names = [str(skel.get_bone_name(i)) for i in range(skel.get_editor_property("bone_tree").__len__())]
    except Exception as e:
        names = ["?(%s)" % e]
w("  bones (%d): %s" % (len(names), names))
w("  materials: %s" % [str(m.get_editor_property("material_slot_name")) for m in sk.get_editor_property("materials")])
w("  lods: %s" % len(g(sk, "lod_info")))
w("  bounds: %s" % sk.get_bounds())

w("== plugins / classes")
for c in ("AnimGraphNode_OrientationWarping", "AnimGraphNode_StrideWarping", "AnimGraphNode_FootPlacement", "AnimGraphNode_Inertialization",
          "AnimGraphNode_CopyPoseFromMesh", "AnimGraphNode_BlendSpaceGraph", "AnimationWarpingLibrary", "AnimDistanceMatchingLibrary",
          "AnimCharacterMovementLibrary", "InterchangeGenericAssetsPipeline", "FbxImportUI", "IKRetargetBatchOperation"):
    w("  %-36s %s" % (c, hasattr(unreal, c)))
w("  IKRetarget* classes: %s" % sorted(x for x in dir(unreal) if x.startswith("IKRetarget")))
try:
    w("  IKRetargeterController metodos: %s" % sorted(x for x in dir(unreal.IKRetargeterController) if not x.startswith("_")))
except Exception as e:
    w("  ctrl erro %s" % e)
try:
    w("  IKRigController metodos: %s" % sorted(x for x in dir(unreal.IKRigController) if not x.startswith("_")))
except Exception as e:
    w("  rigctrl erro %s" % e)
for cv in ("Interchange.FeatureFlags.Import.FBX", "Interchange.FeatureFlags.Import.FBX.ToLevel"):
    try:
        w("  cvar %s = %s" % (cv, unreal.SystemLibrary.get_console_variable_int_value(cv)))
    except Exception as e:
        w("  cvar %s erro %s" % (cv, e))
w("  dirty: %s" % [p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()])
w("  mapa: %s" % unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_path_name())
saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
open(os.path.join(saved, "MixamoFP_inspect.txt"), "w", encoding="utf-8").write("\n".join(out))
