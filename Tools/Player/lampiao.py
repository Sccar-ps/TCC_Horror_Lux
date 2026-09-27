# LUX: lampiao no lugar da lanterna (pedido do Gabriel, 27/09 18:22): luz de chama fraca EM VOLTA do jogador, nao em cone.
# O BP_Player (compartilhado, FPMovement) nao e editado.
# Como a lanterna funcionava (sondar): IMC_Default liga F ao IA_Flashlight; no BP_Player o F (se HasFlashlight?) toca a
# montagem de equipar, mostra o SM_Flashlight (SetVisibility sem propagar) e sobe a intensidade da SpotLight
# Flashlight_Light por uma Timeline. Os dois componentes comecam ocultos.
# Lampiao:
#  1) IA_Lampiao (novo, /Game/Masion/LUX/Player). IMC_Default: F sai do IA_Flashlight e vai para o IA_Lampiao, entao a
#     logica da lanterna do pai nunca roda (a lanterna fica apagada e guardada; nada e apagado).
#  2) BP_Player_Cowboy: PointLightComponent "Lampiao" preso ao corpo, na altura da mao, a frente e a direita da camera;
#     2800 K (laranja de chama, sem puxar para o vermelho), 0,8 cd, raio 5 m, sombras; comeca ACESO.
#  3) BP_Player_Cowboy EventGraph (so ADICIONA nos): IA_Lampiao Started -> Lampiao.ToggleVisibility.
# Sem mesh: o projeto nao tem mesh de lampiao/lamparina de mao.
# Sem oscilacao de chama por enquanto (seria mais grafo; a regra de fotossensibilidade permitiria no maximo +-5%).
#   py "<projeto>/Tools/Player/lampiao.py" sondar|instalar|verificar|desfazer
import json, os, sys, traceback
import unreal

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(AQUI), "Loop"))
import add_loop_events as ale

EAL, BEL, BGE = unreal.EditorAssetLibrary, unreal.BlueprintEditorLibrary, unreal.BlueprintGraphEditor
BP = "/Game/Characters/MixamoFP/Blueprints/BP_Player_Cowboy"
ME = BP + ".BP_Player_Cowboy_C"
IMC = "/Game/FPMovement/Player/Input/IMC_Default"
IA_FLASH = "/Game/FPMovement/Player/Input/Actions/IA_Flashlight"
DIR_IA = "/Game/Masion/LUX/Player"
IA_LAMP = DIR_IA + "/IA_Lampiao"
COMP = "Lampiao"
LUZ = {"intensidade_cd": 0.8, "raio": 500.0, "temperatura": 2800.0, "fonte": 2.0, "pos": (30.0, 25.0, 30.0)}
SNAP = os.path.join(AQUI, "lampiao_original.json")
LOG = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), "LuxSnapshots", "lampiao_log.txt")
NO_EVENTO = "Entrada|EnhancedActionEvents|IA_Lampiao"


def w(*a):
    line = " ".join(str(x) for x in a)
    unreal.log("[LUX lampiao] " + line)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")
        fh.flush()


class Aborta(Exception):
    pass


def teclas(imc, ia):
    return [str(m.get_editor_property("key").get_editor_property("key_name"))
            for m in imc.get_editor_property("default_key_mappings").get_editor_property("mappings") if m.get_editor_property("action") == ia]


def tecla(nome):
    k = unreal.Key()
    k.set_editor_property("key_name", nome)
    return k


def comp():
    return ale.comp_template(EAL.load_asset(BP), COMP)


def no_toggle(bp):
    ge = BGE.get_graph_editor_by_name(bp, "EventGraph")
    for n in ge.list_all_nodes():
        if "IA_Lampiao" in str(n.get_node_title()):
            return n
    return None


