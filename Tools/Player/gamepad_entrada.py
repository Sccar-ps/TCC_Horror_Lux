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


def erros(bp):
    """erros e avisos de todos os grafos, com a mensagem do compilador"""
    out = []
    for gname in [str(x) for x in BEL.list_graph_names(bp)]:
        try:
            ge = BGE.get_graph_editor_by_name(bp, gname)
        except Exception:
            continue
        for tipo, lst in (("ERRO", ge.list_nodes_with_errors()), ("aviso", ge.list_nodes_with_warnings())):
            for n in lst:
                try:
                    msg = str(n.get_editor_property("error_msg"))
                except Exception:
                    msg = "?"
                out.append("%s em %s: %s | %s" % (tipo, gname, str(n.get_node_title()).replace("\n", " "), msg))
    return out


def compila(bp, rotulo):
    BEL.compile_blueprint(bp)
    e = erros(bp)
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
    fe.set_is_pure_function(True)
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
    fe.set_is_pure_function(True)
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
        r = None
        for extra in ({"world_context": None}, {}):   # a BPFL de BP ganha um parametro world_context (a posicao muda entre sessao e disco): por nome
            try:
                r = cdo.call_method("ClassificarDispositivo", kwargs=dict({"input_class_name": unreal.Name(cls), "hardware_id": unreal.Name(ident)}, **extra))
                break
            except TypeError:
                continue
        if r is None:
            raise Aborta("nao consegui chamar ClassificarDispositivo pelo Python")
        r = str(r[0] if isinstance(r, (tuple, list)) else r)
        if r != esperado:
            falhas.append("%s/%s -> %s (esperado %s)" % (cls, ident, r, esperado))
    return falhas


# ------------------------------------------------------------------ 3) WB_LuxPausa
def mk(cls, **props):
    """struct do UE com valores (os structs de UMG nao aceitam kwargs no construtor)"""
    o = cls()
    for k, v in props.items():
        o.set_editor_property(k, v)
    return o


def ensure_widget():
    """Clona o WB_InteractDot do pack (sem referenciadores) e REAPROVEITA os widgets que ele ja tem (HorizontalBox > [Border > TextBlock] x2):
    o Border da esquerda vira o fundo escuro da tela inteira com o texto da pausa (filho 0, o mesmo caminho do prompt do HUD: TextoNoFilho(HorizontalBox, 0, ...)),
    o da direita some. NAO cria widget novo: widget criado por new_object nao ganha GUID no WidgetBlueprint e derruba o compilador do UMG (crash 01/10)."""
    if EAL.does_asset_exist(WBP):
        w("WB_LuxPausa ja existe: mantido")
        return EAL.load_asset(WBP)
    if not EAL.duplicate_asset(SRC_WIDGET, WBP):
        raise Aborta("duplicate_asset falhou")
    bp = EAL.load_asset(WBP)
    try:
        caminho = WBP + ".WB_LuxPausa"
        raiz = unreal.load_object(None, caminho + ":WidgetTree.HorizontalBox")
        if not raiz or raiz.get_children_count() != 2:
            raise Aborta("arvore do clone diferente do esperado (HorizontalBox com 2 filhos)")
        # sem o grafo herdado do clone (referencia variaveis do BP_Player e quebra a compilacao)
        ge = BGE.get_graph_editor_by_name(bp, "EventGraph")
        nos = list(ge.list_all_nodes())
        if nos:
            ge.remove_nodes(nos)
        # a raiz do clone e um CanvasPanel e o HorizontalBox e filho dele: ancora na tela inteira
        cs = raiz.get_editor_property("slot")
        cs.set_anchors(mk(unreal.Anchors, minimum=unreal.Vector2D(0.0, 0.0), maximum=unreal.Vector2D(1.0, 1.0)))
        cs.set_offsets(mk(unreal.Margin, left=0.0, top=0.0, right=0.0, bottom=0.0))
        cs.set_auto_size(False)
        cs.set_alignment(unreal.Vector2D(0.0, 0.0))
        fundo, lado = raiz.get_child_at(0), raiz.get_child_at(1)
        fundo.set_editor_property("brush_color", unreal.LinearColor(0.0, 0.0, 0.0, 0.82))
        fundo.set_editor_property("padding", mk(unreal.Margin, left=40.0, top=40.0, right=40.0, bottom=40.0))
        fundo.set_editor_property("horizontal_alignment", unreal.HorizontalAlignment.H_ALIGN_CENTER)
        fundo.set_editor_property("vertical_alignment", unreal.VerticalAlignment.V_ALIGN_CENTER)
        sl = fundo.get_editor_property("slot")
        sl.set_size(mk(unreal.SlateChildSize, value=1.0, size_rule=unreal.SlateSizeRule.FILL))
        sl.set_horizontal_alignment(unreal.HorizontalAlignment.H_ALIGN_FILL)
        sl.set_vertical_alignment(unreal.VerticalAlignment.V_ALIGN_FILL)
        sl.set_padding(mk(unreal.Margin, left=0.0, top=0.0, right=0.0, bottom=0.0))
        lado.set_editor_property("visibility", unreal.SlateVisibility.COLLAPSED)
        txt = fundo.get_content()
        txt.set_editor_property("text", unreal.Text("PAUSADO"))
        f = txt.get_editor_property("font")
        f.set_editor_property("size", 30)
        txt.set_editor_property("font", f)
        txt.set_editor_property("justification", unreal.TextJustify.CENTER)
        txt.set_editor_property("color_and_opacity", unreal.SlateColor())
        sc = txt.get_editor_property("color_and_opacity")
        sc.set_editor_property("specified_color", unreal.LinearColor(0.92, 0.88, 0.80, 1.0))
        txt.set_editor_property("color_and_opacity", sc)
        compila(bp, "WB_LuxPausa")
        st = bp.get_editor_property("status")
        if st != unreal.BlueprintStatus.BS_UP_TO_DATE:
            raise Aborta("WB_LuxPausa status %s" % st)
    except BaseException:
        EAL.delete_asset(WBP)   # nunca deixa widget pela metade
        raise
    return bp


