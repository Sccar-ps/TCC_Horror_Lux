# LUX: TESTE NO PIE do MENU DE PAUSA (Continuar / Configuracoes / Sair). Roda DENTRO do editor (Python Remote Execution) e nao salva nada.
#   1) gamepad_pie_injetor.py   (BPFL descartavel que entrega o subsistema do Enhanced Input; nao salve)
#   2) py "<projeto>/Tools/Player/gamepad_pie_pausa_menu.py" <rotulo>   -> Saved/LuxSnapshots/pausa_menu/<rotulo>/menu_log.txt e menu_result.json (+ capturas)
# Testa, na ordem: acoes novas (Cima/Baixo) e teclas; tela principal (textos, selecao, cores); navegacao e volta ao topo; Configuracoes (estilo dos icones);
# Sair (confirmacao); dica por dispositivo; cursor (so com teclado/mouse); BLOQUEIO dos controles com o jogo pausado (mover, olhar) e RETORNO ao continuar;
# limpeza ao continuar (sem pecas sobrando); pausa por cima de outra pausa; varios ciclos; e, se o editor estiver em primeiro plano, ENTRADA REAL do sistema
# (teclas Cima/Baixo/Enter/Backspace/Esc e o mouse: passar seleciona, soltar o botao ativa). Por ultimo, Sair encerra o PIE.
# Regras do vault: nunca set_editor_property no componente no PIE; injete com inject_input_vector_for_action.
import ctypes, ctypes.wintypes, glob, json, math, os, shutil, sys, time, traceback, unreal

ROT = sys.argv[1] if len(sys.argv) > 1 else "m1"
SAVED = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
OUT = os.path.join(SAVED, "LuxSnapshots", "pausa_menu", ROT)
os.makedirs(OUT, exist_ok=True)
LOG = os.path.join(OUT, "menu_log.txt")
open(LOG, "w", encoding="utf-8").close()
L = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
UES = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
GS, SL = unreal.GameplayStatics, unreal.SystemLibrary
DIR = "/Game/Masion/LUX/Entrada"
ACT = "/Game/FPMovement/Player/Input/Actions/"
IA = {n: unreal.load_asset(DIR + "/" + n) for n in ("IA_Pausa", "IA_UI_Confirmar", "IA_UI_Voltar", "IA_UI_Alternar", "IA_UI_Cima", "IA_UI_Baixo", "IA_UI_Anterior", "IA_UI_Proximo")}
IA["IA_Move"] = unreal.load_asset(ACT + "IA_Move")
IA["IA_Look"] = unreal.load_asset(ACT + "IA_Look")
COMP_CLS = unreal.load_object(None, DIR + "/BP_LuxEntrada.BP_LuxEntrada_C")
WBP_CLS = unreal.load_object(None, DIR + "/WB_LuxPausa.WB_LuxPausa_C")
S = {"res": [], "t0": time.time()}
AMBAR_R = 0.5            # canal R da faixa: selecionado ~0,85; em repouso ~0,20
VK = {"Cima": 0x26, "Baixo": 0x28, "Enter": 0x0D, "Backspace": 0x08}


def w(*a):
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(" ".join(str(x) for x in a) + "\n")


def chk(nome, ok, detalhe=""):
    S["res"].append({"teste": nome, "ok": bool(ok), "detalhe": str(detalhe)})
    w(("PASS " if ok else "FAIL ") + nome + ((" | " + str(detalhe)) if detalhe != "" else ""))


def espera(seg):
    t0 = time.time()
    while time.time() - t0 < seg:
        yield


def cget(n):
    return S["comp"].get_editor_property(n)


def tipo(forcado=None, manual=None):
    if manual is not None:
        S["comp"].call_method("DefinirEstilo", (manual,))
    if forcado is not None:
        S["comp"].call_method("DefinirTipoForcado", (forcado,))


def injeta(nome, valor=1.0):
    S["sub"].inject_input_vector_for_action(IA[nome], unreal.Vector(valor, 0.0, 0.0), [], [])


def teclas(acao):
    return [str(k.get_editor_property("key_name")) for k in S["sub"].query_keys_mapped_to_action(IA[acao])]


def texto_de(wd, idx=1):
    return str(wd.get_editor_property("HorizontalBox").get_child_at(idx).get_content().get_editor_property("text"))


