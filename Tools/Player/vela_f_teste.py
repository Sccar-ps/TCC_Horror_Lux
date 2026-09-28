# LUX: COM O PIE ABERTO - estado do F da vela (so le). Acrescenta uma linha em Saved/LuxSnapshots/vela_f_teste.txt
#   py "<projeto>/Tools/Player/vela_f_teste.py"
import os, traceback
import unreal

OUT = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), "LuxSnapshots", "vela_f_teste.txt")
try:
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
    mesh = [c for c in pawn.get_components_by_class(unreal.SkeletalMeshComponent) if c.get_name() == "FirstPersonMesh"][0]
    ai = mesh.get_anim_instance()
    vis = {c.get_name(): c.is_visible() for c in pawn.get_components_by_class(unreal.SceneComponent)
           if c.get_name() in ("Vela", "ChamaA", "ChamaB", "Lampiao")}
    linha = "t=%.2f FlashlightOn?=%s CanDoFlashlight=%s montagem=%s visiveis=%s" % (
        unreal.GameplayStatics.get_time_seconds(world), pawn.get_editor_property("FlashlightOn?"),
        pawn.get_editor_property("CanDoFlashlight"), ai.is_any_montage_playing() if ai else "?", vis)
except Exception:
    linha = "ERRO " + traceback.format_exc()
with open(OUT, "a", encoding="utf-8") as fh:
    fh.write(linha + "\n")
unreal.log("[LUX F] " + linha)
