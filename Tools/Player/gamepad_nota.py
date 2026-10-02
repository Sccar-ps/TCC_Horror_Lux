# LUX: suporte a controle nos bilhetes do pack (WB_Note, aberto pelo BP_BaseNote) - ETAPA 4. Depende de gamepad_input.py e gamepad_entrada.py instalar.
# O bilhete e um modal: o BP_BaseNote cria o widget, poe o jogo em UI Only (o motor IGNORA o Enhanced Input nesse modo: SetIgnoreInput) e so tinha
# botoes de clique. Nao existe outro menu no projeto (o pause e a tela do BP_LuxEntrada).
# O que muda (so ADICIONA; nada do que existia e apagado ou reordenado):
#  WB_Note
#   - is_focusable = true (default da classe): o widget recebe o foco e, com ele, as teclas.
#   - 3 eventos novos (LuxFechar, LuxAnterior, LuxProximo) ligados AOS MESMOS nos que os cliques do BTN_Close, BTN_Prev e BTN_Next ja usam: a logica
#     de fechar (som, volta ao modo de jogo, despausa, fade) e de virar pagina (guarda de animacao e de limite) continua uma so.
#   - override de OnKeyDown: pergunta ao Enhanced Input a que ACAO a tecla pertence (BPFL_LuxEntrada.TeclaMapeadaNaAcao), sem tecla fixa:
#       IA_UI_Voltar (B/Circle, Backspace) e IA_Pausa (Start/Options, Esc, P) fecham; IA_UI_Anterior (LB/L1, D-Pad, stick, seta esq.) e
#       IA_UI_Proximo (RB/R1, D-Pad, stick, seta dir.) viram pagina; IA_UI_Confirmar (A/Cross, Enter, Espaco) avanca e, na ultima pagina, fecha.
#       Tecla repetida (segurar o A que abriu o bilhete) e ignorada.
#  BP_BaseNote
#   - o pino InWidgetToFocus do Set Input Mode UI Only ganha o widget recem-criado (antes vazio): e o que entrega o foco ao WB_Note.
#  Config/DefaultInput.ini
#   - [/Script/EnhancedInput.EnhancedInputDeveloperSettings] DefaultMappingContexts += IMC_LuxEntrada (prioridade 1): o contexto fica ativo em qualquer
#     mapa e pawn (o bilhete tambem existe no Mapa_A do pack), sem depender do componente do Cowboy. Registrar duas vezes e inofensivo.
# Os botoes de clique, o mouse e o teclado continuam como eram.
#   py "<projeto>/Tools/Player/gamepad_nota.py" sondar|instalar|verificar|desfazer
import os, sys, traceback
import unreal

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(AQUI), "Loop"))
sys.path.insert(0, AQUI)
import add_loop_events as ale
import gamepad_entrada as ge_

EAL, BEL, BGE = unreal.EditorAssetLibrary, unreal.BlueprintEditorLibrary, unreal.BlueprintGraphEditor
WB = "/Game/FPMovement/Player/Widgets/UserCreated/Note/WB_Note"
WB_C = WB + ".WB_Note_C"
BASE = "/Game/FPMovement/Blueprints/Notes/BP_BaseNote"
PDA_NOTE_C = "/Game/FPMovement/Blueprints/Notes/Structure/PDA_Note.PDA_Note_C"
DIR = "/Game/Masion/LUX/Entrada"
IA = {n: DIR + "/" + n + "." + n for n in ("IA_UI_Voltar", "IA_Pausa", "IA_UI_Anterior", "IA_UI_Proximo", "IA_UI_Confirmar")}
EVENTOS = (("LuxFechar", "BTN_Close"), ("LuxAnterior", "BTN_Prev"), ("LuxProximo", "BTN_Next"))
INI = os.path.join(os.path.dirname(os.path.dirname(AQUI)), "Config", "DefaultInput.ini")
SECAO = "[/Script/EnhancedInput.EnhancedInputDeveloperSettings]"
LINHA = '+DefaultMappingContexts=(InputMappingContext=/Game/Masion/LUX/Entrada/IMC_LuxEntrada.IMC_LuxEntrada,Priority=1)'
LOG = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), "LuxSnapshots", "gamepad_nota_log.txt")
KIL = ge_.KIL
UMGL = "/Script/UMG.WidgetBlueprintLibrary:"