# ------------------------------------------------------------------ 4) BP_LuxEntrada (componente)
def vars_comp(da):
    ia = lambda n: EAL.load_asset((IA_INTERACT if n == "IA_Interact" else DIR + "/" + n))
    return [("VersaoSpec", "int", False, VERSAO),
            ("Glifos", "glifos", True, da),
            ("ContextoEntrada", "imc", True, EAL.load_asset(IMC_LUX)),
            ("AcaoInteragir", "ia", True, ia("IA_Interact")),
            ("AcaoPausa", "ia", True, ia("IA_Pausa")),
            ("AcaoConfirmar", "ia", True, ia("IA_UI_Confirmar")),
            ("AcaoAlternar", "ia", True, ia("IA_UI_Alternar")),
            ("EstiloManual", "string", True, "Auto"),
            ("ForcarTipo", "string", True, "Auto"),
            ("TipoAtual", "string", False, "TecladoMouse"),
            ("bPausado", "bool", False, False),
            ("WidgetPausa", "uw", False, None),
            ("UltChave", "key", False, None),
            ("bUltAchou", "bool", False, False),
            ("UltRotulo", "text", False, None),
            ("Aux1", "string", False, ""),
            ("Aux2", "string", False, "")]


FUNC_COMP = [  # nome, entradas
    ("Iniciar", []), ("AoMudarDispositivo", [("UserId", "puid"), ("DeviceId", "idid")]), ("AtualizarTipo", []),
    ("ObterChavePreferida", [("Acao", "ia"), ("bGamepad", "bool")]), ("ObterRotuloAcao", [("Acao", "ia")]),
    ("TextoNoFilho", [("Painel", "panel"), ("Indice", "int"), ("Texto", "text")]), ("AtualizarPrompts", []),
    ("AtualizarTextoPausa", []), ("Pausar", []), ("Retomar", []), ("AlternarPausa", []), ("AlternarEstilo", []),
]


def abre(bp, nome):
    fe = BGE.get_graph_editor_by_name(bp, nome)
    return B(fe, COMP_C), fe.find_graph_entry_pin().get_owning_node(), fe


def sub_pc(b, fe):
    """(subsistema do Enhanced Input do jogador 0, controle)"""
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


def f_ao_mudar(bp):
    b, en, fe = abre(bp, "AoMudarDispositivo")
    b.ch(en, b.call("AtualizarTipo"))


def f_atualizar_tipo(bp):
    """dispositivo mais recente -> tipo (BPFL) -> estilo manual -> se mudou, atualiza os prompts"""
    b, en, fe = abre(bp, "AtualizarTipo")
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
    # ForcarTipo (QA sem controle fisico): finge o dispositivo detectado (TecladoMouse/Xbox/PlayStation/Generico); "Auto" = o do hardware
    bruto = sel_str(b, (cl, "Tipo"), b.v("ForcarTipo"), igual(b, b.v("ForcarTipo"), "Auto"))
    sem_manual = b.ou(igual(b, b.v("EstiloManual"), "Auto"), igual(b, bruto, "TecladoMouse"))
    efetivo = sel_str(b, bruto, b.v("EstiloManual"), sem_manual)
    mudou = b.br(b.nao(igual(b, efetivo, b.v("TipoAtual"))))
    st = b.setv("TipoAtual", src=efetivo)
    ap = b.call("AtualizarPrompts")
    b.ch(en, mudou)
    b.ch((mudou, "then"), st, ap)


def f_chave_preferida(bp):
    """UltChave/bUltAchou = primeira tecla da acao na categoria pedida (gamepad ou teclado/mouse)"""
    b, en, fe = abre(bp, "ObterChavePreferida")
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


def f_rotulo_acao(bp):
    """UltRotulo = rotulo da tecla da acao para o dispositivo atual (teclado/mouse: nome da tecla; gamepad: DA_LuxGlifos, com o nome da tecla de reserva)"""
    b, en, fe = abre(bp, "ObterRotuloAcao")
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

    def busca(var):
        mapa = b.g.get(var, 0, 0, PDA_C)
        gl = b.v("Glifos")
        b.g.link(gl[0], "Glifos", mapa, "self")
        f = b.c(MAPL + "Map_Find")
        b.lk((mapa, var), f, "TargetMap")
        b.lk(b.v("UltChave"), f, "Key")
        return f

    nao_achou = b.setv("UltRotulo", "?")
    ehg = b.c(KIL + "Key_IsGamepadKey")
    b.lk(b.v("UltChave"), ehg, "Key")
    br_gp = b.br((ehg, "ReturnValue"))
    br_val = b.br(b.valido(b.v("Glifos")))
    br_ps = b.br(igual(b, b.v("TipoAtual"), "PlayStation"))
    f_ps, f_xb = busca("RotulosPlayStation"), busca("RotulosXbox")
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


