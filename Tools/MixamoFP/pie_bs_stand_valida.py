# LUX: VALIDACAO NO PIE do corpo do jogador (ABP_CowboyFP + BS_CB_Stand). Roda DENTRO do editor (Python Remote Execution) e NAO salva nada.
#   py "<projeto>/Tools/MixamoFP/pie_bs_stand_valida.py" <rotulo>   -> Saved/LuxSnapshots/anim_pie/<rotulo>/anim_log.txt e anim_result.json
# Por que existe: o BS_CB_Stand tinha a amostra A_CB_Run_F fora do eixo Speed (400,032 > 400): o motor a marca invalida e a TIRA da triangulacao
# (BlendSpace.cpp, ValidateSampleData / ResampleData2D), entao ela nao entra na mistura. O jogo anda a 170 cm/s (acima do Walk_F, em 150): essa
# mistura passa por triangulos que envolvem as amostras de corrida. Este teste mede, pelo proprio motor, o que o corpo faz:
#   - Speed e Direction que chegam ao BlendSpace (variaveis do ABP_CowboyFP);
#   - o movimento dos pes no referencial do jogador (alcance para frente, para o lado e vertical; passos por segundo), em 8 direcoes a andar,
#     parado, e a corrida para frente (o IA_Sprint esta desligado no IMC; aqui o evento do BP e chamado so no PIE, so para medir a Run_F);
# Rode antes e depois de mexer no BlendSpace e compare os dois anim_result.json (anim_compara.py).
import json, math, os, sys, time, traceback, unreal

ROT = sys.argv[1] if len(sys.argv) > 1 else "anim"
SAVED = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
OUT = os.path.join(SAVED, "LuxSnapshots", "anim_pie", ROT)
os.makedirs(OUT, exist_ok=True)
LOG = os.path.join(OUT, "anim_log.txt")
open(LOG, "w", encoding="utf-8").close()
L = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
UES = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
GS = unreal.GameplayStatics
IA_DIR = "/Game/FPMovement/Player/Input/Actions/"
S = {"res": [], "t0": time.time(), "feat": {}}
PES = ("foot_l", "foot_r")
AQUECE, MEDE = 0.8, 1.6        # segundos de relogio: aceleracao + janela medida
# (nome, (frente, direita), corre). Direcao relativa ao jogador; o jogador nao gira.
FASES = [("parado", None, False),
         ("andar_F", (1.0, 0.0), False), ("andar_FD", (0.7071, 0.7071), False), ("andar_D", (0.0, 1.0), False), ("andar_TD", (-0.7071, 0.7071), False),
         ("andar_T", (-1.0, 0.0), False), ("andar_TE", (-0.7071, -0.7071), False), ("andar_E", (0.0, -1.0), False), ("andar_FE", (0.7071, -0.7071), False),
         ("correr_F", (1.0, 0.0), True)]


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


def cruzamentos(serie):
    """quantas vezes a serie troca de sinal (um passo = uma troca)"""
    n, ant = 0, 0
    for v in serie:
        s = 1 if v > 0 else (-1 if v < 0 else 0)
        if s and ant and s != ant:
            n += 1
        if s:
            ant = s
    return n


def evento_sprint(pawn, inicia):
    """chama o evento do BP_Player (so no PIE): Started (8) liga a corrida, Completed (9) desliga (indices lidos do pie_dirspeed.py de 23/09;
    se o BP for recompilado e mudarem, o teste 'correr para frente' falha e acusa)"""
    ia = unreal.load_asset(IA_DIR + "IA_Sprint")
    idx = 8 if inicia else 9
    try:
        pawn.call_method("InpActEvt_IA_Sprint_K2Node_EnhancedInputActionEvent_%d" % idx, (unreal.InputActionValue(), 0.0, 0.0, ia))
        return idx
    except Exception as e:
        w("   evento do sprint %d falhou: %s" % (idx, str(e)[:120]))
        return None