def w(*a):
    line = " ".join(str(x) for x in a)
    unreal.log("[LUX nota] " + line)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")
        fh.flush()


class Aborta(Exception):
    pass


def titulo(n):
    return str(n.get_node_title()).replace("\n", " ")


def acha(ge, trecho):
    r = [n for n in ge.list_all_nodes() if trecho in titulo(n)]
    if len(r) != 1:
        raise Aborta("esperava 1 no com '%s' em %s e achei %d" % (trecho, ge.get_graph().get_name(), len(r)))
    return r[0]


def b_nota(ge):
    return ge_.B(ge, WB_C)


# ------------------------------------------------------------------ WB_Note
def eventos_novos(bp):
    ge = BGE.get_graph_editor_by_name(bp, "EventGraph")
    graficos = [str(x) for x in BEL.list_graph_names(bp)]
    for nome, botao in EVENTOS:
        if any(titulo(n).startswith(nome) for n in ge.list_all_nodes()):
            continue
        orig = acha(ge, "On Clicked (%s)" % botao)
        destinos = orig.find_output_pin("then").list_connected_pins()
        if not destinos:
            raise Aborta("o clique de %s nao esta ligado a nada" % botao)
        ev = ge.add_custom_event_node(nome)
        for d in destinos:
            if not ev.find_output_pin("then").try_create_connection(d):
                raise Aborta("nao liguei %s ao destino do clique de %s" % (nome, botao))
        w("evento", nome, "ligado ao destino do clique de", botao)


def build_onkeydown(bp):
    if "OnKeyDown" in [str(x) for x in BEL.list_graph_names(bp)]:
        w("OnKeyDown ja esta sobrescrito: mantido")
        return
    g = BEL.add_function_override(bp, "OnKeyDown")
    if not g:
        raise Aborta("add_function_override(OnKeyDown) falhou")
    fe = BGE.get_graph_editor_by_name(bp, "OnKeyDown")
    b = b_nota(fe)
    nos = list(fe.list_all_nodes())
    entrada = next(n for n in nos if "FunctionEntry" in n.get_class().get_name())
    resultado = next(n for n in nos if "FunctionResult" in n.get_class().get_name())
    # o override nasce com um "chama o pai" entre a entrada e o retorno: sai (o pai so devolve Unhandled)
    sai = [n for n in nos if n not in (entrada, resultado)]
    if sai:
        fe.remove_nodes(sai)
    entrada.find_output_pin("then").break_pin_links()
    ret_nao = resultado
    ret_sim = fe.add_return_node()
    unh = b.c(UMGL + "Unhandled")
    han = b.c(UMGL + "Handled")
    b.lk((unh, "ReturnValue"), ret_nao, "ReturnValue")
    b.lk((han, "ReturnValue"), ret_sim, "ReturnValue")
    tecla = b.c(KIL + "GetKey")
    b.lk((entrada, "InKeyEvent"), tecla, "Input")
    rep = b.c(KIL + "InputEvent_IsRepeat")
    b.lk((entrada, "InKeyEvent"), rep, "Input")
    pc = b.c(ge_.GS + "GetPlayerController", PlayerIndex=0)

    def e_acao(nome):
        n = b.c(ge_.BPFL_C + ":TeclaMapeadaNaAcao", Acao=IA[nome])
        b.lk((pc, "ReturnValue"), n, "Controle")
        b.lk((tecla, "ReturnValue"), n, "Tecla")
        return (n, "bMapeada")

    fechar = b.ou(e_acao("IA_UI_Voltar"), e_acao("IA_Pausa"))
    # ultima pagina: NextPageIndex + 1 == Length(Data.Pages) (a mesma conta do clique em Proxima)
    pag = b.g.get("Pages", 0, 0, PDA_NOTE_C)
    dado = b.v("Data")
    b.g.link(dado[0], "Data", pag, "self")
    tam = b.c(ale.ARR + "Array_Length")
    b.lk((pag, "Pages"), tam, "TargetArray")
    ultima = b.op("EqualEqual_IntInt", b.op("Add_IntInt", b.v("NextPageIndex"), 1), (tam, "ReturnValue"))
    br_rep, br_f, br_a, br_p, br_c, br_u = b.br((rep, "ReturnValue")), b.br(fechar), b.br(e_acao("IA_UI_Anterior")), b.br(e_acao("IA_UI_Proximo")), \
        b.br(e_acao("IA_UI_Confirmar")), b.br(ultima)
    f1, a1, p1, f2, p2 = b.call("LuxFechar"), b.call("LuxAnterior"), b.call("LuxProximo"), b.call("LuxFechar"), b.call("LuxProximo")
    b.ch(entrada, br_rep)
    b.ch((br_rep, "then"), ret_nao)
    b.ch((br_rep, "else"), br_f)
    b.ch((br_f, "then"), f1, ret_sim)
    b.ch((br_f, "else"), br_a)
    b.ch((br_a, "then"), a1, ret_sim)
    b.ch((br_a, "else"), br_p)
    b.ch((br_p, "then"), p1, ret_sim)
    b.ch((br_p, "else"), br_c)
    b.ch((br_c, "then"), br_u)
    b.ch((br_c, "else"), ret_nao)
    b.ch((br_u, "then"), f2, ret_sim)
    b.ch((br_u, "else"), p2, ret_sim)
    w("OnKeyDown sobrescrito (Voltar/Pausa fecham; Anterior/Proximo viram pagina; Confirmar avanca e fecha na ultima; repeticao ignorada)")


