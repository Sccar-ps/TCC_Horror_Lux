# LUX: BPFL DESCARTAVEL para os testes de PIE de controle: BPFL_TesteInput.ObterSub(Controle) devolve o EnhancedInputLocalPlayerSubsystem do jogador
# (o Python do UE 5.8 nao alcanca o subsistema do jogador local). Fica em /Game/Masion/LUX/_TesteEntrada, NAO e salvo; apague a pasta ao terminar.
# Rode com o editor aberto no Mapa_B, antes do gamepad_pie_teste.py:   py "<projeto>/Tools/Player/gamepad_pie_injetor.py"
import os, sys, unreal
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(AQUI), "Loop"))
sys.path.insert(0, AQUI)
import gamepad_entrada as ge_

EAL, BEL = unreal.EditorAssetLibrary, unreal.BlueprintEditorLibrary
PASTA = "/Game/Masion/LUX/_TesteEntrada"
P = PASTA + "/BPFL_TesteInput"
if EAL.does_asset_exist(P):
    EAL.delete_asset(P)
if not EAL.does_directory_exist(PASTA):
    EAL.make_directory(PASTA)
bp = BEL.create_blueprint_asset_with_parent(P, unreal.BlueprintFunctionLibrary)
t = ge_.tipos()
t["sub"] = BEL.get_object_reference_type(unreal.Object.static_class())   # o tipo da subclasse nao serve de pino de saida; o Python enxerga a classe real
b, en, ret, fe = ge_.nova_funcao(bp, "ObterSub", [("Controle", "pc")], [("Sub", "sub")], t, P + ".BPFL_TesteInput_C")
fe.set_is_pure_function(True)
sub = ge_.cria_no(fe, "PlayerController", fim="EnhancedInputLocalPlayerSubsystem")
b.lk((en, "Controle"), sub, "PlayerController")
b.lk((sub, "ReturnValue"), ret, "Sub")
b.ch(en, ret)
BEL.compile_blueprint(bp)
print("BPFL_TesteInput:", ge_.erros(bp) or "compilado limpo (nao salvo)")
