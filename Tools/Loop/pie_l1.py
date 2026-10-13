# LUX - harness de PIE do Loop 1 (BP_LuxVultoFluido), 05/10/2026. Rode com `python -B ue_cli.py file pie_l1.py <evento> <cenario>` (editor grafico aberto, Mapa_B carregado, fora do PIE).
# Resultados em Saved/LuxSnapshots/l1_fluido (nao versionado).
# Harness de PIE v2: Loop 1 DE VERDADE (troca real de loop, luzes do Loop 1 ligadas) + capturas de tela nos instantes certos + log por quadro.
#   ue_cli.py file pie_fluido2.py <evento> <cenario>
#   evento: EV_L1_PassosPesados | EV_L1_VultoParado
#   cenario: loop1_leste (jogador na S1 olhando para a sala, a figura passa a direita e segue) | loop1_oeste (S1 olhando para o vao: a figura vem na direcao do jogador)
#            loop1_vao (jogador no corredor olhando para o vao do escritorio; so para o EV_L1_VultoParado)
# Editor em primeiro plano (foco reafirmado). Nao salva nada. Resultado: pie_fluido2_<evento>_<cenario>.json e shots/<evento>_<cenario>_tNNN.png
import ctypes
import ctypes.wintypes as wt
import json
import os
import sys
import time
import traceback
import unreal

SCR = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), "LuxSnapshots", "l1_fluido").replace("\\", "/")
os.makedirs(SCR, exist_ok=True)
EVENTO = sys.argv[1] if len(sys.argv) > 1 else "EV_L1_PassosPesados"
CEN = sys.argv[2] if len(sys.argv) > 2 else "loop1_leste"
OUT = "%s/pie_l1_%s_%s.json" % (SCR, EVENTO, CEN)
SHOTDIR = SCR + "/shots"
os.makedirs(SHOTDIR, exist_ok=True)
FIGURA = {"EV_L1_PassosPesados": "LUX_Vulto_L1_Passos", "EV_L1_VultoParado": "LUX_Vulto_L1_Porta"}[EVENTO]
LUZES = ("LUX_L1_LuzFundo", "LUX_L1_LuzPassos", "LUX_Luz_Corredor_Arandela3", "LUX_Luz_Corredor_Arandela5")
V3LUZ = CEN.endswith("_v3luz")
CEN_BASE = CEN.replace("_v3luz", "")
POS = {"loop1_leste": ((-3054.0, -627.0), 0.0), "loop1_oeste": ((-3054.0, -627.0), 180.0), "loop1_vao": ((-3275.0, -100.0), -90.0),
       "loop1_mira": ((-3054.0, -627.0), 0.0), "loop1_mira_perto": ((-3180.0, -640.0), 0.0)}[CEN_BASE]
MIRA = CEN_BASE.startswith("loop1_mira")
SHOTS = {"EV_L1_PassosPesados": [0.30, 0.90, 1.55, 2.20, 2.60, 3.50, 4.50, 6.80], "EV_L1_VultoParado": [0.15, 0.60, 1.20, 1.70, 2.60]}[EVENTO]
LVL = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
U32 = ctypes.windll.user32
_HW = []

if hasattr(unreal, "_lux_pie_h") and unreal._lux_pie_h is not None:
    try:
        unreal.unregister_slate_post_tick_callback(unreal._lux_pie_h)
    except Exception:
        pass
    unreal._lux_pie_h = None

S = dict(fase="pie", t_wall0=time.time(), frames=[], erros=[], evento=EVENTO, cenario=CEN, fim=False, shots=[], foco=[])
unreal._lux_pie = S


def foco():
    if not _HW:
        pid = os.getpid()

        @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
        def cb(h, _l):
            p = wt.DWORD()
            U32.GetWindowThreadProcessId(h, ctypes.byref(p))
            if p.value == pid and U32.IsWindowVisible(h) and U32.GetWindowTextLengthW(h) > 0:
                buf = ctypes.create_unicode_buffer(256)
                U32.GetWindowTextW(h, buf, 256)
                if "Unreal Editor" in buf.value:
                    _HW.append(h)
            return True
        U32.EnumWindows(cb, 0)
    if not _HW:
        return False
    h = _HW[0]
    if U32.GetForegroundWindow() != h:
        U32.keybd_event(0x12, 0, 0, 0)
        U32.keybd_event(0x12, 0, 2, 0)
        U32.ShowWindow(h, 9)
        U32.SetForegroundWindow(h)
    return U32.GetForegroundWindow() == h


