# LUX: suporte a controle (Xbox e PlayStation) - ETAPAS 2 e 3: tipo de dispositivo, icones por dispositivo, pausa.
# Depende do Tools/Player/gamepad_input.py instalar (acoes IA_Pausa/IA_UI_* e IMC_LuxEntrada). So ADICIONA assets e um componente
# no BP_Player_Cowboy; o BP_Player, o BP_BaseDoor e o BP_BaseKey (D02) nao sao editados e nenhum widget do pack e alterado.
#
# Pecas (todas em /Game/Masion/LUX/Entrada):
#  PDA_LuxGlifos + DA_LuxGlifos  dados: rotulo e icone de cada botao do gamepad por estilo (Xbox / PlayStation). Os icones ficam VAZIOS:
#                                 o projeto nao tem texturas de botao; quando houver, basta arrastar a textura no DA_LuxGlifos (nenhuma logica muda).
#  BPFL_LuxEntrada               ClassificarDispositivo(classe, id) -> TecladoMouse | Xbox | PlayStation | Generico (funcao pura, testada por tabela)
#                                 TeclaMapeadaNaAcao(controle, tecla, acao) -> bool (pergunta ao Enhanced Input; usada por janelas do tipo UIOnly)
#  WB_LuxPausa                   tela de pausa (clone enxuto do WB_InteractDot do pack: fundo escuro + texto)
#  BP_LuxEntrada                 componente do BP_Player_Cowboy: registra o IMC_LuxEntrada, escuta OnInputHardwareDeviceChanged (troca teclado/mouse <->
#                                 controle sem Tick), guarda o tipo atual, escreve o rotulo da tecla da acao no prompt do HUD (WP_Interaction, sem editar o
#                                 widget), pausa/continua (IA_Pausa, IA_UI_Voltar, IA_UI_Confirmar) e troca o estilo dos icones no pause (IA_UI_Alternar).
# Por que o estilo manual: no PC o controle da PlayStation chega ao jogo como XInput (Steam Input, DS4Windows) e a engine so enxerga "XInputController";
# o jogador de PlayStation escolhe os icones no pause (Y/Triangle: Auto -> Xbox -> PlayStation).
#   py "<projeto>/Tools/Player/gamepad_entrada.py" sondar|instalar|verificar|desfazer [glifos|bpfl|widget|comp|cowboy ...]
import json, os, sys, traceback
import unreal

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(AQUI), "Loop"))
import add_loop_events as ale

EAL, BEL, BGE = unreal.EditorAssetLibrary, unreal.BlueprintEditorLibrary, unreal.BlueprintGraphEditor
VERSAO = 1
DIR = "/Game/Masion/LUX/Entrada"
PDA, DA = DIR + "/PDA_LuxGlifos", DIR + "/DA_LuxGlifos"
BPFL, WBP, COMP = DIR + "/BPFL_LuxEntrada", DIR + "/WB_LuxPausa", DIR + "/BP_LuxEntrada"
PDA_C, BPFL_C, WBP_C, COMP_C = PDA + ".PDA_LuxGlifos_C", BPFL + ".BPFL_LuxEntrada_C", WBP + ".WB_LuxPausa_C", COMP + ".BP_LuxEntrada_C"
IMC_LUX = DIR + "/IMC_LuxEntrada"
IA_INTERACT = "/Game/FPMovement/Player/Input/Actions/IA_Interact"
COWBOY = "/Game/Characters/MixamoFP/Blueprints/BP_Player_Cowboy"
COMP_NOME = "LuxEntrada"
WPI = "/Game/FPMovement/Player/Widgets/UserCreated/Interaction/WP_Interaction"
WPI_C = WPI + ".WP_Interaction_C"
SRC_WIDGET = "/Game/FPMovement/Player/Widgets/UserCreated/WB_InteractDot"   # pack, sem referenciadores; so a raiz (HorizontalBox) importa
LOG = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), "LuxSnapshots", "gamepad_entrada_log.txt")
STR, TXT, KML, KSL, GS, MAC = ale.STR, ale.TXT, ale.KML, ale.KSL, ale.GS, ale.MAC
MAPL = "/Script/Engine.BlueprintMapLibrary:"
EIS = "/Script/EnhancedInput.EnhancedInputSubsystemInterface:"
KIL = "/Script/Engine.KismetInputLibrary:"
OPCOES = "(bIgnoreAllPressedKeysUntilRelease=True,bForceImmediately=False,bNotifyUserSettings=False)"