def faixa_r(wd):
    return wd.get_editor_property("HorizontalBox").get_child_at(0).get_editor_property("brush_color").r


def botoes():
    return list(cget("Botoes"))


def diag(rot):
    """uma linha de estado no log (so para investigar quando um passo falha)"""
    try:
        p = ctypes.wintypes.POINT()
        U32.GetCursorPos(ctypes.byref(p))
        w("   [estado] %-26s pausado=%s bPausado=%s Tela=%r Indice=%s cursor=%s hovered=%s widget=%s frente=%s mouseSO=(%d,%d)" % (rot, GS.is_game_paused(S["world"]), cget("bPausado"),
            cget("Tela"), cget("Indice"), S["pc"].get_editor_property("show_mouse_cursor"), [b.is_hovered() for b in botoes()], len(pausa_aberta()), editor_na_frente(), p.x, p.y))
    except Exception as e:
        w("   [estado] %s: erro %s" % (rot, e))


def todos():
    return list(cget("Todos"))


def por_classe(trecho):
    return [x for x in todos() if trecho in x.get_class().get_name()]


def titulo():
    t = por_classe("Titulo")      # [titulo, divisor]: o titulo e o primeiro com texto
    for x in t:
        s = texto_de(x)
        if s:
            return s
    return ""


def dica():
    d = cget("ItemDica")
    return texto_de(d) if d else None


def selecionado():
    bs = botoes()
    sel = [i for i, b in enumerate(bs) if faixa_r(b) > AMBAR_R]
    return sel


def pausa_aberta():
    return [x for x in unreal.WidgetLibrary.get_all_widgets_of_class(S["world"], WBP_CLS, False) if x.is_in_viewport()]


def shot(nome):
    antes = set(glob.glob(os.path.join(SAVED, "Screenshots", "**", "*.png"), recursive=True))
    SL.execute_console_command(S["world"], "Shot ShowUI", S["pc"])
    t0 = time.time()
    while time.time() - t0 < 5.0:
        novos = [f for f in set(glob.glob(os.path.join(SAVED, "Screenshots", "**", "*.png"), recursive=True)) - antes if os.path.getsize(f) > 1000]
        if novos:
            shutil.move(sorted(novos, key=os.path.getmtime)[-1], os.path.join(OUT, nome + ".png"))
            return True
        yield
    return False


# ---- entrada real do sistema operacional (so com o editor em primeiro plano: senao a tecla/clique iria para outra janela)
U32 = ctypes.windll.user32


def editor_na_frente():
    try:
        h = U32.GetForegroundWindow()
        pid = ctypes.c_ulong(0)
        U32.GetWindowThreadProcessId(h, ctypes.byref(pid))
        return pid.value == os.getpid()
    except Exception:
        return False


def tecla_real(nome):
    vk = VK[nome]
    U32.keybd_event(vk, 0, 0, 0)
    time.sleep(0.05)
    U32.keybd_event(vk, 0, 2, 0)


def centro_botao_px(idx):
    """posicao em pixels da viewport do centro do botao idx (centro da tela + Y x escala de DPI do UMG)"""
    vs = unreal.WidgetLayoutLibrary.get_viewport_size(S["world"])
    esc = unreal.WidgetLayoutLibrary.get_viewport_scale(S["world"])
    n = len(botoes())
    h = 270.0 + 68.0 * (n - 1) + (50.0 if cget("Tela") == "Sair" else 0.0)
    topo = 10.0 - h / 2.0
    y = topo + 152.0 + (50.0 if cget("Tela") == "Sair" else 0.0) + 68.0 * idx
    return int(vs.x / 2.0), int(vs.y / 2.0 + y * esc)


def mouse_para(x, y):
    """posiciona o cursor na viewport e mexe 2 pixels de verdade (mouse_event): so assim o Slate recebe movimento e dispara o OnMouseEnter"""
    S["pc"].set_mouse_location(x, y)
    U32.mouse_event(0x0001, 2, 2, 0, 0)
    time.sleep(0.05)
    U32.mouse_event(0x0001, -2, -2, 0, 0)


