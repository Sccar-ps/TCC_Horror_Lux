# LUX: TESTE NO PIE da SOBREPOSICAO de botoes: o botao que fecha a pausa (A/Cross = Confirmar, B/Circle = Voltar) tambem e botao de jogo
# (A = Interagir, B = Agachar). Fechar a pausa com o botao ainda apertado NAO pode disparar a acao de jogo (nem durante o aperto, nem ao soltar).
# Roda DENTRO do editor (Python Remote Execution) e nao salva nada. Precisa do BPFL descartavel do gamepad_pie_injetor.py (rode-o antes, com o Mapa_B aberto).
#   py "<projeto>/Tools/Player/gamepad_pie_sobreposicao.py" <rotulo>   -> Saved/LuxSnapshots/entrada_pie/<rotulo>/sobreposicao_log.txt e sobreposicao_result.json
# Como: o aperto de um botao fisico chega a TODAS as acoes mapeadas nele; aqui a mesma coisa e feita injetando as duas acoes juntas, quadro a quadro, pelo tempo
# do aperto (a logica em jogo e das ACOES - gatilhos Pressed/Released contra o corte da pausa -, nao do mapeamento da tecla). Observa IsCrouching? do jogador.
import json, os, sys, time, traceback, unreal

ROT = sys.argv[1] if len(sys.argv) > 1 else "sobreposicao"
SAVED = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
OUT = os.path.join(SAVED, "LuxSnapshots", "entrada_pie", ROT)
os.makedirs(OUT, exist_ok=True)
LOG = os.path.join(OUT, "sobreposicao_log.txt")
open(LOG, "w", encoding="utf-8").close()
L = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
UES = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
GS = unreal.GameplayStatics
ACT = "/Game/FPMovement/Player/Input/Actions/"
IA = {n: unreal.load_asset(ACT + n) for n in ("IA_Crouch", "IA_Zoom")}
for n in ("IA_Pausa", "IA_UI_Voltar", "IA_UI_Confirmar"):
    IA[n] = unreal.load_asset("/Game/Masion/LUX/Entrada/" + n)
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


def agachado():
    return bool(S["pawn"].get_editor_property("IsCrouching?"))


def pausado():
    return GS.is_game_paused(S["world"])


def aperta(acoes, seg, amostra=None):
    """segura as acoes juntas (um botao fisico) por `seg` s; devolve [(t, pausado, agachado)] amostrado a cada ~0,1 s"""
    t0 = time.time()
    t_am = 0.0
    obs = []
    while time.time() - t0 < seg:
        for n in acoes:
            injeta(n)
        t = time.time() - t0
        if t >= t_am:
            obs.append((round(t, 2), pausado(), agachado()))
            t_am += 0.1
        yield
    return obs


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
    chk("base: em pe e jogo rodando", not agachado() and not pausado(), (agachado(), pausado()))

    for rotulo, botao, fecha in (("B/Circle: Voltar + Agachar", "IA_UI_Voltar", "IA_UI_Voltar"), ("A/Cross: Confirmar + Agachar (Agachar faz o papel de Interagir)", "IA_UI_Confirmar", "IA_UI_Confirmar")):
        w("--- " + rotulo)
        injeta("IA_Pausa")
        yield from espera(0.8)
        chk("[%s] pausado antes do aperto" % rotulo, pausado(), pausado())
        obs = yield from aperta((botao, "IA_Crouch"), 0.5)
        w("   amostras (t, pausado, agachado) durante o aperto:", obs)
        yield from espera(1.4)
        chk("[%s] a pausa fechou depois do aperto" % rotulo, not pausado(), pausado())
        fantasma_durante = any((not p) and a for (_t, p, a) in obs)
        chk("[%s] nenhum agachar fantasma durante o aperto" % rotulo, not fantasma_durante, obs[-3:])
        chk("[%s] nenhum agachar fantasma depois de soltar (em pe)" % rotulo, not agachado(), agachado())
        if agachado():                   # limpa para a proxima rodada
            injeta("IA_Crouch")
            yield from espera(1.4)
        yield from espera(0.4)

    # controle: o agachar de verdade (so o botao de jogo, fora da pausa) continua funcionando depois disso tudo
    injeta("IA_Crouch")
    yield from espera(1.4)
    chk("controle: agachar (B) fora da pausa continua funcionando", agachado(), agachado())
    injeta("IA_Crouch")
    yield from espera(1.4)
    chk("controle: agachar de novo volta em pe", not agachado(), agachado())


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
    with open(os.path.join(OUT, "sobreposicao_result.json"), "w", encoding="utf-8") as fh:
        json.dump({"resultados": S["res"], "erro": S.get("erro")}, fh, ensure_ascii=False, indent=1)
    if L.is_in_play_in_editor():
        L.editor_request_end_play()
    unreal.unregister_slate_post_tick_callback(S["h"])


S["gen"] = teste()
if getattr(unreal, "_lux_sob_h", None) is not None:
    unreal.unregister_slate_post_tick_callback(unreal._lux_sob_h)
S["h"] = unreal.register_slate_post_tick_callback(tick)
unreal._lux_sob_h = S["h"]
w("callback registrado")
