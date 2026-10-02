# LUX: MENU DE PAUSA (pedido do Gabriel, 02/10/2026): organizado, legivel e com a identidade do jogo (casa velha a noite, vela quente contra a lua fria,
# HUD minimo: a vela e a interface). Continuar / Configuracoes / Sair, com teclado, mouse e controle. So ADICIONA e reescreve a pausa do BP_LuxEntrada;
# o BP_Player, o BP_BaseDoor, o BP_BaseKey (D02) e os widgets do pack nao sao editados.
#
# O QUE O PYTHON DO 5.8 NAO FAZ (por isso o desenho): ele nao cria widget na arvore de um Widget Blueprint (a WidgetTree nem e exposta; widget criado por
# new_object nao ganha GUID e derruba o compilador do UMG, P24/01-10) e nao ha como arrastar um Botao no designer. O que da: CLONAR um widget do pack e
# mexer nas propriedades dos widgets que ele ja tem (get_child_at, set_editor_property). Entao o menu e feito de PECAS pequenas, todas clones do
# WB_InteractDot (CanvasPanel > HorizontalBox > [Border > TextBlock] x2), e MONTADO EM TEMPO DE EXECUCAO pelo BP_LuxEntrada: CriarWidget de cada peca e
# AddChildToCanvas na raiz do WB_LuxPausa (ancora no centro, posicao e tamanho por Y/W/H). Pecas (todas em /Game/Masion/LUX/Entrada):
#   WB_LuxPausaPainel   cartao escuro com contorno fino quente (sem texto)
#   WB_LuxPausaTitulo   titulo grande, espacado (tambem serve de divisor: DefinirFundo)
#   WB_LuxPausaBotao    barra de acento + corpo + rotulo; estados normal / selecionado / pressionado; mouse (entra, aperta, solta)
#   WB_LuxPausaDica     linha pequena de ajuda de teclas (rotulos por dispositivo)
# Telas (BP_LuxEntrada.MontarTela): Principal (Continuar, Configuracoes, Sair), Config (icones dos botoes, Voltar), Sair (confirmacao: Cancelar, Sair).
# Entrada: IA_UI_Cima/Baixo (novas, gamepad_input.py) movem a selecao; Confirmar (ao soltar) ativa; Voltar volta (ou continua, na tela principal); Pausa
# continua; Alternar (Y) segue trocando o estilo dos icones. Mouse: passar seleciona, soltar o botao ativa. Cursor so com teclado/mouse. Com a pausa aberta
# o modo de entrada e Game and UI (o Enhanced Input segue valendo, com trigger_when_paused); ao continuar volta Game Only e o cursor some.
# Etapas (em ordem; rode o gamepad_input.py instalar antes). Salva cada etapa so depois de compilar limpo:
#   stubs    variaveis e funcoes VAZIAS no BP_LuxEntrada (os botoes chamam Dono.AoSobreItem/AoClicarItem; a referencia circular se resolve em etapas)
#   itens    as 4 pecas (clone, estilo, grafos)
#   pausa    WB_LuxPausa vira so o fundo escuro
#   estilo   reaplica so o estilo estatico das pecas e refaz DefinirEstado (ajuste visual sem refazer grafos). Rode no COMMANDLET, nao no editor aberto
#   preparo  commandlet: assinaturas das funcoes, limpa o corpo de Mover, compila e salva (separa "criar no" de "compilar" no mesmo editor, ver P21 abaixo)
#   cursor   refaz so AtualizarCursor / EntradaPausaLigar / EntradaPausaDesligar com IsValid no controle (o EndPlay chama Retomar com o controle destruido)
#   comp     corpos das funcoes do BP_LuxEntrada e os eventos de entrada. Rode em um editor RECEM-ABERTO, sem compilacao anterior na sessao
#   py "<projeto>/Tools/Player/pausa_menu.py" sondar|instalar|verificar|desfazer [stubs|itens|pausa|estilo|preparo|cursor|comp ...]
# Licoes que moldaram o script (detalhe em Registro_de_Diagnosticos, P21 e correlatos):
#   - P21: criar no Add_* (Add_IntInt etc.) num BP que tem/ja compilou um derruba o editor. Por isso Mover usa Subtract/Multiply/Percent, sem Add_*.
#   - Funcao de grafo precisa estar COMPILADA antes de ser chamada por caminho; compile so no fim de cada etapa.
#   - SBorder com filho colapsado tem tamanho desejado zero (o padding e ignorado): a faixa do botao tem um TextBlock vazio VISIVEL + min_desired_width.
#   - O clone do WB_InteractDot traz uma Image "Dot" (a mira): colapsada nas pecas.
#   - Cor/brush/texto do UMG sao LINEARES; letter_spacing em 1/1000 de em; auto_wrap_text quebrava a dica cedo demais (desligado).
import json, os, sys, traceback
import unreal

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(AQUI), "Loop"))
sys.path.insert(0, AQUI)
import add_loop_events as ale
import gamepad_entrada as ge_

EAL, BEL, BGE = unreal.EditorAssetLibrary, unreal.BlueprintEditorLibrary, unreal.BlueprintGraphEditor
DIR = ge_.DIR
WBP, COMP = ge_.WBP, ge_.COMP
WBP_C, COMP_C = ge_.WBP_C, ge_.COMP_C
PECAS = {"Painel": DIR + "/WB_LuxPausaPainel", "Titulo": DIR + "/WB_LuxPausaTitulo", "Botao": DIR + "/WB_LuxPausaBotao", "Dica": DIR + "/WB_LuxPausaDica"}
PECA_C = {k: v + "." + v.split("/")[-1] + "_C" for k, v in PECAS.items()}
UMG, UMGL = "/Script/UMG.", "/Script/UMG.WidgetBlueprintLibrary:"
KML, KSL, GS, ARR, STR, TXT, MAC = ale.KML, ale.KSL, ale.GS, ale.ARR, ale.STR, ale.TXT, ale.MAC
LOG = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), "LuxSnapshots", "pausa_menu_log.txt")

# ---- identidade: vela (2200 K) contra lua fria. Cores LINEARES (RGBA): o brush e o texto do UMG recebem cor linear e o monitor mostra sRGB, entao um valor
# "claro" (0,5) sai bem mais claro do que parece. Aqui, o que se quer ver (sRGB aprox.) esta ao lado de cada cor.
AMBAR = (0.85, 0.30, 0.04)           # a chama: sRGB ~ (237, 149, 56)
OSSO = (0.78, 0.70, 0.56)            # titulo: sRGB ~ (230, 220, 200)
OSSO_SUAVE = (0.30, 0.28, 0.25)      # rotulo do botao em repouso: sRGB ~ (151, 146, 139)
MUDO = (0.15, 0.14, 0.13)            # dica: sRGB ~ (108, 105, 101)
FUNDO = (0.003, 0.004, 0.008, 0.82)  # escuro frio por cima do jogo
CARTAO = (0.008, 0.009, 0.013, 0.92) # cartao: sRGB ~ (24, 26, 31)
CORPO_NORMAL = (0.012, 0.012, 0.015, 0.70)
CORPO_SEL = (0.045, 0.020, 0.008, 0.94)    # sRGB ~ (60, 38, 20): brasa apagada
CORPO_PRESS = (0.085, 0.036, 0.012, 0.97)
CONTORNO = (0.20, 0.11, 0.05, 0.75)        # fio quente dos botoes
CONTORNO_CARTAO = (0.45, 0.17, 0.03, 0.55)
ESTADOS = (  # (faixa, corpo, texto) por estado: 0 normal, 1 selecionado, 2 pressionado
    ((0.20, 0.11, 0.05, 1.0), CORPO_NORMAL, (OSSO_SUAVE[0], OSSO_SUAVE[1], OSSO_SUAVE[2], 1.0)),   # faixa em repouso = cor do contorno (todos os botoes com a mesma largura)
    ((AMBAR[0], AMBAR[1], AMBAR[2], 1.0), CORPO_SEL, (0.95, 0.82, 0.62, 1.0)),
    ((1.0, 0.45, 0.08, 1.0), CORPO_PRESS, (1.0, 0.92, 0.75, 1.0)),
)
# layout (unidades de tela do UMG, 1080p = escala 1): o cartao fica centrado em CY; cada tela calcula o Y de cada peca a partir do topo
CY, BOTAO_W, BOTAO_H, PASSO = 10.0, 380.0, 52.0, 68.0


def w(*a):
    line = " ".join(str(x) for x in a)
    unreal.log("[LUX pausa] " + line)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")
        fh.flush()