def mouse_sobre(idx, limite=1.5):
    """prende o cursor no centro do botao idx ate o jogo o marcar como 'hovered' e selecionado (ou estourar `limite`): o usuario mexendo no mouse fisico
    durante o teste tira o cursor do lugar, entao reposiciona a cada quadro"""
    t0 = time.time()
    while time.time() - t0 < limite:
        x, y = centro_botao_px(idx)
        mouse_para(x, y)
        yield
        yield
        bs = botoes()
        if len(bs) > idx and bs[idx].is_hovered() and cget("Indice") == idx:
            return True
    p = ctypes.wintypes.POINT()
    U32.GetCursorPos(ctypes.byref(p))
    S["mouse_info"] = "alvo px=%s | cursor SO=(%d,%d) | jogo=%s | hovered=%s | Indice=%s | frente=%s" % ((x, y), p.x, p.y, S["pc"].get_mouse_position(), [b.is_hovered() for b in botoes()], cget("Indice"), editor_na_frente())
    w("   diagnostico do mouse:", S["mouse_info"])
    return False


def clique_real():
    U32.mouse_event(0x0002, 0, 0, 0, 0)
    time.sleep(0.06)
    U32.mouse_event(0x0004, 0, 0, 0, 0)


_U = ctypes.WinDLL("user32")   # instancia propria: prototipos de 64 bits so aqui, sem mexer nas chamadas acima
_U.WindowFromPoint.argtypes, _U.WindowFromPoint.restype = [ctypes.wintypes.POINT], ctypes.c_void_p
_U.GetAncestor.argtypes, _U.GetAncestor.restype = [ctypes.c_void_p, ctypes.c_uint], ctypes.c_void_p
_U.GetWindowThreadProcessId.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
_U.GetWindowTextW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]


def janela_sob_cursor():
    """(pid, titulo) da janela de topo sob o cursor do SO. O mouse real so vale se for o editor: uma janela flutuante por cima do viewport
    (ex.: 'Log de Mensagens', que o PIE abre sozinho quando ha erro de Blueprint) engole o movimento e o clique"""
    p = ctypes.wintypes.POINT()
    U32.GetCursorPos(ctypes.byref(p))
    h = _U.GetAncestor(_U.WindowFromPoint(p), 2)   # GA_ROOT
    pid = ctypes.c_ulong(0)
    _U.GetWindowThreadProcessId(h, ctypes.byref(pid))
    buf = ctypes.create_unicode_buffer(256)
    _U.GetWindowTextW(h, buf, 256)
    return pid.value, buf.value


def anda(vec, seg):
    """injeta IA_Move por `seg` s e devolve a distancia andada (cm)"""
    p0 = S["pawn"].get_actor_location()
    t0 = time.time()
    while time.time() - t0 < seg:
        S["sub"].inject_input_vector_for_action(IA["IA_Move"], vec, [], [])
        yield
    yield from espera(0.2)
    p1 = S["pawn"].get_actor_location()
    return math.sqrt((p1.x - p0.x) ** 2 + (p1.y - p0.y) ** 2)


def gira(seg):
    """injeta IA_Look (X) por `seg` s e devolve o quanto o yaw mudou"""
    y0 = S["pc"].get_control_rotation().yaw
    t0 = time.time()
    while time.time() - t0 < seg:
        S["sub"].inject_input_vector_for_action(IA["IA_Look"], unreal.Vector(0.2, 0.0, 0.0), [], [])   # 0,5 grau por quadro (2,0 daria uma volta inteira a ~120 FPS)
        yield
    yield from espera(0.2)
    return abs(((S["pc"].get_control_rotation().yaw - y0 + 180.0) % 360.0) - 180.0)


