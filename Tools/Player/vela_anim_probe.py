# LUX: levantamento SO LEITURA da vela/lanterna: grafos do BP_Player, BP_Player_Cowboy e ABP_Arms_Cowboy,
# montagens e notifies da lanterna, sockets e ossos dos bracos. Saida: Saved/LuxSnapshots/vela_anim_probe.txt
#   py "<projeto>/Tools/Player/vela_anim_probe.py"
import os, traceback, unreal

EAL, BEL, BGE = unreal.EditorAssetLibrary, unreal.BlueprintEditorLibrary, unreal.BlueprintGraphEditor
OUT = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), "LuxSnapshots")
os.makedirs(OUT, exist_ok=True)
L = []


def p(*a):
    L.append(" ".join(str(x) for x in a))


def t(n):
    return str(n.get_node_title()).replace("\n", " | ")


def dump_bp(path):
    bp = EAL.load_asset(path)
    p("=" * 20, path)
    try:
        p("vars:", [str(v) for v in BEL.list_member_variable_names(bp)])
    except Exception as e:
        p("vars: ?", e)
    for g in [str(x) for x in BEL.list_graph_names(bp)]:
        try:
            ge = BGE.get_graph_editor_by_name(bp, g)
            nos = list(ge.list_all_nodes())
        except Exception as e:
            p("-- grafo", g, "inacessivel:", e)
            continue
        p("-- grafo", g, "(%d nos)" % len(nos))
        for n in nos:
            pins = []
            for pin in n.list_all_pins():
                try:
                    lig = ["%s.%s" % (t(q.get_owning_node())[:50], q.get_pin_name()) for q in pin.list_connected_pins()]
                except Exception:
                    lig = []
                try:
                    dv = str(pin.get_default_value())
                except Exception:
                    dv = ""
                if lig or (dv and dv not in ("None", "0", "0.0", "false", "")):
                    pins.append("%s=%s%s" % (pin.get_pin_name(), dv[:40], (" ->" + str(lig)) if lig else ""))
            p("  [%s] %s :: %s" % (n.get_name(), t(n)[:90], "; ".join(pins)))


def dump_anim(path):
    a = EAL.load_asset(path)
    if not a:
        p("anim nao achada", path)
        return
    try:
        comp = unreal.AnimationLibrary.get_sequence_length(a)
    except Exception:
        comp = "?"
    p("ANIM", path, "dur", comp, "rate", a.get_editor_property("rate_scale") if hasattr(a, "rate_scale") else "")
    try:
        for e in unreal.AnimationLibrary.get_animation_notify_events(a):
            info = [str(e.get_editor_property("notify_name"))]
            for k in ("notify", "notify_state_class", "link_value", "trigger_time_offset", "duration"):
                try:
                    info.append("%s=%s" % (k, e.get_editor_property(k)))
                except Exception:
                    pass
            p("   notify", info)
    except Exception as ex:
        p("   notifies ?", ex)
    if isinstance(a, unreal.AnimMontage):
        for k in ("blend_in", "blend_out", "blend_out_trigger_time", "enable_auto_blend_out"):
            try:
                v = a.get_editor_property(k)
                p("   ", k, v.get_editor_property("blend_time") if hasattr(v, "get_editor_property") and k.startswith("blend_") and k != "blend_out_trigger_time" else v)
            except Exception:
                pass
        try:
            for st in a.get_editor_property("slot_anim_tracks"):
                p("   slot", st.get_editor_property("slot_name"))
        except Exception:
            pass


try:
    dump_bp("/Game/FPMovement/Player/Blueprints/BP_Player")
    dump_bp("/Game/Characters/MixamoFP/Blueprints/BP_Player_Cowboy")
    dump_bp("/Game/Characters/MixamoFP/Arms/ABP_Arms_Cowboy")
    base = "/Game/FPMovement/Demo/Character/Animations/Flashlight/"
    for n in ("AS_Flashlight_Eqiup", "AS_Flashlight_Unequip", "AS_Flashlight_Idle", "AS_Flashlight_Walk", "AS_Flashlight_Inspection",
              "AS_Flashlight_FlickerReaction", "AS_Flashlight_NearToWall_V2", "Montages/AS_Flashlight_Eqiup_Montage",
              "Montages/AS_Flashlight_Unequip_Montage", "Montages/AS_Flashlight_Inspection_Montage", "Blendspaces/BS_FlashlightMovement"):
        dump_anim(base + n)
    for m in ("/Game/Characters/MixamoFP/Arms/BS_Arms_Flashlight", "/Game/Characters/MixamoFP/Arms/BS_Arms_Unarmed"):
        dump_anim(m)
    sk = EAL.load_asset("/Game/FPMovement/Demo/Character/Arms/MetaHuman/SKM_Metahuman_Arms")
    p("SKM", sk.get_path_name(), "skeleton", sk.skeleton.get_path_name())
    for i in range(sk.num_sockets()):
        s = sk.get_socket_by_index(i)
        p("  socket", s.socket_name, "bone", s.bone_name, "loc", s.relative_location, "rot", s.relative_rotation)
    try:
        pose = unreal.AnimPoseExtensions.get_reference_pose(sk.skeleton)
        nomes = [str(b) for b in unreal.AnimPoseExtensions.get_bone_names(pose)]
        p("  ossos (%d):" % len(nomes), [b for b in nomes if any(k in b.lower() for k in ("hand", "lowerarm", "upperarm", "clavicle", "index", "middle", "thumb", "weapon", "ik_"))])
        for b in ("hand_r", "lowerarm_r", "hand_l"):
            if b in nomes:
                p("  ref", b, unreal.AnimPoseExtensions.get_bone_pose(pose, b, unreal.AnimPoseSpaces.WORLD))
    except Exception as ex:
        p("  ossos ?", ex)
except Exception:
    p(traceback.format_exc())
open(os.path.join(OUT, "vela_anim_probe.txt"), "w", encoding="utf-8").write("\n".join(L))
unreal.log("[LUX vela] anim probe ok: %d linhas" % len(L))