def f_texto_no_filho(bp):
    """Painel[Indice] (Border) -> conteudo (TextBlock) -> SetText. Os widgets do pack nao sao variaveis, so a raiz."""
    b, en, fe = abre(bp, "TextoNoFilho")
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


def f_atualizar_prompts(bp):
    """rotulo da tecla de interagir em todo WP_Interaction (o HUD tem mais de uma instancia) e o texto da pausa"""
    b, en, fe = abre(bp, "AtualizarPrompts")
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


def f_texto_pausa(bp):
    """PAUSADO / [confirmar] ou [pausa] Continuar / (so com controle) [alternar] Icones: estilo"""
    b, en, fe = abre(bp, "AtualizarTextoPausa")
    ok = b.br(b.valido(b.v("WidgetPausa")))
    passos = []
    for acao, aux in (("AcaoConfirmar", "Aux1"), ("AcaoPausa", "Aux2")):
        c = b.call("ObterRotuloAcao")
        b.lk(b.v(acao), c, "Acao")
        t2s = b.c(TXT + "Conv_TextToString")
        b.lk(b.v("UltRotulo"), t2s, "InText")
        passos += [c, b.setv(aux, src=(t2s, "ReturnValue"))]
    cx = b.call("ObterRotuloAcao")
    b.lk(b.v("AcaoAlternar"), cx, "Acao")
    t2s_x = b.c(TXT + "Conv_TextToString")
    b.lk(b.v("UltRotulo"), t2s_x, "InText")
    pad = b.nao(igual(b, b.v("TipoAtual"), "TecladoMouse"))
    estilo = sel_str(b, b.s(["Auto (", b.v("TipoAtual"), ")"]), b.v("EstiloManual"), igual(b, b.v("EstiloManual"), "Auto"))
    extra = sel_str(b, b.s(["\n[", (t2s_x, "ReturnValue"), "] Ícones: ", estilo]), "", pad)
    txt = b.s(["PAUSADO\n\n[", b.v("Aux1"), "] ou [", b.v("Aux2"), "] Continuar", extra])
    conv = b.c(TXT + "Conv_StringToText")
    b.lk(txt, conv, "InString")
    cw = cria_no(fe, fim="CastToWB_LuxPausa")
    b.lk(b.v("WidgetPausa"), cw, "Object")
    hb = b.g.get("HorizontalBox", 0, 0, WBP_C)
    b.g.link(cw, pino_cast(cw), hb, "self")
    tx = b.call("TextoNoFilho", Indice=0)
    b.lk((hb, "HorizontalBox"), tx, "Painel")
    b.lk((conv, "ReturnValue"), tx, "Texto")
    b.ch(en, ok)
    b.ch((ok, "then"), *passos, cx, cw)
    b.ch((cw, "then"), tx)


def f_pausar(bp):
    b, en, fe = abre(bp, "Pausar")
    pode = b.br(b.nao((b.c(GS + "IsGamePaused"), "ReturnValue")))   # nao pausa por cima de outra pausa (ex.: janela de nota)
    sp = b.setv("bPausado", "true")
    gpc = b.c(GS + "GetPlayerController", PlayerIndex=0)
    tem = b.br(b.valido(b.v("WidgetPausa")))
    cr = cria_no(fe, fim="CriarWidget")
    b.g.val(cr, "Class", WBP_C)
    b.lk((gpc, "ReturnValue"), cr, "OwningPlayer")
    sw = b.setv("WidgetPausa", src=(cr, "ReturnValue"))
    j = ale.junc(b)
    av = b.c("/Script/UMG.UserWidget:AddToViewport", ZOrder=100)
    b.lk(b.v("WidgetPausa"), av, "self")
    at = b.call("AtualizarTextoPausa")
    gp = b.c(GS + "SetGamePaused", bPaused="true")
    b.ch(en, pode)
    b.ch((pode, "then"), sp, tem)
    b.ch((tem, "then"), j)
    b.ch((tem, "else"), cr, sw, j)
    b.ch(j, av, at, gp)


def f_retomar(bp):
    """Devolve o jogo da pausa. Nao ha mais RequestRebuildControlMappings aqui: ele nao fazia nada pelas teclas apertadas (o motor so ignora tecla apertada
    em mapeamento NOVO; os que ja existiam voltam com o estado dos gatilhos). O que impede A/B de virarem Interagir/Agachar ao fechar a pausa e a pausa
    fechar ao SOLTAR (IA_UI_Confirmar/IA_UI_Voltar com gatilho Released, evento Triggered; ver f_eventos e gamepad_input.py)."""
    b, en, fe = abre(bp, "Retomar")
    pode = b.br(b.v("bPausado"))
    s0 = b.setv("bPausado", "false")
    gp = b.c(GS + "SetGamePaused", bPaused="false")
    tem = b.br(b.valido(b.v("WidgetPausa")))
    rm = b.c("/Script/UMG.Widget:RemoveFromParent")
    b.lk(b.v("WidgetPausa"), rm, "self")
    b.ch(en, pode)
    b.ch((pode, "then"), s0, gp, tem)
    b.ch((tem, "then"), rm)


