# LUX: chave obrigatoria a partir do loop 2 (pedido do Gabriel, 27/09 22:30), com o sistema de porta trancada que ja
# existe no FPMovement:
#  - BP_BaseDoor (NAO editado; todas as portas da casa usam ele): IsLocked, KeyID (int), CheckForKey(DoorKeys do jogador),
#    UnlockSound (SW_Key_Insertion), TryOpenSound (SW_TryOpen_Door), textos Unlock Notification / Door Name Notification.
#  - BP_BaseKey: KeyID; no Interact soma o KeyID em BP_Player.DoorKeys, mostra o aviso de coleta, toca o som e some.
# Loop N -> Chave LUX_Chave_LN (KeyID 100+N) -> porta do loop N:
#  - loops 2-4: a porta de loop (BP_LuxLoopDoor) ganha, ANTES do PedirTroca (intocado), a tranca por loop: na interacao,
#    se o loop mudou desde a ultima configuracao (LoopTranca), tranca de novo com KeyID = 100 + LoopAtual (so a partir do
#    loop 2). Trancada: CheckForKey -> com a chave: destranca (som + aviso) e consome a chave; sem: som de trancada +
#    "Esta trancada.". Destrancada: segue para o PedirTroca como antes.
#  - loop 5: a porta de saida real (BP_BaseDoor5, o manager a revela no ultimo loop) usa o sistema nativo: IsLocked,
#    KeyID 105 na instancia.
#  - chaves: 4 BP_BaseKey, uma por loop, com tags LOOPn_ON + LOOP(n+1)_OFF (so aparecem e so podem ser pegas no loop delas;
#    esconder pelo manager tambem desliga a colisao), com um brilho metalico quente sutil para achar com a vela.
#   py "<projeto>/Tools/Loop/add_chaves_porta.py" sondar|instalar|verificar|desfazer
import importlib, os, sys, traceback
import unreal

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import add_loop_events as ale

EAL, BEL, BGE, MEL = unreal.EditorAssetLibrary, unreal.BlueprintEditorLibrary, unreal.BlueprintGraphEditor, unreal.MaterialEditingLibrary
LDOOR = "/Game/Masion/LUX/Loop/BP_LuxLoopDoor"
LDOOR_C = LDOOR + ".BP_LuxLoopDoor_C"
DOOR_C = "/Game/FPMovement/Blueprints/Doors/BP_BaseDoor.BP_BaseDoor_C"
PLAYER_C = "/Game/FPMovement/Player/Blueprints/BP_Player.BP_Player_C"
HUD_C = "/Game/FPMovement/Player/Widgets/WB_PlayerHud.WB_PlayerHud_C"
MGR_C = "/Game/Masion/LUX/Loop/BP_LuxLoopManager.BP_LuxLoopManager_C"
KEY_BP = "/Game/FPMovement/Blueprints/Doors/BP_BaseKey"
M_BRILHO = "/Game/Masion/LUX/Loop/M_LuxChaveBrilho"
KEY_BASE = 100
LOOP_MIN = 1  # 27/09 22:59: escolha do Gabriel: chave ja no loop 1 (so a 1a passagem, LoopAtual 0, e livre)
CHAVES = {  # loop: (x, y, z da superficie, superficie, sala)
    # L1: o corredor nao tem movel com tampo e nao ha mesinha junto a poltrona; o banquinho lateral da parede norte da sala
    # (longe da porta, fora do caminho direto; sem colisao propria, a chave tem a dela) e a unica superficie livre
    1: (-2536.0, -664.0, 58.0, "Sala_BanquinhoLateral", "sala (banquinho lateral, parede norte)"),
    2: (-2735.0, 1140.0, 81.2, "Quarto_Mesinha", "quarto"),
    3: (-3795.0, -1170.0, 76.7, "Escritorio_Mesa", "escritorio"),
    4: (-2330.0, -1300.0, 75.5, "Sala_MesaJantar", "sala (mesa de jantar)"),
    5: (-2960.0, -1080.0, 141.9, "Sala_Piano", "sala (piano, longe da porta)")}