def fase(nome, d, corre):
    pawn, pc, mesh, ai, cmc = S["pawn"], S["pc"], S["mesh"], S["ai"], S["cmc"]
    pawn.set_actor_location(S["loc0"], False, True)
    cmc.stop_movement_immediately()
    # o ponto de partida tem parede dos lados e atras: gira o jogador para que o deslocamento (o vetor frente/direita pedido) siga sempre o corredor livre
    # (a direcao RELATIVA ao corpo, a que o ABP ve, e a mesma; o referencial dos pes e o do jogador)
    theta = math.degrees(math.atan2(d[1], d[0])) if d is not None else 0.0
    pc.set_control_rotation(unreal.Rotator(roll=0.0, pitch=0.0, yaw=S["yaw0"] - theta))
    yield from espera(0.6)
    if corre:
        S["sprint_idx"] = evento_sprint(pawn, True)
    fw, rt = pawn.get_actor_forward_vector(), pawn.get_actor_right_vector()
    amost, t0, t_jogo0 = [], time.time(), GS.get_time_seconds(S["world"])
    while time.time() - t0 < AQUECE + MEDE:
        if d is not None:
            pawn.add_movement_input(fw * d[0] + rt * d[1], 1.0, False)
        if time.time() - t0 >= AQUECE:
            p0 = pawn.get_actor_location()
            reg = {"t": GS.get_time_seconds(S["world"]), "speed": ai.get_editor_property("Speed"), "dir": ai.get_editor_property("Direction")}
            for pe in PES:
                q = mesh.get_socket_location(pe) - p0
                reg[pe] = (q.x * fw.x + q.y * fw.y + q.z * fw.z, q.x * rt.x + q.y * rt.y + q.z * rt.z, q.z)
            amost.append(reg)
        yield
    if corre:
        evento_sprint(pawn, False)
    cmc.stop_movement_immediately()
    f = {"n": len(amost)}
    if amost:
        dur = amost[-1]["t"] - amost[0]["t"]
        f["dur_jogo"] = dur
        f["speed_medio"] = sum(a["speed"] for a in amost) / len(amost)
        f["dir_medio"] = math.degrees(math.atan2(sum(math.sin(math.radians(a["dir"])) for a in amost), sum(math.cos(math.radians(a["dir"])) for a in amost)))
        for k, pe in enumerate(PES):
            for j, eixo in enumerate(("frente", "lado", "altura")):
                v = [a[pe][j] for a in amost]
                f["%s_%s_alcance" % (pe, eixo)] = max(v) - min(v)
        for j, eixo in enumerate(("frente", "lado")):
            dif = [a[PES[0]][j] - a[PES[1]][j] for a in amost]
            f["passos_por_s_%s" % eixo] = cruzamentos(dif) / dur if dur > 0 else 0.0
    S["feat"][nome] = f
    w("FASE %-9s n=%3d speed=%6.1f dir=%7.1f | pe_L alcance frente=%5.1f lado=%5.1f altura=%5.1f | pe_R frente=%5.1f lado=%5.1f altura=%5.1f | passos/s frente=%.2f lado=%.2f" % (
        nome, f["n"], f.get("speed_medio", 0), f.get("dir_medio", 0), f.get("foot_l_frente_alcance", 0), f.get("foot_l_lado_alcance", 0), f.get("foot_l_altura_alcance", 0),
        f.get("foot_r_frente_alcance", 0), f.get("foot_r_lado_alcance", 0), f.get("foot_r_altura_alcance", 0), f.get("passos_por_s_frente", 0), f.get("passos_por_s_lado", 0)))


def espera_fps(minimo=40.0, max_s=120.0):
    """o editor cai para ~3 FPS quando perde o foco (a CPU e limitada em segundo plano) e a fase ficaria sem amostras: espera o FPS voltar (quem roda traz o
    editor para a frente) antes de cada fase"""
    t0 = time.time()
    while time.time() - t0 < max_s:
        n, ti = 0, time.time()
        while time.time() - ti < 0.5:
            n += 1
            yield
        if n / (time.time() - ti) >= minimo:
            return True
    return False