def f_alternar_pausa(bp):
    b, en, fe = abre(bp, "AlternarPausa")
    br = b.br(b.v("bPausado"))
    b.ch(en, br)
    b.ch((br, "then"), b.call("Retomar"))
    b.ch((br, "else"), b.call("Pausar"))


def f_alternar_estilo(bp):
    """Auto -> Xbox -> PlayStation -> Auto"""
    b, en, fe = abre(bp, "AlternarEstilo")
    prox = sel_str(b, "Xbox", sel_str(b, "PlayStation", "Auto", igual(b, b.v("EstiloManual"), "Xbox")), igual(b, b.v("EstiloManual"), "Auto"))
    s = b.setv("EstiloManual", src=prox)
    b.ch(en, s, b.call("AtualizarTipo"), b.call("AtualizarPrompts"))


def f_iniciar(bp):
    b, en, fe = abre(bp, "Iniciar")
    sub, _pc = sub_pc(b, fe)
    v = b.br(b.valido(sub))
    add = b.c(EIS + "AddMappingContext", Priority=1, Options=OPCOES)
    b.lk(sub, add, "self")
    b.lk(b.v("ContextoEntrada"), add, "MappingContext")
    bind = delegado_dispositivo(b, fe, "BindEventtoOnInputHardwareDeviceChanged")
    at = b.call("AtualizarTipo")
    tm = b.timer("AtualizarPrompts", 3.0, loop=True)   # rede de seguranca: o HUD pode ser recriado
    b.g.val(tm, "InitialStartDelay", 0.5)               # e o primeiro rotulo sai logo depois do HUD nascer
    b.ch(en, v)
    b.ch((v, "then"), add, bind, at, tm)


def f_eventos(bp):
    ge = BGE.get_graph_editor_by_name(bp, "EventGraph")
    b = B(ge, COMP_C)
    # D06 (sem Tick): o BP de componente nasce com um "Event Tick" solto; sai do grafo
    for n in list(ge.list_all_nodes()):
        if "Tick" in str(n.get_node_title()) and not any(p.list_connected_pins() for p in n.list_output_pins()):
            ge.remove_nodes([n])
    # BeginPlay -> Iniciar
    bg = BEL.add_event_override(bp, "ReceiveBeginPlay", unreal.IntPoint(0, 0))
    b.ch(bg, b.call("Iniciar"))
    # EndPlay: solta o delegate e devolve o jogo da pausa. O IMC_LuxEntrada FICA registrado (nao e removido): ele tambem e contexto padrao do projeto
    # (Config/DefaultInput.ini) e o bilhete (WB_Note) pergunta a ele a que acao cada tecla pertence; remover aqui o tiraria de um mapa sem o componente.
    ep = BEL.add_event_override(bp, "ReceiveEndPlay", unreal.IntPoint(0, 400))
    un = delegado_dispositivo(b, ge, "UnbindEventfromOnInputHardwareDeviceChanged")
    pz = b.br(b.v("bPausado"))
    b.ch(ep, un, pz)
    b.ch((pz, "then"), b.call("Retomar"))

    def evento_ia(nome, y):
        return cria_no(ge, fim="EnhancedActionEvents|" + nome, x=0, y=y)

    e = evento_ia("IA_Pausa", 900)
    c = b.call("AlternarPausa")
    b.g.link(e, "Started", c, b.g.exec_in(c))
    # Voltar e Confirmar (B/A) agem ao SOLTAR: o gatilho da acao e Released e o evento e o Triggered (ver gamepad_input.py); Alternar age ao apertar (Started)
    for i, (nome, fn, pino) in enumerate((("IA_UI_Voltar", "Retomar", "Triggered"), ("IA_UI_Confirmar", "Retomar", "Triggered"), ("IA_UI_Alternar", "AlternarEstilo", "Started"))):
        e = evento_ia(nome, 1300 + i * 400)
        g = b.br(b.v("bPausado"))
        c = b.call(fn)
        b.g.link(e, pino, g, b.g.exec_in(g))
        b.ch((g, "then"), c)


def ensure_comp(t, da):
    if EAL.does_asset_exist(COMP):
        w("BP_LuxEntrada ja existe: mantido")
        return EAL.load_asset(COMP)
    wpi = EAL.load_asset(WPI)   # o no "Cast To WP_Interaction" so entra na paleta depois que o widget e carregado e compilado (o commandlet nasce sem ele)
    if not wpi:
        raise Aborta("WP_Interaction nao encontrado: " + WPI)
    BEL.compile_blueprint(wpi)   # so em memoria: este script nunca salva o widget do pack
    if erros(wpi):
        raise Aborta("WP_Interaction compila com erros antes de qualquer mudanca: %s" % erros(wpi))
    bp = BEL.create_blueprint_asset_with_parent(COMP, unreal.ActorComponent)
    try:
        t = dict(t)
        t["glifos"] = BEL.get_object_reference_type(EAL.load_asset(PDA).generated_class())
        lista = vars_comp(da)
        ale.cria_vars(bp, lista, t, "LUX Entrada")
        BEL.compile_blueprint(bp)
        ale.padroes(bp, lista)
        ale.cria_funcoes(bp, [(n, e) for n, e in FUNC_COMP], t)
        BEL.compile_blueprint(bp)
        for f in (f_ao_mudar, f_atualizar_tipo, f_chave_preferida, f_rotulo_acao, f_texto_no_filho, f_atualizar_prompts, f_texto_pausa, f_pausar,
                  f_retomar, f_alternar_pausa, f_alternar_estilo, f_iniciar, f_eventos):
            f(bp)
        BEL.compile_blueprint(bp)
        BEL.compile_blueprint(bp)
        compila(bp, "BP_LuxEntrada")
    except BaseException:
        EAL.delete_asset(COMP)
        raise
    return bp