def teste():
    L.editor_request_begin_play()
    while True:
        world = UES.get_game_world()
        if world:
            pawn, pc = GS.get_player_pawn(world, 0), GS.get_player_controller(world, 0)
            if pawn and pc:
                break
        yield
    S.update(world=world, pawn=pawn, pc=pc)
    yield from espera(2.5)
    S["comp"] = pawn.get_component_by_class(COMP_CLS)
    chk("componente BP_LuxEntrada no jogador", S["comp"] is not None)
    cls = unreal.load_object(None, "/Game/Masion/LUX/_TesteEntrada/BPFL_TesteInput.BPFL_TesteInput_C")
    r = unreal.get_default_object(cls).call_method("ObterSub", (world, pc))
    S["sub"] = r[0] if isinstance(r, (tuple, list)) else r
    chk("subsistema do Enhanced Input encontrado", S["sub"] is not None)
    if S["comp"] is None or S["sub"] is None:
        return
    tipo(forcado="TecladoMouse", manual="Auto")
    yield from espera(0.5)
    # ---------------- 1) acoes e teclas
    chk("IA_UI_Cima: seta, D-Pad e stick esquerdo para cima", sorted(teclas("IA_UI_Cima")) == sorted(["Up", "Gamepad_DPad_Up", "Gamepad_LeftStick_Up"]), teclas("IA_UI_Cima"))
    chk("IA_UI_Baixo: seta, D-Pad e stick esquerdo para baixo", sorted(teclas("IA_UI_Baixo")) == sorted(["Down", "Gamepad_DPad_Down", "Gamepad_LeftStick_Down"]), teclas("IA_UI_Baixo"))
    chk("fora da pausa: nada montado e cursor escondido", len(todos()) == 0 and not pc.get_editor_property("show_mouse_cursor") and not pausa_aberta(), (len(todos()), pc.get_editor_property("show_mouse_cursor")))
    injeta("IA_UI_Baixo")
    yield from espera(0.3)
    chk("fora da pausa, Cima/Baixo nao fazem nada", cget("Indice") == 0 and len(todos()) == 0 and not GS.is_game_paused(world), (cget("Indice"), len(todos())))
    # ---------------- 2) tela principal
    loc0, rot0 = pawn.get_actor_location(), pc.get_control_rotation()
    injeta("IA_Pausa")
    yield from espera(1.0)
    chk("IA_Pausa pausa o jogo e monta a tela Principal", GS.is_game_paused(world) and cget("bPausado") is True and cget("Tela") == "Principal", (cget("Tela"), cget("bPausado")))
    chk("fundo da pausa no viewport", len(pausa_aberta()) == 1, len(pausa_aberta()))
    chk("titulo PAUSADO e 3 botoes: CONTINUAR / CONFIGURAÇÕES / SAIR", titulo() == "PAUSADO" and [texto_de(b) for b in botoes()] == ["CONTINUAR", "CONFIGURAÇÕES", "SAIR"], (titulo(), [texto_de(b) for b in botoes()]))
    chk("selecao inicial no 1o botao (faixa ambar so nele)", cget("Indice") == 0 and selecionado() == [0], (cget("Indice"), selecionado()))
    chk("cursor visivel com teclado/mouse", pc.get_editor_property("show_mouse_cursor") is True)
    tp = dica() or ""
    chk("dica de teclas (teclado): [Enter] Selecionar / [ESC] Continuar", "[Enter] Selecionar" in tp and "[ESC] Continuar" in tp, repr(tp))
    yield from shot("m01_principal")
    # ---------------- 3) navegacao
    seq = []
    for _ in range(3):
        injeta("IA_UI_Baixo")
        yield from espera(0.35)
        seq.append(cget("Indice"))
    chk("Baixo x3: 1, 2 e volta ao topo (0)", seq == [1, 2, 0], seq)
    injeta("IA_UI_Cima")
    yield from espera(0.35)
    chk("Cima no topo: vai para o ultimo (2) e a faixa acompanha", cget("Indice") == 2 and selecionado() == [2], (cget("Indice"), selecionado()))
    injeta("IA_UI_Cima")
    yield from espera(0.35)
    injeta("IA_UI_Cima")
    yield from espera(0.35)
    chk("Cima x2: 1 e 0", cget("Indice") == 0, cget("Indice"))
    # ---------------- 4) bloqueio dos controles do jogador com a pausa aberta
    d = yield from anda(unreal.Vector(0.0, 1.0, 0.0), 0.6)
    chk("pausado: IA_Move NAO move o jogador (%.1f cm)" % d, d < 3.0, round(d, 2))
    a = yield from gira(0.6)
    chk("pausado: IA_Look NAO gira a camera (%.2f graus)" % a, a < 0.5, round(a, 3))
    p1 = pawn.get_actor_location()
    chk("pausado: o jogador ficou onde estava", abs(p1.x - loc0.x) + abs(p1.y - loc0.y) < 3.0, (round(p1.x - loc0.x, 2), round(p1.y - loc0.y, 2)))
    # ---------------- 5) Configuracoes: estilo dos icones
    injeta("IA_UI_Baixo")
    yield from espera(0.35)
    injeta("IA_UI_Confirmar")
    yield from espera(0.8)
    chk("Confirmar em CONFIGURAÇÕES abre a tela Config", cget("Tela") == "Config" and titulo() == "CONFIGURAÇÕES", (cget("Tela"), titulo()))
    chk("Config: linha de icones e VOLTAR", [texto_de(b) for b in botoes()][1:] == ["VOLTAR"] and texto_de(botoes()[0]).startswith("ÍCONES: AUTO"), [texto_de(b) for b in botoes()])
    yield from shot("m02_config")
    injeta("IA_UI_Confirmar")
    yield from espera(0.6)
    chk("Confirmar na linha de icones: Auto -> Xbox (linha acompanha)", cget("EstiloManual") == "Xbox" and texto_de(botoes()[0]) == "ÍCONES: XBOX", (cget("EstiloManual"), texto_de(botoes()[0])))
    injeta("IA_UI_Alternar")
    yield from espera(0.6)
    chk("Y (Alternar) segue funcionando na pausa: Xbox -> PlayStation (linha acompanha)", cget("EstiloManual") == "PlayStation" and texto_de(botoes()[0]) == "ÍCONES: PLAYSTATION", (cget("EstiloManual"), texto_de(botoes()[0])))
    injeta("IA_UI_Confirmar")
    yield from espera(0.6)
    chk("PlayStation -> Auto (volta ao ciclo)", cget("EstiloManual") == "Auto", cget("EstiloManual"))
    injeta("IA_UI_Baixo")
    yield from espera(0.35)
    injeta("IA_UI_Confirmar")
    yield from espera(0.8)
    chk("Confirmar em VOLTAR volta a Principal", cget("Tela") == "Principal" and len(botoes()) == 3 and cget("Indice") == 0, (cget("Tela"), cget("Indice")))
    injeta("IA_UI_Baixo")
    yield from espera(0.35)
    injeta("IA_UI_Confirmar")
    yield from espera(0.8)
    injeta("IA_UI_Voltar")
    yield from espera(0.8)
    chk("Voltar (B/Backspace) na Config volta a Principal e o jogo segue pausado", cget("Tela") == "Principal" and GS.is_game_paused(world), (cget("Tela"), GS.is_game_paused(world)))
    # ---------------- 6) Sair: confirmacao
    injeta("IA_UI_Baixo")
    yield from espera(0.3)
    injeta("IA_UI_Baixo")
    yield from espera(0.3)
    injeta("IA_UI_Confirmar")
    yield from espera(0.8)
    chk("Confirmar em SAIR abre a confirmacao (nao sai direto)", cget("Tela") == "Sair" and titulo() == "SAIR DO JOGO?", (cget("Tela"), titulo()))
    chk("Sair: CANCELAR (selecionado) e SAIR", [texto_de(b) for b in botoes()] == ["CANCELAR", "SAIR"] and cget("Indice") == 0, ([texto_de(b) for b in botoes()], cget("Indice")))
    yield from shot("m03_sair")
    injeta("IA_UI_Confirmar")
    yield from espera(0.8)
    chk("Confirmar em CANCELAR volta a Principal; o jogo continua aberto", cget("Tela") == "Principal" and L.is_in_play_in_editor(), cget("Tela"))
    # ---------------- 7) dica por dispositivo e cursor
    tipo(forcado="Xbox")
    yield from espera(0.8)
    tp = dica() or ""
    chk("dica com controle Xbox: [A] Selecionar / [Menu] Continuar", "[A] Selecionar" in tp and "[Menu] Continuar" in tp and "[D-Pad]" in tp, repr(tp))
    chk("cursor ESCONDIDO com controle", pc.get_editor_property("show_mouse_cursor") is False)
    yield from shot("m04_xbox")
    tipo(forcado="PlayStation")
    yield from espera(0.8)
    tp = dica() or ""
    chk("dica com controle PlayStation: [Cross] Selecionar / [Options] Continuar", "[Cross] Selecionar" in tp and "[Options] Continuar" in tp, repr(tp))
    tipo(forcado="TecladoMouse")
    yield from espera(0.8)
    chk("de volta ao teclado/mouse: cursor visivel e dica com [Enter]", pc.get_editor_property("show_mouse_cursor") is True and "[Enter] Selecionar" in (dica() or ""), (pc.get_editor_property("show_mouse_cursor"), dica()))
    # ---------------- 8) continuar: de cada jeito; retorno dos controles
    injeta("IA_UI_Confirmar")
    yield from espera(1.0)
    chk("Confirmar em CONTINUAR despausa e limpa tudo", not GS.is_game_paused(world) and cget("bPausado") is False and len(todos()) == 0 and len(botoes()) == 0 and not pausa_aberta(),
        (GS.is_game_paused(world), len(todos()), len(pausa_aberta())))
    chk("ao continuar: cursor escondido", pc.get_editor_property("show_mouse_cursor") is False)
    d = yield from anda(unreal.Vector(0.0, 1.0, 0.0), 0.6)
    chk("depois de continuar: IA_Move volta a mover o jogador (%.0f cm)" % d, d > 30.0, round(d, 1))
    a = yield from gira(0.6)
    chk("depois de continuar: IA_Look volta a girar a camera (%.1f graus)" % a, a > 3.0, round(a, 2))
    for caminho, acao in (("IA_UI_Voltar", "Voltar"), ("IA_Pausa", "IA_Pausa")):
        injeta("IA_Pausa")
        yield from espera(0.9)
        injeta(caminho)
        yield from espera(1.0)
        chk("pausa e %s na tela principal continuam o jogo" % acao, not GS.is_game_paused(world) and len(todos()) == 0 and not pausa_aberta(), (GS.is_game_paused(world), len(todos())))
    # IA_Pausa dentro de uma tela secundaria continua o jogo (nao fica presa no menu)
    injeta("IA_Pausa")
    yield from espera(0.9)
    injeta("IA_UI_Baixo")
    yield from espera(0.3)
    injeta("IA_UI_Confirmar")
    yield from espera(0.8)
    injeta("IA_Pausa")
    yield from espera(1.0)
    chk("IA_Pausa dentro de Configuracoes tambem continua o jogo", not GS.is_game_paused(world) and len(todos()) == 0 and cget("bPausado") is False, (GS.is_game_paused(world), cget("Tela")))
    # varios ciclos: sem pecas sobrando
    for _ in range(4):
        injeta("IA_Pausa")
        yield from espera(0.7)
        injeta("IA_Pausa")
        yield from espera(0.7)
    chk("4 ciclos de pausa/continua: sem pecas sobrando, sem pausa, sem cursor", not GS.is_game_paused(world) and len(todos()) == 0 and not pausa_aberta() and not pc.get_editor_property("show_mouse_cursor"),
        (len(todos()), len(pausa_aberta())))
    # ---------------- 9) ENTRADA REAL do sistema
    injeta("IA_Pausa")
    yield from espera(1.0)
    # teclado: vai para a janela em primeiro plano, entao exige o editor na frente (se o usuario estiver usando o PC, pula e avisa)
    if not editor_na_frente():
        w("(editor sem foco: teclado real nao testado)")
    else:
        for nome, esperado in (("Baixo", 1), ("Baixo", 2), ("Cima", 1)):
            tecla_real(nome)
            yield from espera(0.45)
            chk("tecla REAL %s move a selecao para %d" % (nome, esperado), cget("Indice") == esperado, cget("Indice"))
        tecla_real("Enter")
        yield from espera(0.9)
        chk("tecla REAL Enter ativa CONFIGURAÇÕES", cget("Tela") == "Config", cget("Tela"))
        tecla_real("Backspace")
        yield from espera(0.9)
        chk("tecla REAL Backspace volta a Principal", cget("Tela") == "Principal" and GS.is_game_paused(world), cget("Tela"))
    # mouse: passar seleciona; soltar ativa. O evento vai para a janela sob o cursor (nao precisa de foco; o clique ate ativa o editor),
    # mas so vale se essa janela for o editor: senao pula e diz qual janela esta por cima
    mouse_para(*centro_botao_px(1))
    yield
    yield
    pid_j, tit_j = janela_sob_cursor()
    if pid_j != os.getpid() or "Unreal Editor" not in tit_j:
        w("(janela sob o cursor nao e o editor: '%s' pid=%s; mouse real nao testado)" % (tit_j, pid_j))
    else:
        ok = yield from mouse_sobre(2)
        chk("mouse REAL sobre o 3o botao seleciona-o (indice %s)" % cget("Indice"), ok and cget("Indice") == 2, cget("Indice"))
        ok = yield from mouse_sobre(1)
        chk("mouse REAL sobre o 2o botao seleciona-o", ok and cget("Indice") == 1, cget("Indice"))
        if ok:
            clique_real()
            yield from espera(0.9)
            chk("clique REAL em CONFIGURAÇÕES abre a tela Config", cget("Tela") == "Config", cget("Tela"))
            ok = yield from mouse_sobre(1)
            if ok:
                clique_real()
                yield from espera(0.9)
                chk("clique REAL em VOLTAR volta a Principal", cget("Tela") == "Principal", cget("Tela"))
        diag("antes de mirar CONTINUAR")
        ok = yield from mouse_sobre(0)
        if ok:
            clique_real()
            yield from espera(1.0)
            chk("clique REAL em CONTINUAR despausa e esconde o cursor", not GS.is_game_paused(world) and not pc.get_editor_property("show_mouse_cursor") and len(todos()) == 0,
                (GS.is_game_paused(world), pc.get_editor_property("show_mouse_cursor")))
    diag("fim da entrada real")
    if not GS.is_game_paused(world):   # o clique em CONTINUAR despausou: pausa de novo para o passo final
        injeta("IA_Pausa")
        yield from espera(0.9)
        diag("pausado de novo")
    # ---------------- 10) Sair encerra o jogo (por ultimo: o PIE acaba)
    if L.is_in_play_in_editor():
        diag("antes do passo final")
        if not GS.is_game_paused(world):
            injeta("IA_Pausa")
            yield from espera(0.9)
        if cget("Tela") != "Principal":
            injeta("IA_UI_Voltar")
            yield from espera(0.6)
        diag("pausado para o passo final")
        for _ in range(4):   # vai ate o 3o botao (SAIR) por estado: a selecao inicial depende de onde o mouse real a deixou (hover)
            if cget("Indice") == 2:
                break
            injeta("IA_UI_Baixo")
            yield from espera(0.3)
        diag("SAIR selecionado")
        injeta("IA_UI_Confirmar")
        yield from espera(0.8)
        diag("apos Confirmar")
        injeta("IA_UI_Baixo")
        yield from espera(0.3)
        diag("apos Baixo 3")
        chk("na confirmacao, SAIR selecionado (indice 1)", cget("Indice") == 1 and cget("Tela") == "Sair", (cget("Indice"), cget("Tela")))
        injeta("IA_UI_Confirmar")
        t0 = time.time()
        while L.is_in_play_in_editor() and time.time() - t0 < 6.0:
            yield
        chk("SAIR encerra o jogo (o PIE termina)", not L.is_in_play_in_editor(), round(time.time() - t0, 2))


def tick(dt):
    try:
        next(S["gen"])
    except StopIteration:
        encerra()
    except Exception:
        S["erro"] = traceback.format_exc()
        w("ERRO", S["erro"])
        encerra()
    if time.time() - S["t0"] > 240 and not S.get("fim"):
        w("TEMPO ESGOTADO")
        encerra()


def encerra():
    if S.get("fim"):
        return
    S["fim"] = True
    n_ok = len([r for r in S["res"] if r["ok"]])
    w("FIM: %d PASS, %d FAIL" % (n_ok, len(S["res"]) - n_ok))
    with open(os.path.join(OUT, "menu_result.json"), "w", encoding="utf-8") as fh:
        json.dump({"resultados": S["res"], "erro": S.get("erro")}, fh, ensure_ascii=False, indent=1)
    if L.is_in_play_in_editor():
        L.editor_request_end_play()
    unreal.unregister_slate_post_tick_callback(S["h"])


S["gen"] = teste()
S["h"] = unreal.register_slate_post_tick_callback(tick)
