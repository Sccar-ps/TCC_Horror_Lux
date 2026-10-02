# LUX: TESTE NO PIE de SEGURAR/SOLTAR (hold e release) e do estado depois da pausa: o zoom (LT) e o agachar (B) com a pausa no meio.
# Roda DENTRO do editor (Python Remote Execution) e nao salva nada. Precisa do BPFL descartavel do gamepad_pie_injetor.py (rode-o antes, com o Mapa_B aberto).
#   py "<projeto>/Tools/Player/gamepad_pie_hold.py" <rotulo>     -> Saved/LuxSnapshots/entrada_pie/<rotulo>/hold_log.txt e hold_result.json
# Injeta as ACOES (inject_input_vector_for_action) quadro a quadro, como um botao segurado: parar de injetar = soltar. Mede as variaveis do BP_Player
# (IsZooming?, IsCrouching?). O que o teste NAO cobre: o estado da tecla fisica no motor (bShouldBeIgnored do RequestRebuildControlMappings): isso so com o controle.
import json, os, sys, time, traceback, unreal

ROT = sys.argv[1] if len(sys.argv) > 1 else "hold"
SAVED = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
OUT = os.path.join(SAVED, "LuxSnapshots", "entrada_pie", ROT)
os.makedirs(OUT, exist_ok=True)
LOG = os.path.join(OUT, "hold_log.txt")
open(LOG, "w", encoding="utf-8").close()
L = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
UES = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
GS = unreal.GameplayStatics
ACT = "/Game/FPMovement/Player/Input/Actions/"
IA = {n: unreal.load_asset(ACT + n) for n in ("IA_Zoom", "IA_Crouch", "IA_Move", "IA_Interact", "IA_Flashlight")}
IA["IA_Pausa"] = unreal.load_asset("/Game/Masion/LUX/Entrada/IA_Pausa")
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


def injeta(nome, v=1.0):
    S["sub"].inject_input_vector_for_action(IA[nome], unreal.Vector(v, 0.0, 0.0), [], [])


def frames(seg, *acoes):
    """segura as acoes (injeta a cada quadro) por `seg` s; parar de injetar = soltar"""
    t0 = time.time()
    while time.time() - t0 < seg:
        for n in acoes:
            injeta(n)
        yield


def zoom():
    return bool(S["pawn"].get_editor_property("IsZooming?"))


def agachado():
    return bool(S["pawn"].get_editor_property("IsCrouching?"))