# ------------------------------------------------------------------ 4b) API publica do componente
def f_definir(bp):
    b, en, fe = abre(bp, "DefinirEstilo")
    b.ch(en, b.setv("EstiloManual", src=(en, "Estilo")), b.call("AtualizarTipo"), b.call("AtualizarPrompts"))
    b, en, fe = abre(bp, "DefinirTipoForcado")
    b.ch(en, b.setv("ForcarTipo", src=(en, "Tipo")), b.call("AtualizarTipo"), b.call("AtualizarPrompts"))


def tira_remocao_do_imc(bp):
    """BP ja instalado antes desta decisao: o EndPlay deixa de remover o IMC_LuxEntrada (idempotente)"""
    ge = BGE.get_graph_editor_by_name(bp, "EventGraph")
    rm = [n for n in ge.list_all_nodes() if str(n.get_node_title()).replace("\n", " ").startswith("RemoveMappingContext")]
    if not rm:
        return False
    ge.remove_nodes(rm)
    BEL.compile_blueprint(bp)
    BEL.compile_blueprint(bp)
    compila(bp, "BP_LuxEntrada (EndPlay sem remover o IMC)")
    w("EndPlay do BP_LuxEntrada: remocao do IMC_LuxEntrada retirada")
    return True


def ensure_api(t):
    """DefinirEstilo(Estilo) e DefinirTipoForcado(Tipo): para o futuro menu de opcoes (Auto/Xbox/PlayStation) e para teste sem controle fisico.
    ContTrocasDispositivo: quantas vezes o motor avisou "o dispositivo mudou" (prova de que o delegate chega ao componente).
    No PIE nao se grava variavel do componente por Python (set_editor_property reconstroi o ator e o componente antigo fica orfao)."""
    bp = EAL.load_asset(COMP)
    if not bp:
        raise Aborta("BP_LuxEntrada nao existe: rode instalar comp antes")
    tira_remocao_do_imc(bp)
    existentes = [str(x) for x in BEL.list_graph_names(bp)]
    novas = [(n, e) for n, e in (("DefinirEstilo", [("Estilo", "string")]), ("DefinirTipoForcado", [("Tipo", "string")])) if n not in existentes]
    tem_cont = "ContTrocasDispositivo" in [str(x) for x in BEL.list_member_variable_names(bp)]
    if not novas and tem_cont:
        w("API do componente ja existe: mantida")
        return bp
    if not tem_cont:
        BEL.add_member_variable(bp, "ContTrocasDispositivo", t["int"])
        BEL.set_blueprint_variable_category(bp, "ContTrocasDispositivo", unreal.Text("LUX Entrada|Estado"))
        BEL.compile_blueprint(bp)
    if novas:
        ale.cria_funcoes(bp, novas, t)
        BEL.compile_blueprint(bp)
        f_definir(bp)
    if not tem_cont:
        b, en, fe = abre(bp, "AoMudarDispositivo")
        chamada = next(n for n in fe.list_all_nodes() if str(n.get_node_title()).replace("\n", " ") == "AtualizarTipo")
        en.find_output_pin("then").break_pin_links()
        inc = b.setv("ContTrocasDispositivo", src=b.op("Add_IntInt", b.v("ContTrocasDispositivo"), 1))
        b.ch(en, inc, chamada)
    BEL.compile_blueprint(bp)
    BEL.compile_blueprint(bp)
    compila(bp, "BP_LuxEntrada (API)")
    return bp


def no_evento_ia(ge, nome):
    """os nos 'EnhancedInputAction <nome>' do EventGraph (o titulo traz o nome da acao)"""
    return [n for n in ge.list_all_nodes() if nome in str(n.get_node_title()) and n.find_output_pin("Started") is not None and n.find_output_pin("Triggered") is not None]


def poda_inutil(ge):
    """tira nos sem efeito: Branch sem nenhuma saida ligada e nos puros (getters, IsValid, Obter...) sem nenhuma saida ligada, ate nao sobrar nenhum.
    Nunca toca em evento nem em chamada com efeito (nao tem como ser 'sem saida ligada' e fazer algo: so Branch e puros entram)."""
    total = 0
    while True:
        alvo = []
        for n in ge.list_all_nodes():
            if any(p.list_connected_pins() for p in n.list_output_pins()):
                continue
            tem_exec = any('"exec"' in str(p.get_pin_type_as_json_schema()) for p in list(n.list_input_pins()) + list(n.list_output_pins()))   # evento e chamada com efeito tem pino exec
            titulo = str(n.get_node_title()).replace("\n", " ")
            if (not tem_exec) or titulo in ("Ramo", "Branch"):
                alvo.append(n)
        if not alvo:
            return total
        ge.remove_nodes(alvo)
        total += len(alvo)