Aborta = ge_.Aborta
mk = ge_.mk
cria_no, pino_cast, igual, sel_str = ge_.cria_no, ge_.pino_cast, ge_.igual, ge_.sel_str


def lin(c):
    return "(R=%.6f,G=%.6f,B=%.6f,A=%.6f)" % (c[0], c[1], c[2], c[3] if len(c) > 3 else 1.0)


def cor(c):
    return unreal.LinearColor(c[0], c[1], c[2], c[3] if len(c) > 3 else 1.0)


def slate_color(c):
    s = unreal.SlateColor()
    s.set_editor_property("specified_color", cor(c))
    return s


def tipos():
    t = ge_.tipos()
    t["uw[]"] = BEL.get_array_type(t["uw"])
    t["cor"] = BEL.get_struct_type(unreal.LinearColor.static_struct())
    return t


def abre(bp, nome):
    return ge_.abre(bp, nome)


# ------------------------------------------------------------------ BP_LuxEntrada: variaveis e funcoes novas
VARS_NOVAS = [("Tela", "string", False, "Principal"), ("Indice", "int", False, 0), ("Todos", "uw[]", False, None), ("Botoes", "uw[]", False, None),
              ("ItemDica", "uw", False, None), ("AcaoVoltar", "ia", True, None), ("Aux3", "string", False, "")]
FUNC_NOVAS = [  # nome, entradas
    ("LimparTela", []), ("Colocar", [("Item", "uw"), ("Y", "real"), ("W", "real"), ("H", "real")]), ("CriarBotao", [("Texto", "text"), ("Y", "real"), ("Idx", "int")]),
    ("CriarTitulo", [("Texto", "text"), ("Y", "real")]), ("CriarNota", [("Texto", "text"), ("Y", "real")]), ("CriarDica", [("Y", "real")]), ("CriarDivisor", [("Y", "real")]), ("CriarPainel", [("Altura", "real")]), ("MontarTela", [("Nome", "string")]),
    ("AplicarSelecao", []), ("Mover", [("Delta", "int")]), ("AoSobreItem", [("Idx", "int")]), ("AoClicarItem", [("Idx", "int")]), ("Ativar", []), ("Voltar", []),
    ("AtualizarLinhaEstilo", []), ("AtualizarCursor", []), ("EntradaPausaLigar", []), ("EntradaPausaDesligar", []), ("SairDoJogo", []),
]


def etapa_stubs():
    bp = EAL.load_asset(COMP)
    if not bp:
        raise Aborta("BP_LuxEntrada nao existe: rode gamepad_entrada.py instalar antes")
    t = tipos()
    exist = [str(n) for n in BEL.list_member_variable_names(bp)]
    novas = [v for v in VARS_NOVAS if v[0] not in exist]
    ale.cria_vars(bp, novas, t, "LUX Entrada")
    BEL.compile_blueprint(bp)
    pad = [(n, tp, ed, EAL.load_asset(ge_.DIR + "/IA_UI_Voltar") if n == "AcaoVoltar" else pd) for n, tp, ed, pd in novas]
    ale.padroes(bp, pad)
    graficos = [str(x) for x in BEL.list_graph_names(bp)]
    nf = [(n, e) for n, e in FUNC_NOVAS if n not in graficos]
    ale.cria_funcoes(bp, nf, t)
    BEL.compile_blueprint(bp)
    e = ge_.erros(bp)
    w("stubs: %d variaveis e %d funcoes novas; erros/avisos: %s" % (len(novas), len(nf), e))
    if e:
        raise Aborta("BP_LuxEntrada compilou com erros nos stubs: %s" % e)
    w("BP_LuxEntrada (stubs) salvo:", EAL.save_loaded_asset(bp, False))
    return bp


# ------------------------------------------------------------------ pecas (clones do WB_InteractDot)
def borda(bp_path, i):
    hb = unreal.load_object(None, bp_path + "." + bp_path.split("/")[-1] + ":WidgetTree.HorizontalBox")
    return hb.get_child_at(i)


def margem(l, t, r, b):
    return mk(unreal.Margin, left=float(l), top=float(t), right=float(r), bottom=float(b))


def brush_caixa(arredondado, contorno=None, largura=1.0, raio=0.0):
    br = unreal.SlateBrush()
    br.set_editor_property("tint_color", slate_color((1.0, 1.0, 1.0, 1.0)))
    if arredondado:
        ol = unreal.SlateBrushOutlineSettings()
        ol.set_editor_property("rounding_type", unreal.SlateBrushRoundingType.FIXED_RADIUS)
        v4 = unreal.Vector4()
        for k in "xyzw":
            v4.set_editor_property(k, float(raio))
        ol.set_editor_property("corner_radii", v4)
        ol.set_editor_property("color", slate_color(contorno))
        ol.set_editor_property("width", float(largura))
        br.set_editor_property("draw_as", unreal.SlateBrushDrawType.ROUNDED_BOX)
        br.set_editor_property("outline_settings", ol)
    return br


def fonte(txt, tamanho, espaco, peso="Bold"):
    f = txt.get_editor_property("font")
    f.set_editor_property("size", int(tamanho))
    f.set_editor_property("letter_spacing", int(espaco))
    f.set_editor_property("typeface_font_name", unreal.Name(peso))
    txt.set_editor_property("font", f)


def esconde_imagens(wd, achados=None):
    """o WB_InteractDot e a mira do jogo: o clone traz uma Image (o ponto branco no centro) que aparecia no meio de cada peca. Colapsa todas"""
    achados = [] if achados is None else achados
    try:
        if wd.get_class().get_name() == "Image":
            wd.set_editor_property("visibility", unreal.SlateVisibility.COLLAPSED)
            achados.append(wd.get_name())
            return achados
    except Exception:
        return achados
    filhos = []
    try:
        filhos = [wd.get_child_at(i) for i in range(wd.get_children_count())]
    except Exception:
        try:
            filhos = [wd.get_content()]
        except Exception:
            filhos = []
    for f in filhos:
        if f:
            esconde_imagens(f, achados)
    return achados


def estilo_peca(nome, caminho):
    """propriedades estaticas dos widgets do clone: raiz ancorada na tela toda do slot, faixa (filho 0) e corpo (filho 1 > texto)"""
    raiz = unreal.load_object(None, caminho + "." + caminho.split("/")[-1] + ":WidgetTree.HorizontalBox")
    if not raiz or raiz.get_children_count() != 2:
        raise Aborta("arvore do clone diferente do esperado em " + nome)
    w("   imagens da mira colapsadas em %s: %s" % (nome, esconde_imagens(raiz.get_parent())))
    cs = raiz.get_editor_property("slot")
    cs.set_anchors(mk(unreal.Anchors, minimum=unreal.Vector2D(0.0, 0.0), maximum=unreal.Vector2D(1.0, 1.0)))
    cs.set_offsets(margem(0, 0, 0, 0))
    cs.set_auto_size(False)
    cs.set_alignment(unreal.Vector2D(0.0, 0.0))
    faixa, corpo = raiz.get_child_at(0), raiz.get_child_at(1)
    tf, tc = faixa.get_content(), corpo.get_content()
    for tb in (tf, tc):
        tb.set_editor_property("text", unreal.Text(""))
    # slots no HorizontalBox: faixa automatica, corpo preenche
    for wid, regra in ((faixa, unreal.SlateSizeRule.AUTOMATIC), (corpo, unreal.SlateSizeRule.FILL)):
        sl = wid.get_editor_property("slot")
        sl.set_size(mk(unreal.SlateChildSize, value=1.0, size_rule=regra))
        sl.set_horizontal_alignment(unreal.HorizontalAlignment.H_ALIGN_FILL)
        sl.set_vertical_alignment(unreal.VerticalAlignment.V_ALIGN_FILL)
        sl.set_padding(margem(0, 0, 0, 0))
    # SBorder devolve tamanho ZERO quando o filho esta colapsado (ignora o padding): a faixa do botao precisa de um filho VISIVEL, vazio, com largura minima
    tf.set_editor_property("visibility", unreal.SlateVisibility.HIT_TEST_INVISIBLE if nome == "Botao" else unreal.SlateVisibility.COLLAPSED)
    if nome == "Botao":
        tf.set_editor_property("min_desired_width", 5.0)
    corpo.set_editor_property("vertical_alignment", unreal.VerticalAlignment.V_ALIGN_CENTER)
    if nome == "Botao":
        faixa.set_editor_property("brush_color", cor(ESTADOS[0][0]))
        faixa.set_editor_property("padding", margem(0, 0, 0, 0))
        faixa.set_editor_property("visibility", unreal.SlateVisibility.HIT_TEST_INVISIBLE)
        corpo.set_editor_property("background", brush_caixa(True, CONTORNO, 1.0, 0.0))
        corpo.set_editor_property("brush_color", cor(ESTADOS[0][1]))
        corpo.set_editor_property("padding", margem(24, 0, 12, 0))
        corpo.set_editor_property("horizontal_alignment", unreal.HorizontalAlignment.H_ALIGN_LEFT)
        fonte(tc, 20, 110)   # letter_spacing e em milesimos de em
        tc.set_editor_property("justification", unreal.TextJustify.LEFT)
        tc.set_editor_property("color_and_opacity", slate_color(ESTADOS[0][2]))
    elif nome == "Painel":
        faixa.set_editor_property("visibility", unreal.SlateVisibility.COLLAPSED)
        corpo.set_editor_property("background", brush_caixa(True, CONTORNO_CARTAO, 1.0, 2.0))
        corpo.set_editor_property("brush_color", cor(CARTAO))
        tc.set_editor_property("visibility", unreal.SlateVisibility.COLLAPSED)
    else:  # Titulo, Dica
        faixa.set_editor_property("visibility", unreal.SlateVisibility.COLLAPSED)
        corpo.set_editor_property("brush_color", unreal.LinearColor(0.0, 0.0, 0.0, 0.0))
        corpo.set_editor_property("horizontal_alignment", unreal.HorizontalAlignment.H_ALIGN_CENTER)
        corpo.set_editor_property("padding", margem(0, 0, 0, 0))
        if nome == "Titulo":
            fonte(tc, 32, 260)
            tc.set_editor_property("color_and_opacity", slate_color(OSSO + (1.0,)))
        else:
            fonte(tc, 12, 20, "Regular")
            tc.set_editor_property("color_and_opacity", slate_color(MUDO + (1.0,)))
            tc.set_editor_property("auto_wrap_text", False)   # com quebra automatica a dica quebrava na metade da largura (Border centrado)
        tc.set_editor_property("justification", unreal.TextJustify.CENTER)


