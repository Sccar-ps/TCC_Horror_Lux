# LUX: TESTE NO PIE dos EIXOS do controle (Move e Look): DIRECAO e VELOCIDADE reais, pela cadeia de modificadores que esta no IMC_Default.
# Roda DENTRO do editor (Python Remote Execution) e nao salva nada. Precisa do BPFL descartavel do gamepad_pie_injetor.py (rode-o antes, com o Mapa_B aberto).
#   py "<projeto>/Tools/Player/gamepad_pie_eixos.py" <rotulo>     -> Saved/LuxSnapshots/entrada_pie/<rotulo>/eixos_log.txt e eixos_result.json
# Como: inject_input_vector_for_action(IA, vetor_bruto, modificadores_do_mapeamento, []) faz o que o hardware faria (valor bruto da tecla ou do stick
# passando pelos MESMOS modificadores do IMC), menos o dispositivo. Compara o stick com o mouse (Mouse2D) e com as teclas (W/A/S/D).
# Por que existe: com bEnableLegacyInputScales ligado, a escala de pitch do PlayerController e -2,5 (BaseGame.ini): AddControllerPitchInput(+) olha para BAIXO.
# O mouse tem Negate no Y por isso; o stick do pack nao tinha e empurrar o stick direito para cima olhava para baixo (corrigido em gamepad_input.py).
import json, math, os, sys, time, traceback, unreal

ROT = sys.argv[1] if len(sys.argv) > 1 else "eixos"
SAVED = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
OUT = os.path.join(SAVED, "LuxSnapshots", "entrada_pie", ROT)
os.makedirs(OUT, exist_ok=True)
LOG = os.path.join(OUT, "eixos_log.txt")
open(LOG, "w", encoding="utf-8").close()
L = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
UES = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
GS = unreal.GameplayStatics
SL = unreal.SystemLibrary
ACT = "/Game/FPMovement/Player/Input/Actions/"
IA_LOOK = unreal.load_asset(ACT + "IA_Look")
IA_MOVE = unreal.load_asset(ACT + "IA_Move")
IMC_DEFAULT = unreal.load_asset("/Game/FPMovement/Player/Input/IMC_Default")
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


def mapeamento(acao, tecla):
    for m in IMC_DEFAULT.get_editor_property("default_key_mappings").get_editor_property("mappings"):
        if m.get_editor_property("action") == acao and str(m.get_editor_property("key").get_editor_property("key_name")) == tecla:
            return m
    raise RuntimeError("mapeamento %s <- %s nao existe" % (acao.get_name(), tecla))


def mods(acao, tecla, sem=()):
    """a cadeia de modificadores do mapeamento (sem=nomes de classes a tirar: reconstitui o que o pack tinha)"""
    return [x for x in mapeamento(acao, tecla).get_editor_property("modifiers") if x.get_class().get_name() not in sem]


def norm(a):
    return (a + 180.0) % 360.0 - 180.0


def injeta(acao, vec, lista, seg):
    """injeta o valor bruto com os modificadores do mapeamento a cada quadro por `seg` s de relogio; devolve (tempo de JOGO decorrido, injecoes, quadros do motor)"""
    t_ini, f_ini = GS.get_time_seconds(S["world"]), SL.get_frame_count()
    n = 0
    t0 = time.time()
    while time.time() - t0 < seg:
        S["sub"].inject_input_vector_for_action(acao, vec, lista, [])
        n += 1
        yield
    return GS.get_time_seconds(S["world"]) - t_ini, n, SL.get_frame_count() - f_ini


def gira(vec, lista, seg):
    """zera a rotacao, injeta no IA_Look e devolve (pitch, yaw, tempo_de_jogo, injecoes, quadros)"""
    S["pc"].set_control_rotation(unreal.Rotator(roll=0.0, pitch=0.0, yaw=0.0))
    yield from espera(0.4)
    dt, n, nf = yield from injeta(IA_LOOK, vec, lista, seg)
    yield from espera(0.4)
    r = S["pc"].get_control_rotation()
    return norm(r.pitch), norm(r.yaw), dt, n, nf


