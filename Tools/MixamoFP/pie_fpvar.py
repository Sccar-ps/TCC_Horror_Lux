# PIE apenas: compara variantes da visao em 1a pessoa olhando para baixo (em pe e agachado).
import os, unreal
saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
LOG = os.path.join(saved, "MixamoFP_fpvar.txt")
open(LOG, "w", encoding="utf-8").write("inicio\n")
IA = "/Game/FPMovement/Player/Input/Actions/"
NEVER = unreal.PropertyAccessChangeNotifyMode.NEVER
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
pc = unreal.GameplayStatics.get_player_controller(w, 0)
pawn = pc.get_controlled_pawn()
mesh = pawn.get_editor_property("mesh")
vis = next(c for c in pawn.get_components_by_class(unreal.SkeletalMeshComponent) if c.get_name().startswith("BodyVisible"))
arms = next(c for c in pawn.get_components_by_class(unreal.SkeletalMeshComponent) if c.get_name().startswith("FirstPersonMesh"))
ai = mesh.get_anim_instance()
S = {"i": 0, "t": 0.0, "shot": False, "h": None}


def log(m):
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(m + "\n")


log("arms visible=%s hidden_in_game=%s only_owner=%s" % (arms.is_visible(), arms.get_editor_property("hidden_in_game"), arms.get_editor_property("only_owner_see")))


def back(v_stand=None, v_crouch=None):
    if v_stand is not None:
        ai.set_editor_property("BackOffsetStand", v_stand, NEVER)
    if v_crouch is not None:
        ai.set_editor_property("BackOffsetCrouch", v_crouch, NEVER)


def pitch(p):
    r = pc.get_control_rotation()
    pc.set_control_rotation(unreal.Rotator(roll=0.0, pitch=p, yaw=r.yaw))


# (nome, dur, acao)
PH = [("A_atual_-75", 1.0, lambda: (pitch(-75.0), back(4.0, 30.0))),
      ("B_atual_-55", 0.8, lambda: pitch(-55.0)),
      ("C_back12_-75", 0.8, lambda: (pitch(-75.0), back(12.0, None))),
      ("D_back12_spine03_-75", 0.8, lambda: vis.hide_bone_by_name("spine_03", unreal.PhysBodyOp.PBO_NONE)),
      ("E_back12_spine03_-55", 0.8, lambda: pitch(-55.0)),
      ("F_crouch_-65", 1.4, lambda: (vis.un_hide_bone_by_name("spine_03"), back(4.0, 30.0), pitch(-65.0),
                                      pawn.call_method("InpActEvt_IA_Crouch_K2Node_EnhancedInputActionEvent_4", (unreal.InputActionValue(), 0.0, 0.0, unreal.load_asset(IA + "IA_Crouch"))))),
      ("G_crouch_back40_-65", 0.8, lambda: back(None, 40.0)),
      ("H_crouch_back40_-40", 0.8, lambda: pitch(-40.0)),
      ("fim", 0.3, lambda: (back(4.0, 30.0), pitch(0.0)))]


def tick(dt):
    try:
        if S["i"] >= len(PH):
            unreal.unregister_slate_post_tick_callback(S["h"])
            log("fim")
            return
        name, dur, act = PH[S["i"]]
        if S["t"] == 0.0:
            act()
            log("fase %s" % name)
        S["t"] += dt
        if name != "fim" and not S["shot"] and S["t"] >= dur * 0.8:
            unreal.SystemLibrary.execute_console_command(w, "HighResShot 1")
            S["shot"] = True
            log("  shot %s crouchA=%.2f root=%s" % (name, ai.get_editor_property("CrouchAlpha"), ai.get_editor_property("RootOffset")))
        if S["t"] >= dur:
            S["i"] += 1
            S["t"] = 0.0
            S["shot"] = False
    except Exception:
        import traceback
        log("ERRO " + traceback.format_exc())
        unreal.unregister_slate_post_tick_callback(S["h"])


S["h"] = unreal.register_slate_post_tick_callback(tick)