# estilos e tipos: texto simples (Auto/Xbox/PlayStation; TecladoMouse/Xbox/PlayStation/Generico) - o UE 5.8 nao deixa o Python criar enum de usuario
TIPOS = ("TecladoMouse", "Xbox", "PlayStation", "Generico")

# rotulos por tecla de gamepad (Xbox, PlayStation). Texto do pedido: A/B/X/Y e Cross/Circle/Square/Triangle.
ROTULOS = (
    ("Gamepad_FaceButton_Bottom", "A", "Cross"), ("Gamepad_FaceButton_Right", "B", "Circle"), ("Gamepad_FaceButton_Left", "X", "Square"),
    ("Gamepad_FaceButton_Top", "Y", "Triangle"), ("Gamepad_LeftShoulder", "LB", "L1"), ("Gamepad_RightShoulder", "RB", "R1"),
    ("Gamepad_LeftTriggerAxis", "LT", "L2"), ("Gamepad_RightTriggerAxis", "RT", "R2"), ("Gamepad_LeftTrigger", "LT", "L2"),
    ("Gamepad_RightTrigger", "RT", "R2"), ("Gamepad_LeftThumbstick", "LS", "L3"), ("Gamepad_RightThumbstick", "RS", "R3"),
    ("Gamepad_Special_Left", "View", "Share"), ("Gamepad_Special_Right", "Menu", "Options"),
    ("Gamepad_DPad_Up", "D-Pad Up", "D-Pad Up"), ("Gamepad_DPad_Down", "D-Pad Down", "D-Pad Down"),
    ("Gamepad_DPad_Left", "D-Pad Left", "D-Pad Left"), ("Gamepad_DPad_Right", "D-Pad Right", "D-Pad Right"),
    ("Gamepad_LeftStick_Up", "LS Up", "LS Up"), ("Gamepad_LeftStick_Down", "LS Down", "LS Down"),
    ("Gamepad_LeftStick_Left", "LS Left", "LS Left"), ("Gamepad_LeftStick_Right", "LS Right", "LS Right"),
    ("Gamepad_Left2D", "LS", "LS"), ("Gamepad_Right2D", "RS", "RS"),
)
# tabela de verificacao do classificador: (classe, id) -> tipo
CASOS = (("WindowsApplication", "KBM", "TecladoMouse"), ("None", "None", "TecladoMouse"), ("XInputInterface", "XInputController", "Xbox"),
         ("GameInput", "XboxOne", "Xbox"), ("GameInput", "Xbox360", "Xbox"), ("FWinDualShock", "DualSense", "PlayStation"),
         ("FWinDualShock", "DualShock4", "PlayStation"), ("SonyInterface", "PS5Controller", "PlayStation"), ("PlayStationDevice", "Pad", "PlayStation"),
         ("GameInput", "Hid", "Generico"), ("RawInput", "Wireless Controller", "Generico"), ("Foo", "Gamepad", "Generico"))


def w(*a):
    line = " ".join(str(x) for x in a)
    unreal.log("[LUX entrada] " + line)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")
        fh.flush()


class Aborta(Exception):
    pass


# ------------------------------------------------------------------ utilidades de grafo
_PAL = {}


def paleta(ge):
    k = ge.get_graph().get_path_name()
    if k not in _PAL:
        _PAL[k] = [str(x) for x in ge.list_available_nodes([])]
    return _PAL[k]


def cria_no(ge, *chaves, fim=None, sem=(), x=0, y=0):
    """no da paleta (independe do idioma do editor): termina em `fim`, contem todas as `chaves`, nenhuma de `sem`"""
    for p in paleta(ge):
        q = p.replace(" ", "")
        if fim is not None and not q.endswith(fim.replace(" ", "")):
            continue
        if all(k.replace(" ", "") in q for k in chaves) and not any(s in q for s in sem):
            n = ge.create_node_from_name(p, unreal.Vector2D(x, y), [])
            if n:
                return n
    raise Aborta("no da paleta nao encontrado: fim=%s chaves=%s" % (fim, chaves))