def ensure_soltar():
    """BP ja instalado antes desta decisao: (1) IA_UI_Voltar/IA_UI_Confirmar passam do evento Started ao Triggered (a acao tem gatilho Released: o Triggered sai
    ao SOLTAR); (2) o RequestRebuildControlMappings do Retomar sai (nao fazia nada pelas teclas apertadas). Idempotente."""
    bp = EAL.load_asset(COMP)
    if not bp:
        raise Aborta("BP_LuxEntrada nao existe: rode instalar comp antes")
    mudou = False
    ge = BGE.get_graph_editor_by_name(bp, "EventGraph")
    for nome in ("IA_UI_Voltar", "IA_UI_Confirmar"):
        nos = no_evento_ia(ge, nome)
        if len(nos) != 1:
            raise Aborta("esperava 1 no de evento de %s no EventGraph, achei %d" % (nome, len(nos)))
        st, tr = nos[0].find_output_pin("Started"), nos[0].find_output_pin("Triggered")
        alvos = list(st.list_connected_pins())
        if alvos:
            st.break_pin_links()
            for a in alvos:
                if not tr.try_create_connection(a):
                    raise Aborta("nao liguei o Triggered de %s" % nome)
            mudou = True
            w("%s: evento Started -> Triggered (age ao soltar)" % nome)
    fr = BGE.get_graph_editor_by_name(bp, "Retomar")
    rb = [n for n in fr.list_all_nodes() if str(n.get_node_title()).replace("\n", " ").startswith("RequestRebuildControlMappings")]
    if rb:
        # sai o rebuild e o Branch "subsistema valido" que so existia para ele; o resto do Retomar nao muda
        alvo = set(rb)
        for n in fr.list_all_nodes():
            if n.find_input_pin("Condition") is not None and any(p.get_owning_node() in alvo for q in n.list_output_pins() for p in q.list_connected_pins()):
                alvo.add(n)
        fr.remove_nodes(list(alvo))
        mudou = True
        w("Retomar: RequestRebuildControlMappings (e o Branch que o guardava) retirados")
    # o que sobrou de mudancas antigas (a validade do subsistema que so guardava o rebuild; o ramo do EndPlay que so guardava o RemoveMappingContext)
    podados = poda_inutil(fr) + poda_inutil(ge)
    if podados:
        mudou = True
        w("nos sem efeito retirados do Retomar e do EventGraph:", podados)
    if mudou:
        BEL.compile_blueprint(bp)
        BEL.compile_blueprint(bp)
        compila(bp, "BP_LuxEntrada (soltar)")
    else:
        w("BP_LuxEntrada ja age ao soltar: mantido")
    return bp


# ------------------------------------------------------------------ 4c) icones por dispositivo (estrutura pronta; o projeto ainda nao tem texturas de botao)
def f_icone_acao(bp):
    """UltIcone = textura do botao da acao para o dispositivo atual (DA_LuxGlifos: IconesXbox/IconesPlayStation por tecla de gamepad; IconesTeclado por tecla de
    teclado/mouse). None enquanto o DA nao tiver a textura: o widget cai no texto de ObterRotuloAcao. Nenhum widget do pack e tocado."""
    b, en, fe = abre(bp, "ObterIconeAcao")
    limpa = b.setv("UltIcone")
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
    valido = b.br(b.valido(b.v("Glifos")))

    def busca(var):
        mapa = b.g.get(var, 0, 0, PDA_C)
        gl = b.v("Glifos")
        b.g.link(gl[0], "Glifos", mapa, "self")
        f = b.c(MAPL + "Map_Find")
        b.lk((mapa, var), f, "TargetMap")
        b.lk(b.v("UltChave"), f, "Key")
        return f, b.br((f, "ReturnValue")), b.setv("UltIcone", src=(f, "Value"))

    ehg = b.c(KIL + "Key_IsGamepadKey")
    b.lk(b.v("UltChave"), ehg, "Key")
    br_gp = b.br((ehg, "ReturnValue"))
    br_ps = b.br(igual(b, b.v("TipoAtual"), "PlayStation"))
    _, br_fps, set_ps = busca("IconesPlayStation")
    _, br_fxb, set_xb = busca("IconesXbox")
    _, br_fkb, set_kb = busca("IconesTeclado")
    b.ch(en, limpa, c1, achou)
    b.ch((achou, "then"), j)
    b.ch((achou, "else"), c2, j)
    b.ch(j, final)
    b.ch((final, "then"), valido)
    b.ch((valido, "then"), br_gp)
    b.ch((br_gp, "then"), br_ps)
    b.ch((br_gp, "else"), br_fkb)
    b.ch((br_ps, "then"), br_fps)
    b.ch((br_ps, "else"), br_fxb)
    b.ch((br_fps, "then"), set_ps)
    b.ch((br_fxb, "then"), set_xb)
    b.ch((br_fkb, "then"), set_kb)


def ensure_icones(t):
    bp = EAL.load_asset(COMP)
    if not bp:
        raise Aborta("BP_LuxEntrada nao existe: rode instalar comp antes")
    if "ObterIconeAcao" in [str(x) for x in BEL.list_graph_names(bp)]:
        w("ObterIconeAcao ja existe: mantida")
        return bp
    t = dict(t)
    BEL.add_member_variable(bp, "UltIcone", t["tex"])
    BEL.set_blueprint_variable_category(bp, "UltIcone", unreal.Text("LUX Entrada|Estado"))
    BEL.compile_blueprint(bp)
    ale.cria_funcoes(bp, [("ObterIconeAcao", [("Acao", "ia")])], dict(t, glifos=BEL.get_object_reference_type(EAL.load_asset(PDA).generated_class())))
    BEL.compile_blueprint(bp)
    f_icone_acao(bp)
    BEL.compile_blueprint(bp)
    BEL.compile_blueprint(bp)
    compila(bp, "BP_LuxEntrada (icones)")
    return bp