def txt_no_filho(b, en, fe, indice, texto_pin):
    """HorizontalBox[indice] (Border) > conteudo (TextBlock) > SetText(texto_pin)"""
    raiz = b.g.get("HorizontalBox", 0, 0, b.me)
    gc = b.c("/Script/UMG.PanelWidget:GetChildAt")
    b.lk((raiz, "HorizontalBox"), gc, "self")
    b.g.val(gc, "Index", indice)
    cb = cria_no(fe, fim="CastToBorder")
    b.lk((gc, "ReturnValue"), cb, "Object")
    cont = b.c(UMG + "ContentWidget:GetContent")
    b.lk((cb, pino_cast(cb)), cont, "self")
    ct = cria_no(fe, fim="CastToTextBlock")
    b.lk((cont, "ReturnValue"), ct, "Object")
    stx = b.c(UMG + "TextBlock:SetText")
    b.lk((ct, pino_cast(ct)), stx, "self")
    b.lk(texto_pin, stx, "InText")
    b.ch(en, cb, ct, stx)


def f_definir_texto(bp, c):
    b, en, ret, fe = ge_.nova_funcao(bp, "DefinirTexto", [("Texto", "text")], [], tipos(), c)
    txt_no_filho(b, en, fe, 1, (en, "Texto"))


def f_definir_fundo(bp, c):
    """DefinirFundo(Cor): so o corpo (Border filho 1). O divisor e o Titulo com o texto vazio e o fundo ambar"""
    b, en, ret, fe = ge_.nova_funcao(bp, "DefinirFundo", [("Cor", "cor")], [], tipos(), c)
    raiz = b.g.get("HorizontalBox", 0, 0, c)
    gc = b.c("/Script/UMG.PanelWidget:GetChildAt")
    b.lk((raiz, "HorizontalBox"), gc, "self")
    b.g.val(gc, "Index", 1)
    cb = cria_no(fe, fim="CastToBorder")
    b.lk((gc, "ReturnValue"), cb, "Object")
    sb = b.c(UMG + "Border:SetBrushColor")
    b.lk((cb, pino_cast(cb)), sb, "self")
    b.lk((en, "Cor"), sb, "InBrushColor")
    b.ch(en, cb, sb)


def funcao_peca(bp, nome, entradas, c):
    """cria a funcao; se ja existe (refazer o estilo), limpa o corpo e reaproveita. Devolve (B, entrada, editor do grafo)"""
    if nome in [str(x) for x in BEL.list_graph_names(bp)]:
        fe = limpa_funcao(bp, nome)
        return ge_.B(fe, c), fe.find_graph_entry_pin().get_owning_node(), fe
    b, en, ret, fe = ge_.nova_funcao(bp, nome, entradas, [], tipos(), c)
    return b, en, fe


def f_definir_estado(bp, c):
    """DefinirEstado(Estado): 0 normal, 1 selecionado, 2 pressionado. Faixa (filho 0), corpo (filho 1) e rotulo (conteudo do corpo)"""
    b, en, fe = funcao_peca(bp, "DefinirEstado", [("Estado", "int")], c)
    raiz = b.g.get("HorizontalBox", 0, 0, c)
    g0, g1 = b.c("/Script/UMG.PanelWidget:GetChildAt"), b.c("/Script/UMG.PanelWidget:GetChildAt")
    b.lk((raiz, "HorizontalBox"), g0, "self")
    b.lk((raiz, "HorizontalBox"), g1, "self")
    b.g.val(g0, "Index", 0)
    b.g.val(g1, "Index", 1)
    c0, c1 = cria_no(fe, fim="CastToBorder"), cria_no(fe, fim="CastToBorder")
    b.lk((g0, "ReturnValue"), c0, "Object")
    b.lk((g1, "ReturnValue"), c1, "Object")
    cont = b.c(UMG + "ContentWidget:GetContent")
    b.lk((c1, pino_cast(c1)), cont, "self")
    ct = cria_no(fe, fim="CastToTextBlock")
    b.lk((cont, "ReturnValue"), ct, "Object")
    b.ch(en, c0, c1, ct)

    def aplica(idx):
        fa, co, te = ESTADOS[idx]
        s0 = b.c(UMG + "Border:SetBrushColor")
        b.lk((c0, pino_cast(c0)), s0, "self")
        b.g.val(s0, "InBrushColor", lin(fa))
        s1 = b.c(UMG + "Border:SetBrushColor")
        b.lk((c1, pino_cast(c1)), s1, "self")
        b.g.val(s1, "InBrushColor", lin(co))
        s2 = b.c(UMG + "TextBlock:SetColorAndOpacity")
        b.lk((ct, pino_cast(ct)), s2, "self")
        b.g.val(s2, "InColorAndOpacity", "(SpecifiedColor=%s,ColorUseRule=UseColor_Specified)" % lin(te))
        b.ch(s0, s1, s2)
        return s0, s2

    br0 = b.br(b.op("EqualEqual_IntInt", (en, "Estado"), 0))
    br1 = b.br(b.op("EqualEqual_IntInt", (en, "Estado"), 1))
    a0, a1, a2 = aplica(0), aplica(1), aplica(2)
    b.ch((ct, "then"), br0)
    b.ch((br0, "then"), a0[0])
    b.ch((br0, "else"), br1)
    b.ch((br1, "then"), a1[0])
    b.ch((br1, "else"), a2[0])


def vars_botao(bp):
    t = tipos()
    dono = BEL.get_object_reference_type(EAL.load_asset(COMP).generated_class())
    t["dono"] = dono
    lista = [("Indice", "int", False, 0), ("Dono", "dono", False, None)]
    ale.cria_vars(bp, lista, t, "LUX Pausa")
    BEL.compile_blueprint(bp)