class B(ale.B):
    """B do add_loop_events com x e y opcionais em c()"""

    def c(self, path, x=0, y=0, **vals):
        return super().c(path, x, y, **vals)


def pino_cast(n):
    return next(str(p.get_pin_name()) for p in n.list_output_pins() if str(p.get_pin_name()).startswith("As") and '"exec"' not in str(p.get_pin_type_as_json_schema()))


def pino_exec_saida(n, nome):
    return next(str(p.get_pin_name()) for p in n.list_output_pins() if str(p.get_pin_name()) == nome)


def tipos():
    t = ale.tipos_base()
    obj = lambda c: BEL.get_object_reference_type(c.static_class())
    t.update({"text": BEL.get_basic_type_by_name("text"), "key": BEL.get_struct_type(unreal.Key.static_struct()),
              "ia": obj(unreal.InputAction), "imc": obj(unreal.InputMappingContext), "pc": obj(unreal.PlayerController), "uw": obj(unreal.UserWidget),
              "panel": obj(unreal.PanelWidget), "tex": obj(unreal.Texture2D), "puid": BEL.get_struct_type(unreal.PlatformUserId.static_struct()),
              "idid": BEL.get_struct_type(unreal.InputDeviceId.static_struct())})
    return t


def nova_funcao(bp, nome, entradas, saidas, t, me):
    if nome in [str(x) for x in BEL.list_graph_names(bp)]:
        raise Aborta("%s ja tem a funcao %s (estado incompleto: rode desfazer)" % (bp.get_name(), nome))
    fe = BGE.create_and_edit_function_graph(bp, nome)
    if fe.get_graph().get_name() != nome:
        raise Aborta("grafo %s criado como %s" % (nome, fe.get_graph().get_name()))
    for pn, pt in entradas:
        fe.add_graph_input_parameter(pn, t[pt])
    for pn, pt in saidas:
        fe.add_graph_output_parameter(pn, t[pt])
    en = fe.find_graph_entry_pin().get_owning_node()
    ret = next((n for n in fe.list_all_nodes() if "FunctionResult" in n.get_class().get_name()), None)
    return B(fe, me), en, ret, fe


def compila(bp, rotulo):
    BEL.compile_blueprint(bp)
    e = ale.erros_bp(bp)
    if e:
        raise Aborta("%s compilou com erros/avisos: %s" % (rotulo, e))
    w("  %s compilado limpo" % rotulo)


def sel_str(b, a, bb, cond):
    """SelectString: A se cond, senao B (a/bb: texto literal ou (no, pino))"""
    n = b.c(KML + "SelectString")
    for pino, v in (("A", a), ("B", bb)):
        if isinstance(v, tuple):
            b.lk(v, n, pino)
        else:
            b.g.val(n, pino, v)
    b.lk(cond, n, "bPickA")
    return (n, "ReturnValue")


def igual(b, a, v):
    n = b.c(STR + "EqualEqual_StrStr")
    b.lk(a, n, "A")
    if isinstance(v, tuple):
        b.lk(v, n, "B")
    else:
        b.g.val(n, "B", v)
    return (n, "ReturnValue")


def tecla(nome):
    k = unreal.Key()
    k.set_editor_property("key_name", nome)
    return k


# ------------------------------------------------------------------ 1) dados: PDA_LuxGlifos + DA_LuxGlifos
def ensure_glifos():
    at = unreal.AssetToolsHelpers.get_asset_tools()
    if not EAL.does_directory_exist(DIR):
        EAL.make_directory(DIR)
    if not EAL.does_asset_exist(PDA):
        pda = BEL.create_blueprint_asset_with_parent(PDA, unreal.PrimaryDataAsset)
        key_t, text_t = BEL.get_struct_type(unreal.Key.static_struct()), BEL.get_basic_type_by_name("text")
        tex_t = BEL.get_object_reference_type(unreal.Texture2D.static_class())
        for nome, vt in (("RotulosXbox", text_t), ("RotulosPlayStation", text_t), ("IconesXbox", tex_t), ("IconesPlayStation", tex_t), ("IconesTeclado", tex_t)):
            BEL.add_member_variable(pda, nome, BEL.get_map_type(key_t, vt))
            BEL.set_blueprint_variable_instance_editable(pda, nome, True)
            BEL.set_blueprint_variable_category(pda, nome, unreal.Text("LUX Glifos"))
        BEL.compile_blueprint(pda)
        w("criado PDA_LuxGlifos")
    pda = EAL.load_asset(PDA)
    if not EAL.does_asset_exist(DA):
        fac = unreal.DataAssetFactory()
        fac.set_editor_property("data_asset_class", pda.generated_class())
        at.create_asset("DA_LuxGlifos", DIR, pda.generated_class(), fac)
        w("criado DA_LuxGlifos")
    da = EAL.load_asset(DA)
    xb = {tecla(k): unreal.Text(x) for k, x, _ in ROTULOS}
    ps = {tecla(k): unreal.Text(p) for k, _, p in ROTULOS}
    for nome, valor in (("RotulosXbox", xb), ("RotulosPlayStation", ps)):
        atual = da.get_editor_property(nome)
        if len(atual) != len(valor):
            da.set_editor_property(nome, valor)
            w("DA_LuxGlifos.%s: %d rotulos" % (nome, len(valor)))
    return pda, da


