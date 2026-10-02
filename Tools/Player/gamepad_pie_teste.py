# LUX: TESTE NO PIE do suporte a controle (Xbox/PlayStation) - 64 checagens. Roda DENTRO do editor (Python Remote Execution) e nao salva nada.
# Testes irmaos (mesmo preparo): gamepad_pie_eixos.py (direcao e velocidade de Move e Look), gamepad_pie_hold.py (segurar/soltar e a pausa no meio) e
# gamepad_pie_sobreposicao.py (o botao que fecha a pausa nao pode disparar a acao de jogo)
#   1) gamepad_pie_injetor.py          (cria o BPFL descartavel que entrega o subsistema do Enhanced Input ao Python; nao salve)
#   2) py "<projeto>/Tools/Player/gamepad_pie_teste.py" <rotulo>      -> Saved/LuxSnapshots/entrada_pie/<rotulo>/entrada_log.txt e entrada_result.json
# Testa: componente no jogador e sem Tick; contextos ativos; teclas de teclado/mouse e de gamepad por acao; D09 (sem corrida/pulo); modificadores do Look;
# rotulo do prompt do HUD por dispositivo (teclado "E", Xbox "A", PlayStation "Cross") e estilo manual; o aviso de troca de dispositivo chegando ao
# componente (contador); pausa/continua por acao injetada (com o jogo pausado), tela de pausa (texto e quadro com UI); estado depois de voltar;
# movimento e camera. Regras aprendidas: nunca set_editor_property no componente no PIE (reconstroi o ator): use DefinirEstilo/DefinirTipoForcado;
# injete com inject_input_vector_for_action (inject_input_for_action com InputActionValue(1.0) nao dispara nada).
import glob, json, os, shutil, sys, time, traceback, unreal

ROT = sys.argv[1] if len(sys.argv) > 1 else "t1"
SAVED = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
OUT = os.path.join(SAVED, "LuxSnapshots", "entrada_pie", ROT)
os.makedirs(OUT, exist_ok=True)
LOG = os.path.join(OUT, "entrada_log.txt")
open(LOG, "w", encoding="utf-8").close()
L = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
UES = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
GS = unreal.GameplayStatics
SL = unreal.SystemLibrary
DIR = "/Game/Masion/LUX/Entrada"
ACT = "/Game/FPMovement/Player/Input/Actions/"
IA = {n: unreal.load_asset(ACT + n) for n in ("IA_Interact", "IA_Crouch", "IA_Flashlight", "IA_Inspect", "IA_Zoom", "IA_Move", "IA_Look", "IA_Sprint", "IA_Jump")}
for n in ("IA_Pausa", "IA_UI_Confirmar", "IA_UI_Voltar", "IA_UI_Anterior", "IA_UI_Proximo", "IA_UI_Alternar"):
    IA[n] = unreal.load_asset(DIR + "/" + n)
IMC_DEFAULT = unreal.load_asset("/Game/FPMovement/Player/Input/IMC_Default")
IMC_LUX = unreal.load_asset(DIR + "/IMC_LuxEntrada")
COMP_CLS = unreal.load_object(None, DIR + "/BP_LuxEntrada.BP_LuxEntrada_C")
WPI_CLS = unreal.load_object(None, "/Game/FPMovement/Player/Widgets/UserCreated/Interaction/WP_Interaction.WP_Interaction_C")
WBP_CLS = unreal.load_object(None, DIR + "/WB_LuxPausa.WB_LuxPausa_C")
S = {"res": [], "t0": time.time()}


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


def prompts():
    out = []
    for wd in unreal.WidgetLibrary.get_all_widgets_of_class(S["world"], WPI_CLS, False):
        try:
            out.append(str(wd.get_editor_property("HorizontalBox").get_child_at(0).get_content().get_editor_property("text")))
        except Exception as ex:
            out.append("ERRO " + str(ex)[:60])
    return out


def texto_pausa():
    ws = [x for x in unreal.WidgetLibrary.get_all_widgets_of_class(S["world"], WBP_CLS, False) if x.is_in_viewport()]   # o objeto sobrevive ao RemoveFromParent ate o GC
    if not ws:
        return None
    try:
        return str(ws[0].get_editor_property("HorizontalBox").get_child_at(0).get_content().get_editor_property("text"))
    except Exception as ex:
        return "ERRO " + str(ex)[:80]