def teste():
    L.editor_request_begin_play()
    while True:
        world = UES.get_game_world()
        if world:
            pawn, pc = GS.get_player_pawn(world, 0), GS.get_player_controller(world, 0)
            if pawn and pc:
                break
        yield
    mesh = pawn.get_editor_property("mesh")
    S.update(world=world, pawn=pawn, pc=pc, mesh=mesh, cmc=pawn.get_editor_property("character_movement"), loc0=pawn.get_actor_location(), yaw0=pc.get_control_rotation().yaw)
    yield from espera(2.5)
    S["ai"] = mesh.get_anim_instance()
    w("PIE pronto | pawn:", pawn.get_class().get_name(), "| ABP:", S["ai"].get_class().get_name() if S["ai"] else None, "| inicio:", S["loc0"])
    chk("o corpo (Mesh) roda o ABP_CowboyFP", S["ai"] is not None and S["ai"].get_class().get_name().startswith("ABP_CowboyFP"), S["ai"].get_class().get_name() if S["ai"] else None)
    for pe in PES:
        chk("o osso %s existe na malha-sombra" % pe, mesh.does_socket_exist(pe))
    if S["ai"] is None or not all(mesh.does_socket_exist(pe) for pe in PES):
        return
    quais = sys.argv[2].split(",") if len(sys.argv) > 2 else None        # 2o argumento opcional: so essas fases (ex.: correr_F,andar_T)
    for nome, d, corre in FASES:
        if quais and nome not in quais:
            continue
        ok_fps = yield from espera_fps()
        if not ok_fps:
            w("   (FPS baixo por mais de 120 s antes da fase %s: o editor esta sem foco)" % nome)
        yield from fase(nome, d, corre)
    pawn.set_actor_location(S["loc0"], False, True)
    # ---- o que se confere em qualquer estado do BlendSpace (o antes x depois fica no anim_compara.py)
    parado, andar = S["feat"].get("parado", {}), S["feat"].get("andar_F", {})
    chk("parado: os pes quase nao se movem (alcance frente %.1f cm)" % parado.get("foot_l_frente_alcance", 999), parado.get("foot_l_frente_alcance", 999) < 12.0, round(parado.get("foot_l_frente_alcance", 999), 2))
    chk("andar para frente: Speed no ABP = %.0f (esperado ~170)" % andar.get("speed_medio", 0), 140.0 < andar.get("speed_medio", 0) < 185.0, round(andar.get("speed_medio", 0), 1))
    chk("andar para frente: os pes se movem (alcance %.0f cm) e alternam (%.1f passos/s)" % (andar.get("foot_l_frente_alcance", 0), andar.get("passos_por_s_frente", 0)),
        andar.get("foot_l_frente_alcance", 0) > 15.0 and andar.get("passos_por_s_frente", 0) > 1.0, (round(andar.get("foot_l_frente_alcance", 0), 1), round(andar.get("passos_por_s_frente", 0), 2)))
    poucas = [n for n, f in S["feat"].items() if f.get("n", 0) < 100]
    chk("amostragem suficiente em todas as fases (>= 100 quadros medidos; o editor nao pode ter caido para ~3 FPS): %s" % (poucas or "ok"), not poucas, poucas)
    bloq = [n for n, f in S["feat"].items() if n.startswith("andar_") and f.get("speed_medio", 0) < 100.0]
    chk("nenhuma fase de andar ficou bloqueada por parede (Speed < 100: %s)" % (bloq or "nenhuma"), not bloq, bloq)
    cor = S["feat"].get("correr_F", {})
    chk("correr para frente: Speed no ABP = %.0f (esperado ~400)" % cor.get("speed_medio", 0), cor.get("speed_medio", 0) > 330.0, round(cor.get("speed_medio", 0), 1))


def tick(dt):
    try:
        next(S["gen"])
    except StopIteration:
        encerra()
    except Exception:
        S["erro"] = traceback.format_exc()
        w("ERRO", S["erro"])
        encerra()
    if time.time() - S["t0"] > 420 and not S.get("fim"):
        w("TEMPO ESGOTADO")
        encerra()


def encerra():
    if S.get("fim"):
        return
    S["fim"] = True
    n_ok = len([r for r in S["res"] if r["ok"]])
    w("FIM: %d PASS, %d FAIL" % (n_ok, len(S["res"]) - n_ok))
    with open(os.path.join(OUT, "anim_result.json"), "w", encoding="utf-8") as fh:
        json.dump({"resultados": S["res"], "fases": S["feat"], "erro": S.get("erro"), "sprint_evento": S.get("sprint_idx")}, fh, ensure_ascii=False, indent=1)
    if L.is_in_play_in_editor():
        L.editor_request_end_play()
    unreal.unregister_slate_post_tick_callback(S["h"])


S["gen"] = teste()
S["h"] = unreal.register_slate_post_tick_callback(tick)
w("callback registrado")