PORTA_SAIDA = "BP_BaseDoor5"
TXT_TRANCADA = "Está trancada."
TXT_DESTRANCOU = "Destrancou a porta."
TXT_PORTA = "Porta"
TXT_CHAVE = "Pegou a chave."
LOG = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), "LuxSnapshots", "chaves_porta_log.txt")


def w(*a):
    line = " ".join(str(x) for x in a)
    unreal.log("[LUX chave] " + line)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")
        fh.flush()


class Aborta(Exception):
    pass


def label(n):
    return "LUX_Chave_L%d" % n


# ------------------------------------------------------------------ chaves
def ensure_material():
    if EAL.does_asset_exist(M_BRILHO):
        return []
    at = unreal.AssetToolsHelpers.get_asset_tools()
    m = at.create_asset("M_LuxChaveBrilho", "/Game/Masion/LUX/Loop", unreal.Material, unreal.MaterialFactoryNew())
    for prop, cls, val in ((unreal.MaterialProperty.MP_BASE_COLOR, unreal.MaterialExpressionConstant3Vector, unreal.LinearColor(0.85, 0.62, 0.3, 1)),
                           (unreal.MaterialProperty.MP_EMISSIVE_COLOR, unreal.MaterialExpressionConstant3Vector, unreal.LinearColor(0.035, 0.022, 0.008, 1))):
        e = MEL.create_material_expression(m, cls, -400, 0 if prop == unreal.MaterialProperty.MP_BASE_COLOR else 300)
        e.set_editor_property("constant", val)
        MEL.connect_material_property(e, "", prop)
    for prop, val, y in ((unreal.MaterialProperty.MP_METALLIC, 1.0, 100), (unreal.MaterialProperty.MP_ROUGHNESS, 0.28, 200)):
        e = MEL.create_material_expression(m, unreal.MaterialExpressionConstant, -400, y)
        e.set_editor_property("r", val)
        MEL.connect_material_property(e, "", prop)
    MEL.recompile_material(m)
    w("M_LuxChaveBrilho criado")
    return [m]


def ensure_chaves():
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    cls = EAL.load_asset(KEY_BP).generated_class()
    mud = []
    for n, (x, y, z, sup, sala) in CHAVES.items():
        lst = [a for a in ale.atores() if a.get_actor_label() == label(n)]
        a = lst[0] if lst else None
        if not a:
            a = eas.spawn_actor_from_class(cls, unreal.Vector(x, y, z + 0.5), unreal.Rotator(0, 0, 25.0 * n))
            a.set_actor_label(label(n))
            a.set_folder_path("LUX/Chaves")
            mud.append(label(n))
        if (a.get_actor_location() - unreal.Vector(x, y, z + 0.5)).length() > 0.5:
            a.set_actor_location(unreal.Vector(x, y, z + 0.5), False, True)
            mud.append(label(n) + " posicao")
        for k, v in (("KeyID", KEY_BASE + n),):
            if a.get_editor_property(k) != v:
                a.set_editor_property(k, v)
                mud.append("%s.%s" % (label(n), k))
        for k, v in (("Pickup Notification", TXT_CHAVE),):
            try:
                if str(a.get_editor_property(k)) != v:
                    a.set_editor_property(k, unreal.Text(v))
                    mud.append("%s.%s" % (label(n), k))
            except Exception as ex:
                w("aviso: %s sem %s (%s)" % (label(n), k, ex))
        quer = ["LOOP%d_ON" % n] + (["LOOP%d_OFF" % (n + 1)] if n < 5 else []) + ["LUX_CHAVE"]
        if sorted(str(t) for t in a.tags) != sorted(quer):
            a.set_editor_property("tags", [unreal.Name(t) for t in quer])
            mud.append(label(n) + " tags")
        br = EAL.load_asset(M_BRILHO)
        for c in a.get_components_by_class(unreal.StaticMeshComponent):
            for i in range(c.get_num_materials()):
                if c.get_material(i) != br:
                    c.set_material(i, br)
                    mud.append(label(n) + " brilho")
    return mud