def eventos_botao(bp, c):
    """mouse: entrar seleciona; apertar pinta de pressionado; soltar (com o mouse ainda em cima) ativa. O BP_LuxEntrada decide o que cada item faz"""
    ge = BGE.get_graph_editor_by_name(bp, "EventGraph")
    b = ge_.B(ge, c)
    # entrar: Dono valido -> Dono.AoSobreItem(Indice)
    ev = BEL.add_event_override(bp, "OnMouseEnter", unreal.IntPoint(0, 0))
    ok = b.br(b.valido(b.v("Dono")))
    ch = b.call("AoSobreItem", alvo=b.v("Dono"), cls=COMP_C)
    b.lk(b.v("Indice"), ch, "Idx")
    b.ch(ev, ok)
    b.ch((ok, "then"), ch)

    def override(nome):
        g = BEL.add_function_override(bp, nome)
        if not g:
            raise Aborta("add_function_override(%s) falhou" % nome)
        fe = BGE.get_graph_editor_by_name(bp, nome)
        nos = list(fe.list_all_nodes())
        entrada = next(n for n in nos if "FunctionEntry" in n.get_class().get_name())
        resultado = next(n for n in nos if "FunctionResult" in n.get_class().get_name())
        sai = [n for n in nos if n not in (entrada, resultado)]
        if sai:
            fe.remove_nodes(sai)
        entrada.find_output_pin("then").break_pin_links()
        bb = ge_.B(fe, c)
        han = bb.c(UMGL + "Handled")
        bb.lk((han, "ReturnValue"), resultado, "ReturnValue")
        return bb, fe, entrada, resultado

    bb, fe, entrada, res = override("OnMouseButtonDown")
    ds = bb.call("DefinirEstado")
    bb.g.val(ds, "Estado", 2)
    bb.ch(entrada, ds, res)
    bb, fe, entrada, res = override("OnMouseButtonUp")
    hov = bb.c(UMG + "Widget:IsHovered")
    em_cima = bb.br((hov, "ReturnValue"))
    ok2 = bb.br(bb.valido(bb.v("Dono")))
    ch2 = bb.call("AoClicarItem", alvo=bb.v("Dono"), cls=COMP_C)
    bb.lk(bb.v("Indice"), ch2, "Idx")
    bb.ch(entrada, em_cima)
    bb.ch((em_cima, "then"), ok2)
    bb.ch((ok2, "then"), ch2, res)
    bb.ch((em_cima, "else"), res)
    bb.ch((ok2, "else"), res)


def limpa_grafo_herdado(bp):
    """o clone traz o EventGraph do WB_InteractDot (variaveis do BP_Player): sai, senao nao compila"""
    ge = BGE.get_graph_editor_by_name(bp, "EventGraph")
    nos = list(ge.list_all_nodes())
    if nos:
        ge.remove_nodes(nos)


GRAFOS_PECA = {"Painel": ("DefinirTexto",), "Titulo": ("DefinirTexto", "DefinirFundo"), "Dica": ("DefinirTexto",),
               "Botao": ("DefinirTexto", "DefinirEstado", "OnMouseButtonDown", "OnMouseButtonUp")}


def peca_completa(bp, nome):
    graficos = [str(x) for x in BEL.list_graph_names(bp)]
    return all(g in graficos for g in GRAFOS_PECA[nome])


def ensure_peca(nome):
    caminho = PECAS[nome]
    c = PECA_C[nome]
    if EAL.does_asset_exist(caminho) or EAL.load_asset(caminho):
        bp0 = EAL.load_asset(caminho)
        if bp0 and peca_completa(bp0, nome):
            w("%s ja existe: mantido" % nome)
            return bp0
        w("%s existe mas esta INCOMPLETA (execucao anterior interrompida): apagando para refazer" % nome)
        if not (EAL.delete_loaded_asset(bp0) if bp0 else EAL.delete_asset(caminho)):
            raise Aborta("nao consegui apagar a peca incompleta %s: feche o editor sem salvar e rode de novo" % nome)
    if not EAL.duplicate_asset(ge_.SRC_WIDGET, caminho):
        raise Aborta("duplicate_asset falhou para " + nome)
    bp = EAL.load_asset(caminho)
    try:
        limpa_grafo_herdado(bp)
        estilo_peca(nome, caminho)
        if nome == "Botao":
            vars_botao(bp)
        f_definir_texto(bp, c)
        if nome == "Titulo":
            f_definir_fundo(bp, c)
        if nome == "Botao":
            f_definir_estado(bp, c)
            BEL.compile_blueprint(bp)   # os overrides chamam DefinirEstado por caminho: a funcao tem de estar compilada (sem Add_* aqui, P21 nao se aplica)
            eventos_botao(bp, c)
        BEL.compile_blueprint(bp)
        e = ge_.erros(bp)
        if e:
            raise Aborta("%s compilou com erros/avisos: %s" % (nome, e))
        if bp.get_editor_property("status") != unreal.BlueprintStatus.BS_UP_TO_DATE:
            raise Aborta("%s status %s" % (nome, bp.get_editor_property("status")))
        w("peca %s criada e compilada limpa" % nome)
        w("   salva:", EAL.save_loaded_asset(bp, False))
    except BaseException:
        EAL.delete_asset(caminho)   # nunca deixa peca pela metade
        raise
    return bp


def etapa_itens():
    if not EAL.load_asset(COMP):
        raise Aborta("BP_LuxEntrada nao existe")
    if "AoClicarItem" not in [str(x) for x in BEL.list_graph_names(EAL.load_asset(COMP))]:
        raise Aborta("rode a etapa stubs antes (BP_LuxEntrada sem AoClicarItem)")
    for nome in ("Painel", "Titulo", "Botao", "Dica"):
        ensure_peca(nome)


# ------------------------------------------------------------------ WB_LuxPausa: so o fundo escuro
def etapa_pausa():
    bp = EAL.load_asset(WBP)
    if not bp:
        raise Aborta("WB_LuxPausa nao existe: rode gamepad_entrada.py instalar antes")
    raiz = unreal.load_object(None, WBP + ".WB_LuxPausa:WidgetTree.HorizontalBox")
    fundo = raiz.get_child_at(0)
    fundo.set_editor_property("brush_color", cor(FUNDO))
    txt = fundo.get_content()
    txt.set_editor_property("text", unreal.Text(""))
    txt.set_editor_property("visibility", unreal.SlateVisibility.COLLAPSED)   # o titulo agora e a peca WB_LuxPausaTitulo
    w("   imagens da mira colapsadas em WB_LuxPausa: %s" % esconde_imagens(raiz.get_parent()))
    ge_.compila(bp, "WB_LuxPausa")
    w("WB_LuxPausa (fundo escuro) salvo:", EAL.save_loaded_asset(bp, False))


def etapa_estilo():
    """reaplica o estilo estatico (cores, fonte, imagem da mira) nas 4 pecas ja criadas e no WB_LuxPausa; refaz o DefinirEstado do botao (cores no grafo)"""
    for nome in ("Painel", "Titulo", "Botao", "Dica"):
        bp = EAL.load_asset(PECAS[nome])
        if not bp:
            raise Aborta("peca %s nao existe: rode a etapa itens" % nome)
        estilo_peca(nome, PECAS[nome])
        if nome == "Botao":
            f_definir_estado(bp, PECA_C[nome])
        ge_.compila(bp, nome)
        w("peca %s reestilizada e salva: %s" % (nome, EAL.save_loaded_asset(bp, False)))
    etapa_pausa()


# ------------------------------------------------------------------ BP_LuxEntrada: corpos das funcoes
def no_self(fe):
    """no 'obter uma referencia para si' (a paleta traduz o nome; acha pelo fim do texto)"""
    for p in ge_.paleta(fe):
        fim = p.split("|")[-1]
        if (fim.endswith("parasi") and p.startswith("Vari")) or fim.lower().endswith("getareferencetoself"):
            n = fe.create_node_from_name(p, unreal.Vector2D(0, 0), [])
            if n:
                return n
    raise Aborta("no de self nao achado na paleta")


def texto_lit(b, s):
    n = b.c(TXT + "Conv_StringToText")
    b.g.val(n, "InString", s)
    return (n, "ReturnValue")


def limpa_funcao(bp, nome):
    """tira todos os nos da funcao (menos a entrada e o retorno) para reescreve-la"""
    fe = BGE.get_graph_editor_by_name(bp, nome)
    sai = [n for n in fe.list_all_nodes() if not any(k in n.get_class().get_name() for k in ("FunctionEntry", "FunctionResult"))]
    if sai:
        fe.remove_nodes(sai)
    return fe


def f_limpar_tela(bp):
    b, en, fe = abre(bp, "LimparTela")
    loop = b.g.pos(fe.add_macro_node(MAC + "ForEachLoop"), 300, 0)
    b.lk(b.v("Todos"), loop, "Array")
    rm = b.c(UMG + "Widget:RemoveFromParent")
    b.lk((loop, "Array Element"), rm, "self")
    c1, c2 = b.c(ARR + "Array_Clear"), b.c(ARR + "Array_Clear")
    b.lk(b.v("Todos"), c1, "TargetArray")
    b.lk(b.v("Botoes"), c2, "TargetArray")
    b.ch(en, loop)
    b.ch((loop, "LoopBody"), rm)
    b.ch((loop, "Completed"), c1, c2)


