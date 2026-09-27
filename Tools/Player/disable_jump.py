# LUX: o jogador nao pula. O BP_Player (compartilhado) nao e editado.
# Como o pulo funcionava: IMC_Default liga Espaco/A do gamepad ao IA_Jump; no BP_Player o IA_Jump chama Jump() e
# logo depois toca o camera shake BP_Jump (head bob) sem conferir se o pulo aconteceu. Por isso, so travar o pulo
# no Character (passo 1) ainda deixava a visao subir.
# 1) BP_Player_Cowboy, Class Defaults: JumpMaxCount = 0 e CharacterMovement > Can Jump = false.
# 2) IMC_Default (usado so pelo BP_PlayerController): tira as teclas do IA_Jump. O evento do BP_Player nunca dispara.
#    (No Enhanced Input o evento do pai continua ligado mesmo se o filho tiver o seu; nao ha "Override Parent Binding".)
# Idempotente. Salva so o BP_Player_Cowboy e o IMC_Default.
#   py "<projeto>/Tools/Player/disable_jump.py"          -> aplica
#   py "<projeto>/Tools/Player/disable_jump.py" desfazer -> volta Espaco/A no IA_Jump e o pulo no Character
import sys
import unreal

BP = "/Game/Characters/MixamoFP/Blueprints/BP_Player_Cowboy"
IMC = "/Game/FPMovement/Player/Input/IMC_Default"
IA_JUMP = "/Game/FPMovement/Player/Input/Actions/IA_Jump"
TECLAS = ("SpaceBar", "Gamepad_FaceButton_Bottom")  # o mapeamento original do IA_Jump
DESFAZER = "desfazer" in [str(a).lower() for a in sys.argv[1:]]

EAL = unreal.EditorAssetLibrary
bp = EAL.load_asset(BP)
imc = EAL.load_asset(IMC)
ia = EAL.load_asset(IA_JUMP)


def teclas_jump():
    return [str(m.get_editor_property("key").get_editor_property("key_name"))
            for m in imc.get_editor_property("default_key_mappings").get_editor_property("mappings")
            if m.get_editor_property("action") == ia]


def estado():
    cdo = unreal.get_default_object(bp.generated_class())
    cm = cdo.get_editor_property("character_movement")
    return "JumpMaxCount=%s CanJump=%s | teclas do IA_Jump no IMC_Default: %s" % (
        cdo.get_editor_property("jump_max_count"),
        cm.get_editor_property("nav_agent_props").get_editor_property("can_jump"), teclas_jump())


print("antes:  " + estado())
with unreal.ScopedEditorTransaction("LUX: sem pulo"):
    cdo = unreal.get_default_object(bp.generated_class())
    cm = cdo.get_editor_property("character_movement")
    cdo.modify()
    cm.modify()
    cdo.set_editor_property("jump_max_count", 1 if DESFAZER else 0)
    nav = cm.get_editor_property("nav_agent_props")
    nav.set_editor_property("can_jump", DESFAZER)
    cm.set_editor_property("nav_agent_props", nav)

    imc.modify()
    if DESFAZER:
        for k in TECLAS:
            if k not in teclas_jump():
                imc.map_key(ia, unreal.Key(key_name=k))
    else:
        imc.unmap_all_keys_from_action(ia)

unreal.BlueprintEditorLibrary.compile_blueprint(bp)
print("depois: " + estado())
print("salvo BP_Player_Cowboy:", EAL.save_loaded_asset(bp, False), "| salvo IMC_Default:", EAL.save_loaded_asset(imc, False))