def fim(motivo):
    S["fim"] = True
    S["motivo"] = motivo
    try:
        if unreal._lux_pie_h is not None:
            unreal.unregister_slate_post_tick_callback(unreal._lux_pie_h)
            unreal._lux_pie_h = None
    except Exception as ex:
        S["erros"].append("unregister: %s" % ex)
    try:
        if LVL.is_in_play_in_editor():
            LVL.editor_request_end_play()
    except Exception as ex:
        S["erros"].append("end_play: %s" % ex)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(S, fh, default=str)


def mundo():
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()


def acha(w):
    todos = unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Actor)
    quer = set((EVENTO, FIGURA, "LOOP_Manager", "LOOP_PortaSala") + LUZES)
    return {a.get_actor_label(): a for a in todos if a.get_actor_label() in quer}


def tick(dt):
    try:
        agora = time.time()
        if agora - S.get("t_foco", 0.0) > 1.0:
            S["t_foco"] = agora
            S["foco"].append(bool(foco()))
        w = mundo()
        if S["fase"] == "pie":
            if agora - S["t_wall0"] > 150:
                return fim("timeout esperando o PIE")
            if not w or not unreal.GameplayStatics.get_player_pawn(w, 0):
                return
            S["t_pie0"] = unreal.GameplayStatics.get_time_seconds(w)
            S["fase"] = "aquecer"
            return
        tg = unreal.GameplayStatics.get_time_seconds(w)
        a = S.get("a")
        if S["fase"] == "aquecer":
            if tg - S["t_pie0"] < 6.0:
                return
            S["a"] = a = acha(w)
            faltam = [k for k in (EVENTO, FIGURA, "LOOP_Manager", "LOOP_PortaSala") + LUZES if k not in a]
            if faltam:
                return fim("atores ausentes no PIE: %s" % faltam)
            S["orig"] = {l: a[l].point_light_component.get_editor_property("intensity") for l in LUZES}
            S["disparo0"] = a[EVENTO].get_editor_property("DisparoT")
            S["loop0"] = a["LOOP_Manager"].get_editor_property("LoopAtual")
            pawn = unreal.GameplayStatics.get_player_pawn(w, 0)
            z = pawn.get_actor_location().z
            # troca REAL de loop: jogador diante da porta da sala (150 cm ao norte), olhando para ela, e Interagir
            pawn.set_actor_location(unreal.Vector(-2294.0, -1827.0, z), False, True)
            unreal.GameplayStatics.get_player_controller(w, 0).set_control_rotation(unreal.Rotator(0, 0, -90))
            S["fase"] = "interagir"
            S["t_f"] = tg
            return
        if S["fase"] == "interagir":
            if tg - S["t_f"] < 1.0:
                return
            pawn = unreal.GameplayStatics.get_player_pawn(w, 0)
            try:
                pawn.call_method("Interact")
                S["interact"] = "ok"
            except Exception as ex:
                S["interact"] = "ERRO %s" % ex
            S["fase"] = "esperar_troca"
            S["t_f"] = tg
            return
        if S["fase"] == "esperar_troca":
            loop = a["LOOP_Manager"].get_editor_property("LoopAtual")
            if tg - S["t_f"] > 20.0:
                return fim("a troca de loop nao aconteceu (LoopAtual=%s, interact=%s)" % (loop, S.get("interact")))
            if loop >= 1:
                S["loop1"] = loop
                S["fase"] = "assentar_troca"
                S["t_f"] = tg
            return
        if S["fase"] == "assentar_troca":
            if tg - S["t_f"] < 5.0:                      # termina a transicao (camera volta aos olhos, libera o input)
                return
            pawn = unreal.GameplayStatics.get_player_pawn(w, 0)
            z = pawn.get_actor_location().z
            pawn.set_actor_location(unreal.Vector(POS[0][0], POS[0][1], z), False, True)
            unreal.GameplayStatics.get_player_controller(w, 0).set_control_rotation(unreal.Rotator(0, 0, POS[1]))
            if V3LUZ:      # SO NO PIE (descartado ao fechar): a LuzPassos na posicao do v3, para comparar a legibilidade
                a["LUX_L1_LuzPassos"].set_actor_location(unreal.Vector(-3300.0, -660.0, 230.0), False, True)
                S["luz_v3"] = True
            S["disparo0"] = a[EVENTO].get_editor_property("DisparoT")
            S["fase"] = "assentar"
            S["t_f"] = tg
            return
        if S["fase"] == "assentar":
            if tg - S["t_f"] < 1.5:
                return
            pawn = unreal.GameplayStatics.get_player_pawn(w, 0)
            loc = pawn.get_actor_location()
            S["jogador"] = [loc.x, loc.y, loc.z]
            unreal.SystemLibrary.execute_console_command(w, "ke * ForcarSe %s" % EVENTO)
            S["fase"] = "gravar"
            S["t_cmd"] = tg
            return
        if S["fase"] == "gravar":
            ev, fig = a[EVENTO], a[FIGURA]
            dT = ev.get_editor_property("DisparoT")
            cam = unreal.GameplayStatics.get_player_camera_manager(w, 0).get_camera_location()
            fl = fig.get_actor_location()
            comp = fig.get_components_by_class(unreal.SkeletalMeshComponent)[0]
            fr = dict(tg=tg, dt=unreal.GameplayStatics.get_world_delta_seconds(w), dT=dT, P=fig.get_editor_property("PAtual"),
                      NSub=fig.get_editor_property("NSub"), ativo=fig.get_editor_property("bAtivo"), x=fl.x, y=fl.y, z=fl.z,
                      yaw=fig.get_actor_rotation().yaw, oculto=comp.get_editor_property("hidden_in_game"),
                      dcam=((fl.x - cam.x) ** 2 + (fl.y - cam.y) ** 2) ** 0.5,
                      luz={l: a[l].point_light_component.get_editor_property("intensity") / S["orig"][l] for l in LUZES})
            if MIRA and dT != S["disparo0"]:           # melhor caso de legibilidade: o jogador olha direto para a figura
                import math
                pw = unreal.GameplayStatics.get_player_pawn(w, 0).get_actor_location()
                ox, oy, oz = pw.x, pw.y, pw.z + 68.0                     # olho ~ capsula 98 + 68 = 166
                dx, dy, dz = fl.x - ox, fl.y - oy, (fl.z + 110.0) - oz
                unreal.GameplayStatics.get_player_controller(w, 0).set_control_rotation(unreal.Rotator(0, math.degrees(math.atan2(dz, math.hypot(dx, dy))), math.degrees(math.atan2(dy, dx))))
            S["frames"].append(fr)
            if dT != S["disparo0"]:
                t = tg - dT
                for alvo in SHOTS:
                    if t >= alvo and alvo not in [s[0] for s in S["shots"]]:
                        nome = "%s/%s_%s_t%03d.png" % (SHOTDIR, EVENTO, CEN, int(round(alvo * 100)))
                        unreal.SystemLibrary.execute_console_command(w, 'HighResShot 1280x720 filename="%s"' % nome)
                        S["shots"].append((alvo, round(t, 3), nome, fr["P"], fr["luz"][LUZES[1]]))
                        break
                if t > 8.0:
                    return fim("ok")
            elif tg - S["t_cmd"] > 4.0:
                return fim("o evento NAO disparou (DisparoT nao mudou em 4 s)")
            if len(S["frames"]) > 6000:
                return fim("quadros demais")
    except Exception:
        S["erros"].append(traceback.format_exc())
        fim("excecao")


unreal._lux_pie_h = unreal.register_slate_post_tick_callback(tick)
LVL.editor_request_begin_play()
print("PIE pedido; resultado em", OUT)