def f_colocar(bp):
    """Colocar(Item, Y, W, H): Item vira filho do CanvasPanel raiz do WB_LuxPausa, ancorado no centro, centro do item em (0, Y), tamanho W x H"""
    b, en, fe = abre(bp, "Colocar")
    cw = cria_no(fe, fim="CastToWB_LuxPausa")
    b.lk(b.v("WidgetPausa"), cw, "Object")
    hb = b.g.get("HorizontalBox", 0, 0, WBP_C)
    b.g.link(cw, pino_cast(cw), hb, "self")
    par = b.c(UMG + "Widget:GetParent")
    b.lk((hb, "HorizontalBox"), par, "self")
    cc = cria_no(fe, fim="CastToCanvasPanel", sem=("Slot", "Class"))
    b.lk((par, "ReturnValue"), cc, "Object")
    add = b.c(UMG + "CanvasPanel:AddChildToCanvas")
    b.lk((cc, pino_cast(cc)), add, "self")
    b.lk((en, "Item"), add, "Content")
    sl = (add, "ReturnValue")
    a1 = b.c(UMG + "CanvasPanelSlot:SetAutoSize")
    b.lk(sl, a1, "self")
    b.g.val(a1, "InbAutoSize", "false")
    a2 = b.c(UMG + "CanvasPanelSlot:SetAnchors")
    b.lk(sl, a2, "self")
    b.g.val(a2, "InAnchors", "(Minimum=(X=0.500000,Y=0.500000),Maximum=(X=0.500000,Y=0.500000))")
    a3 = b.c(UMG + "CanvasPanelSlot:SetAlignment")
    b.lk(sl, a3, "self")
    b.g.val(a3, "InAlignment", "(X=0.500000,Y=0.500000)")
    mp = b.c(KML + "MakeVector2D")
    b.g.val(mp, "X", 0.0)
    b.lk((en, "Y"), mp, "Y")
    a4 = b.c(UMG + "CanvasPanelSlot:SetPosition")
    b.lk(sl, a4, "self")
    b.lk((mp, "ReturnValue"), a4, "InPosition")
    ms = b.c(KML + "MakeVector2D")
    b.lk((en, "W"), ms, "X")
    b.lk((en, "H"), ms, "Y")
    a5 = b.c(UMG + "CanvasPanelSlot:SetSize")
    b.lk(sl, a5, "self")
    b.lk((ms, "ReturnValue"), a5, "InSize")
    b.ch(en, cw, cc, add, a1, a2, a3, a4, a5)


def cria_peca(b, fe, nome):
    """CriarWidget da peca `nome`; devolve o no (saida ReturnValue = a peca)"""
    pc = b.c(GS + "GetPlayerController", PlayerIndex=0)
    cr = cria_no(fe, fim="CriarWidget")
    b.g.val(cr, "Class", PECA_C[nome])
    b.lk((pc, "ReturnValue"), cr, "OwningPlayer")
    return cr


def adiciona(b, arr, item):
    n = b.c(ARR + "Array_Add")
    b.lk(b.v(arr), n, "TargetArray")
    b.lk(item, n, "NewItem")
    return n


def f_criar_botao(bp):
    b, en, fe = abre(bp, "CriarBotao")
    cr = cria_peca(b, fe, "Botao")
    w_ = (cr, "ReturnValue")
    s1 = b.setv("Indice", src=(en, "Idx"), alvo=w_, cls=PECA_C["Botao"])
    sf = no_self(fe)
    s2 = b.setv("Dono", src=(sf, "self"), alvo=w_, cls=PECA_C["Botao"])
    dt = b.call("DefinirTexto", alvo=w_, cls=PECA_C["Botao"])
    b.lk((en, "Texto"), dt, "Texto")
    cl = b.call("Colocar")
    b.lk(w_, cl, "Item")
    b.lk((en, "Y"), cl, "Y")
    b.g.val(cl, "W", 380.0)
    b.g.val(cl, "H", 52.0)
    b.ch(en, cr, s1, s2, dt, cl, adiciona(b, "Todos", w_), adiciona(b, "Botoes", w_))


def f_criar_titulo(bp):
    b, en, fe = abre(bp, "CriarTitulo")
    cr = cria_peca(b, fe, "Titulo")
    w_ = (cr, "ReturnValue")
    dt = b.call("DefinirTexto", alvo=w_, cls=PECA_C["Titulo"])
    b.lk((en, "Texto"), dt, "Texto")
    cl = b.call("Colocar")
    b.lk(w_, cl, "Item")
    b.lk((en, "Y"), cl, "Y")
    b.g.val(cl, "W", 440.0)
    b.g.val(cl, "H", 52.0)
    b.ch(en, cr, dt, cl, adiciona(b, "Todos", w_))


def f_criar_nota(bp):
    """CriarNota(Texto, Y): linha de texto pequena (mensagem da tela de sair). Nao e a dica de teclas (essa e a ItemDica)"""
    b, en, fe = abre(bp, "CriarNota")
    cr = cria_peca(b, fe, "Dica")
    w_ = (cr, "ReturnValue")
    dt = b.call("DefinirTexto", alvo=w_, cls=PECA_C["Dica"])
    b.lk((en, "Texto"), dt, "Texto")
    cl = b.call("Colocar")
    b.lk(w_, cl, "Item")
    b.lk((en, "Y"), cl, "Y")
    b.g.val(cl, "W", 440.0)
    b.g.val(cl, "H", 30.0)
    b.ch(en, cr, dt, cl, adiciona(b, "Todos", w_))


def f_criar_dica(bp):
    b, en, fe = abre(bp, "CriarDica")
    cr = cria_peca(b, fe, "Dica")
    w_ = (cr, "ReturnValue")
    sd = b.setv("ItemDica", src=w_)
    cl = b.call("Colocar")
    b.lk(w_, cl, "Item")
    b.lk((en, "Y"), cl, "Y")
    b.g.val(cl, "W", 470.0)
    b.g.val(cl, "H", 40.0)
    b.ch(en, cr, sd, cl, adiciona(b, "Todos", w_))


def f_criar_divisor(bp):
    b, en, fe = abre(bp, "CriarDivisor")
    cr = cria_peca(b, fe, "Titulo")
    w_ = (cr, "ReturnValue")
    df = b.call("DefinirFundo", alvo=w_, cls=PECA_C["Titulo"])
    b.g.val(df, "Cor", lin((AMBAR[0], AMBAR[1], AMBAR[2], 0.60)))
    cl = b.call("Colocar")
    b.lk(w_, cl, "Item")
    b.lk((en, "Y"), cl, "Y")
    b.g.val(cl, "W", 300.0)
    b.g.val(cl, "H", 2.0)
    b.ch(en, cr, df, cl, adiciona(b, "Todos", w_))


def f_criar_painel(bp):
    b, en, fe = abre(bp, "CriarPainel")
    cr = cria_peca(b, fe, "Painel")
    w_ = (cr, "ReturnValue")
    cl = b.call("Colocar")
    b.lk(w_, cl, "Item")
    b.g.val(cl, "Y", CY)
    b.g.val(cl, "W", 500.0)
    b.lk((en, "Altura"), cl, "H")
    b.ch(en, cr, cl, adiciona(b, "Todos", w_))


# telas: nome -> (botoes, titulo, mensagem ou None). O Y de cada peca sai de layout(): o cartao fica centrado em CY e tudo conta a partir do topo
TELAS = {
    "Principal": (["CONTINUAR", "CONFIGURAÇÕES", "SAIR"], "PAUSADO", None),
    "Config": (["ÍCONES", "VOLTAR"], "CONFIGURAÇÕES", None),
    "Sair": (["CANCELAR", "SAIR"], "SAIR DO JOGO?", "Você voltará para a área de trabalho."),
}


def layout(nome):
    """alturas e Y (centro de cada peca, a partir do centro da tela) da tela `nome`"""
    botoes, _t, msg = TELAS[nome]
    extra = 50.0 if msg else 0.0
    h = 270.0 + PASSO * (len(botoes) - 1) + extra
    topo = CY - h / 2.0
    return {"H": h, "titulo": topo + 52.0, "divisor": topo + 98.0, "nota": topo + 142.0, "botao0": topo + 152.0 + extra, "dica": CY + h / 2.0 - 46.0}