def patch_wb():
    for p in (ge_.BPFL, "/Game/FPMovement/Blueprints/Notes/Structure/PDA_Note") + tuple(IA.values()):   # classes/assets usados por caminho nos nos
        if not EAL.load_asset(p.split(".")[0]):
            raise Aborta("asset nao encontrado: " + p)
    bp = EAL.load_asset(WB)
    base = ge_.erros(bp)
    w("WB_Note: erros/avisos antes de mexer: %d" % len(base))
    eventos_novos(bp)
    BEL.compile_blueprint(bp)
    build_onkeydown(bp)
    cdo = unreal.get_default_object(bp.generated_class())
    if not cdo.get_editor_property("is_focusable"):
        cdo.set_editor_property("is_focusable", True)
        w("WB_Note: is_focusable = true")
    BEL.compile_blueprint(bp)
    BEL.compile_blueprint(bp)
    novos = [e for e in ge_.erros(bp) if e not in base]
    if novos:
        raise Aborta("WB_Note com erros/avisos NOVOS: %s" % novos)
    return bp


# ------------------------------------------------------------------ BP_BaseNote
def patch_base():
    bp = EAL.load_asset(BASE)
    ge = BGE.get_graph_editor_by_name(bp, "EventGraph")
    modo = acha(ge, "Set Input Mode UI Only")
    pino = modo.find_input_pin("InWidgetToFocus")
    if pino.list_connected_pins():
        w("BP_BaseNote: InWidgetToFocus ja esta ligado: mantido")
        return bp
    base = ge_.erros(bp)
    criar = acha(ge, "Criar Widget")
    if not criar.find_output_pin("ReturnValue").try_create_connection(pino):
        raise Aborta("nao liguei o widget criado ao InWidgetToFocus")
    BEL.compile_blueprint(bp)
    BEL.compile_blueprint(bp)
    novos = [e for e in ge_.erros(bp) if e not in base]
    if novos:
        raise Aborta("BP_BaseNote com erros/avisos NOVOS: %s" % novos)
    w("BP_BaseNote: Criar Widget -> Set Input Mode UI Only.InWidgetToFocus")
    return bp


# ------------------------------------------------------------------ DefaultInput.ini
def patch_ini():
    txt = open(INI, encoding="utf-8").read()
    if LINHA in txt:
        w("DefaultInput.ini ja tem o contexto padrao")
        return False
    nl = "\r\n" if "\r\n" in txt else "\n"
    if SECAO in txt:
        txt = txt.replace(SECAO, SECAO + nl + LINHA, 1)
    else:
        txt = txt.rstrip() + nl + nl + SECAO + nl + LINHA + nl
    open(INI, "w", encoding="utf-8", newline="").write(txt)
    w("DefaultInput.ini: DefaultMappingContexts += IMC_LuxEntrada (prioridade 1)")
    return True