def sondar():
    imc = EAL.load_asset(IMC)
    w("F no IMC_Default:", [(m.get_editor_property("action").get_name(), str(m.get_editor_property("key").get_editor_property("key_name")))
                            for m in imc.get_editor_property("default_key_mappings").get_editor_property("mappings")
                            if str(m.get_editor_property("key").get_editor_property("key_name")) == "F"])
    c = comp()
    w("componente Lampiao:", bool(c), "| no do F:", bool(no_toggle(EAL.load_asset(BP))) if EAL.does_asset_exist(BP) else None)


def instalar():
    if unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor():
        raise Aborta("feche o PIE")
    imc, bp = EAL.load_asset(IMC), EAL.load_asset(BP)
    if ale.comp_template(bp, "Vela"):
        raise Aborta("a vela (Tools/Player/vela.py) esta instalada: o lampiao nao e reinstalado por cima (use vela.py desfazer)")
    ia_f = EAL.load_asset(IA_FLASH)
    salvar = set()
    if not EAL.does_asset_exist(IA_LAMP):
        if not EAL.does_directory_exist(DIR_IA):
            EAL.make_directory(DIR_IA)
        unreal.AssetToolsHelpers.get_asset_tools().create_asset("IA_Lampiao", DIR_IA, unreal.InputAction, unreal.InputAction_Factory())
        w("IA_Lampiao criado")
    ia_l = EAL.load_asset(IA_LAMP)
    if IA_LAMP in ale.sujos():
        salvar.add(IA_LAMP)
    # 1) F: IA_Flashlight -> IA_Lampiao
    orig = teclas(imc, ia_f)
    if orig and not os.path.exists(SNAP):
        json.dump({"IA_Flashlight": orig}, open(SNAP, "w", encoding="utf-8"))
    if orig or "F" not in teclas(imc, ia_l):
        with unreal.ScopedEditorTransaction("LUX: lampiao (F)"):
            imc.modify()
            if orig:
                imc.unmap_all_keys_from_action(ia_f)
            if "F" not in teclas(imc, ia_l):
                imc.map_key(ia_l, tecla("F"))
        salvar.add(IMC)
        w("IMC_Default: F -> IA_Lampiao (IA_Flashlight sem teclas; original %s)" % orig)
    # 2) componente
    c = comp()
    if not c:
        w("adicionando PointLight Lampiao")
        _, c = ale.add_comp(bp, unreal.PointLightComponent, COMP)
        salvar.add(BP)
    for k, v in (("intensity_units", unreal.LightUnits.CANDELAS), ("intensity", LUZ["intensidade_cd"]), ("attenuation_radius", LUZ["raio"]),
                 ("use_temperature", True), ("temperature", LUZ["temperatura"]), ("source_radius", LUZ["fonte"]), ("cast_shadows", True),
                 ("visible", True), ("mobility", unreal.ComponentMobility.MOVABLE), ("relative_location", unreal.Vector(*LUZ["pos"]))):
        atual = c.get_editor_property(k)
        if atual != v:
            c.set_editor_property(k, v)
            salvar.add(BP)
    # 3) no do F no EventGraph do Cowboy (so adiciona)
    if not no_toggle(bp):
        w("adicionando no IA_Lampiao -> ToggleVisibility (EventGraph do Cowboy)")
        BEL.compile_blueprint(bp)
        ge = BGE.get_graph_editor_by_name(bp, "EventGraph")
        g = ale.G(ge)
        ev = g.pos(ge.create_node_from_name(NO_EVENTO, unreal.Vector2D(0, 900), []), 0, 900)
        if not ev:
            raise Aborta("no %s nao criado" % NO_EVENTO)
        w("  evento criado:", str(ev.get_node_title()).replace("\n", " "), [str(p.get_pin_name()) for p in ev.list_output_pins()])
        tg = g.call("/Script/Engine.SceneComponent:ToggleVisibility", 400, 900, bPropagateToChildren="false")
        lamp = g.get(COMP, 200, 1050)
        g.link(lamp, COMP, tg, "self")
        g.link(ev, "Started", tg, g.exec_in(tg))
        BEL.compile_blueprint(bp)
        e = ale.erros_bp(bp)
        w("  compilado:", e or "limpo")
        if e:
            raise Aborta("BP_Player_Cowboy com erros (nada salvo): %s" % e)
        salvar.add(BP)
    else:
        BEL.compile_blueprint(bp)
    f = verificar()
    if f:
        raise Aborta("verificar FAIL (nada salvo): %s" % f)
    for p in sorted(salvar):
        w("salvo", p, EAL.save_loaded_asset(EAL.load_asset(p), False))