def ensure_porta_saida():
    a = ale.por_label(PORTA_SAIDA)
    mud = []
    for k, v in (("IsLocked", True), ("KeyID", KEY_BASE + 5)):
        if a.get_editor_property(k) != v:
            a.set_editor_property(k, v)
            mud.append("%s.%s=%s" % (PORTA_SAIDA, k, v))
    for k, v in (("Unlock Notification", TXT_DESTRANCOU),):
        if str(a.get_editor_property(k)) != v:
            a.set_editor_property(k, unreal.Text(v))
            mud.append("%s.%s" % (PORTA_SAIDA, k))
    return mud


def ensure_texto_porta_loop():
    a = ale.por_label("LOOP_PortaSala")
    mud = []
    for k, v in (("Unlock Notification", TXT_DESTRANCOU), ("Door Name Notification", TXT_PORTA)):
        if str(a.get_editor_property(k)) != v:
            a.set_editor_property(k, unreal.Text(v))
            mud.append("LOOP_PortaSala.%s" % k)
    if a.get_editor_property("Manager") is None:
        raise Aborta("LOOP_PortaSala.Manager ficou None")
    return mud


# ------------------------------------------------------------------ tranca na porta de loop (so adiciona nos)
def tem_tranca(bp):
    return "LoopTranca" in [str(v) for v in BEL.list_member_variable_names(bp)] if hasattr(BEL, "list_member_variable_names") else False


def txt(g, n, pino, texto):
    p = ale.ok_pin(n.find_input_pin(pino))
    for fmt in ("%s", 'INVTEXT("%s")', 'NSLOCTEXT("LUX", "LUX", "%s")'):
        if p.set_pin_value(fmt % texto):
            return
    raise Aborta("texto nao aceito em %s" % pino)