def cget(n):
    return S["comp"].get_editor_property(n)


def tipo(forcado=None, manual=None):
    """aplica pelas funcoes publicas do componente (set_editor_property no PIE reconstroi o ator e deixa o componente orfao)"""
    if manual is not None:
        S["comp"].call_method("DefinirEstilo", (manual,))
    if forcado is not None:
        S["comp"].call_method("DefinirTipoForcado", (forcado,))


def tem_ctx(imc):
    return S["sub"].has_mapping_context(imc) is not None   # devolve a prioridade (0 e valida) ou None


def teclas(acao):
    return [str(k.get_editor_property("key_name")) for k in S["sub"].query_keys_mapped_to_action(IA[acao])]


def injeta(nome, valor=1.0):
    """inject_input_vector_for_action converte para o tipo da acao (inject_input_for_action com InputActionValue(1.0) nao dispara nada)"""
    S["sub"].inject_input_vector_for_action(IA[nome], unreal.Vector(valor, 0.0, 0.0), [], [])


def shot(nome):
    antes = set(glob.glob(os.path.join(SAVED, "Screenshots", "**", "*.png"), recursive=True))
    SL.execute_console_command(S["world"], "Shot ShowUI", S["pc"])
    t0 = time.time()
    while time.time() - t0 < 4.0:
        novos = set(glob.glob(os.path.join(SAVED, "Screenshots", "**", "*.png"), recursive=True)) - antes
        novos = [f for f in novos if os.path.getsize(f) > 1000]
        if novos:
            dest = os.path.join(OUT, nome + ".png")
            shutil.move(sorted(novos, key=os.path.getmtime)[-1], dest)
            return dest
        yield
    return None