# ------------------------------------------------------------------ 2) BPFL_LuxEntrada
def build_classificar(bp, t):
    b, en, ret, fe = nova_funcao(bp, "ClassificarDispositivo", [("InputClassName", "name"), ("HardwareId", "name")], [("Tipo", "string")], t, BPFL_C)
    nomes = []
    for pino in ("InputClassName", "HardwareId"):
        c = b.c(STR + "Conv_NameToString")
        b.lk((en, pino), c, "InName")
        nomes.append((c, "ReturnValue"))
    txt = b.s([nomes[0], "|", nomes[1]])
    low = b.c(STR + "ToLower")
    b.lk(txt, low, "SourceString")
    s = (low, "ReturnValue")

    def tem(sub):
        n = b.c(STR + "Contains")
        b.lk(s, n, "SearchIn")
        b.g.val(n, "Substring", sub)
        return (n, "ReturnValue")

    def algum(subs):
        acc = tem(subs[0])
        for x in subs[1:]:
            acc = b.ou(acc, tem(x))
        return acc

    kbm = algum(["kbm", "windowsapplication", "none|none"])
    ps = algum(["dualsense", "dualshock", "ps5", "ps4", "playstation", "sony"])
    xb = algum(["xinput", "xbox"])
    r = sel_str(b, "TecladoMouse", sel_str(b, "PlayStation", sel_str(b, "Xbox", "Generico", xb), ps), kbm)
    b.lk(r, ret, "Tipo")
    b.ch(en, ret)


def build_tecla_mapeada(bp, t):
    b, en, ret, fe = nova_funcao(bp, "TeclaMapeadaNaAcao", [("Controle", "pc"), ("Tecla", "key"), ("Acao", "ia")], [("bMapeada", "bool")], t, BPFL_C)
    sub = cria_no(fe, "PlayerController", fim="EnhancedInputLocalPlayerSubsystem")
    b.lk((en, "Controle"), sub, "PlayerController")
    q = b.c(EIS + "QueryKeysMappedToAction")
    b.lk((sub, "ReturnValue"), q, "self")
    b.lk((en, "Acao"), q, "Action")
    c = b.contem((q, "ReturnValue"), (en, "Tecla"))
    b.lk(c, ret, "bMapeada")
    b.ch(en, ret)


def ensure_bpfl(t):
    if EAL.does_asset_exist(BPFL):
        w("BPFL_LuxEntrada ja existe: mantido")
        return EAL.load_asset(BPFL)
    bp = BEL.create_blueprint_asset_with_parent(BPFL, unreal.BlueprintFunctionLibrary)
    try:
        build_classificar(bp, t)
        build_tecla_mapeada(bp, t)
        compila(bp, "BPFL_LuxEntrada")
    except BaseException:
        EAL.delete_asset(BPFL)   # nunca deixa BP pela metade
        raise
    return bp


def testa_classificador(bp):
    cdo = unreal.get_default_object(bp.generated_class())
    falhas = []
    for cls, ident, esperado in CASOS:
        r = cdo.call_method("ClassificarDispositivo", (None, unreal.Name(cls), unreal.Name(ident)))   # 1o argumento: world_context (a BPFL de BP ganha esse parametro)
        r = str(r[0] if isinstance(r, (tuple, list)) else r)
        if r != esperado:
            falhas.append("%s/%s -> %s (esperado %s)" % (cls, ident, r, esperado))
    return falhas