def pausado():
    return GS.is_game_paused(S["world"])


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
    cls = unreal.load_object(None, "/Game/Masion/LUX/_TesteEntrada/BPFL_TesteInput.BPFL_TesteInput_C")
    r = unreal.get_default_object(cls).call_method("ObterSub", (world, pc))
    S["sub"] = r[0] if isinstance(r, (tuple, list)) else r
    chk("subsistema do Enhanced Input do jogador encontrado", S["sub"] is not None)
    if S["sub"] is None:
        return
    chk("base: sem zoom, em pe, jogo rodando", not zoom() and not agachado() and not pausado(), (zoom(), agachado(), pausado()))

    # ---- A) segurar e soltar (LT): Started liga, Completed desliga
    yield from frames(0.7, "IA_Zoom")
    chk("zoom (LT): segurar liga o zoom", zoom(), zoom())
    yield from espera(0.4)
    chk("zoom (LT): soltar desliga o zoom", not zoom(), zoom())

    # ---- B) pausar com o botao ainda segurado, soltar DURANTE a pausa, continuar
    yield from frames(0.5, "IA_Zoom")
    chk("zoom ligado antes de pausar", zoom(), zoom())
    injeta("IA_Pausa"); injeta("IA_Zoom")
    yield
    yield from frames(0.8, "IA_Zoom")      # ainda segurando, com o jogo pausado
    chk("o jogo pausou com o zoom segurado", pausado(), pausado())
    w("   (informativo) zoom com o jogo pausado e o botao segurado:", zoom())
    S["zoom_na_pausa"] = zoom()
    yield from espera(0.4)                 # soltou durante a pausa
    injeta("IA_Pausa")
    yield from espera(0.9)
    chk("continuou", not pausado(), pausado())
    chk("zoom NAO fica preso depois de pausar segurando e soltar na pausa", not zoom(), zoom())

    # ---- C) o controle volta a responder depois da pausa
    yield from frames(0.7, "IA_Zoom")
    chk("depois da pausa: segurar liga o zoom de novo", zoom(), zoom())
    yield from espera(0.4)
    chk("depois da pausa: soltar desliga o zoom", not zoom(), zoom())

    # ---- D) pausar segurando e continuar com o botao AINDA segurado: ao soltar, desliga (nada preso)
    yield from frames(0.5, "IA_Zoom")
    injeta("IA_Pausa"); injeta("IA_Zoom")
    yield
    yield from frames(0.5, "IA_Zoom")
    injeta("IA_Pausa"); injeta("IA_Zoom")
    yield
    yield from frames(0.8, "IA_Zoom")      # voltou ao jogo ainda segurando
    w("   (informativo) zoom logo depois de continuar com o botao segurado:", zoom())
    yield from espera(0.5)                 # soltou
    chk("pausar e continuar segurando, depois soltar: zoom desligado", not zoom() and not pausado(), (zoom(), pausado()))

    # ---- E) agachar alterna (B): estado preservado pela pausa e o toggle segue funcionando
    injeta("IA_Crouch")
    yield from espera(1.4)
    chk("agachar (B) alterna: agachado", agachado(), agachado())
    injeta("IA_Pausa")
    yield from espera(0.8)
    injeta("IA_Pausa")
    yield from espera(0.8)
    chk("estado agachado preservado depois de pausar e continuar", agachado() and not pausado(), (agachado(), pausado()))
    injeta("IA_Crouch")
    yield from espera(1.4)
    chk("agachar alterna de volta depois da pausa: em pe", not agachado(), agachado())

    # ---- F) acoes de gameplay NAO agem com o jogo pausado (nao ha tecla que passe pela pausa)
    injeta("IA_Pausa")
    yield from espera(0.8)
    chk("pausado (para o teste das acoes de gameplay)", pausado(), pausado())
    injeta("IA_Crouch")
    yield from frames(0.4, "IA_Zoom")
    yield from espera(0.3)
    injeta("IA_Pausa")
    yield from espera(0.9)
    chk("com o jogo pausado, agachar e zoom nao agem (em pe, sem zoom)", not agachado() and not zoom() and not pausado(), (agachado(), zoom(), pausado()))

    # ---- G) andar segurando, pausar e continuar: nao fica andando sozinho
    yield from frames(0.5, "IA_Move")
    injeta("IA_Pausa"); injeta("IA_Move")
    yield
    yield from frames(0.5, "IA_Move")
    injeta("IA_Pausa")
    yield from espera(1.2)
    v = pawn.get_velocity()
    vel = (v.x ** 2 + v.y ** 2) ** 0.5
    chk("andar, pausar e continuar sem segurar: o jogador para (velocidade %.1f cm/s)" % vel, vel < 10.0 and not pausado(), (round(vel, 1), pausado()))


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
    try:
        wd = UES.get_game_world()
        if wd and GS.is_game_paused(wd):
            GS.set_game_paused(wd, False)
    except Exception:
        pass
    n_ok = len([r for r in S["res"] if r["ok"]])
    w("FIM: %d PASS, %d FAIL" % (n_ok, len(S["res"]) - n_ok))
    with open(os.path.join(OUT, "hold_result.json"), "w", encoding="utf-8") as fh:
        json.dump({"resultados": S["res"], "erro": S.get("erro")}, fh, ensure_ascii=False, indent=1)
    if L.is_in_play_in_editor():
        L.editor_request_end_play()
    unreal.unregister_slate_post_tick_callback(S["h"])


S["gen"] = teste()
if getattr(unreal, "_lux_hold_h", None) is not None:
    unreal.unregister_slate_post_tick_callback(unreal._lux_hold_h)
S["h"] = unreal.register_slate_post_tick_callback(tick)
unreal._lux_hold_h = S["h"]
w("callback registrado")