def modificadores_look():
    """Right2D do IMC_Default: zona morta + Negate so no Y + ScaleByDeltaTime x60. A direcao e a velocidade REAIS (mouse x stick, 30/60 FPS, zona morta)
    sao medidas por injecao com esta mesma cadeia em gamepad_pie_eixos.py (a conta direta com InputActionValue nao e possivel no Python do 5.8)."""
    mapa = None
    for m in IMC_DEFAULT.get_editor_property("default_key_mappings").get_editor_property("mappings"):
        if m.get_editor_property("action") == IA["IA_Look"] and str(m.get_editor_property("key").get_editor_property("key_name")) == "Gamepad_Right2D":
            mapa = m
    mods = list(mapa.get_editor_property("modifiers"))
    nomes = [x.get_class().get_name() for x in mods]
    chk("Look do gamepad: modificadores = zona morta, Negate Y, delta tempo, escala", nomes == ["InputModifierDeadZone", "InputModifierNegate", "InputModifierScaleByDeltaTime", "InputModifierScalar"], nomes)
    neg = next((x for x in mods if isinstance(x, unreal.InputModifierNegate)), None)
    xyz = [neg.get_editor_property(c) for c in "xyz"] if neg else None
    chk("Look do gamepad: o Negate e so no Y (o pitch legado e -2,5; o mouse tem o mesmo Negate)", xyz == [False, True, False], xyz)


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
    w("PIE pronto | pawn:", pawn.get_class().get_name(), "| tempo real %.1f s" % (time.time() - S["t0"]))
    yield from espera(2.5)
    # 1) componente
    comp = pawn.get_component_by_class(COMP_CLS)
    chk("componente BP_LuxEntrada no jogador", comp is not None, comp)
    if comp is None:
        return
    S["comp"] = comp
    chk("sem Tick (D06): o componente nao ticka", not comp.is_component_tick_enabled(), comp.is_component_tick_enabled())
    chk("TipoAtual inicial = TecladoMouse", cget("TipoAtual") == "TecladoMouse", cget("TipoAtual"))
    chk("Glifos (DA_LuxGlifos) ligado por padrao", cget("Glifos") is not None, cget("Glifos"))
    cls = unreal.load_object(None, "/Game/Masion/LUX/_TesteEntrada/BPFL_TesteInput.BPFL_TesteInput_C")
    r = unreal.get_default_object(cls).call_method("ObterSub", (world, pc))
    S["sub"] = r[0] if isinstance(r, (tuple, list)) else r
    chk("subsistema do Enhanced Input do jogador encontrado", S["sub"] is not None, S["sub"])
    if S["sub"] is None:
        return
    # 2) contextos
    chk("IMC_Default ativo (prioridade %s)" % S["sub"].has_mapping_context(IMC_DEFAULT), tem_ctx(IMC_DEFAULT))
    chk("IMC_LuxEntrada ativo (prioridade %s; registrado pelo componente)" % S["sub"].has_mapping_context(IMC_LUX), tem_ctx(IMC_LUX))
    # 3) teclas por acao: teclado/mouse como sempre + gamepad
    esperado = {"IA_Interact": ("E", "Gamepad_FaceButton_Bottom"), "IA_Crouch": ("C", "Gamepad_FaceButton_Right"), "IA_Flashlight": ("F", "Gamepad_FaceButton_Left"),
                "IA_Inspect": ("I", "Gamepad_FaceButton_Top"), "IA_Zoom": ("RightMouseButton", "Gamepad_LeftTriggerAxis"), "IA_Move": ("W", "Gamepad_Left2D"),
                "IA_Look": ("Mouse2D", "Gamepad_Right2D"), "IA_Pausa": ("Escape", "Gamepad_Special_Right"), "IA_UI_Confirmar": ("Enter", "Gamepad_FaceButton_Bottom"),
                "IA_UI_Voltar": ("BackSpace", "Gamepad_FaceButton_Right"), "IA_UI_Anterior": ("Left", "Gamepad_LeftShoulder"), "IA_UI_Proximo": ("Right", "Gamepad_RightShoulder"),
                "IA_UI_Alternar": ("Tab", "Gamepad_FaceButton_Top")}
    for acao, (kbm, pad) in esperado.items():
        t = teclas(acao)
        chk("%s: teclado/mouse (%s) e gamepad (%s)" % (acao, kbm, pad), kbm in t and pad in t, t)
    for acao in ("IA_Sprint", "IA_Jump"):
        chk("%s sem nenhuma tecla (D09)" % acao, teclas(acao) == [], teclas(acao))
    gat = {n: [type(t).__name__ for t in IA[n].get_editor_property("triggers")] for n in ("IA_Pausa", "IA_UI_Confirmar", "IA_UI_Voltar", "IA_UI_Anterior", "IA_UI_Proximo", "IA_UI_Alternar")}
    chk("Confirmar e Voltar agem ao SOLTAR (Released); Pausa, Anterior, Proximo e Alternar ao apertar (Pressed)",
        gat["IA_UI_Confirmar"] == ["InputTriggerReleased"] and gat["IA_UI_Voltar"] == ["InputTriggerReleased"] and all(gat[n] == ["InputTriggerPressed"] for n in ("IA_Pausa", "IA_UI_Anterior", "IA_UI_Proximo", "IA_UI_Alternar")), gat)
    chk("IA_Zoom segue o botao tambem com o jogo pausado (trigger_when_paused): sem zoom preso depois da pausa", IA["IA_Zoom"].get_editor_property("trigger_when_paused"), IA["IA_Zoom"].get_editor_property("trigger_when_paused"))
    # 4) modificadores do Look
    modificadores_look()
    # 5) prompt do HUD por dispositivo (pelo caminho real: ForcarTipo finge o dispositivo e AtualizarTipo recalcula)
    p = prompts()
    chk("WP_Interaction no HUD (instancias: %d)" % len(p), len(p) >= 1, p)
    chk("prompt do HUD = E no teclado/mouse", p and all(x == "E" for x in p), p)
    for f, esp in (("Xbox", "A"), ("PlayStation", "Cross"), ("Generico", "A"), ("TecladoMouse", "E")):
        tipo(forcado=f)
        yield from espera(0.4)
        p = prompts()
        chk("dispositivo %s: prompt do HUD = %s" % (f, esp), cget("TipoAtual") == f and p and all(x == esp for x in p), (cget("TipoAtual"), p))
    # 6) estilo manual so vale para controle; Auto devolve o detectado
    tipo(forcado="Generico", manual="PlayStation")
    yield from espera(0.3)
    chk("controle generico + estilo manual PlayStation = PlayStation (prompt Cross)", cget("TipoAtual") == "PlayStation" and all(x == "Cross" for x in prompts()), (cget("TipoAtual"), prompts()))
    tipo(manual="Xbox")
    yield from espera(0.3)
    chk("estilo manual Xbox = Xbox (prompt A)", cget("TipoAtual") == "Xbox" and all(x == "A" for x in prompts()), (cget("TipoAtual"), prompts()))
    tipo(forcado="TecladoMouse", manual="PlayStation")
    yield from espera(0.3)
    chk("teclado/mouse ignora o estilo manual (prompt E)", cget("TipoAtual") == "TecladoMouse" and all(x == "E" for x in prompts()), (cget("TipoAtual"), prompts()))
    tipo(forcado="Auto", manual="Auto")
    yield from espera(0.3)
    chk("Auto/Auto volta ao dispositivo real (teclado/mouse no editor)", cget("TipoAtual") == "TecladoMouse", cget("TipoAtual"))
    # 7) delegate de troca de dispositivo: o motor avisa e o componente conta/recalcula
    dev = unreal.get_engine_subsystem(unreal.InputDeviceSubsystem)
    try:
        uid = unreal.InputDeviceLibrary.get_primary_platform_user()
        did = dev.get_most_recently_used_input_device_id(uid, unreal.HardwareDevicePrimaryType.UNSPECIFIED)
        ident = dev.get_input_device_hardware_identifier(did)
        w("dispositivo mais recente:", ident.get_editor_property("input_class_name"), "/", ident.get_editor_property("hardware_device_identifier"))
        antes = cget("ContTrocasDispositivo")
        dev.on_input_hardware_device_changed.broadcast(uid, did)
        yield from espera(0.4)
        chk("OnInputHardwareDeviceChanged chega ao componente (contador %s -> %s)" % (antes, cget("ContTrocasDispositivo")), cget("ContTrocasDispositivo") == antes + 1, cget("ContTrocasDispositivo"))
        chk("o tipo detectado no editor e TecladoMouse (WindowsApplication/KBM)", cget("TipoAtual") == "TecladoMouse", cget("TipoAtual"))
    except Exception as ex:
        chk("OnInputHardwareDeviceChanged chega ao componente", False, "excecao: " + str(ex)[:200])
    # 8) pausa por acao injetada (teclado/mouse)
    chk("jogo nao esta pausado antes", not GS.is_game_paused(world))
    injeta("IA_Pausa")
    yield from espera(1.0)
    chk("IA_Pausa pausa o jogo", GS.is_game_paused(world), GS.is_game_paused(world))
    chk("bPausado verdadeiro", cget("bPausado") is True, cget("bPausado"))
    tp = texto_pausa()
    chk("tela de pausa no viewport: PAUSADO / [Enter] ou [ESC] Continuar", tp is not None and tp.startswith("PAUSADO") and "[Enter] ou [ESC] Continuar" in tp, repr(tp))
    d = yield from shot("pausa_teclado")
    w("quadro:", d)
    # 9) pausa com controle (Xbox): texto com glifos e linha de icones
    tipo(forcado="Xbox")
    yield from espera(0.5)
    tp = texto_pausa()
    chk("pausa com controle Xbox: [A] ou [Menu] + linha de icones", tp is not None and "[A] ou [Menu] Continuar" in tp and "[Y]" in tp and "cones: Auto (Xbox)" in tp, repr(tp))
    d = yield from shot("pausa_xbox")
    w("quadro:", d)
    tipo(forcado="PlayStation")
    yield from espera(0.5)
    tp = texto_pausa()
    chk("pausa com controle PlayStation: [Cross] ou [Options] + [Triangle]", tp is not None and "[Cross] ou [Options] Continuar" in tp and "[Triangle]" in tp, repr(tp))
    d = yield from shot("pausa_playstation")
    w("quadro:", d)
    tipo(forcado="Xbox")
    yield from espera(0.4)
    # estilo manual no pause (Y/Triangle) com o jogo pausado
    injeta("IA_UI_Alternar")
    yield from espera(0.8)
    chk("IA_UI_Alternar (jogo pausado): Auto -> Xbox", cget("EstiloManual") == "Xbox", cget("EstiloManual"))
    injeta("IA_UI_Alternar")
    yield from espera(0.8)
    chk("IA_UI_Alternar: Xbox -> PlayStation e o tipo/rotulos seguem (Cross)", cget("EstiloManual") == "PlayStation" and cget("TipoAtual") == "PlayStation" and "[Cross]" in (texto_pausa() or ""), (cget("EstiloManual"), cget("TipoAtual"), texto_pausa()))
    d = yield from shot("pausa_estilo_playstation")
    w("quadro:", d)
    injeta("IA_UI_Alternar")
    yield from espera(0.8)
    chk("IA_UI_Alternar: PlayStation -> Auto", cget("EstiloManual") == "Auto" and cget("TipoAtual") == "Xbox", (cget("EstiloManual"), cget("TipoAtual")))
    tipo(forcado="Auto")
    # continua por B/Circle
    injeta("IA_UI_Voltar")
    yield from espera(1.0)
    chk("IA_UI_Voltar continua o jogo", not GS.is_game_paused(world), GS.is_game_paused(world))
    chk("bPausado falso", cget("bPausado") is False, cget("bPausado"))
    yield from espera(0.5)
    chk("tela de pausa fora do viewport", texto_pausa() is None, texto_pausa())
    # continua por A/Cross
    injeta("IA_Pausa")
    yield from espera(0.8)
    chk("pausa de novo", GS.is_game_paused(world))
    injeta("IA_UI_Confirmar")
    yield from espera(0.8)
    chk("IA_UI_Confirmar continua o jogo", not GS.is_game_paused(world))
    # Start/Menu duas vezes
    injeta("IA_Pausa")
    yield from espera(0.8)
    injeta("IA_Pausa")
    yield from espera(0.8)
    chk("IA_Pausa duas vezes: pausa e continua", not GS.is_game_paused(world))
    # fora da pausa, as acoes de UI nao fazem nada no jogo
    estilo0 = cget("EstiloManual")
    injeta("IA_UI_Alternar")
    injeta("IA_UI_Voltar")
    injeta("IA_UI_Confirmar")
    yield from espera(0.8)
    chk("acoes de UI fora da pausa sao ignoradas (estilo, pausa)", cget("EstiloManual") == estilo0 and not GS.is_game_paused(world) and cget("bPausado") is False, (cget("EstiloManual"), cget("bPausado")))
    # 10) o gameplay segue mapeado depois de pausar e voltar
    chk("IA_Move/IA_Look/IA_Interact/IA_Crouch seguem com teclado e gamepad depois da pausa", all(len(teclas(a)) >= 2 for a in ("IA_Move", "IA_Look", "IA_Interact", "IA_Crouch")))
    chk("IMC_Default continua ativo depois da pausa", tem_ctx(IMC_DEFAULT))
    # 11) nao pausa por cima de outra pausa
    GS.set_game_paused(world, True)
    yield from espera(0.4)
    injeta("IA_Pausa")
    yield from espera(0.8)
    chk("nao cria a tela de pausa quando outro sistema ja pausou", cget("bPausado") is False and texto_pausa() is None, (cget("bPausado"), texto_pausa()))
    GS.set_game_paused(world, False)
    yield from espera(0.4)


    # 12) movimento e camera continuam respondendo as acoes (o pawn nao foi tocado; o IMC ganhou so o gamepad)
    loc0 = pawn.get_actor_location()
    t0 = time.time()
    while time.time() - t0 < 1.5:
        S["sub"].inject_input_vector_for_action(IA["IA_Move"], unreal.Vector(0.0, 1.0, 0.0), [], [])
        yield
    loc1 = pawn.get_actor_location()
    dist = ((loc1.x - loc0.x) ** 2 + (loc1.y - loc0.y) ** 2) ** 0.5
    chk("IA_Move injetada (frente) move o jogador (%.0f cm em 1,5 s)" % dist, dist > 50.0, round(dist, 1))
    yaw0 = pc.get_control_rotation().yaw
    S["sub"].inject_input_vector_for_action(IA["IA_Look"], unreal.Vector(3.0, 0.0, 0.0), [], [])
    yield from espera(0.8)
    dyaw = (pc.get_control_rotation().yaw - yaw0 + 540.0) % 360.0 - 180.0
    chk("IA_Look injetada gira a camera (%.1f graus; 3,0 x escala legada 2,5 = 7,5)" % dyaw, abs(dyaw - 7.5) < 0.6, round(dyaw, 2))


    # 13) icones: o DA nao tem texturas (estrutura pronta). Com uma textura de teste em memoria (nao salva), ObterIconeAcao a devolve; sem, devolve vazio
    da = cget("Glifos")
    tex = unreal.load_asset("/Engine/EngineResources/WhiteSquareTexture")

    def tecla_k(nome):
        k = unreal.Key()
        k.set_editor_property("key_name", nome)
        return k

    def icone(tipo_forcado):
        S["comp"].call_method("DefinirTipoForcado", (tipo_forcado,))
        S["comp"].call_method("ObterIconeAcao", (IA["IA_Interact"],))
        return cget("UltIcone")

    chk("sem textura no DA: ObterIconeAcao devolve vazio (Xbox)", icone("Xbox") is None, icone("Xbox"))
    da.set_editor_property("IconesXbox", {tecla_k("Gamepad_FaceButton_Bottom"): tex})
    da.set_editor_property("IconesPlayStation", {tecla_k("Gamepad_FaceButton_Bottom"): tex})
    da.set_editor_property("IconesTeclado", {tecla_k("E"): tex})
    chk("com textura no DA (A/Cross): ObterIconeAcao devolve a textura (Xbox)", icone("Xbox") == tex, icone("Xbox"))
    chk("com textura no DA (A/Cross): ObterIconeAcao devolve a textura (PlayStation)", icone("PlayStation") == tex, icone("PlayStation"))
    chk("com textura no DA (E): ObterIconeAcao devolve a textura (teclado/mouse)", icone("TecladoMouse") == tex, icone("TecladoMouse"))
    da.set_editor_property("IconesXbox", {})
    chk("textura removida do mapa Xbox: devolve vazio de novo", icone("Xbox") is None, icone("Xbox"))
    da.set_editor_property("IconesPlayStation", {})
    da.set_editor_property("IconesTeclado", {})
    S["comp"].call_method("DefinirTipoForcado", ("Auto",))
    yield from espera(0.3)