def ensure_tranca():
    bp = EAL.load_asset(LDOOR)
    ge = BGE.get_graph_editor_by_name(bp, "EventGraph")
    nos = list(ge.list_all_nodes())
    if [n for n in nos if "CheckForKey" in str(n.get_node_title())]:
        w("tranca ja existe na BP_LuxLoopDoor")
        # o loop minimo e o valor B do no ">=" (LoopAtual >= LOOP_MIN) que liga a tranca: mantem igual a constante
        ge_n = [n for n in nos if n.find_input_pin("B") and ("GreaterEqual" in n.get_name() or ">=" in str(n.get_node_title()) or "PromotableOperator" in n.get_name())
                and n.find_output_pin("ReturnValue") and "bool" in str(n.find_output_pin("ReturnValue").get_pin_type_as_json_schema()).lower()
                and "int" in str(n.find_input_pin("B").get_pin_type_as_json_schema()).lower()]
        ge_n = [n for n in ge_n if str(n.find_input_pin("B").get_pin_value()) in ("1", "2", str(LOOP_MIN))]
        if len(ge_n) != 1:
            raise Aborta("no do loop minimo nao encontrado (%d candidatos)" % len(ge_n))
        if str(ge_n[0].find_input_pin("B").get_pin_value()) != str(LOOP_MIN):
            ge_n[0].find_input_pin("B").set_pin_value(str(LOOP_MIN))
            BEL.compile_blueprint(bp)
            e = ale.erros_bp(bp)
            if e:
                raise Aborta("BP_LuxLoopDoor com erros: %s" % e)
            w("loop minimo da tranca ->", LOOP_MIN)
            return True
        return False
    w("tranca: variavel LoopTranca")
    if "LoopTranca" not in [str(v) for v in BEL.list_member_variable_names(bp)]:
        BEL.add_member_variable(bp, "LoopTranca", BEL.get_basic_type_by_name("int"))
        BEL.compile_blueprint(bp)
        unreal.get_default_object(bp.generated_class()).set_editor_property("LoopTranca", -1)
    ev = [n for n in nos if "Interact" in str(n.get_node_title()) and n.find_output_pin("then")][0]
    ramo = [n for n in nos if str(n.get_node_title()) in ("Ramo", "Branch")][0]
    b = ale.B(ge, LDOOR_C)
    g = b.g
    w("tranca: nos de configuracao por loop")
    gm = b.c(ale.GS + "GetActorOfClass", 0, 0, ActorClass="/Script/Engine.BlueprintGeneratedClass'%s'" % MGR_C)
    L = b.v("LoopAtual", cls=MGR_C)
    b.lk((gm, "ReturnValue"), L[0], "self")
    bcfg = b.br(b.op("NotEqual_IntInt", L, b.v("LoopTranca")))
    s1 = b.setv("LoopTranca", src=L)
    s2 = b.setv("IsLocked", src=b.op("GreaterEqual_IntInt", L, LOOP_MIN))
    s3 = b.setv("KeyID", src=b.op("Add_IntInt", L, KEY_BASE))
    j = ale.junc(b)
    blk = b.br(b.v("IsLocked"))
    w("tranca: checagem da chave (CheckForKey do BP_BaseDoor)")
    pref = b.v("Player Reference")
    dk = b.v("DoorKeys", cls=PLAYER_C)
    b.lk(pref, dk[0], "self")
    ck = b.c(DOOR_C + ":CheckForKey", 0, 0)
    b.lk(dk, ck, "Keys")
    bkey = b.br((ck, "HasKey"))
    loc = b.c("/Script/Engine.Actor:K2_GetActorLocation", 0, 0)
    # com a chave
    su = b.setv("IsLocked", "false")
    snd1 = b.c(ale.GS + "PlaySoundAtLocation", 0, 0, VolumeMultiplier=0.8)
    b.lk(b.v("UnlockSound"), snd1, "Sound")
    b.lk((loc, "ReturnValue"), snd1, "Location")
    hud1 = b.v("WP_PlayerHUD", cls=PLAYER_C)
    b.lk(b.v("Player Reference"), hud1[0], "self")
    n1 = b.c(HUD_C + ":AddNotification", 0, 0)
    b.lk(hud1, n1, "self")
    b.lk(b.v("Unlock Notification"), n1, "Message")
    b.lk(b.v("Door Name Notification"), n1, "Item")
    b.lk(b.v("Door Name Color Notification"), n1, "InColorAndOpacity")
    dk2 = b.v("DoorKeys", cls=PLAYER_C)
    b.lk(b.v("Player Reference"), dk2[0], "self")
    rm = b.c(ale.ARR + "Array_RemoveItem", 0, 0)
    b.lk(dk2, rm, "TargetArray")
    b.lk(b.v("KeyID"), rm, "Item")
    # sem a chave
    snd2 = b.c(ale.GS + "PlaySoundAtLocation", 0, 0, VolumeMultiplier=0.8)
    b.lk(b.v("TryOpenSound"), snd2, "Sound")
    loc2 = b.c("/Script/Engine.Actor:K2_GetActorLocation", 0, 0)
    b.lk((loc2, "ReturnValue"), snd2, "Location")
    hud2 = b.v("WP_PlayerHUD", cls=PLAYER_C)
    b.lk(b.v("Player Reference"), hud2[0], "self")
    n2 = b.c(HUD_C + ":AddNotification", 0, 0)
    b.lk(hud2, n2, "self")
    txt(g, n2, "Message", TXT_TRANCADA)
    b.lk(b.v("Door Name Notification"), n2, "Item")
    b.lk(b.v("Door Name Color Notification"), n2, "InColorAndOpacity")
    w("tranca: religando a entrada do Interact")
    pin_then = ev.find_output_pin("then")
    pin_then.break_pin_links()
    g.link(ev, "then", gm, g.exec_in(gm))
    b.ch(gm, bcfg)
    b.ch((bcfg, "then"), s1, s2, s3, j)
    b.ch((bcfg, "else"), j)
    b.ch((j, "then"), blk)
    b.ch((blk, "then"), ck, bkey)
    b.ch((bkey, "then"), su, snd1, n1, rm)
    b.ch((bkey, "else"), snd2, n2)
    g.link(blk, "else", ramo, "execute")
    BEL.compile_blueprint(bp)
    e = ale.erros_bp(bp)
    w("tranca compilada:", e or "limpa")
    if e:
        raise Aborta("BP_LuxLoopDoor com erros (nada salvo): %s" % e)
    return True