def limita_fps(fps):
    """teto de FPS do motor (t.MaxFPS): o teste mede a mesma coisa a 30, 60 e 120 quadros/s. No editor em segundo plano o teto nem chega a valer"""
    SL.execute_console_command(S["world"], "t.MaxFPS %d" % fps, S["pc"])


def anda(vec, lista, seg):
    """volta ao ponto de partida, injeta no IA_Move e devolve (distancia para a frente, para a direita) em cm"""
    S["pc"].set_control_rotation(unreal.Rotator(roll=0.0, pitch=0.0, yaw=S["yaw0"]))
    S["pawn"].set_actor_location(S["loc0"], False, True)
    yield from espera(0.7)
    p0 = S["pawn"].get_actor_location()
    yield from injeta(IA_MOVE, vec, lista, seg)
    p1 = S["pawn"].get_actor_location()
    d = p1 - p0
    f, r = S["pawn"].get_actor_forward_vector(), S["pawn"].get_actor_right_vector()
    return d.x * f.x + d.y * f.y + d.z * f.z, d.x * r.x + d.y * r.y + d.z * r.z


def teste():
    L.editor_request_begin_play()
    while True:
        world = UES.get_game_world()
        if world:
            pawn, pc = GS.get_player_pawn(world, 0), GS.get_player_controller(world, 0)
            if pawn and pc:
                break
        yield
    S.update(world=world, pawn=pawn, pc=pc, loc0=pawn.get_actor_location(), yaw0=norm(pc.get_control_rotation().yaw))
    w("PIE pronto | pawn:", pawn.get_class().get_name(), "| inicio:", S["loc0"])
    yield from espera(2.5)
    cls = unreal.load_object(None, "/Game/Masion/LUX/_TesteEntrada/BPFL_TesteInput.BPFL_TesteInput_C")
    r = unreal.get_default_object(cls).call_method("ObterSub", (world, pc))
    S["sub"] = r[0] if isinstance(r, (tuple, list)) else r
    chk("subsistema do Enhanced Input do jogador encontrado", S["sub"] is not None, S["sub"])
    if S["sub"] is None:
        return
    w("cadeia do mouse:", [x.get_class().get_name() for x in mods(IA_LOOK, "Mouse2D")])
    w("cadeia do stick direito:", [x.get_class().get_name() for x in mods(IA_LOOK, "Gamepad_Right2D")])
    w("cadeia do stick esquerdo:", [x.get_class().get_name() for x in mods(IA_MOVE, "Gamepad_Left2D")])

    # ---------------- LOOK: direcao (o valor bruto do eixo e +Y para CIMA e +X para a DIREITA, tanto no mouse quanto no stick) ----------------
    # valores pequenos para a rotacao nao dar a volta a quadros altos (so o sinal importa aqui); a velocidade vem abaixo
    up = unreal.Vector(0.0, 1.0, 0.0)
    rt = unreal.Vector(1.0, 0.0, 0.0)
    p, y, _, _, _ = yield from gira(unreal.Vector(0.0, 0.2, 0.0), mods(IA_LOOK, "Mouse2D"), 0.3)   # mouse: contagens por quadro, nao -1..1
    chk("Look: MOUSE para cima olha para cima (pitch %+.2f)" % p, p > 0.05, round(p, 3))
    p, y, _, _, _ = yield from gira(unreal.Vector(0.2, 0.0, 0.0), mods(IA_LOOK, "Mouse2D"), 0.3)
    chk("Look: MOUSE para a direita gira a direita (yaw %+.2f)" % y, y > 0.05, round(y, 3))
    p, y, _, _, _ = yield from gira(unreal.Vector(0.0, 0.3, 0.0), mods(IA_LOOK, "Gamepad_Right2D", sem=("InputModifierNegate",)), 0.3)
    w("   (referencia: o stick SEM o Negate, como o pack o entregava, deu pitch %+.2f)" % p)
    S["pitch_sem_negate"] = p
    p, y, _, _, _ = yield from gira(unreal.Vector(0.0, 0.3, 0.0), mods(IA_LOOK, "Gamepad_Right2D"), 0.3)
    chk("Look: STICK para cima olha para cima (pitch %+.2f; sem o Negate dava %+.2f)" % (p, S["pitch_sem_negate"]), p > 0.05 and S["pitch_sem_negate"] < -0.05, (round(p, 3), round(S["pitch_sem_negate"], 3)))
    p, y, _, _, _ = yield from gira(unreal.Vector(0.0, -0.3, 0.0), mods(IA_LOOK, "Gamepad_Right2D"), 0.3)
    chk("Look: STICK para baixo olha para baixo (pitch %+.2f)" % p, p < -0.05, round(p, 3))
    p, y, _, _, _ = yield from gira(unreal.Vector(0.3, 0.0, 0.0), mods(IA_LOOK, "Gamepad_Right2D"), 0.3)
    chk("Look: STICK para a direita gira a direita (yaw %+.2f)" % y, y > 0.05, round(y, 3))
    p, y, _, _, _ = yield from gira(unreal.Vector(-0.3, 0.0, 0.0), mods(IA_LOOK, "Gamepad_Right2D"), 0.3)
    chk("Look: STICK para a esquerda gira a esquerda (yaw %+.2f)" % y, y < -0.05, round(y, 3))
    # ---------------- LOOK: velocidade em graus por segundo de TEMPO DE JOGO, a varios FPS (ScaleByDeltaTime x60 = independe do FPS) ----------------
    esperado = 150.0
    for fps in (30, 60, 120):
        limita_fps(fps)
        yield from espera(0.8)
        p, y, dt, n, nf = yield from gira(rt, mods(IA_LOOK, "Gamepad_Right2D"), 0.9)
        taxa = y / dt if dt > 0 else 0.0
        w("   teto %d FPS: %.1f graus em %.3f s de jogo (%d injecoes, %d quadros do motor = %.0f quadros/s)" % (fps, y, dt, n, nf, nf / dt if dt else 0))
        chk("Look: stick a fundo = ~150 graus/s de tempo de jogo com teto de %d FPS (medido %.0f, %d quadros/s)" % (fps, taxa, nf / dt if dt else 0), abs(taxa - esperado) < 0.15 * esperado, round(taxa, 1))
    limita_fps(60)
    yield from espera(0.5)
    p, y, dt, n, nf = yield from gira(unreal.Vector(0.5, 0.0, 0.0), mods(IA_LOOK, "Gamepad_Right2D"), 0.9)
    taxa_m = y / dt if dt > 0 else 0.0
    esperado_m = 150.0 * (0.5 - 0.25) / (0.95 - 0.25)
    chk("Look: stick a meia inclinacao = %.0f graus/s (zona morta radial 0,25..0,95, curva linear): medido %.0f" % (esperado_m, taxa_m), abs(taxa_m - esperado_m) < 0.2 * esperado_m, round(taxa_m, 1))
    p, y, dt, n, nf = yield from gira(unreal.Vector(0.2, 0.1, 0.0), mods(IA_LOOK, "Gamepad_Right2D"), 0.9)
    chk("Look: dentro da zona morta (0,22 de inclinacao) a camera nao se move (pitch %.2f, yaw %.2f)" % (p, y), abs(p) < 0.5 and abs(y) < 0.5, (round(p, 3), round(y, 3)))
    limita_fps(0)

    # ---------------- MOVE: direcao e velocidade ----------------
    seg = 0.6
    esquerdo = mods(IA_MOVE, "Gamepad_Left2D")
    f_w, r_w = yield from anda(unreal.Vector(1.0, 0.0, 0.0), mods(IA_MOVE, "W"), seg)
    f_s, r_s = yield from anda(unreal.Vector(1.0, 0.0, 0.0), mods(IA_MOVE, "S"), seg)
    f_d, r_d = yield from anda(unreal.Vector(1.0, 0.0, 0.0), mods(IA_MOVE, "D"), seg)
    f_a, r_a = yield from anda(unreal.Vector(1.0, 0.0, 0.0), mods(IA_MOVE, "A"), seg)
    w("   teclado (cm em %.1f s): W frente %.0f | S frente %.0f | D direita %.0f | A direita %.0f" % (seg, f_w, f_s, r_d, r_a))
    f_u, r_u = yield from anda(unreal.Vector(0.0, 1.0, 0.0), esquerdo, seg)
    f_dn, r_dn = yield from anda(unreal.Vector(0.0, -1.0, 0.0), esquerdo, seg)
    f_r, r_r = yield from anda(unreal.Vector(1.0, 0.0, 0.0), esquerdo, seg)
    f_l, r_l = yield from anda(unreal.Vector(-1.0, 0.0, 0.0), esquerdo, seg)
    w("   stick (cm em %.1f s): cima frente %.0f | baixo frente %.0f | direita %.0f | esquerda %.0f" % (seg, f_u, f_dn, r_r, r_l))
    chk("Move: W anda para a frente (%.0f cm)" % f_w, f_w > 30.0, round(f_w, 1))
    chk("Move: STICK para cima anda para a frente, como o W (%.0f cm contra %.0f)" % (f_u, f_w), f_u > 30.0 and abs(f_u - f_w) < 0.2 * max(f_w, 1.0), (round(f_u, 1), round(f_w, 1)))
    chk("Move: S e STICK para baixo andam para tras (%.0f e %.0f cm)" % (f_s, f_dn), f_s < -30.0 and f_dn < -30.0, (round(f_s, 1), round(f_dn, 1)))
    chk("Move: D e STICK para a direita andam para a direita (%.0f e %.0f cm)" % (r_d, r_r), r_d > 30.0 and r_r > 30.0, (round(r_d, 1), round(r_r, 1)))
    chk("Move: A e STICK para a esquerda andam para a esquerda (%.0f e %.0f cm)" % (r_a, r_l), r_a < -30.0 and r_l < -30.0, (round(r_a, 1), round(r_l, 1)))
    chk("Move: STICK sem desvio lateral ao andar para a frente (%.0f cm)" % r_u, abs(r_u) < 10.0, round(r_u, 1))
    f_30, _ = yield from anda(unreal.Vector(0.0, 0.3, 0.0), esquerdo, seg)
    chk("Move: stick a 0,3 de inclinacao ja anda na velocidade cheia (x50 satura, como as teclas): %.0f cm contra %.0f" % (f_30, f_u), abs(f_30 - f_u) < 0.15 * max(f_u, 1.0), (round(f_30, 1), round(f_u, 1)))
    f_dz, r_dz = yield from anda(unreal.Vector(0.0, 0.2, 0.0), esquerdo, seg)
    chk("Move: dentro da zona morta (0,2) o jogador nao anda (%.1f cm)" % f_dz, abs(f_dz) < 5.0 and abs(r_dz) < 5.0, (round(f_dz, 2), round(r_dz, 2)))
    f_dg, r_dg = yield from anda(unreal.Vector(0.12, 0.13, 0.0), esquerdo, seg)
    chk("Move: drift em diagonal (0,18 de inclinacao) nao anda (%.1f cm)" % ((f_dg ** 2 + r_dg ** 2) ** 0.5), (f_dg ** 2 + r_dg ** 2) ** 0.5 < 5.0, (round(f_dg, 2), round(r_dg, 2)))
    S["pawn"].set_actor_location(S["loc0"], False, True)
    S["pc"].set_control_rotation(unreal.Rotator(roll=0.0, pitch=0.0, yaw=S["yaw0"]))


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
    with open(os.path.join(OUT, "eixos_result.json"), "w", encoding="utf-8") as fh:
        json.dump({"resultados": S["res"], "erro": S.get("erro")}, fh, ensure_ascii=False, indent=1)
    if L.is_in_play_in_editor():
        L.editor_request_end_play()
    unreal.unregister_slate_post_tick_callback(S["h"])


S["gen"] = teste()
if getattr(unreal, "_lux_eixos_h", None) is not None:
    unreal.unregister_slate_post_tick_callback(unreal._lux_eixos_h)
S["h"] = unreal.register_slate_post_tick_callback(tick)
unreal._lux_eixos_h = S["h"]
w("callback registrado")