# ------------------------------------------------------------------ 3) WB_LuxPausa
def ensure_widget():
    if EAL.does_asset_exist(WBP):
        w("WB_LuxPausa ja existe: mantido")
        return EAL.load_asset(WBP)
    if not EAL.duplicate_asset(SRC_WIDGET, WBP):
        raise Aborta("duplicate_asset falhou")
    bp = EAL.load_asset(WBP)
    caminho = WBP + ".WB_LuxPausa"
    tree = unreal.load_object(None, caminho + ":WidgetTree")
    raiz = unreal.load_object(None, caminho + ":WidgetTree.HorizontalBox")
    if not tree or not raiz:
        raise Aborta("arvore do widget nao encontrada")
    # sem o grafo herdado do clone (referencia variaveis do BP_Player)
    ge = BGE.get_graph_editor_by_name(bp, "EventGraph")
    nos = list(ge.list_all_nodes())
    if nos:
        ge.remove_nodes(nos)
    raiz.clear_children()
    borda = unreal.new_object(unreal.Border, outer=tree, name="Fundo")
    borda.set_editor_property("brush_color", unreal.LinearColor(0.0, 0.0, 0.0, 0.8))
    borda.set_editor_property("horizontal_alignment", unreal.HorizontalAlignment.H_ALIGN_CENTER)
    borda.set_editor_property("vertical_alignment", unreal.VerticalAlignment.V_ALIGN_CENTER)
    slot = raiz.add_child(borda)
    slot.set_editor_property("size", unreal.SlateChildSize(value=1.0, size_rule=unreal.SlateSizeRule.FILL))
    slot.set_editor_property("horizontal_alignment", unreal.HorizontalAlignment.H_ALIGN_FILL)
    slot.set_editor_property("vertical_alignment", unreal.VerticalAlignment.V_ALIGN_FILL)
    txt = unreal.new_object(unreal.TextBlock, outer=tree, name="Texto")
    txt.set_editor_property("text", unreal.Text("PAUSADO"))
    f = txt.get_editor_property("font")
    f.set_editor_property("size", 32)
    txt.set_editor_property("font", f)
    txt.set_editor_property("justification", unreal.TextJustify.CENTER)
    txt.set_editor_property("color_and_opacity", unreal.SlateColor(unreal.LinearColor(0.92, 0.88, 0.80, 1.0)))
    borda.set_content(txt)
    compila(bp, "WB_LuxPausa")
    st = bp.get_editor_property("status")
    if st != unreal.BlueprintStatus.BS_UP_TO_DATE:
        raise Aborta("WB_LuxPausa status %s" % st)
    return bp


# ------------------------------------------------------------------ 4) BP_LuxEntrada (componente)
def vars_comp(da):
    ia = lambda n: EAL.load_asset("/Game/FPMovement/Player/Input/Actions/IA_Interact") if n == "IA_Interact" else EAL.load_asset(DIR + "/" + n)
    return [("VersaoSpec", "int", False, VERSAO),
            ("Glifos", "glifos", True, da),
            ("ContextoEntrada", "imc", True, EAL.load_asset(IMC_LUX)),
            ("AcaoInteragir", "ia", True, ia("IA_Interact")),
            ("AcaoPausa", "ia", True, ia("IA_Pausa")),
            ("AcaoConfirmar", "ia", True, ia("IA_UI_Confirmar")),
            ("AcaoAlternar", "ia", True, ia("IA_UI_Alternar")),
            ("EstiloManual", "string", True, "Auto"),
            ("TipoAtual", "string", False, "TecladoMouse"),
            ("bPausado", "bool", False, False),
            ("WidgetPausa", "uw", False, None),
            ("UltChave", "key", False, None),
            ("bUltAchou", "bool", False, False),
            ("UltRotulo", "text", False, None),
            ("Aux1", "string", False, ""),
            ("Aux2", "string", False, "")]


