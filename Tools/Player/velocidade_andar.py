# LUX: caminhada levemente mais rapida (pedido do Gabriel, 27/09 21:49): 150 -> 170 cm/s (+13%), longe da corrida (360,
# desligada). So dados no BP_Player_Cowboy (o BP_Player compartilhado nao e editado):
#  - CharacterMovement.MaxWalkSpeed (velocidade ao nascer);
#  - variavel MaxWalkSpeed (o BP_Player a usa para voltar a andar depois de agachar).
# Aceleracao, frenagem, agachado (MaxCrouchSpeed) e animacoes ficam como estao: o blend space de andar do corpo e dos
# bracos e dirigido pela velocidade, entao a animacao acompanha.
#   py "<projeto>/Tools/Player/velocidade_andar.py" sondar|instalar|verificar|desfazer
import sys
import unreal

BP = "/Game/Characters/MixamoFP/Blueprints/BP_Player_Cowboy"
ORIGINAL, NOVA = 150.0, 170.0
EAL = unreal.EditorAssetLibrary


def valores():
    cdo = unreal.get_default_object(EAL.load_asset(BP).generated_class())
    return cdo.get_editor_property("character_movement").get_editor_property("max_walk_speed"), cdo.get_editor_property("MaxWalkSpeed")


def aplica(v):
    bp = EAL.load_asset(BP)
    cdo = unreal.get_default_object(bp.generated_class())
    if valores() == (v, v):
        print("ja em", v)
        return
    cm = cdo.get_editor_property("character_movement")
    cm.set_editor_property("max_walk_speed", v)
    cdo.set_editor_property("MaxWalkSpeed", v)
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    print("salvo:", EAL.save_loaded_asset(bp, False), valores())


def verificar():
    cm, var = valores()
    ok = abs(cm - NOVA) < 1e-3 and abs(var - NOVA) < 1e-3
    print("MaxWalkSpeed componente=%s variavel=%s" % (cm, var), "| verificar:", "PASS" if ok else "FAIL (esperado %s)" % NOVA)
    return ok


modo = next((a for a in sys.argv[1:] if a in ("sondar", "instalar", "verificar", "desfazer")), "sondar")
print("modo:", modo)
if modo == "sondar":
    print("MaxWalkSpeed (componente, variavel):", valores())
elif modo == "instalar":
    aplica(NOVA)
    verificar()
elif modo == "verificar":
    verificar()
else:
    aplica(ORIGINAL)