# ------------------------------------------------------------------ verificar / instalar
def verificar():
    falhas = []
    bp = EAL.load_asset(WB)
    graficos = [str(x) for x in BEL.list_graph_names(bp)]
    if "OnKeyDown" not in graficos:
        falhas.append("WB_Note sem o override de OnKeyDown")
    ge = BGE.get_graph_editor_by_name(bp, "EventGraph")
    for nome, _ in EVENTOS:
        if not [n for n in ge.list_all_nodes() if titulo(n).startswith(nome)]:
            falhas.append("WB_Note sem o evento " + nome)
    if not unreal.get_default_object(bp.generated_class()).get_editor_property("is_focusable"):
        falhas.append("WB_Note nao e focavel")
    if bp.get_editor_property("status") != unreal.BlueprintStatus.BS_UP_TO_DATE:
        falhas.append("WB_Note nao esta compilado")
    # os cliques continuam ligados (nada foi desligado)
    for _, botao in EVENTOS:
        if not acha(ge, "On Clicked (%s)" % botao).find_output_pin("then").list_connected_pins():
            falhas.append("o clique de %s perdeu a ligacao" % botao)
    base = EAL.load_asset(BASE)
    gb = BGE.get_graph_editor_by_name(base, "EventGraph")
    if not acha(gb, "Set Input Mode UI Only").find_input_pin("InWidgetToFocus").list_connected_pins():
        falhas.append("BP_BaseNote: InWidgetToFocus vazio")
    if LINHA not in open(INI, encoding="utf-8").read():
        falhas.append("DefaultInput.ini sem o contexto padrao")
    w("verificar:", ("FAIL %s" % falhas) if falhas else "PASS")
    return falhas


def instalar():
    patch_wb()
    patch_base()
    patch_ini()   # so acrescenta uma linha (o IMC_LuxEntrada ja existe em disco)
    f = verificar()
    if f:
        raise Aborta("verificar FAIL (assets nao salvos): %s" % f)
    for p in (WB, BASE):
        ok = EAL.save_loaded_asset(EAL.load_asset(p), False)
        w("salvo", p, ok)
        if not ok:
            raise Aborta("falhou ao salvar " + p)


def sondar():
    bp = EAL.load_asset(WB)
    w("override OnKeyDown:", "OnKeyDown" in [str(x) for x in BEL.list_graph_names(bp)], "| focavel:", unreal.get_default_object(bp.generated_class()).get_editor_property("is_focusable"))
    ge = BGE.get_graph_editor_by_name(bp, "EventGraph")
    w("eventos Lux*:", [titulo(n) for n in ge.list_all_nodes() if titulo(n).startswith("Lux")])
    w("titulos dos eventos de clique:", [titulo(n) for n in ge.list_all_nodes() if "On Clicked" in titulo(n)])
    w("DefaultInput.ini tem o contexto:", LINHA in open(INI, encoding="utf-8").read())


def desfazer():
    w("desfazer: o WB_Note e o BP_BaseNote voltam com `git checkout -- Content/FPMovement/Player/Widgets/UserCreated/Note/WB_Note.uasset Content/FPMovement/Blueprints/Notes/BP_BaseNote.uasset`;"
      " no Config/DefaultInput.ini apague a linha DefaultMappingContexts do IMC_LuxEntrada.")


def main():
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    open(LOG, "w", encoding="utf-8").close()
    modo = next((a for a in sys.argv[1:] if a in ("sondar", "instalar", "verificar", "desfazer")), "sondar")
    w("modo:", modo)
    try:
        {"sondar": sondar, "instalar": instalar, "verificar": verificar, "desfazer": desfazer}[modo]()
    except Aborta as ex:
        w("ABORTADO:", ex)
    except Exception:
        w("ERRO " + traceback.format_exc())


if __name__ == "__main__":
    main()