FUNC_COMP = [  # nome, entradas, saidas
    ("Iniciar", [], []), ("AoMudarDispositivo", [("UserId", "puid"), ("DeviceId", "idid")], []), ("AtualizarTipo", [], []),
    ("ObterChavePreferida", [("Acao", "ia"), ("bGamepad", "bool")], []), ("ObterRotuloAcao", [("Acao", "ia")], []),
    ("TextoNoFilho", [("Painel", "panel"), ("Indice", "int"), ("Texto", "text")], []), ("AtualizarPrompts", [], []),
    ("AtualizarTextoPausa", [], []), ("Pausar", [], []), ("Retomar", [], []), ("AlternarPausa", [], []), ("AlternarEstilo", [], []),
]


def sub_pc(b, fe):
    """(no do subsistema do Enhanced Input do jogador 0)"""
    gpc = b.c(GS + "GetPlayerController", PlayerIndex=0)
    sub = cria_no(fe, "PlayerController", fim="EnhancedInputLocalPlayerSubsystem")
    b.lk((gpc, "ReturnValue"), sub, "PlayerController")
    return (sub, "ReturnValue"), (gpc, "ReturnValue")


def delegado_dispositivo(b, fe, bind_fim):
    """Bind/Unbind em OnInputHardwareDeviceChanged com um Create Event para AoMudarDispositivo"""
    dev = cria_no(fe, "InputDeviceSubsystem", sem=("Cast", "Class"), fim="InputDeviceSubsystem")
    n = cria_no(fe, fim=bind_fim)
    b.lk((dev, "ReturnValue"), n, "self")
    cd = cria_no(fe, fim="CriarEvento")
    b.lk((cd, "OutputDelegate"), n, "Delegate")
    BEL.set_create_delegate_function(cd, "AoMudarDispositivo")
    if str(BEL.get_create_delegate_function(cd)) != "AoMudarDispositivo":
        raise Aborta("Create Event sem a funcao AoMudarDispositivo")
    return n