# ------------------------------------------------------------------ modos
def verificar():
    falhas = []
    bp = EAL.load_asset(LDOOR)
    if not [n for n in BGE.get_graph_editor_by_name(bp, "EventGraph").list_all_nodes() if "CheckForKey" in str(n.get_node_title())]:
        falhas.append("porta de loop sem a checagem da chave")
    falhas += ale.erros_bp(bp)
    for n, (x, y, z, sup, sala) in CHAVES.items():
        lst = [a for a in ale.atores() if a.get_actor_label() == label(n)]
        if len(lst) != 1:
            falhas.append("%s ausente" % label(n))
            continue
        a = lst[0]
        if a.get_editor_property("KeyID") != KEY_BASE + n:
            falhas.append("%s com KeyID errado" % label(n))
        if "LOOP%d_ON" % n not in [str(t) for t in a.tags]:
            falhas.append("%s sem a tag do loop" % label(n))
    mins = [str(n.find_input_pin("B").get_pin_value()) for n in BGE.get_graph_editor_by_name(bp, "EventGraph").list_all_nodes()
            if n.find_input_pin("B") and n.find_output_pin("ReturnValue") and "bool" in str(n.find_output_pin("ReturnValue").get_pin_type_as_json_schema()).lower()
            and "int" in str(n.find_input_pin("B").get_pin_type_as_json_schema()).lower() and str(n.find_input_pin("B").get_pin_value()) in ("1", "2")]
    if mins != [str(LOOP_MIN)]:
        falhas.append("loop minimo da tranca na porta = %s (esperado %s)" % (mins, LOOP_MIN))
    ps = ale.por_label(PORTA_SAIDA)
    if not ps.get_editor_property("IsLocked") or ps.get_editor_property("KeyID") != KEY_BASE + 5:
        falhas.append("porta de saida (loop 5) nao esta trancada com a chave 105")
    lp = ale.por_label("LOOP_PortaSala")
    if not lp.get_editor_property("Manager"):
        falhas.append("LOOP_PortaSala.Manager = None")
    ids = [a.get_editor_property("KeyID") for a in ale.atores() if "Key" in a.get_class().get_name()]
    if len(ids) != len(set(ids)):
        falhas.append("KeyID repetido entre chaves: %s" % ids)
    w("verificar:", ("FAIL %s" % falhas) if falhas else "PASS")
    return falhas


def instalar():
    if unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor():
        raise Aborta("feche o PIE")
    salvar = ensure_material()
    mud = ensure_chaves() + ensure_porta_saida() + ensure_texto_porta_loop()
    w("mapa:", mud or "nada")
    if ensure_tranca():
        salvar.append(EAL.load_asset(LDOOR))
    f = verificar()
    if f:
        raise Aborta("verificar FAIL (nada salvo): %s" % f)
    for a in salvar:
        w("salvo", a.get_path_name(), EAL.save_loaded_asset(a, False))
    U = unreal.EditorLoadingAndSavingUtils
    m = [p for p in U.get_dirty_map_packages() if p.get_name() == "/Game/Masion/Mapa_B"]
    if m:
        w("salvo Mapa_B", U.save_packages(m, True))


def desfazer():
    """Porta sem chave de novo: chaves fora do mapa, porta de saida destrancada; na porta de loop a tranca fica no grafo
    (nao se apagam grafos), mas LOOP_MIN alto a desliga: rode com LOOP_MIN = 99 e instalar, ou apague os nos a mao."""
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for a in [a for a in ale.atores() if "LUX_CHAVE" in [str(t) for t in a.tags]]:
        eas.destroy_actor(a)
    ps = ale.por_label(PORTA_SAIDA)
    ps.set_editor_property("IsLocked", False)
    ps.set_editor_property("KeyID", 0)
    U = unreal.EditorLoadingAndSavingUtils
    U.save_packages([p for p in U.get_dirty_map_packages() if p.get_name() == "/Game/Masion/Mapa_B"], True)
    w("chaves removidas e porta de saida destrancada")


def sondar():
    for a in ale.atores():
        cn = a.get_class().get_name()
        if "Door" in cn or "Key" in cn:
            w(a.get_actor_label(), cn, "KeyID", a.get_editor_property("KeyID"), "IsLocked", a.get_editor_property("IsLocked") if "Door" in cn else "")


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