def tick(dt):
    try:
        next(S["gen"])
    except StopIteration:
        encerra()
    except Exception:
        S["erro"] = traceback.format_exc()
        w("ERRO", S["erro"])
        encerra()
    if time.time() - S["t0"] > 300 and not S.get("fim"):
        w("TEMPO ESGOTADO")
        encerra()


def encerra():
    if S.get("fim"):
        return
    S["fim"] = True
    try:
        wd = UES.get_game_world()
        if wd and GS.is_game_paused(wd):
            GS.set_game_paused(wd, False)
    except Exception:
        pass
    n_ok = len([r for r in S["res"] if r["ok"]])
    w("FIM: %d PASS, %d FAIL" % (n_ok, len(S["res"]) - n_ok))
    with open(os.path.join(OUT, "entrada_result.json"), "w", encoding="utf-8") as fh:
        json.dump({"resultados": S["res"], "erro": S.get("erro")}, fh, ensure_ascii=False, indent=1)
    if L.is_in_play_in_editor():
        L.editor_request_end_play()
    unreal.unregister_slate_post_tick_callback(S["h"])


S["gen"] = teste()
if getattr(unreal, "_lux_ent_h", None) is not None:
    unreal.unregister_slate_post_tick_callback(unreal._lux_ent_h)
S["h"] = unreal.register_slate_post_tick_callback(tick)
unreal._lux_ent_h = S["h"]
w("callback registrado")