def f_montar_tela(bp):
    b, en, fe = abre(bp, "MontarTela")
    lt = b.call("LimparTela")
    s1 = b.setv("Tela", src=(en, "Nome"))
    s2 = b.setv("Indice", 0)
    cfg = b.br(igual(b, (en, "Nome"), "Config"))
    sair = b.br(igual(b, (en, "Nome"), "Sair"))
    j = ale.junc(b)

    def seq(nome):
        botoes, titulo, msg = TELAS[nome]
        ly = layout(nome)
        passos = []
        cp = b.call("CriarPainel")
        b.g.val(cp, "Altura", ly["H"])
        passos.append(cp)
        ct = b.call("CriarTitulo")
        b.lk(texto_lit(b, titulo), ct, "Texto")
        b.g.val(ct, "Y", ly["titulo"])
        passos.append(ct)
        cd = b.call("CriarDivisor")
        b.g.val(cd, "Y", ly["divisor"])
        passos.append(cd)
        if msg:
            cn = b.call("CriarNota")
            b.lk(texto_lit(b, msg), cn, "Texto")
            b.g.val(cn, "Y", ly["nota"])
            passos.append(cn)
        for i, rot in enumerate(botoes):
            cb = b.call("CriarBotao")
            b.lk(texto_lit(b, rot), cb, "Texto")
            b.g.val(cb, "Y", ly["botao0"] + PASSO * i)
            b.g.val(cb, "Idx", i)
            passos.append(cb)
        cdi = b.call("CriarDica")
        b.g.val(cdi, "Y", ly["dica"])
        passos.append(cdi)
        return passos

    b.ch(en, lt, s1, s2, cfg)
    b.ch((cfg, "then"), *seq("Config"), j)
    b.ch((cfg, "else"), sair)
    b.ch((sair, "then"), *seq("Sair"), j)
    b.ch((sair, "else"), *seq("Principal"), j)
    b.ch(j, b.call("AplicarSelecao"), b.call("AtualizarLinhaEstilo"), b.call("AtualizarTextoPausa"))


def assinaturas(bp):
    """funcoes que ganharam entrada (Y) ou nasceram depois dos stubs: ajusta sem recriar"""
    t = tipos()
    graficos = [str(x) for x in BEL.list_graph_names(bp)]
    if "CriarNota" not in graficos:
        ale.cria_funcoes(bp, [("CriarNota", [("Texto", "text"), ("Y", "real")])], t)
        w("  funcao nova: CriarNota")
    for nome in ("CriarTitulo", "CriarDica", "CriarDivisor"):
        fe = BGE.get_graph_editor_by_name(bp, nome)
        pinos = [str(p.get_pin_name()) for p in fe.find_graph_entry_pin().get_owning_node().list_output_pins()]
        if "Y" not in pinos:
            fe.add_graph_input_parameter("Y", t["real"])
            w("  %s ganhou a entrada Y" % nome)


def f_aplicar_selecao(bp):
    b, en, fe = abre(bp, "AplicarSelecao")
    loop = b.g.pos(fe.add_macro_node(MAC + "ForEachLoop"), 300, 0)
    b.lk(b.v("Botoes"), loop, "Array")
    cb = cria_no(fe, fim="CastToWB_LuxPausaBotao", sem=("Class",))
    b.lk((loop, "Array Element"), cb, "Object")
    sel = b.c(KML + "SelectInt")
    b.g.val(sel, "A", 1)
    b.g.val(sel, "B", 0)
    b.lk(b.op("EqualEqual_IntInt", (loop, "Array Index"), b.v("Indice")), sel, "bPickA")
    ds = b.call("DefinirEstado", alvo=(cb, pino_cast(cb)), cls=PECA_C["Botao"])
    b.lk((sel, "ReturnValue"), ds, "Estado")
    b.ch(en, loop)
    b.ch((loop, "LoopBody"), cb, ds)


def f_mover(bp):
    b, en, fe = abre(bp, "Mover")
    n = b.c(ARR + "Array_Length")
    b.lk(b.v("Botoes"), n, "TargetArray")
    ok = b.br(b.op("Greater_IntInt", (n, "ReturnValue"), 0))
    # Indice + Delta + N, sem Add_* (P21: criar um Add_* num BP que ja tem outro derruba o editor): Indice - (-Delta) - (-N)
    neg_d = b.op("Multiply_IntInt", (en, "Delta"), -1)
    neg_n = b.op("Multiply_IntInt", (n, "ReturnValue"), -1)
    soma = b.op("Subtract_IntInt", b.op("Subtract_IntInt", b.v("Indice"), neg_d), neg_n)
    novo = b.op("Percent_IntInt", soma, (n, "ReturnValue"))
    st = b.setv("Indice", src=novo)
    b.ch(en, ok)   # Array_Length e as contas sao nos puros: nao entram na cadeia de execucao
    b.ch((ok, "then"), st, b.call("AplicarSelecao"))


def f_ao_sobre(bp):
    b, en, fe = abre(bp, "AoSobreItem")
    b.ch(en, b.setv("Indice", src=(en, "Idx")), b.call("AplicarSelecao"))


def f_ao_clicar(bp):
    b, en, fe = abre(bp, "AoClicarItem")
    b.ch(en, b.setv("Indice", src=(en, "Idx")), b.call("AplicarSelecao"), b.call("Ativar"))


def tela_ir(b, nome):
    n = b.call("MontarTela")
    b.g.val(n, "Nome", nome)
    return n


def f_ativar(bp):
    b, en, fe = abre(bp, "Ativar")
    i = b.v("Indice")
    t_cfg, t_sair = b.br(igual(b, b.v("Tela"), "Config")), b.br(igual(b, b.v("Tela"), "Sair"))
    b.ch(en, t_cfg)
    # Principal
    p0, p1 = b.br(b.op("EqualEqual_IntInt", i, 0)), b.br(b.op("EqualEqual_IntInt", b.v("Indice"), 1))
    b.ch((t_cfg, "else"), t_sair)
    b.ch((t_sair, "else"), p0)
    b.ch((p0, "then"), b.call("Retomar"))
    b.ch((p0, "else"), p1)
    b.ch((p1, "then"), tela_ir(b, "Config"))
    b.ch((p1, "else"), tela_ir(b, "Sair"))
    # Config: 0 = alterna o estilo dos icones; 1 = voltar
    c0 = b.br(b.op("EqualEqual_IntInt", b.v("Indice"), 0))
    b.ch((t_cfg, "then"), c0)
    b.ch((c0, "then"), b.call("AlternarEstilo"), b.call("AtualizarLinhaEstilo"))
    b.ch((c0, "else"), tela_ir(b, "Principal"))
    # Sair: 0 = cancelar; 1 = sair
    s0 = b.br(b.op("EqualEqual_IntInt", b.v("Indice"), 0))
    b.ch((t_sair, "then"), s0)
    b.ch((s0, "then"), tela_ir(b, "Principal"))
    b.ch((s0, "else"), b.call("SairDoJogo"))


def f_voltar(bp):
    b, en, fe = abre(bp, "Voltar")
    br = b.br(igual(b, b.v("Tela"), "Principal"))
    b.ch(en, br)
    b.ch((br, "then"), b.call("Retomar"))
    b.ch((br, "else"), tela_ir(b, "Principal"))


def f_linha_estilo(bp):
    """Config, linha 0: 'ICONES: AUTO (XBOX)' / XBOX / PLAYSTATION (segue o EstiloManual)"""
    b, en, fe = abre(bp, "AtualizarLinhaEstilo")
    n = b.c(ARR + "Array_Length")
    b.lk(b.v("Botoes"), n, "TargetArray")
    ok = b.br(b.e(igual(b, b.v("Tela"), "Config"), b.op("Greater_IntInt", (n, "ReturnValue"), 0)))
    up = b.c(STR + "ToUpper")
    b.lk(b.v("TipoAtual"), up, "SourceString")
    auto = sel_str(b, "AUTO", b.s(["AUTO (", (up, "ReturnValue"), ")"]), igual(b, b.v("TipoAtual"), "TecladoMouse"))
    up2 = b.c(STR + "ToUpper")
    b.lk(b.v("EstiloManual"), up2, "SourceString")
    estilo = sel_str(b, auto, (up2, "ReturnValue"), igual(b, b.v("EstiloManual"), "Auto"))
    txt = b.s(["ÍCONES: ", estilo])
    conv = b.c(TXT + "Conv_StringToText")
    b.lk(txt, conv, "InString")
    g0 = b.c(ARR + "Array_Get")
    b.lk(b.v("Botoes"), g0, "TargetArray")
    b.g.val(g0, "Index", 0)
    cb = cria_no(fe, fim="CastToWB_LuxPausaBotao", sem=("Class",))
    b.lk((g0, "Item"), cb, "Object")
    dt = b.call("DefinirTexto", alvo=(cb, pino_cast(cb)), cls=PECA_C["Botao"])
    b.lk((conv, "ReturnValue"), dt, "Texto")
    b.ch(en, ok)
    b.ch((ok, "then"), cb, dt)   # Array_Get e puro