# ------------------------------------------------------------------ 5) componente no BP_Player_Cowboy
def ensure_cowboy():
    """adiciona o componente LuxEntrada ao BP_Player_Cowboy (filho; o BP_Player nao e editado). Sem Tick, sem mudar nenhum no existente."""
    bp = EAL.load_asset(COWBOY)
    if ale.comp_template(bp, COMP_NOME):
        w("BP_Player_Cowboy ja tem o componente", COMP_NOME)
        return bp
    base = erros(bp)
    comp_bp = EAL.load_asset(COMP)
    if not comp_bp:
        raise Aborta("BP_LuxEntrada nao existe: rode instalar comp antes")
    ale.add_comp(bp, comp_bp.generated_class(), COMP_NOME)
    BEL.compile_blueprint(bp)
    novos = [e for e in erros(bp) if e not in base]
    if novos:
        raise Aborta("BP_Player_Cowboy compilou com erros/avisos NOVOS: %s" % novos)
    w("componente %s adicionado ao BP_Player_Cowboy (erros/avisos ja existentes antes: %d)" % (COMP_NOME, len(base)))
    return bp


# ------------------------------------------------------------------ desfazer
def remove_comp_do_cowboy():
    bp = EAL.load_asset(COWBOY)
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    hs = sds.k2_gather_subobject_data_for_blueprint(bp)
    alvo = [h for h in hs if (lambda o: o and o.get_name().replace("_GEN_VARIABLE", "") == COMP_NOME)(lib.get_object_for_blueprint(lib.get_data(h), bp))]
    if alvo:
        n = sds.delete_subobject(hs[0], alvo[0], bp)
        BEL.compile_blueprint(bp)
        w("componente %s removido do BP_Player_Cowboy (%s)" % (COMP_NOME, n))
    return bool(alvo)


def desfazer(etapas):
    """remove o que o instalar criou, na ordem inversa das dependencias. O BP_Player_Cowboy volta a ficar sem o componente (nada mais nele muda)."""
    if "cowboy" in etapas:
        remove_comp_do_cowboy()
    for etapa, caminho in (("comp", COMP), ("widget", WBP), ("bpfl", BPFL), ("glifos", DA), ("glifos", PDA)):
        if etapa in etapas and EAL.does_asset_exist(caminho):
            w("apagado", caminho, EAL.delete_asset(caminho))


# ------------------------------------------------------------------ verificar e salvar
DADOS = ("glifos", "bpfl", "widget")
TODAS = ["glifos", "bpfl", "widget", "comp", "api", "icones", "soltar", "cowboy"]


