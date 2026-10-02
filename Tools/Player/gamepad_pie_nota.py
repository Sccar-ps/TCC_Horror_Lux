# LUX: TESTE DO BILHETE NO PIE (Mapa_A, que tem BP_BaseNote) com TECLAS REAIS. Abre um bilhete de 2 paginas e um de 1, e AMOSTRA o estado a cada 0,2 s
# (pagina, animando, pausado, cursor, foco) enquanto um processo de fora manda Right, Left, Enter, Enter (e depois Backspace) ao editor, que precisa
# estar em PRIMEIRO PLANO: SendInput vai para a janela ativa (em 01/10 uma rodada com o editor em 2o plano mandou as teclas ao navegador).
# Resultado esperado (01/10): foco no widget ao abrir; Right/Left viram pagina; Enter avanca e fecha na ultima; Backspace fecha; jogo despausado e cursor oculto.
#   py "<projeto>/Tools/Player/gamepad_pie_nota.py" <rotulo>    -> Saved/LuxSnapshots/entrada_pie/<rotulo>/nota_log.txt
import os, sys, time, traceback, unreal

ROT = sys.argv[1] if len(sys.argv) > 1 else "nota"
SAVED = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
OUT = os.path.join(SAVED, "LuxSnapshots", "entrada_pie", ROT)
os.makedirs(OUT, exist_ok=True)
LOG = os.path.join(OUT, "nota_log.txt")
open(LOG, "w", encoding="utf-8").close()
L = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
UES = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
GS = unreal.GameplayStatics
MAPA = "/Game/FPMovement/Demo/Maps/Mapa_A"
NOTE_CLS = unreal.load_object(None, "/Game/FPMovement/Blueprints/Notes/BP_BaseNote.BP_BaseNote_C")
WB_CLS = unreal.load_object(None, "/Game/FPMovement/Player/Widgets/UserCreated/Note/WB_Note.WB_Note_C")
S = {"t0": time.time()}


def w(*a):
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(" ".join(str(x) for x in a) + "\n")


def espera(seg):
    t0 = time.time()
    while time.time() - t0 < seg:
        yield


def amostra(world, pc, rot):
    ws = [x for x in unreal.WidgetLibrary.get_all_widgets_of_class(world, WB_CLS, False) if x.is_in_viewport()]
    if not ws:
        w("t=%.1f %s | bilhete: FECHADO | pausado=%s | cursor=%s" % (time.time() - S["t0"], rot, GS.is_game_paused(world), pc.get_editor_property("show_mouse_cursor")))
        return None
    wd = ws[0]
    w("t=%.1f %s | bilhete: ABERTO | pagina(NextPageIndex)=%s | animando=%s | pausado=%s | cursor=%s | foco_usuario=%s | foco_descendente=%s | focavel=%s" % (
        time.time() - S["t0"], rot, wd.get_editor_property("NextPageIndex"), wd.get_editor_property("bIsAnimationPlaying"), GS.is_game_paused(world),
        pc.get_editor_property("show_mouse_cursor"), wd.has_user_focus(pc), wd.has_user_focused_descendants(pc), wd.get_editor_property("is_focusable")))
    return wd


def teste():
    L.load_level(MAPA)
    yield from espera(3.0)
    w("mapa carregado:", L.get_current_level() if hasattr(L, "get_current_level") else "?")
    L.editor_request_begin_play()
    while True:
        world = UES.get_game_world()
        if world:
            pawn, pc = GS.get_player_pawn(world, 0), GS.get_player_controller(world, 0)
            if pawn and pc:
                break
        yield
    yield from espera(2.0)
    notas = GS.get_all_actors_of_class(world, NOTE_CLS)
    w("PIE pronto | pawn:", pawn.get_class().get_name(), "| notas no mapa:", len(notas))
    info = []
    for n in notas:
        da = n.get_editor_property("DataAsset")
        info.append((n, da.get_name() if da else None, len(da.get_editor_property("Pages")) if da else None, n.get_editor_property("Pause Game?")))
    w("notas:", [(i[1], i[2], i[3]) for i in info])
    multi = next((i for i in info if i[2] and i[2] > 1), None)
    uma = next((i for i in info if i[2] == 1), None)
    for rotulo, alvo in (("MULTIPAGINA", multi), ("UMA PAGINA", uma)):
        if not alvo:
            w("sem bilhete de", rotulo)
            continue
        nota = alvo[0]
        pawn.set_actor_location(nota.get_actor_location() + unreal.Vector(-60, 0, 0), False, True)
        yield from espera(0.5)
        w("ABRINDO", rotulo, alvo[1], "paginas:", alvo[2])
        try:
            nota.call_method("Interact", (pawn,))
        except Exception as ex:
            w("Interact EXC", str(ex)[:200])
        yield from espera(0.4)
        amostra(world, pc, rotulo)
        w("NOTA ABERTA", rotulo)
        # amostra ate o bilhete fechar ou 25 s
        t0 = time.time()
        while time.time() - t0 < 25.0:
            wd = amostra(world, pc, rotulo)
            if wd is None and time.time() - t0 > 1.0:
                break
            yield from espera(0.25)
        w("NOTA ENCERRADA", rotulo)
        yield from espera(1.0)
        # a nota fecha por Backspace na segunda rodada; entre uma e outra, o jogo tem que voltar ao normal
        amostra(world, pc, "apos " + rotulo)
        # reabilita a nota (SaveNote?/DestroyOnRead?: o ator pode ter sido destruido)
    w("FIM")


def tick(dt):
    try:
        next(S["gen"])
    except StopIteration:
        fim()
    except Exception:
        w("ERRO", traceback.format_exc())
        fim()
    if time.time() - S["t0"] > 150 and not S.get("fim"):
        w("TEMPO ESGOTADO")
        fim()


def fim():
    if S.get("fim"):
        return
    S["fim"] = True
    try:
        wd = UES.get_game_world()
        if wd and GS.is_game_paused(wd):
            GS.set_game_paused(wd, False)
    except Exception:
        pass
    if L.is_in_play_in_editor():
        L.editor_request_end_play()
    unreal.unregister_slate_post_tick_callback(S["h"])
    w("encerrado")


S["gen"] = teste()
if getattr(unreal, "_lux_nota_h", None) is not None:
    unreal.unregister_slate_post_tick_callback(unreal._lux_nota_h)
S["h"] = unreal.register_slate_post_tick_callback(tick)
unreal._lux_nota_h = S["h"]
w("callback registrado")