def f_atualizar_cursor(bp):
    """com a pausa aberta: cursor so com teclado/mouse (com controle some). IsValid no controle: o EndPlay chama Retomar com o controle ja destruido"""
    b, en, fe = abre(bp, "AtualizarCursor")
    ok = b.br(b.v("bPausado"))
    gpc = b.c(GS + "GetPlayerController", PlayerIndex=0)
    vp = b.br(b.valido((gpc, "ReturnValue")))
    st = b.g.set("bShowMouseCursor", 0, 0, None, "/Script/Engine.PlayerController")
    b.lk((gpc, "ReturnValue"), st, "self")
    b.lk(igual(b, b.v("TipoAtual"), "TecladoMouse"), st, "bShowMouseCursor")
    b.ch(en, ok)
    b.ch((ok, "then"), vp)
    b.ch((vp, "then"), st)


def f_entrada_ligar(bp):
    b, en, fe = abre(bp, "EntradaPausaLigar")
    gpc = b.c(GS + "GetPlayerController", PlayerIndex=0)
    vp = b.br(b.valido((gpc, "ReturnValue")))
    m = b.c(UMGL + "SetInputMode_GameAndUIEx", InMouseLockMode="DoNotLock", bHideCursorDuringCapture="false", bFlushInput="false")
    b.lk((gpc, "ReturnValue"), m, "PlayerController")
    b.ch(en, vp)
    b.ch((vp, "then"), m, b.call("AtualizarCursor"))


def f_entrada_desligar(bp):
    b, en, fe = abre(bp, "EntradaPausaDesligar")
    gpc = b.c(GS + "GetPlayerController", PlayerIndex=0)
    vp = b.br(b.valido((gpc, "ReturnValue")))
    m = b.c(UMGL + "SetInputMode_GameOnly", bFlushInput="false")
    b.lk((gpc, "ReturnValue"), m, "PlayerController")
    st = b.g.set("bShowMouseCursor", 0, 0, "false", "/Script/Engine.PlayerController")
    b.lk((gpc, "ReturnValue"), st, "self")
    b.ch(en, vp)
    b.ch((vp, "then"), m, st)


def f_sair(bp):
    b, en, fe = abre(bp, "SairDoJogo")
    gpc = b.c(GS + "GetPlayerController", PlayerIndex=0)
    q = b.c(KSL + "QuitGame", QuitPreference="Quit", bIgnorePlatformRestrictions="false")
    b.lk((gpc, "ReturnValue"), q, "SpecificPlayer")
    b.ch(en, q)


def f_pausar(bp):
    """Pausar: cria o fundo (WB_LuxPausa), monta a tela principal, liga o modo Game and UI (cursor com mouse) e pausa"""
    limpa_funcao(bp, "Pausar")
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
    av = b.c(UMG + "UserWidget:AddToViewport", ZOrder=100)
    b.lk(b.v("WidgetPausa"), av, "self")
    mt = tela_ir(b, "Principal")
    ep = b.call("EntradaPausaLigar")
    gp = b.c(GS + "SetGamePaused", bPaused="true")
    b.ch(en, pode)
    b.ch((pode, "then"), sp, tem)
    b.ch((tem, "then"), j)
    b.ch((tem, "else"), cr, sw, j)
    b.ch(j, av, mt, ep, gp)


def f_retomar(bp):
    limpa_funcao(bp, "Retomar")
    b, en, fe = abre(bp, "Retomar")
    pode = b.br(b.v("bPausado"))
    s0 = b.setv("bPausado", "false")
    gp = b.c(GS + "SetGamePaused", bPaused="false")
    lt = b.call("LimparTela")
    tem = b.br(b.valido(b.v("WidgetPausa")))
    rm = b.c(UMG + "Widget:RemoveFromParent")
    b.lk(b.v("WidgetPausa"), rm, "self")
    ed = b.call("EntradaPausaDesligar")
    b.ch(en, pode)
    b.ch((pode, "then"), s0, gp, lt, tem)
    b.ch((tem, "then"), rm, ed)
    b.ch((tem, "else"), ed)


def f_dica(bp):
    """AtualizarTextoPausa: a linha de dica (rotulos por dispositivo) na peca ItemDica; depois reaplica o cursor"""
    limpa_funcao(bp, "AtualizarTextoPausa")
    b, en, fe = abre(bp, "AtualizarTextoPausa")
    ok = b.br(b.valido(b.v("ItemDica")))
    passos = []
    for acao, aux in (("AcaoConfirmar", "Aux1"), ("AcaoPausa", "Aux2"), ("AcaoVoltar", "Aux3")):
        c = b.call("ObterRotuloAcao")
        b.lk(b.v(acao), c, "Acao")
        t2s = b.c(TXT + "Conv_TextToString")
        b.lk(b.v("UltRotulo"), t2s, "InText")
        passos += [c, b.setv(aux, src=(t2s, "ReturnValue"))]
    nav = sel_str(b, "[↑ ↓]", "[D-Pad]", igual(b, b.v("TipoAtual"), "TecladoMouse"))
    principal = b.s([nav, " Navegar    [", b.v("Aux1"), "] Selecionar    [", b.v("Aux2"), "] Continuar"])
    outras = b.s([nav, " Navegar    [", b.v("Aux1"), "] Selecionar    [", b.v("Aux3"), "] Voltar"])
    txt = sel_str(b, principal, outras, igual(b, b.v("Tela"), "Principal"))
    conv = b.c(TXT + "Conv_StringToText")
    b.lk(txt, conv, "InString")
    cb = cria_no(fe, fim="CastToWB_LuxPausaDica", sem=("Class",))
    b.lk(b.v("ItemDica"), cb, "Object")
    dt = b.call("DefinirTexto", alvo=(cb, pino_cast(cb)), cls=PECA_C["Dica"])
    b.lk((conv, "ReturnValue"), dt, "Texto")
    b.ch(en, ok)
    b.ch((ok, "then"), *passos, cb, dt, b.call("AtualizarCursor"))


def refaz_evento_ui(bp):
    """EventGraph: Voltar -> Voltar(), Confirmar -> Ativar() (ambos ao SOLTAR), Alternar -> estilo + linha, Cima/Baixo -> Mover. So com a pausa aberta"""
    ge = BGE.get_graph_editor_by_name(bp, "EventGraph")
    b = ge_.B(ge, COMP_C)

    def titulo(n):
        return str(n.get_node_title()).replace("\n", " ")

    def acha(trecho):
        r = [n for n in ge.list_all_nodes() if "EnhancedInputAction" in n.get_class().get_name() and trecho in titulo(n)]
        return r[0] if len(r) == 1 else None

    def corpo(ev, pino):
        """nos alcancaveis pelo exec de `pino` (a cadeia antiga)"""
        vistos, fila = [], [p for p in ev.list_output_pins() if str(p.get_pin_name()) == pino]
        while fila:
            p = fila.pop()
            for q in p.list_connected_pins():
                n = q.get_owning_node()
                if n not in vistos:
                    vistos.append(n)
                    fila += [o for o in n.list_output_pins() if '"exec"' in str(o.get_pin_type_as_json_schema())]
        return vistos

    def evento(nome, y):
        e = acha(nome)
        return e or cria_no(ge, fim="EnhancedActionEvents|" + nome, x=0, y=y)

    def refaz(nome, y, pino, passos_fn):
        ev = evento(nome, y)
        velhos = corpo(ev, pino)
        if velhos:
            ge.remove_nodes(velhos)
        g = b.br(b.v("bPausado"))
        b.g.link(ev, pino, g, b.g.exec_in(g))
        b.ch((g, "then"), *passos_fn())

    def mover(delta):
        n = b.call("Mover")
        b.g.val(n, "Delta", delta)
        return [n]

    refaz("IA_UI_Voltar", 1300, "Triggered", lambda: [b.call("Voltar")])
    refaz("IA_UI_Confirmar", 1700, "Triggered", lambda: [b.call("Ativar")])
    refaz("IA_UI_Alternar", 2100, "Started", lambda: [b.call("AlternarEstilo"), b.call("AtualizarLinhaEstilo")])
    refaz("IA_UI_Cima", 2500, "Started", lambda: mover(-1))
    refaz("IA_UI_Baixo", 2900, "Started", lambda: mover(1))
    # nos puros que ficaram soltos (get de variavel sem uso)
    soltos = [n for n in ge.list_all_nodes() if not any(p.list_connected_pins() for p in n.list_all_pins()) and "Event" not in n.get_class().get_name()
              and "Comment" not in n.get_class().get_name()]
    if soltos:
        ge.remove_nodes(soltos)