def verificar():
    falhas = []
    imc, bp = EAL.load_asset(IMC), EAL.load_asset(BP)
    if teclas(imc, EAL.load_asset(IA_FLASH)):
        falhas.append("IA_Flashlight ainda tem teclas (a lanterna ainda liga)")
    if not EAL.does_asset_exist(IA_LAMP) or teclas(imc, EAL.load_asset(IA_LAMP)) != ["F"]:
        falhas.append("F nao esta no IA_Lampiao")
    c = comp()
    vela = ale.comp_template(bp, "Vela")
    if not c:
        falhas.append("sem componente Lampiao")
    elif vela:
        pass  # 27/09 21:49: a vela (Tools/Player/vela.py) assumiu o Lampiao como luz da chama; valores conferidos no vela.py
    else:
        if not c.get_editor_property("visible"):
            falhas.append("Lampiao comeca apagado")
        if abs(c.get_editor_property("attenuation_radius") - LUZ["raio"]) > 1 or abs(c.get_editor_property("intensity") - LUZ["intensidade_cd"]) > 1e-3:
            falhas.append("Lampiao com intensidade/raio diferentes do previsto")
    if not no_toggle(bp):
        falhas.append("sem o no IA_Lampiao no EventGraph do Cowboy")
    falhas += ale.erros_bp(bp)
    for nome in ("IA_Crouch", "IA_Interact", "IA_Move", "IA_Look"):
        if not [m for m in imc.get_editor_property("default_key_mappings").get_editor_property("mappings")
                if m.get_editor_property("action") and m.get_editor_property("action").get_name() == nome]:
            falhas.append("%s ficou sem tecla" % nome)
    w("verificar:", ("FAIL %s" % falhas) if falhas else "PASS")
    return falhas


def desfazer():
    """Devolve a lanterna: F volta ao IA_Flashlight, IA_Lampiao sem tecla e o Lampiao apagado (componente e no ficam)."""
    imc, bp = EAL.load_asset(IMC), EAL.load_asset(BP)
    ia_f, ia_l = EAL.load_asset(IA_FLASH), EAL.load_asset(IA_LAMP)
    orig = json.load(open(SNAP, encoding="utf-8"))["IA_Flashlight"] if os.path.exists(SNAP) else ["F"]
    with unreal.ScopedEditorTransaction("LUX: volta a lanterna"):
        imc.modify()
        if ia_l:
            imc.unmap_all_keys_from_action(ia_l)
        for k in orig:
            if k not in teclas(imc, ia_f):
                imc.map_key(ia_f, tecla(k))
    c = comp()
    if c:
        c.set_editor_property("visible", False)
        BEL.compile_blueprint(bp)
    w("salvo IMC", EAL.save_loaded_asset(imc, False), "| salvo BP", EAL.save_loaded_asset(bp, False))


def main():
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    open(LOG, "w", encoding="utf-8").close()
    modo = next((a for a in sys.argv[1:] if a in ("sondar", "instalar", "verificar", "desfazer")), "sondar")
    w("modo:", modo)
    try:
        {"sondar": sondar, "instalar": instalar, "verificar": verificar, "desfazer": desfazer}[modo]()
    except Aborta as ex:
        w("ABORTADO:", ex, "| sujos:", ale.sujos())
    except Exception:
        w("ERRO " + traceback.format_exc(), "| sujos:", ale.sujos())


if __name__ == "__main__":
    main()