def build_comp(bp, t):
    me = COMP_C
    # --- funcoes
    b, en, _, fe = nova_funcao(bp, "AoMudarDispositivo", [("UserId", "puid"), ("DeviceId", "idid")], [], t, me)
    c = b.call("AtualizarTipo")
    b.ch(en, c)

    # AtualizarTipo: dispositivo mais recente -> tipo (BPFL) -> aplica o estilo manual -> se mudou, atualiza os prompts
    b, en, _, fe = nova_funcao(bp, "AtualizarTipo", [], [], t, me)
    dev = cria_no(fe, "InputDeviceSubsystem", sem=("Cast", "Class"), fim="InputDeviceSubsystem")
    pu = b.c("/Script/Engine.InputDeviceLibrary:GetPrimaryPlatformUser")
    mru = b.c("/Script/Engine.InputDeviceSubsystem:GetMostRecentlyUsedHardwareDevice")
    b.lk((dev, "ReturnValue"), mru, "self")
    b.lk((pu, "ReturnValue"), mru, "InUserId")
    brk = cria_no(fe, fim="BreakHardwareDeviceIdentifier")
    b.lk((mru, "ReturnValue"), brk, "HardwareDeviceIdentifier")
    cl = b.c(BPFL_C + ":ClassificarDispositivo")
    b.lk((brk, "InputClassName"), cl, "InputClassName")
    b.lk((brk, "HardwareDeviceIdentifier"), cl, "HardwareId")
    bruto = (cl, "Tipo")
    manual_off = b.ou(igual(b, b.v("EstiloManual"), "Auto"), igual(b, bruto, "TecladoMouse"))
    efetivo = sel_str(b, bruto, b.v("EstiloManual"), manual_off)
    mudou = b.br(b.nao(igual(b, efetivo, b.v("TipoAtual"))))
    st = b.setv("TipoAtual", src=efetivo)
    ap = b.call("AtualizarPrompts")
    b.ch(en, mudou)
    b.ch((mudou, "then"), st, ap)

    # ObterChavePreferida(Acao, bGamepad): UltChave/bUltAchou = primeira tecla da acao da categoria pedida (gamepad ou teclado/mouse)
    b, en, _, fe = nova_funcao(bp, "ObterChavePreferida", [("Acao", "ia"), ("bGamepad", "bool")], [], t, me)
    s0 = b.setv("bUltAchou", "false")
    sub, _pc = sub_pc(b, fe)
    q = b.c(EIS + "QueryKeysMappedToAction")
    b.lk(sub, q, "self")
    b.lk((en, "Acao"), q, "Action")
    loop = b.g.pos(fe.add_macro_node(MAC + "ForEachLoopWithBreak"), 600, 0)
    b.lk((q, "ReturnValue"), loop, "Array")
    isg = b.c(KIL + "Key_IsGamepadKey")
    b.lk((loop, "Array Element"), isg, "Key")
    br = b.br(b.op("EqualEqual_BoolBool", (isg, "ReturnValue"), (en, "bGamepad")))
    s1 = b.setv("UltChave", src=(loop, "Array Element"))
    s2 = b.setv("bUltAchou", "true")
    b.ch(en, s0, loop)
    b.ch((loop, "LoopBody"), br)
    b.ch((br, "then"), s1, s2)
    b.g.link(s2, "then", loop, "Break")

    # ObterRotuloAcao(Acao): UltRotulo = rotulo da tecla da acao para o dispositivo atual (teclado: nome da tecla; gamepad: DA_LuxGlifos)
    b, en, _, fe = nova_funcao(bp, "ObterRotuloAcao", [("Acao", "ia")], [], t, me)
    pad = b.nao(igual(b, b.v("TipoAtual"), "TecladoMouse"))
    c1 = b.call("ObterChavePreferida")
    b.lk((en, "Acao"), c1, "Acao")
    b.lk(pad, c1, "bGamepad")
    achou = b.br(b.v("bUltAchou"))
    c2 = b.call("ObterChavePreferida")
    b.lk((en, "Acao"), c2, "Acao")
    b.lk(b.nao(pad), c2, "bGamepad")
    j = ale.junc(b)
    final = b.br(b.v("bUltAchou"))

    def nome_tecla():
        n = b.c(KIL + "Key_GetDisplayName")
        b.lk(b.v("UltChave"), n, "Key")
        return b.setv("UltRotulo", src=(n, "ReturnValue"))

    def do_mapa(var):
        mapa = b.g.get(var, 0, 0, PDA_C)
        b.lk(b.v("Glifos"), mapa, "self") if False else b.g.link(b.v("Glifos")[0], "Glifos", mapa, "self")
        f = b.c(MAPL + "Map_Find")
        b.lk((mapa, var), f, "TargetMap")
        b.lk(b.v("UltChave"), f, "Key")
        return f

    nao_achou = b.setv("UltRotulo", None)
    b.g.val(nao_achou, "UltRotulo", "?")
    ehg = b.c(KIL + "Key_IsGamepadKey")
    b.lk(b.v("UltChave"), ehg, "Key")
    br_gp = b.br((ehg, "ReturnValue"))
    br_val = b.br(b.valido(b.v("Glifos")))
    br_ps = b.br(igual(b, b.v("TipoAtual"), "PlayStation"))
    f_ps, f_xb = do_mapa("RotulosPlayStation"), do_mapa("RotulosXbox")
    br_fps, br_fxb = b.br((f_ps, "ReturnValue")), b.br((f_xb, "ReturnValue"))
    set_ps = b.setv("UltRotulo", src=(f_ps, "Value"))
    set_xb = b.setv("UltRotulo", src=(f_xb, "Value"))
    b.ch(en, c1, achou)
    b.ch((achou, "then"), j)
    b.ch((achou, "else"), c2, j)
    b.ch(j, final)
    b.ch((final, "else"), nao_achou)
    b.ch((final, "then"), br_gp)
    b.ch((br_gp, "else"), nome_tecla())
    b.ch((br_gp, "then"), br_val)
    b.ch((br_val, "else"), nome_tecla())
    b.ch((br_val, "then"), br_ps)
    b.ch((br_ps, "then"), br_fps)
    b.ch((br_ps, "else"), br_fxb)
    b.ch((br_fps, "then"), set_ps)
    b.ch((br_fps, "else"), nome_tecla())
    b.ch((br_fxb, "then"), set_xb)
    b.ch((br_fxb, "else"), nome_tecla())

    # TextoNoFilho(Painel, Indice, Texto): Painel[Indice] (Border) -> conteudo (TextBlock) -> SetText. Os widgets do pack nao sao variaveis.
    b, en, _, fe = nova_funcao(bp, "TextoNoFilho", [("Painel", "panel"), ("Indice", "int"), ("Texto", "text")], [], t, me)
    gc = b.c("/Script/UMG.PanelWidget:GetChildAt")
    b.lk((en, "Painel"), gc, "self")
    b.lk((en, "Indice"), gc, "Index")
    cb = cria_no(fe, fim="CastToBorder")
    b.lk((gc, "ReturnValue"), cb, "Object")
    cont = b.c("/Script/UMG.ContentWidget:GetContent")
    b.lk((cb, pino_cast(cb)), cont, "self")
    ct = cria_no(fe, fim="CastToTextBlock")
    b.lk((cont, "ReturnValue"), ct, "Object")
    stx = b.c("/Script/UMG.TextBlock:SetText")
    b.lk((ct, pino_cast(ct)), stx, "self")
    b.lk((en, "Texto"), stx, "InText")
    b.ch(en, cb)
    b.ch((cb, "then"), ct)
    b.ch((ct, "then"), stx)

    # AtualizarPrompts: rotulo da tecla de interagir em todo WP_Interaction (o HUD tem mais de uma instancia) + texto da pausa
    b, en, _, fe = nova_funcao(bp, "AtualizarPrompts", [], [], t, me)
    r1 = b.call("ObterRotuloAcao")
    b.lk(b.v("AcaoInteragir"), r1, "Acao")
    gaw = b.c("/Script/UMG.WidgetBlueprintLibrary:GetAllWidgetsOfClass", WidgetClass=WPI_C, TopLevelOnly="false")
    loop = b.g.pos(fe.add_macro_node(MAC + "ForEachLoop"), 700, 0)
    b.lk((gaw, "FoundWidgets"), loop, "Array")
    cw = cria_no(fe, fim="CastToWP_Interaction")
    b.lk((loop, "Array Element"), cw, "Object")
    hb = b.g.get("HorizontalBox", 0, 0, WPI_C)
    b.g.link(cw, pino_cast(cw), hb, "self")
    tx = b.call("TextoNoFilho", Indice=0)
    b.lk((hb, "HorizontalBox"), tx, "Painel")
    b.lk(b.v("UltRotulo"), tx, "Texto")
    r2 = b.call("AtualizarTextoPausa")
    b.ch(en, r1, gaw, loop)
    b.ch((loop, "LoopBody"), cw)
    b.ch((cw, "then"), tx)
    b.ch((loop, "Completed"), r2)

    # AtualizarTextoPausa: "PAUSADO [confirmar] ou [pausa] Continuar" + (com controle) "[alternar] Icones: estilo"
    b, en, _, fe = nova_funcao(bp, "AtualizarTextoPausa", [], [], t, me)
    ok = b.br(b.valido(b.v("WidgetPausa")))
    ca = b.call("ObterRotuloAcao")
    b.lk(b.v("AcaoConfirmar"), ca, "Acao")
    s_a1 = b.setv("Aux1", src=(b.c(TXT + "Conv_TextToString"), "ReturnValue"))
    # (o no de conversao precisa da origem: refaz ligando)
    conv1 = s_a1.find_input_pin("Aux1").get_linked_to()[0].get_owning_node() if False else None
    raise Aborta("rascunho: AtualizarTextoPausa sera finalizado na proxima iteracao")


def ensure_comp(t, da):
    raise Aborta("rascunho")


def main():
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    open(LOG, "w", encoding="utf-8").close()
    modo = next((a for a in sys.argv[1:] if a in ("sondar", "instalar", "verificar", "desfazer")), "sondar")
    etapas = [a for a in sys.argv[1:] if a in ("glifos", "bpfl", "widget", "comp", "cowboy")] or ["glifos", "bpfl", "widget", "comp", "cowboy"]
    w("modo:", modo, etapas)
    try:
        if modo == "instalar":
            t = tipos()
            if "glifos" in etapas:
                ensure_glifos()
            if "bpfl" in etapas:
                bp = ensure_bpfl(t)
                f = testa_classificador(bp)
                w("classificador:", ("FAIL %s" % f) if f else "PASS (%d casos)" % len(CASOS))
                if f:
                    raise Aborta("classificador reprovado")
            if "widget" in etapas:
                ensure_widget()
    except Aborta as ex:
        w("ABORTADO:", ex, "| sujos:", ale.sujos())
    except Exception:
        w("ERRO " + traceback.format_exc(), "| sujos:", ale.sujos())


if __name__ == "__main__":
    main()
