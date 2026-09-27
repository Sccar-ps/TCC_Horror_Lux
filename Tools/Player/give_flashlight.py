# LUX: o jogador ja comeca com a lanterna (a tecla F funciona desde o inicio). So mexe no BP_Player_Cowboy.
# O pickup BP_Flashlight, ao ser pego, so faz HasFlashlight? = true no jogador (mais aviso no HUD, som e sumir a malha
# dele). O Mapa_B nao tem pickup, entao a flag fica ligada direto nos Class Defaults.
# Idempotente. Compila e salva so o BP_Player_Cowboy.
#   py "<projeto>/Tools/Player/give_flashlight.py"          -> HasFlashlight? = true
#   py "<projeto>/Tools/Player/give_flashlight.py" desfazer -> HasFlashlight? = false (volta a precisar do pickup)
import sys
import unreal

BP = "/Game/Characters/MixamoFP/Blueprints/BP_Player_Cowboy"
DESFAZER = "desfazer" in [str(a).lower() for a in sys.argv[1:]]

bp = unreal.EditorAssetLibrary.load_asset(BP)


def estado():
    cdo = unreal.get_default_object(bp.generated_class())
    return "HasFlashlight?=%s FlashlightOn?=%s" % (cdo.get_editor_property("HasFlashlight?"), cdo.get_editor_property("FlashlightOn?"))


print("antes:  " + estado())
with unreal.ScopedEditorTransaction("LUX: lanterna"):
    cdo = unreal.get_default_object(bp.generated_class())
    cdo.modify()
    cdo.set_editor_property("HasFlashlight?", not DESFAZER)
unreal.BlueprintEditorLibrary.compile_blueprint(bp)
print("depois: " + estado())
print("salvo:", unreal.EditorAssetLibrary.save_loaded_asset(bp, False))
