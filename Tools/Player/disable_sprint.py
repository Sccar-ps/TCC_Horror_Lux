# LUX: o jogador nao corre (decisao do Gabriel, 27/09: correndo ele chegava na porta antes de a distorcao dos loops 3/5
# acabar e perdia os sustos). O BP_Player (compartilhado) nao e editado.
# Como a corrida funciona (sondar, 27/09): IMC_Default liga LeftShift ao IA_Sprint (sem gamepad, sem triggers/modifiers no
# mapeamento; o IA_Sprint tem Pressed+Released). No BP_Player: Started -> se nao agachado: Footsteps_TL.SetPlayRate(2.2),
# CharacterMovement.MaxWalkSpeed = MaxSprintSpeed (360), IsSprinting? = true; Completed -> PlayRate 1, MaxWalkSpeed =
# MaxWalkSpeed (150), IsSprinting? = false. IsSprinting? nao e lido em nenhum lugar (sem HUD, stamina, FOV ou animacao) e
# nenhum outro IMC nem asset usa o IA_Sprint. Tirar a tecla basta: o evento nunca dispara e a caminhada fica em 150.
# Idempotente. Salva so o IMC_Default (e so se mudar).
#   py "<projeto>/Tools/Player/disable_sprint.py" sondar|instalar|verificar|desfazer
import json, os, sys
import unreal

IMC = "/Game/FPMovement/Player/Input/IMC_Default"
IA_SPRINT = "/Game/FPMovement/Player/Input/Actions/IA_Sprint"
BP = "/Game/Characters/MixamoFP/Blueprints/BP_Player_Cowboy"
TECLAS = ("LeftShift",)  # o mapeamento original do IA_Sprint no IMC_Default
OUTRAS = ("IA_Crouch", "IA_Interact", "IA_Move", "IA_Look")  # 27/09: IA_Flashlight saiu (F agora e o IA_Lampiao, Tools/Player/lampiao.py)
SNAP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sprint_original.json")

EAL = unreal.EditorAssetLibrary
imc = EAL.load_asset(IMC)
ia = EAL.load_asset(IA_SPRINT)


def mapeamentos():
    return list(imc.get_editor_property("default_key_mappings").get_editor_property("mappings"))


def teclas(acao_nome):
    return [str(m.get_editor_property("key").get_editor_property("key_name")) for m in mapeamentos()
            if m.get_editor_property("action") and m.get_editor_property("action").get_name() == acao_nome]


def sondar():
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    print("referenciadores do IA_Sprint:", [str(x) for x in ar.get_referencers(IA_SPRINT, unreal.AssetRegistryDependencyOptions())])
    f = unreal.ARFilter(class_paths=[unreal.TopLevelAssetPath("/Script/EnhancedInput", "InputMappingContext")], package_paths=["/Game"],
                        recursive_paths=True)
    for a in ar.get_assets(f):
        c = EAL.load_asset(str(a.package_name))
        for m in c.get_editor_property("default_key_mappings").get_editor_property("mappings"):
            if m.get_editor_property("action") == ia:
                print("  %s: %s triggers=%s modifiers=%s" % (a.package_name, m.get_editor_property("key").get_editor_property("key_name"),
                      [t.get_class().get_name() for t in m.get_editor_property("triggers")],
                      [t.get_class().get_name() for t in m.get_editor_property("modifiers")]))
    print("IA_Sprint triggers:", [t.get_class().get_name() for t in ia.get_editor_property("triggers")])
    cdo = unreal.get_default_object(EAL.load_asset(BP).generated_class())
    print("MaxWalkSpeed=%s MaxSprintSpeed=%s" % (cdo.get_editor_property("character_movement").get_editor_property("max_walk_speed"),
                                                 cdo.get_editor_property("MaxSprintSpeed")))


def verificar():
    falhas = []
    if teclas("IA_Sprint"):
        falhas.append("IA_Sprint ainda tem teclas: %s" % teclas("IA_Sprint"))
    cdo = unreal.get_default_object(EAL.load_asset(BP).generated_class())
    v = cdo.get_editor_property("character_movement").get_editor_property("max_walk_speed")
    if abs(v - 170.0) > 1e-3:  # 27/09 21:49: caminhada 150 -> 170 (Tools/Player/velocidade_andar.py)
        falhas.append("MaxWalkSpeed = %s (esperado 170)" % v)
    for nome in OUTRAS:
        if not teclas(nome):
            falhas.append("%s ficou sem tecla" % nome)
    print("teclas: " + " | ".join("%s=%s" % (n, teclas(n)) for n in ("IA_Sprint",) + OUTRAS))
    print("verificar:", ("FAIL %s" % falhas) if falhas else "PASS")
    return falhas


def instalar():
    atuais = teclas("IA_Sprint")
    if atuais:
        if not os.path.exists(SNAP):
            with open(SNAP, "w", encoding="utf-8") as fh:
                json.dump({"IA_Sprint": atuais}, fh)
        with unreal.ScopedEditorTransaction("LUX: sem corrida"):
            imc.modify()
            imc.unmap_all_keys_from_action(ia)
        print("salvo IMC_Default:", EAL.save_loaded_asset(imc, False))
    else:
        print("IA_Sprint ja sem teclas: nada a fazer")
    verificar()


def desfazer():
    orig = json.load(open(SNAP, encoding="utf-8"))["IA_Sprint"] if os.path.exists(SNAP) else list(TECLAS)
    faltam = [k for k in orig if k not in teclas("IA_Sprint")]
    if faltam:
        with unreal.ScopedEditorTransaction("LUX: volta a corrida"):
            imc.modify()
            for k in faltam:
                imc.map_key(ia, unreal.Key(key_name=k))
        print("salvo IMC_Default:", EAL.save_loaded_asset(imc, False))
    print("IA_Sprint:", teclas("IA_Sprint"))


modo = next((a for a in sys.argv[1:] if a in ("sondar", "instalar", "verificar", "desfazer")), "sondar")
print("modo:", modo)
{"sondar": sondar, "instalar": instalar, "verificar": verificar, "desfazer": desfazer}[modo]()