def verificar(silencioso=False, etapas=None):
    """so confere o que as etapas pedidas montam (a geracao e em dois processos: dados no commandlet, componente no editor)"""
    etapas = etapas or TODAS
    dados = any(e in etapas for e in DADOS)
    comp = any(e in etapas for e in ("comp", "api", "icones", "soltar", "cowboy"))
    falhas = []
    for p in ((PDA, DA, BPFL, WBP) if dados else ()) + ((COMP,) if comp else ()):
        if not EAL.does_asset_exist(p):
            falhas.append("asset ausente: " + p)
    if falhas:
        if not silencioso:
            w("verificar: FAIL", falhas)
        return falhas
    if dados:
        for p, rot in ((BPFL, "BPFL_LuxEntrada"), (WBP, "WB_LuxPausa")):
            bp = EAL.load_asset(p)
            if bp.get_editor_property("status") != unreal.BlueprintStatus.BS_UP_TO_DATE:
                falhas.append("%s nao esta compilado (%s)" % (rot, bp.get_editor_property("status")))
            falhas += ["%s: %s" % (rot, e) for e in erros(bp)]
        falhas += ["classificador: " + f for f in testa_classificador(EAL.load_asset(BPFL))]
        da = EAL.load_asset(DA)
        xb = {str(k.get_editor_property("key_name")): str(v) for k, v in da.get_editor_property("RotulosXbox").items()}
        ps = {str(k.get_editor_property("key_name")): str(v) for k, v in da.get_editor_property("RotulosPlayStation").items()}
        for k, a, b in ROTULOS:
            if xb.get(k) != a or ps.get(k) != b:
                falhas.append("DA_LuxGlifos %s: Xbox=%s PlayStation=%s (esperado %s / %s)" % (k, xb.get(k), ps.get(k), a, b))
        for nome in ("IconesXbox", "IconesPlayStation", "IconesTeclado"):
            if len(da.get_editor_property(nome)) != 0:
                w("  (aviso) %s ja tem %d icones" % (nome, len(da.get_editor_property(nome))))
    if comp:
        bp = EAL.load_asset(COMP)
        if bp.get_editor_property("status") != unreal.BlueprintStatus.BS_UP_TO_DATE:
            falhas.append("BP_LuxEntrada nao esta compilado (%s)" % bp.get_editor_property("status"))
        falhas += ["BP_LuxEntrada: %s" % e for e in erros(bp)]
        cdo = unreal.get_default_object(bp.generated_class())
        for v in ("Glifos", "ContextoEntrada", "AcaoInteragir", "AcaoPausa", "AcaoConfirmar", "AcaoAlternar"):
            if cdo.get_editor_property(v) is None:
                falhas.append("BP_LuxEntrada.%s sem valor padrao" % v)
        ticks = [str(n.get_node_title()) for g in [str(x) for x in BEL.list_graph_names(bp)] for n in BGE.get_graph_editor_by_name(bp, g).list_all_nodes() if "Tick" in str(n.get_node_title())]
        if ticks:
            falhas.append("BP_LuxEntrada tem no de Tick (D06: sem Tick): %s" % ticks)
        if "comp" in etapas or "soltar" in etapas or etapas == TODAS:
            # fechar a pausa com A/B ao SOLTAR (gatilho Released): o evento sai pelo Triggered; e o Retomar nao chama o rebuild (ver ensure_soltar)
            ge_ev = BGE.get_graph_editor_by_name(bp, "EventGraph")
            for nome in ("IA_UI_Voltar", "IA_UI_Confirmar"):
                nos = no_evento_ia(ge_ev, nome)
                if len(nos) != 1:
                    falhas.append("EventGraph: esperava 1 no de evento de %s, achei %d" % (nome, len(nos)))
                elif nos[0].find_output_pin("Started").list_connected_pins() or not nos[0].find_output_pin("Triggered").list_connected_pins():
                    falhas.append("%s: o evento que fecha a pausa deve sair pelo Triggered (ao soltar), nao pelo Started" % nome)
            if [n for n in BGE.get_graph_editor_by_name(bp, "Retomar").list_all_nodes() if str(n.get_node_title()).replace("\n", " ").startswith("RequestRebuildControlMappings")]:
                falhas.append("Retomar ainda chama RequestRebuildControlMappings (nao faz nada pelas teclas apertadas)")
        for v, esp in (("TipoAtual", "TecladoMouse"), ("EstiloManual", "Auto"), ("ForcarTipo", "Auto")):
            if str(cdo.get_editor_property(v)) != esp:
                falhas.append("BP_LuxEntrada.%s padrao = %s (esperado %s)" % (v, cdo.get_editor_property(v), esp))
        graf = [str(x) for x in BEL.list_graph_names(bp)]
        for f in ("DefinirEstilo", "DefinirTipoForcado", "ObterIconeAcao"):
            if (("api" in etapas and f != "ObterIconeAcao") or ("icones" in etapas and f == "ObterIconeAcao") or etapas == TODAS) and f not in graf:
                falhas.append("BP_LuxEntrada sem a funcao " + f)
        cow = EAL.load_asset(COWBOY)
        if "cowboy" in etapas:
            if not ale.comp_template(cow, COMP_NOME):
                falhas.append("BP_Player_Cowboy sem o componente " + COMP_NOME)
            falhas += ["BP_Player_Cowboy: %s" % e for e in erros(cow)]
    if not silencioso:
        w("verificar:", ("FAIL %s" % falhas) if falhas else "PASS")
    return falhas


def salvar_tudo(etapas=None):
    etapas = etapas or TODAS
    ordem = ((PDA, DA, BPFL, WBP) if any(e in etapas for e in DADOS) else ()) + ((COMP,) if any(e in etapas for e in ("comp", "api", "icones", "soltar")) else ()) + ((COWBOY,) if "cowboy" in etapas else ())
    for p in ordem:
        a = EAL.load_asset(p)
        ok = EAL.save_loaded_asset(a, False)
        w("salvo", p, ok)
        if not ok:
            raise Aborta("falhou ao salvar " + p + " (arquivo em uso por outro editor?)")


def sondar():
    for p in (PDA, DA, BPFL, WBP, COMP, COWBOY):
        w("asset", p, "existe" if EAL.does_asset_exist(p) else "NAO existe")
    cow = EAL.load_asset(COWBOY)
    w("BP_Player_Cowboy tem o componente:", bool(ale.comp_template(cow, COMP_NOME)))
    verificar()


def main():
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    open(LOG, "w", encoding="utf-8").close()
    modo = next((a for a in sys.argv[1:] if a in ("sondar", "instalar", "verificar", "desfazer")), "sondar")
    etapas = [a for a in sys.argv[1:] if a in ("glifos", "bpfl", "widget", "comp", "api", "icones", "soltar", "cowboy", "salvar")] or ["glifos", "bpfl", "widget", "comp", "api", "icones", "soltar", "cowboy", "salvar"]
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
            if "comp" in etapas:
                ensure_comp(t, EAL.load_asset(DA))
            if "api" in etapas:
                ensure_api(t)
            if "icones" in etapas:
                ensure_icones(t)
            if "soltar" in etapas:
                ensure_soltar()
            if "cowboy" in etapas:
                ensure_cowboy()
            if "salvar" in etapas:
                f = verificar(etapas=etapas)
                if f:
                    raise Aborta("verificar FAIL (nada salvo): %s" % f)
                salvar_tudo(etapas)
        elif modo == "desfazer":
            desfazer(etapas)
        elif modo == "verificar":
            verificar(etapas=[e for e in etapas if e != "salvar"])
        else:
            sondar()
    except Aborta as ex:
        w("ABORTADO:", ex, "| sujos:", ale.sujos())
    except Exception:
        w("ERRO " + traceback.format_exc(), "| sujos:", ale.sujos())


if __name__ == "__main__":
    main()