def etapa_cursor():
    """reescreve so AtualizarCursor / EntradaPausaLigar / EntradaPausaDesligar (guardas IsValid) sem mexer no resto do BP_LuxEntrada. Sem Add_* aqui"""
    bp = EAL.load_asset(COMP)
    for nome, f in (("AtualizarCursor", f_atualizar_cursor), ("EntradaPausaLigar", f_entrada_ligar), ("EntradaPausaDesligar", f_entrada_desligar)):
        w("  funcao", nome)
        limpa_funcao(bp, nome)
        f(bp)
    BEL.compile_blueprint(bp)
    e = ge_.erros(bp)
    if e:
        raise Aborta("BP_LuxEntrada compilou com erros/avisos (nada salvo): %s" % e)
    w("BP_LuxEntrada (cursor) salvo:", EAL.save_loaded_asset(bp, False))


def etapa_preparo():
    """roda no commandlet (processo limpo): assinaturas novas (Y; CriarNota), Mover sem corpo (tira os Add_* antigos) e compila. Assim o BP que o
    etapa_comp edita no editor nao tem nenhum Add_* e as funcoes novas ja estao registradas para serem chamadas por caminho"""
    bp = EAL.load_asset(COMP)
    assinaturas(bp)
    limpa_funcao(bp, "Mover")
    BEL.compile_blueprint(bp)
    w("preparo: BP_LuxEntrada compilado; erros/avisos (esperados: funcoes vazias nao dao erro):", ge_.erros(bp))
    w("preparo salvo:", EAL.save_loaded_asset(bp, False))


def etapa_comp():
    bp = EAL.load_asset(COMP)
    for nome in PECAS.values():
        if not EAL.load_asset(nome):
            raise Aborta("falta a peca %s: rode a etapa itens antes" % nome)
    assinaturas(bp)
    funcs = (("LimparTela", f_limpar_tela), ("Colocar", f_colocar), ("CriarBotao", f_criar_botao), ("CriarTitulo", f_criar_titulo), ("CriarNota", f_criar_nota), ("CriarDica", f_criar_dica),
             ("CriarDivisor", f_criar_divisor), ("CriarPainel", f_criar_painel), ("MontarTela", f_montar_tela), ("AplicarSelecao", f_aplicar_selecao), ("Mover", f_mover),
             ("AoSobreItem", f_ao_sobre), ("AoClicarItem", f_ao_clicar), ("Ativar", f_ativar), ("Voltar", f_voltar), ("AtualizarLinhaEstilo", f_linha_estilo),
             ("AtualizarCursor", f_atualizar_cursor), ("EntradaPausaLigar", f_entrada_ligar), ("EntradaPausaDesligar", f_entrada_desligar), ("SairDoJogo", f_sair),
             ("Pausar", f_pausar), ("Retomar", f_retomar), ("AtualizarTextoPausa", f_dica))
    for nome, f in funcs:
        w("  funcao", nome)
        limpa_funcao(bp, nome)   # idempotente: um aborto anterior deixa o estado parcial so na memoria do editor
        f(bp)
    refaz_evento_ui(bp)
    BEL.compile_blueprint(bp)   # so aqui (P21: nao compile entre um Add_* e outro)
    e = ge_.erros(bp)
    if e:
        raise Aborta("BP_LuxEntrada compilou com erros/avisos (nada salvo): %s" % e)
    w("BP_LuxEntrada salvo:", EAL.save_loaded_asset(bp, False))


# ------------------------------------------------------------------ sondar / verificar / desfazer
NOVOS_ASSETS = [DIR + "/IA_UI_Cima", DIR + "/IA_UI_Baixo"] + list(PECAS.values())
ALTERADOS = ["Content/Masion/LUX/Entrada/BP_LuxEntrada.uasset", "Content/Masion/LUX/Entrada/WB_LuxPausa.uasset", "Content/Masion/LUX/Entrada/IMC_LuxEntrada.uasset",
             "Tools/Player/gamepad_input.py", "Tools/Player/gamepad_pie_teste.py"]


def sondar():
    w("pecas:", {k: bool(EAL.does_asset_exist(v)) for k, v in PECAS.items()})
    bp = EAL.load_asset(COMP)
    graficos = [str(x) for x in BEL.list_graph_names(bp)] if bp else []
    w("BP_LuxEntrada: funcoes novas presentes:", {n: (n in graficos) for n, _ in FUNC_NOVAS})
    for nome, tp, ed, pd in VARS_NOVAS:
        w("   variavel", nome, "presente:", nome in [str(x) for x in BEL.list_member_variable_names(bp)] if bp else False)
    verificar()


def verificar(silencioso=False):
    """pecas completas e compilando limpas; BP_LuxEntrada com todas as funcoes e sem erro; acoes de navegacao existentes (no commandlet ou no editor)"""
    falhas = []
    for nome, caminho in PECAS.items():
        bp = EAL.load_asset(caminho)
        if not bp:
            falhas.append("peca %s nao existe" % nome)
            continue
        if not peca_completa(bp, nome):
            falhas.append("peca %s incompleta (faltam graficos)" % nome)
        BEL.compile_blueprint(bp)
        e = ge_.erros(bp)
        if e:
            falhas.append("peca %s compila com erros/avisos: %s" % (nome, e[:2]))
    bp = EAL.load_asset(COMP)
    if not bp:
        falhas.append("BP_LuxEntrada nao existe")
    else:
        graficos = [str(x) for x in BEL.list_graph_names(bp)]
        faltam = [n for n, _ in FUNC_NOVAS if n not in graficos]
        if faltam:
            falhas.append("BP_LuxEntrada sem as funcoes %s" % faltam)
        BEL.compile_blueprint(bp)
        e = ge_.erros(bp)
        if e:
            falhas.append("BP_LuxEntrada compila com erros/avisos: %s" % e[:3])
    for a in (DIR + "/IA_UI_Cima", DIR + "/IA_UI_Baixo"):
        if not EAL.does_asset_exist(a):
            falhas.append("acao %s nao existe (rode gamepad_input.py instalar)" % a)
    wp = EAL.load_asset(WBP)
    if wp:
        BEL.compile_blueprint(wp)
        e = ge_.erros(wp)
        if e:
            falhas.append("WB_LuxPausa compila com erros/avisos: %s" % e[:2])
    if not silencioso:
        w("verificar:", ("FAIL %s" % falhas) if falhas else "PASS")
    return falhas


def desfazer():
    """volta a pausa de texto simples de 01/10. O BP_LuxEntrada referencia as pecas: restaure o que mudou pelo git ANTES de apagar os assets novos"""
    w("desfazer: nada e apagado por script (o BP_LuxEntrada referencia as pecas). No projeto, com o editor FECHADO:")
    w("   git checkout -- " + " ".join(ALTERADOS))
    w("   depois apague os assets novos (sem referenciadores): " + ", ".join(a.replace("/Game/", "Content/") + ".uasset" for a in NOVOS_ASSETS))


# ------------------------------------------------------------------ main
def main():
    modo = sys.argv[1] if len(sys.argv) > 1 else "sondar"
    etapas = sys.argv[2:]
    w("modo:", modo, etapas)
    try:
        if modo == "instalar":
            for e in (etapas or ["stubs", "itens", "pausa", "comp"]):
                {"stubs": etapa_stubs, "itens": etapa_itens, "pausa": etapa_pausa, "estilo": etapa_estilo, "preparo": etapa_preparo, "cursor": etapa_cursor, "comp": etapa_comp}[e]()
        elif modo in ("sondar", "verificar", "desfazer"):
            {"sondar": sondar, "verificar": verificar, "desfazer": desfazer}[modo]()
        else:
            w("modo desconhecido:", modo)
    except Aborta as e:
        w("ABORTA:", e)
    except Exception:
        w("ERRO:", traceback.format_exc())


main()
